"""Prefab-first analyser - produces a per-prefab view of the Unity project.

Walks the project for ``.prefab`` files and produces a GUID-keyed dictionary
with per-prefab metadata: name, path, GameObject hierarchy, attached component
scripts, and nested (child) / referencing (parent) prefabs.

Key classes:
    - PrefabAnalyser: Per-prefab metadata extractor

Features:
    - Reads prefab GUID from sidecar .prefab.meta files
    - Parses Unity's multi-document YAML with regex (no PyYAML dependency)
    - Extracts attached component scripts (m_Script, type 3) with hierarchy paths
    - Extracts nested/child prefab references (m_SourcePrefab, type 3)
    - Computes reverse (parent) prefab edges across the whole scan
    - Resolves script GUIDs against script_report.json (name/namespace/assembly)
    - Respects ``filter_paths`` to skip whole subtrees (e.g. Library/PackageCache)

Usage:
    from analysers import PrefabAnalyser

    analyser = PrefabAnalyser(asmdef_dict, root_path, script_report=script_report)
    result = analyser.analyse()
"""

import re
from pathlib import Path
from typing import Any

from common.dictionary import extract_guid_from_meta

from .file_analyser import FileAnalyser

# Unity YAML block header, e.g. ``--- !u!114 &1234567890 stripped``.
# Object anchor ids (``&``) can be negative.
_BLOCK_HEADER_RE = re.compile(r"^--- !u!(\d+) &(-?\d+)(.*)$", re.MULTILINE)

# MonoBehaviour script reference. type:3 is a MonoScript (.cs asset); type 2 is a
# material/ScriptableObject and type 0 a built-in - only type 3 is a component script.
_MONOSCRIPT_RE = re.compile(
    r"m_Script:\s*\{\s*fileID:\s*-?\d+\s*,\s*guid:\s*([0-9a-fA-F]{32})\s*,\s*type:\s*3\s*\}"
)
# Nested/child prefab reference. One per PrefabInstance block; the same guid is
# repeated in m_Modifications/stripped blocks, so matching m_SourcePrefab only
# gives an exact per-instance count.
_SOURCE_PREFAB_RE = re.compile(
    r"m_SourcePrefab:\s*\{\s*fileID:\s*-?\d+\s*,\s*guid:\s*([0-9a-fA-F]{32})\s*,\s*type:\s*3\s*\}"
)
_GAMEOBJECT_REF_RE = re.compile(r"m_GameObject:\s*\{\s*fileID:\s*(-?\d+)\s*\}")
_FATHER_RE = re.compile(r"m_Father:\s*\{\s*fileID:\s*(-?\d+)\s*\}")
_NAME_RE = re.compile(r"^\s{2}m_Name:\s*(.*)$", re.MULTILINE)
_COMPONENT_RE = re.compile(r"-\s*component:\s*\{\s*fileID:\s*(-?\d+)\s*\}")

_TYPE_GAMEOBJECT = 1
_TYPE_TRANSFORM = 4
_TYPE_RECT_TRANSFORM = 224
_TYPE_MONOBEHAVIOUR = 114


def _bare_guid(guid: str) -> str:
    """Return the lowercase 32-hex form of a GUID, stripping a ``GUID:`` prefix."""
    if guid.startswith("GUID:"):
        guid = guid[len("GUID:") :]
    return guid.lower()


