"""Unit tests for ScriptReporter JSON shape."""

from pathlib import Path

from analysers import ScriptAnalyser
from reporting import ScriptReporter


def _make(cs_path: Path, content: str, guid: str) -> None:
    cs_path.parent.mkdir(parents=True, exist_ok=True)
    cs_path.write_text(content, encoding="utf-8")
    Path(str(cs_path) + ".meta").write_text(
        f"fileFormatVersion: 2\nguid: {guid}\n", encoding="utf-8"
    )


def test_json_report_shape(tmp_path: Path):
    cs = tmp_path / "Bar.cs"
    _make(cs, "using System;\nnamespace Foo;\nclass C {}\n", "scriptguid")

    result = ScriptAnalyser({}, tmp_path).analyse()
    payload = ScriptReporter(root_path=tmp_path).generate_json_report(result)

    assert set(payload.keys()) == {"summary", "scripts"}

    summary = payload["summary"]
    assert summary["totalScripts"] == 1
    assert summary["scriptsWithNamespace"] == 1
    assert summary["scriptsWithoutNamespace"] == 0
    assert summary["scriptsWithoutMeta"] == 0
    assert summary["totalImports"] == 1
    assert summary["uniqueNamespacesImported"] == 1

    entry = payload["scripts"]["GUID:scriptguid"]
    assert entry["name"] == "Bar"
    assert entry["relativePath"] == "Bar.cs"
    assert entry["namespace"] == "Foo"
    assert entry["importCount"] == 1
    assert entry["imports"] == ["System"]
    assert entry["assembly"] is None


def test_json_report_entries_are_guid_sorted(tmp_path: Path):
    _make(tmp_path / "Z.cs", "namespace Z;\n", "zzz")
    _make(tmp_path / "A.cs", "namespace A;\n", "aaa")

    result = ScriptAnalyser({}, tmp_path).analyse()
    payload = ScriptReporter(root_path=tmp_path).generate_json_report(result)

    keys = list(payload["scripts"].keys())
    assert keys == sorted(keys)


def test_json_report_assembly_resolution(tmp_path: Path):
    cs_file = tmp_path / "Assets" / "Foo" / "Bar.cs"
    _make(cs_file, "namespace Foo;\n", "scriptguid")
    asmdef_dict = {
        "GUID:asm1": {
            "name": "Foo",
            "rootNamespace": "Foo",
            "references": [],
            "relativePath": "Assets/Foo",
        }
    }

    result = ScriptAnalyser(asmdef_dict, tmp_path).analyse()
    payload = ScriptReporter(root_path=tmp_path).generate_json_report(result)

    entry = payload["scripts"]["GUID:scriptguid"]
    assert entry["assembly"] == "GUID:asm1"
    assert entry["relativePath"] == "Assets/Foo/Bar.cs"


def test_json_report_external_imports_field(tmp_path: Path):
    # Script imports one internal and two external namespaces.
    cs = tmp_path / "Script.cs"
    content = (
        "using MyProject.Core;\n"  # internal
        "using UnityEngine;\n"     # external
        "using System;\n"          # external
    )
    _make(cs, content, "sg1")
    asmdef_dict = {
        "GUID:asm1": {
            "name": "Core",
            "rootNamespace": "MyProject.Core",
            "references": [],
            "relativePath": "Assets/Core",
        }
    }

    result = ScriptAnalyser(asmdef_dict, tmp_path).analyse()
    payload = ScriptReporter(root_path=tmp_path).generate_json_report(result)

    entry = payload["scripts"]["GUID:sg1"]
    # imports is still the full list
    assert entry["imports"] == ["MyProject.Core", "System", "UnityEngine"]
    # externalImports excludes the internal one
    assert entry["externalImports"] == ["System", "UnityEngine"]


def test_json_report_summary_unique_external_namespaces(tmp_path: Path):
    # Two scripts; union of external namespaces across both should appear in summary.
    _make(tmp_path / "A.cs", "using UnityEngine;\nusing System;\n", "g1")
    _make(tmp_path / "B.cs", "using UnityEngine;\nusing System.Linq;\n", "g2")
    asmdef_dict = {
        "GUID:asm1": {
            "name": "Internal",
            "rootNamespace": "MyProject",
            "references": [],
            "relativePath": "Assets/Internal",
        }
    }

    result = ScriptAnalyser(asmdef_dict, tmp_path).analyse()
    payload = ScriptReporter(root_path=tmp_path).generate_json_report(result)

    assert "uniqueExternalNamespaces" in payload["summary"]
    # UnityEngine + System + System.Linq = 3 unique external namespaces
    assert payload["summary"]["uniqueExternalNamespaces"] == 3
