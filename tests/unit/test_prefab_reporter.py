"""Unit tests for PrefabReporter."""

from pathlib import Path

from analysers import PrefabAnalyser
from reporting import PrefabReporter
from tests.unit.test_prefab_analyser import (
    CHILD_GUID,
    PARENT_GUID,
    SCRIPT_GUID,
    SCRIPT_REPORT,
    _standard_project,
)


def _report(tmp_path: Path) -> dict:
    result = PrefabAnalyser({}, _standard_project(tmp_path), script_report=SCRIPT_REPORT).analyse()
    return PrefabReporter(root_path=tmp_path).generate_json_report(result)


class TestPrefabReporterJson:
    def test_summary_shape(self, tmp_path: Path):
        report = _report(tmp_path)
        summary = report["summary"]
        assert summary["totalPrefabs"] == 2
        assert summary["prefabsWithScripts"] == 2
        assert summary["prefabsWithNested"] == 1
        assert summary["nestedPrefabEdges"] == 1
        assert summary["unresolvedScriptRefs"] == 1

    def test_prefab_entry_shape(self, tmp_path: Path):
        report = _report(tmp_path)
        child = report["prefabs"]["GUID:" + CHILD_GUID]
        assert child["name"] == "Child"
        assert child["relativePath"] == "Child.prefab"
        assert child["rootObject"] == "Child"
        assert child["gameObjectCount"] == 1
        assert child["scriptCount"] == 1
        assert child["scripts"][0]["guid"] == "GUID:" + SCRIPT_GUID
        assert child["referencedAssemblies"] == ["GUID:asm1"]

    def test_child_and_parent_paths_formatted(self, tmp_path: Path):
        report = _report(tmp_path)
        parent = report["prefabs"]["GUID:" + PARENT_GUID]
        child = report["prefabs"]["GUID:" + CHILD_GUID]
        assert parent["childPrefabs"][0]["relativePath"] == "Child.prefab"
        assert child["parentPrefabs"][0]["relativePath"] == "Parent.prefab"

    def test_prefabs_are_guid_sorted(self, tmp_path: Path):
        report = _report(tmp_path)
        keys = list(report["prefabs"].keys())
        assert keys == sorted(keys)


class TestPrefabReporterConsole:
    def test_console_report_runs(self, tmp_path: Path):
        result = PrefabAnalyser(
            {}, _standard_project(tmp_path), script_report=SCRIPT_REPORT
        ).analyse()
        # Should not raise.
        PrefabReporter(root_path=tmp_path).print_console_report(result)
