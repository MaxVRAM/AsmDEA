"""Unit tests for PrefabAnalyser."""

import json
from pathlib import Path

from analysers import PrefabAnalyser
from reporting import PrefabReporter

# 32-hex GUIDs (m_Script / m_SourcePrefab references require 32 hex chars).
CHILD_GUID = "a" * 32
PARENT_GUID = "b" * 32
SCRIPT_GUID = "c" * 32
UNRESOLVED_SCRIPT_GUID = "d" * 32

SCRIPT_REPORT = {
    "scripts": {
        "GUID:"
        + SCRIPT_GUID: {
            "name": "MyComponent",
            "namespace": "My.NS",
            "assembly": "GUID:asm1",
        }
    }
}

CHILD_PREFAB = f"""%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!1 &100
GameObject:
  m_Component:
  - component: {{fileID: 200}}
  - component: {{fileID: 300}}
  m_Name: Child
--- !u!4 &200
Transform:
  m_GameObject: {{fileID: 100}}
  m_Children: []
  m_Father: {{fileID: 0}}
--- !u!114 &300
MonoBehaviour:
  m_GameObject: {{fileID: 100}}
  m_Script: {{fileID: 11500000, guid: {SCRIPT_GUID}, type: 3}}
"""

PARENT_PREFAB = f"""%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!1 &1
GameObject:
  m_Component:
  - component: {{fileID: 2}}
  - component: {{fileID: 3}}
  m_Name: Parent
--- !u!4 &2
Transform:
  m_GameObject: {{fileID: 1}}
  m_Children:
  - {{fileID: 5}}
  m_Father: {{fileID: 0}}
--- !u!114 &3
MonoBehaviour:
  m_GameObject: {{fileID: 1}}
  m_Script: {{fileID: 11500000, guid: {UNRESOLVED_SCRIPT_GUID}, type: 3}}
--- !u!1001 &4
PrefabInstance:
  m_Modification:
    m_TransformParent: {{fileID: 2}}
    m_Modifications:
    - target: {{fileID: 999, guid: {CHILD_GUID}, type: 3}}
      propertyPath: m_Name
      value: ChildInstance
      objectReference: {{fileID: 0}}
  m_SourcePrefab: {{fileID: 100100000, guid: {CHILD_GUID}, type: 3}}
--- !u!4 &5 stripped
Transform:
  m_CorrespondingSourceObject: {{fileID: 999, guid: {CHILD_GUID}, type: 3}}
  m_PrefabInstance: {{fileID: 4}}
"""


