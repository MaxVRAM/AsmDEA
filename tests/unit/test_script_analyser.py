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


class TestScriptAnalyserExternalImports:
    """Tests for _is_internal_namespace and external_imports tracking."""

    _ROOT = "OPT.CUAS.Audio"

    def _make_analyser(self, root_namespaces: list[str]) -> ScriptAnalyser:
        asmdef_dict = {
            f"GUID:asm{i}": {"name": f"Asm{i}", "rootNamespace": ns, "references": [], "relativePath": f"Assets/Asm{i}"}
            for i, ns in enumerate(root_namespaces)
        }
        return ScriptAnalyser(asmdef_dict, Path("/fake"))

    def test_exact_match_is_internal(self):
        analyser = self._make_analyser([self._ROOT])
        assert analyser._is_internal_namespace("OPT.CUAS.Audio") is True

    def test_dotted_descendant_is_internal(self):
        analyser = self._make_analyser([self._ROOT])
        # OPT.CUAS.Audio is a true ancestor (dotted boundary satisfied)
        assert analyser._is_internal_namespace("OPT.CUAS.Audio.Engine.DSP") is True

    def test_dotted_boundary_trap_is_external(self):
        analyser = self._make_analyser([self._ROOT])
        # OPT.CUAS.AudioPlus must NOT be matched — it shares only a prefix, not a dotted boundary
        assert analyser._is_internal_namespace("OPT.CUAS.AudioPlus") is False

    def test_unrelated_namespace_is_external(self):
        analyser = self._make_analyser([self._ROOT])
        assert analyser._is_internal_namespace("UnityEngine") is False
        assert analyser._is_internal_namespace("System") is False
        assert analyser._is_internal_namespace("NUnit.Framework") is False

    def test_empty_root_namespace_never_matches(self):
        # An assembly with an empty rootNamespace must not cause everything to be internal.
        asmdef_dict = {
            "GUID:asm0": {"name": "Asm0", "rootNamespace": "", "references": [], "relativePath": "Assets/Asm0"},
        }
        analyser = ScriptAnalyser(asmdef_dict, Path("/fake"))
        assert analyser._is_internal_namespace("System") is False
        assert analyser._is_internal_namespace("") is False

    def test_missing_root_namespace_key_never_matches(self):
        # An assembly entry missing the rootNamespace key entirely must not cause false-matches.
        asmdef_dict = {
            "GUID:asm0": {"name": "Asm0", "references": [], "relativePath": "Assets/Asm0"},
        }
        analyser = ScriptAnalyser(asmdef_dict, Path("/fake"))
        assert analyser._is_internal_namespace("System") is False

    def test_metadata_key_skipped(self):
        # _metadata must never contribute a root namespace.
        asmdef_dict = {
            "_metadata": {"rootNamespace": "System"},
        }
        analyser = ScriptAnalyser(asmdef_dict, Path("/fake"))
        assert analyser._is_internal_namespace("System") is False

    def test_external_imports_preserves_order_and_filters(self, tmp_path: Path):
        content = (
            "using OPT.CUAS.Audio;\n"          # internal
            "using OPT.CUAS.Audio.Engine.DSP;\n"  # internal (descendant)
            "using OPT.CUAS.AudioPlus;\n"       # external
            "using UnityEngine;\n"              # external
            "using System;\n"                   # external
        )
        _make_script(tmp_path / "A.cs", content, "g1")
        asmdef_dict = {
            "GUID:asm1": {
                "name": "Audio",
                "rootNamespace": "OPT.CUAS.Audio",
                "references": [],
                "relativePath": "Assets/Audio",
            }
        }
        result = ScriptAnalyser(asmdef_dict, tmp_path).analyse()
        entry = result["scripts"]["GUID:g1"]

        # imports is unchanged (full sorted list)
        assert entry["imports"] == [
            "OPT.CUAS.Audio",
            "OPT.CUAS.Audio.Engine.DSP",
            "OPT.CUAS.AudioPlus",
            "System",
            "UnityEngine",
        ]
        # external_imports contains only the non-internal entries, in the same relative order
        assert entry["external_imports"] == ["OPT.CUAS.AudioPlus", "System", "UnityEngine"]

    def test_unique_external_namespaces_stat(self, tmp_path: Path):
        # Two scripts sharing one external namespace; stat should reflect the union size.
        _make_script(tmp_path / "A.cs", "using UnityEngine;\nusing System;\n", "g1")
        _make_script(tmp_path / "B.cs", "using UnityEngine;\nusing System.Linq;\n", "g2")
        asmdef_dict = {
            "GUID:asm1": {
                "name": "Internal",
                "rootNamespace": "MyProject",
                "references": [],
                "relativePath": "Assets/Internal",
            }
        }
        result = ScriptAnalyser(asmdef_dict, tmp_path).analyse()
        # UnityEngine, System, System.Linq — 3 unique external namespaces
        assert result["stats"]["unique_external_namespaces"] == 3
