"""Unit tests for ScriptAnalyser."""

import json
from pathlib import Path

from analysers import ScriptAnalyser
from reporting import ScriptReporter


def _make_meta(cs_path: Path, guid: str) -> None:
    meta_path = Path(str(cs_path) + ".meta")
    meta_path.write_text(f"fileFormatVersion: 2\nguid: {guid}\n", encoding="utf-8")


def _make_script(path: Path, content: str, guid: str | None = "abc123") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if guid is not None:
        _make_meta(path, guid)


class TestScriptAnalyserGuids:
    def test_guid_resolution(self, tmp_path: Path):
        cs_file = tmp_path / "Assets" / "Foo" / "Bar.cs"
        _make_script(cs_file, "namespace Foo;\n", guid="myguid123")

        asmdef_dict = {
            "GUID:asm1": {
                "name": "Foo",
                "rootNamespace": "Foo",
                "references": [],
                "relativePath": "Assets/Foo",
            }
        }

        result = ScriptAnalyser(asmdef_dict, tmp_path).analyse()

        assert "GUID:myguid123" in result["scripts"]
        entry = result["scripts"]["GUID:myguid123"]
        assert entry["name"] == "Bar"

    def test_missing_meta_counted_and_excluded(self, tmp_path: Path):
        cs_file = tmp_path / "Foo.cs"
        cs_file.write_text("namespace Foo;\n", encoding="utf-8")
        # Intentionally no .meta sidecar.

        result = ScriptAnalyser({}, tmp_path).analyse()

        assert result["stats"]["scripts_without_meta"] == 1
        assert len(result["scripts"]) == 0
        assert cs_file in result["scripts_without_meta"]


class TestScriptAnalyserNamespaces:
    def test_file_scoped_namespace(self, tmp_path: Path):
        _make_script(tmp_path / "A.cs", "namespace Modern;\nclass C {}", "g1")

        result = ScriptAnalyser({}, tmp_path).analyse()

        assert result["scripts"]["GUID:g1"]["namespace"] == "Modern"

    def test_traditional_namespace(self, tmp_path: Path):
        _make_script(tmp_path / "A.cs", "namespace Trad\n{\nclass C {}\n}\n", "g1")

        result = ScriptAnalyser({}, tmp_path).analyse()

        assert result["scripts"]["GUID:g1"]["namespace"] == "Trad"

    def test_missing_namespace(self, tmp_path: Path):
        _make_script(tmp_path / "A.cs", "class C {}", "g1")

        result = ScriptAnalyser({}, tmp_path).analyse()

        assert result["scripts"]["GUID:g1"]["namespace"] is None
        assert result["stats"]["scripts_without_namespace"] == 1


class TestScriptAnalyserImports:
    def _imports(self, tmp_path: Path, content: str) -> list[str]:
        _make_script(tmp_path / "A.cs", content, "g1")
        result = ScriptAnalyser({}, tmp_path).analyse()
        return result["scripts"]["GUID:g1"]["imports"]

    def test_plain_using(self, tmp_path: Path):
        assert self._imports(tmp_path, "using System;\n") == ["System"]

    def test_global_using(self, tmp_path: Path):
        assert self._imports(tmp_path, "global using System.Linq;\n") == ["System.Linq"]

    def test_static_using(self, tmp_path: Path):
        assert self._imports(tmp_path, "using static System.Math;\n") == ["System.Math"]

    def test_generic_alias_excluded(self, tmp_path: Path):
        content = "using L = System.Collections.Generic.List<int>;\n"
        assert self._imports(tmp_path, content) == []

    def test_deduplicated_and_sorted(self, tmp_path: Path):
        content = "using System;\nusing UnityEngine;\nusing System;\n"
        assert self._imports(tmp_path, content) == ["System", "UnityEngine"]

    def test_using_inside_block_comment_currently_captured(self, tmp_path: Path):
        # Documents current behaviour: block /* ... */ comments are not stripped.
        # If this changes intentionally in future, update both the analyser
        # docstring and this assertion.
        content = "/*\nusing System;\n*/\n"
        assert self._imports(tmp_path, content) == ["System"]


class TestScriptAnalyserOwnership:
    def test_assembly_resolution(self, tmp_path: Path):
        cs_file = tmp_path / "Assets" / "Foo" / "Bar.cs"
        _make_script(cs_file, "namespace Foo;\n", "g1")
        asmdef_dict = {
            "GUID:asm1": {
                "name": "Foo",
                "rootNamespace": "Foo",
                "references": [],
                "relativePath": "Assets/Foo",
            }
        }

        result = ScriptAnalyser(asmdef_dict, tmp_path).analyse()

        assert result["scripts"]["GUID:g1"]["assembly"] == "GUID:asm1"

    def test_orphaned_script(self, tmp_path: Path):
        _make_script(tmp_path / "Orphan.cs", "namespace X;\n", "g1")

        result = ScriptAnalyser({}, tmp_path).analyse()

        assert result["scripts"]["GUID:g1"]["assembly"] is None
        assert result["stats"]["orphaned_scripts"] == 1


class TestScriptAnalyserFilters:
    def test_filter_paths_excludes_subtree(self, tmp_path: Path):
        included = tmp_path / "Assets" / "Foo.cs"
        excluded = tmp_path / "Library" / "PackageCache" / "Bar.cs"
        _make_script(included, "namespace A;\n", "g_inc")
        _make_script(excluded, "namespace B;\n", "g_exc")

        result = ScriptAnalyser(
            {}, tmp_path, filter_paths=["Library/PackageCache"]
        ).analyse()

        guids = set(result["scripts"].keys())
        assert "GUID:g_inc" in guids
        assert "GUID:g_exc" not in guids


class TestScriptAnalyserSortingStability:
    def test_json_output_is_byte_stable(self, tmp_path: Path):
        _make_script(tmp_path / "B.cs", "namespace B;\nusing System;\n", "g2")
        _make_script(tmp_path / "A.cs", "namespace A;\nusing UnityEngine;\n", "g1")

        reporter = ScriptReporter(root_path=tmp_path)
        first = json.dumps(
            reporter.generate_json_report(ScriptAnalyser({}, tmp_path).analyse()),
            indent=2,
        )
        second = json.dumps(
            reporter.generate_json_report(ScriptAnalyser({}, tmp_path).analyse()),
            indent=2,
        )

        assert first == second
