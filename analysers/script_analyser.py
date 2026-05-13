"""Script-first analyser - produces a per-script view of the Unity project.

Walks the project for .cs files and produces a GUID-keyed dictionary with
per-script metadata: name, path, namespace, imports, and owning assembly.

Key classes:
    - ScriptAnalyser: Per-script metadata extractor

Features:
    - Reads script GUID from sidecar .cs.meta files
    - Extracts namespace declarations (delegates to NamespaceAnalyser)
    - Parses ``using`` directives (global, static, alias-to-namespace)
    - Resolves owning assembly via FileAnalyser composition
    - Respects ``filter_paths`` to skip whole subtrees (e.g. Library/PackageCache)

Usage:
    from analysers import ScriptAnalyser

    analyser = ScriptAnalyser(asmdef_dict, root_path, filter_paths=[...])
    result = analyser.analyse()
"""

import re
from pathlib import Path
from typing import Any

from common.dictionary import extract_guid_from_meta

from .file_analyser import FileAnalyser
from .namespace_analyser import NamespaceAnalyser

# Matches:
#   using System;
#   global using System.Linq;
#   using static System.Math;
#   using Alias = System.Collections.Generic;   (alias to namespace)
# Does NOT match (intentional):
#   using L = System.Collections.Generic.List<int>;   (generic alias target)
_USING_RE = re.compile(
    r"^\s*(?:global\s+)?using\s+(?:static\s+)?"
    r"(?:[\w@]+\s*=\s*)?"
    r"([\w\.]+)\s*;"
)


class ScriptAnalyser:
    """Build a per-script metadata view of the project."""

    def __init__(
        self,
        asmdef_dict: dict[str, Any],
        root_path: Path,
        filter_paths: list[str] | None = None,
    ):
        """Initialise script analyser.

        Args:
            asmdef_dict: Dictionary of assembly definitions
            root_path: Root directory path (typically the Unity Assets folder)
            filter_paths: Relative path prefixes to exclude from scanning entirely
        """
        self.asmdef_dict = asmdef_dict
        self.root_path = Path(root_path).resolve()
        # Compose a FileAnalyser to avoid re-implementing the project walk and
        # owning-assembly resolution.
        self._file_analyser = FileAnalyser(asmdef_dict, root_path, filter_paths=filter_paths)

    @staticmethod
    def _extract_imports(file_path: Path) -> list[str]:
        """Parse ``using`` directives from a C# source file.

        Captures plain, ``global``, and ``static`` usings, plus alias-to-namespace
        forms. Aliases to generic types are intentionally skipped (the regex won't
        match across ``<``). Block ``/* ... */`` comments are not stripped, so a
        ``using`` line inside a block comment will be captured — acceptable for
        a static-analysis tool.

        Returns:
            Sorted list of unique namespace strings.
        """
        imports: set[str] = set()

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return []

        for raw in content.split("\n"):
            comment_pos = raw.find("//")
            line = raw[:comment_pos] if comment_pos >= 0 else raw
            if not line.strip():
                continue
            match = _USING_RE.match(line)
            if match:
                imports.add(match.group(1))

        return sorted(imports)

    @staticmethod
    def _read_script_guid(cs_path: Path) -> str | None:
        """Look up the sidecar ``<cs_path>.meta`` and extract its GUID."""
        meta_path = Path(str(cs_path) + ".meta")
        if not meta_path.exists():
            return None
        return extract_guid_from_meta(meta_path)

    def analyse(self) -> dict[str, Any]:
        """Produce per-script metadata for every ``.cs`` file in the project.

        Returns:
            Dictionary with the following structure::

                {
                    "scripts": {GUID: {name, path, namespace, imports, assembly}},
                    "stats": {...},
                    "scripts_without_meta": [Path, ...],
                }

            ``path`` is the absolute path to the .cs file; the reporter applies
            ``filepath_type`` formatting at JSON-generation time.
        """
        scripts: dict[str, dict[str, Any]] = {}
        scripts_without_meta: list[Path] = []
        total_imports = 0
        unique_namespaces: set[str] = set()
        no_namespace = 0
        orphaned = 0

        for cs_file in self._file_analyser._iter_cs_files():
            guid = self._read_script_guid(cs_file)
            if guid is None:
                scripts_without_meta.append(cs_file)
                continue

            namespaces = NamespaceAnalyser.extract_namespace_from_file(cs_file)
            namespace = namespaces[0] if namespaces else None
            if namespace is None:
                no_namespace += 1

            imports = self._extract_imports(cs_file)
            total_imports += len(imports)
            unique_namespaces.update(imports)

            assembly = self._file_analyser.find_owning_assembly(cs_file)
            if assembly is None:
                orphaned += 1

            scripts[guid] = {
                "name": cs_file.stem,
                "path": cs_file,
                "namespace": namespace,
                "imports": imports,
                "assembly": assembly,
            }

        stats = {
            "total_scripts": len(scripts) + len(scripts_without_meta),
            "scripts_with_namespace": len(scripts) - no_namespace,
            "scripts_without_namespace": no_namespace,
            "scripts_without_meta": len(scripts_without_meta),
            "orphaned_scripts": orphaned,
            "total_imports": total_imports,
            "unique_namespaces_imported": len(unique_namespaces),
        }

        return {
            "scripts": scripts,
            "stats": stats,
            "scripts_without_meta": scripts_without_meta,
        }