def _make_prefab(path: Path, content: str, guid: str | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if guid is not None:
        meta = Path(str(path) + ".meta")
        meta.write_text(f"fileFormatVersion: 2\nguid: {guid}\n", encoding="utf-8")


def _standard_project(tmp_path: Path) -> Path:
    _make_prefab(tmp_path / "Child.prefab", CHILD_PREFAB, CHILD_GUID)
    _make_prefab(tmp_path / "Parent.prefab", PARENT_PREFAB, PARENT_GUID)
    return tmp_path


class TestPrefabAnalyserBasics:
    def test_guid_keys_and_names(self, tmp_path: Path):
        result = PrefabAnalyser({}, _standard_project(tmp_path)).analyse()
        prefabs = result["prefabs"]
        assert "GUID:" + CHILD_GUID in prefabs
        assert "GUID:" + PARENT_GUID in prefabs
        assert prefabs["GUID:" + CHILD_GUID]["name"] == "Child"

    def test_root_object_and_game_object_count(self, tmp_path: Path):
        result = PrefabAnalyser({}, _standard_project(tmp_path)).analyse()
        child = result["prefabs"]["GUID:" + CHILD_GUID]
        parent = result["prefabs"]["GUID:" + PARENT_GUID]
        assert child["root_object"] == "Child"
        assert child["game_object_count"] == 1
        assert parent["root_object"] == "Parent"
        assert parent["game_object_count"] == 1

    def test_missing_meta_counted_and_excluded(self, tmp_path: Path):
        _make_prefab(tmp_path / "NoMeta.prefab", CHILD_PREFAB, guid=None)
        result = PrefabAnalyser({}, tmp_path).analyse()
        assert result["stats"]["prefabs_without_meta"] == 1
        assert len(result["prefabs"]) == 0
        assert (tmp_path / "NoMeta.prefab") in result["prefabs_without_meta"]


class TestPrefabAnalyserScripts:
    def test_resolved_script(self, tmp_path: Path):
        result = PrefabAnalyser(
            {}, _standard_project(tmp_path), script_report=SCRIPT_REPORT
        ).analyse()
        scripts = result["prefabs"]["GUID:" + CHILD_GUID]["scripts"]
        assert len(scripts) == 1
        s = scripts[0]
        assert s["guid"] == "GUID:" + SCRIPT_GUID
        assert s["name"] == "MyComponent"
        assert s["namespace"] == "My.NS"
        assert s["assembly"] == "GUID:asm1"
        assert s["resolved"] is True
        assert s["instances"] == ["Child"]

    def test_unresolved_script(self, tmp_path: Path):
        result = PrefabAnalyser(
            {}, _standard_project(tmp_path), script_report=SCRIPT_REPORT
        ).analyse()
        scripts = result["prefabs"]["GUID:" + PARENT_GUID]["scripts"]
        assert len(scripts) == 1
        assert scripts[0]["guid"] == "GUID:" + UNRESOLVED_SCRIPT_GUID
        assert scripts[0]["resolved"] is False
        assert scripts[0]["name"] is None
        assert result["stats"]["unresolved_script_refs"] == 1

    def test_referenced_assemblies(self, tmp_path: Path):
        result = PrefabAnalyser(
            {}, _standard_project(tmp_path), script_report=SCRIPT_REPORT
        ).analyse()
        child = result["prefabs"]["GUID:" + CHILD_GUID]
        assert child["referenced_assemblies"] == ["GUID:asm1"]


class TestPrefabAnalyserEdges:
    def test_child_prefab_reference(self, tmp_path: Path):
        result = PrefabAnalyser({}, _standard_project(tmp_path)).analyse()
        parent = result["prefabs"]["GUID:" + PARENT_GUID]
        children = parent["child_prefabs"]
        assert len(children) == 1
        # m_SourcePrefab appears once even though the guid is repeated in
        # m_Modifications and the stripped Transform block.
        assert children[0]["count"] == 1
        assert children[0]["guid"] == "GUID:" + CHILD_GUID
        assert children[0]["name"] == "Child"
        assert result["stats"]["nested_prefab_edges"] == 1

    def test_parent_prefab_reverse_edge(self, tmp_path: Path):
        result = PrefabAnalyser({}, _standard_project(tmp_path)).analyse()
        child = result["prefabs"]["GUID:" + CHILD_GUID]
        parents = child["parent_prefabs"]
        assert len(parents) == 1
        assert parents[0]["guid"] == "GUID:" + PARENT_GUID
        assert parents[0]["name"] == "Parent"
        # Child has no nested prefabs of its own.
        assert child["child_prefabs"] == []


class TestPrefabAnalyserFilters:
    def test_filter_paths_excludes_subtree(self, tmp_path: Path):
        _make_prefab(tmp_path / "Assets" / "Keep.prefab", CHILD_PREFAB, CHILD_GUID)
        _make_prefab(
            tmp_path / "Library" / "PackageCache" / "Drop.prefab",
            PARENT_PREFAB,
            PARENT_GUID,
        )
        result = PrefabAnalyser({}, tmp_path, filter_paths=["Library/PackageCache"]).analyse()
        guids = set(result["prefabs"].keys())
        assert "GUID:" + CHILD_GUID in guids
        assert "GUID:" + PARENT_GUID not in guids


class TestPrefabAnalyserSortingStability:
    def test_json_output_is_byte_stable(self, tmp_path: Path):
        _standard_project(tmp_path)
        reporter = PrefabReporter(root_path=tmp_path)
        first = json.dumps(
            reporter.generate_json_report(
                PrefabAnalyser({}, tmp_path, script_report=SCRIPT_REPORT).analyse()
            ),
            indent=2,
        )
        second = json.dumps(
            reporter.generate_json_report(
                PrefabAnalyser({}, tmp_path, script_report=SCRIPT_REPORT).analyse()
            ),
            indent=2,
        )
        assert first == second