class PrefabAnalyser:
    """Build a per-prefab metadata view of the project."""

    def __init__(
        self,
        asmdef_dict: dict[str, Any],
        root_path: Path,
        filter_paths: list[str] | None = None,
        script_report: dict[str, Any] | None = None,
    ):
        """Initialise prefab analyser.

        Args:
            asmdef_dict: Dictionary of assembly definitions
            root_path: Root directory path (typically the Unity Assets folder)
            filter_paths: Relative path prefixes to exclude from scanning entirely
            script_report: Parsed ``script_report.json`` used to resolve script
                GUIDs to name/namespace/owning-assembly. When ``None``, script
                references are reported unresolved.
        """
        self.asmdef_dict = asmdef_dict
        self.root_path = Path(root_path).resolve()
        # Compose a FileAnalyser to reuse the project walk + owning-assembly resolution.
        self._file_analyser = FileAnalyser(asmdef_dict, root_path, filter_paths=filter_paths)

        # Index script metadata by bare guid for O(1) resolution.
        self._script_index: dict[str, dict[str, Any]] = {}
        for key, entry in (script_report or {}).get("scripts", {}).items():
            if isinstance(entry, dict):
                self._script_index[_bare_guid(key)] = entry

    @staticmethod
    def _read_prefab_guid(prefab_path: Path) -> str | None:
        """Look up the sidecar ``<prefab_path>.meta`` and extract its GUID."""
        meta_path = Path(str(prefab_path) + ".meta")
        if not meta_path.exists():
            return None
        return extract_guid_from_meta(meta_path)

    @staticmethod
    def _parse_blocks(text: str) -> list[dict[str, Any]]:
        """Split the prefab YAML into per-object blocks keyed by type and anchor."""
        blocks: list[dict[str, Any]] = []
        headers = list(_BLOCK_HEADER_RE.finditer(text))
        for i, h in enumerate(headers):
            start = h.end()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
            blocks.append(
                {
                    "type_id": int(h.group(1)),
                    "file_id": h.group(2),
                    "body": text[start:end],
                }
            )
        return blocks

    @classmethod
    def _parse_hierarchy(cls, text: str) -> dict[str, Any]:
        """Build lookup maps for GameObjects, Transforms and MonoBehaviours.

        Returns a dict with ``game_objects`` (fileID -> {name, transform_id}),
        ``transforms`` (fileID -> {game_object_id, parent_id}) and
        ``mono_behaviours`` (list of {game_object_id, script_guid}).
        """
        transforms: dict[str, dict[str, Any]] = {}
        transforms_by_go: dict[str, str] = {}
        raw_game_objects: dict[str, dict[str, Any]] = {}
        mono_behaviours: list[dict[str, Any]] = []

        for b in cls._parse_blocks(text):
            body = b["body"]
            type_id = b["type_id"]
            if type_id in (_TYPE_TRANSFORM, _TYPE_RECT_TRANSFORM):
                go = _GAMEOBJECT_REF_RE.search(body)
                father = _FATHER_RE.search(body)
                go_id = go.group(1) if go else None
                transforms[b["file_id"]] = {
                    "game_object_id": go_id,
                    "parent_id": father.group(1) if father else None,
                }
                if go_id:
                    transforms_by_go[go_id] = b["file_id"]
            elif type_id == _TYPE_GAMEOBJECT:
                name = _NAME_RE.search(body)
                components = [m.group(1) for m in _COMPONENT_RE.finditer(body)]
                raw_game_objects[b["file_id"]] = {
                    "name": name.group(1).strip() if name else "",
                    "component_ids": components,
                }
            elif type_id == _TYPE_MONOBEHAVIOUR:
                script = _MONOSCRIPT_RE.search(body)
                if script:
                    go = _GAMEOBJECT_REF_RE.search(body)
                    mono_behaviours.append(
                        {
                            "game_object_id": go.group(1) if go else None,
                            "script_guid": script.group(1).lower(),
                        }
                    )

        game_objects: dict[str, dict[str, Any]] = {}
        for go_id, info in raw_game_objects.items():
            transform_id = transforms_by_go.get(go_id)
            if not transform_id:
                # Fallback: a listed component that resolved to a Transform block.
                for comp_id in info["component_ids"]:
                    if comp_id in transforms:
                        transform_id = comp_id
                        break
            game_objects[go_id] = {"name": info["name"], "transform_id": transform_id}

        return {
            "game_objects": game_objects,
            "transforms": transforms,
            "mono_behaviours": mono_behaviours,
        }

    @staticmethod
    def _build_hierarchy_path(go_id: str | None, hierarchy: dict[str, Any]) -> str | None:
        """Walk parent Transforms to build a ``Root/Child/Leaf`` path string."""
        if not go_id or go_id == "0":
            return None
        game_objects = hierarchy["game_objects"]
        transforms = hierarchy["transforms"]
        go = game_objects.get(go_id)
        if not go:
            return None

        segments = [go["name"] or "(unnamed)"]
        visited = {go_id}
        transform_id = go.get("transform_id")
        while transform_id and transform_id != "0":
            t = transforms.get(transform_id)
            if not t:
                break
            parent_id = t.get("parent_id")
            if not parent_id or parent_id == "0":
                break
            parent_t = transforms.get(parent_id)
            if not parent_t or not parent_t.get("game_object_id"):
                break
            parent_go_id = parent_t["game_object_id"]
            if parent_go_id in visited:
                break
            visited.add(parent_go_id)
            parent_go = game_objects.get(parent_go_id)
            segments.append(parent_go["name"] if parent_go and parent_go["name"] else "(unnamed)")
            transform_id = parent_id

        return "/".join(reversed(segments))

    @staticmethod
    def _find_root_object(hierarchy: dict[str, Any]) -> str | None:
        """Return the name of the root GameObject (Transform with m_Father fileID 0)."""
        for t in hierarchy["transforms"].values():
            parent_id = t.get("parent_id")
            if (parent_id is None or parent_id == "0") and t.get("game_object_id"):
                go = hierarchy["game_objects"].get(t["game_object_id"])
                if go:
                    return go["name"] or "(unnamed)"
        return None

    def _extract_prefab(self, prefab_path: Path, guid: str) -> dict[str, Any]:
        """Parse a single ``.prefab`` file into raw (pre-resolution) metadata."""
        try:
            text = prefab_path.read_text(encoding="utf-8-sig")
        except Exception:
            text = ""

        hierarchy = self._parse_hierarchy(text)

        # Aggregate script references by guid, keeping instance hierarchy paths.
        scripts: dict[str, dict[str, Any]] = {}
        for mb in hierarchy["mono_behaviours"]:
            sguid = mb["script_guid"]
            entry = scripts.setdefault(sguid, {"count": 0, "instances": []})
            entry["count"] += 1
            path = self._build_hierarchy_path(mb["game_object_id"], hierarchy) or "(unknown)"
            entry["instances"].append(path)

        # Aggregate child prefab references by guid (one m_SourcePrefab per instance).
        child_counts: dict[str, int] = {}
        for m in _SOURCE_PREFAB_RE.finditer(text):
            cguid = m.group(1).lower()
            child_counts[cguid] = child_counts.get(cguid, 0) + 1

        return {
            "guid": guid,
            "name": prefab_path.stem,
            "path": prefab_path,
            "root_object": self._find_root_object(hierarchy),
            "game_object_count": len(hierarchy["game_objects"]),
            "assembly": self._file_analyser.find_owning_assembly(prefab_path),
            "scripts_raw": scripts,
            "child_counts": child_counts,
        }

    def analyse(self) -> dict[str, Any]:
        """Produce per-prefab metadata for every ``.prefab`` file in the project.

        Returns:
            Dictionary with the following structure::

                {
                    "prefabs": {GUID: {name, path, rootObject, gameObjectCount,
                                       assembly, scripts, childPrefabs,
                                       parentPrefabs, referencedAssemblies}},
                    "stats": {...},
                    "prefabs_without_meta": [Path, ...],
                }

            ``path`` is the absolute path to the .prefab file; the reporter
            applies ``filepath_type`` formatting at JSON-generation time.
        """
        prefabs_without_meta: list[Path] = []
        raw: dict[str, dict[str, Any]] = {}

        # Pass 1: parse every prefab into raw metadata keyed by its own GUID.
        for prefab_file in self._file_analyser._iter_files_by_suffix(".prefab"):
            guid = self._read_prefab_guid(prefab_file)
            if guid is None:
                prefabs_without_meta.append(prefab_file)
                continue
            raw[guid] = self._extract_prefab(prefab_file, guid)

        # Index prefabs by bare guid so raw child guids can be resolved.
        by_bare: dict[str, str] = {_bare_guid(g): g for g in raw}

        # Pass 2: resolve child guids, compute reverse (parent) edges, resolve scripts.
        parents: dict[str, list[dict[str, Any]]] = {g: [] for g in raw}
        prefabs: dict[str, dict[str, Any]] = {}

        total_script_refs = 0
        unique_scripts: set[str] = set()
        unresolved_script_refs = 0
        nested_edges = 0
        with_scripts = 0
        with_nested = 0

        for guid, data in raw.items():
            # Resolve scripts against script_report.
            scripts_out: list[dict[str, Any]] = []
            referenced_assemblies: set[str] = set()
            for sguid, sinfo in data["scripts_raw"].items():
                unique_scripts.add(sguid)
                total_script_refs += sinfo["count"]
                meta = self._script_index.get(sguid)
                if meta:
                    if meta.get("assembly"):
                        referenced_assemblies.add(meta["assembly"])
                    scripts_out.append(
                        {
                            "guid": "GUID:" + sguid,
                            "name": meta.get("name"),
                            "namespace": meta.get("namespace"),
                            "assembly": meta.get("assembly"),
                            "count": sinfo["count"],
                            "instances": sorted(sinfo["instances"]),
                            "resolved": True,
                        }
                    )
                else:
                    unresolved_script_refs += sinfo["count"]
                    scripts_out.append(
                        {
                            "guid": "GUID:" + sguid,
                            "name": None,
                            "namespace": None,
                            "assembly": None,
                            "count": sinfo["count"],
                            "instances": sorted(sinfo["instances"]),
                            "resolved": False,
                        }
                    )
            if scripts_out:
                with_scripts += 1

            # Resolve child prefabs and register the reverse edge on the child.
            children: list[dict[str, Any]] = []
            for cbare, count in data["child_counts"].items():
                nested_edges += count
                child_key = by_bare.get(cbare)
                child = {
                    "guid": "GUID:" + cbare,
                    "name": raw[child_key]["name"] if child_key else None,
                    "path": raw[child_key]["path"] if child_key else None,
                    "count": count,
                }
                children.append(child)
                if child_key:
                    parents[child_key].append(
                        {"guid": guid, "name": data["name"], "path": data["path"]}
                    )
            if children:
                with_nested += 1

            prefabs[guid] = {
                "name": data["name"],
                "path": data["path"],
                "root_object": data["root_object"],
                "game_object_count": data["game_object_count"],
                "assembly": data["assembly"],
                "scripts": scripts_out,
                "child_prefabs": children,
                "referenced_assemblies": sorted(referenced_assemblies),
            }

        # Attach the reverse (parent) edges computed above.
        for guid, plist in parents.items():
            prefabs[guid]["parent_prefabs"] = plist

        stats = {
            "total_prefabs": len(prefabs) + len(prefabs_without_meta),
            "prefabs_without_meta": len(prefabs_without_meta),
            "prefabs_with_scripts": with_scripts,
            "prefabs_with_nested": with_nested,
            "total_script_refs": total_script_refs,
            "unique_scripts_referenced": len(unique_scripts),
            "unresolved_script_refs": unresolved_script_refs,
            "nested_prefab_edges": nested_edges,
        }

        return {
            "prefabs": prefabs,
            "stats": stats,
            "prefabs_without_meta": prefabs_without_meta,
        }
