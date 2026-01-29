"""Pytest configuration and shared fixtures."""

from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def sample_asmdef_data() -> dict[str, Any]:
    """Sample assembly definition data for testing."""
    return {
        "name": "TestAssembly",
        "rootNamespace": "Test.Namespace",
        "references": ["GUID:abc123", "GUID:def456"],
        "includePlatforms": [],
        "excludePlatforms": [],
        "allowUnsafeCode": False,
        "overrideReferences": False,
        "precompiledReferences": [],
        "autoReferenced": True,
        "defineConstraints": [],
        "versionDefines": [],
        "noEngineReferences": False,
    }


@pytest.fixture
def sample_asmdef_dict() -> dict[str, Any]:
    """Sample asmdef dictionary with multiple assemblies."""
    return {
        "GUID:assembly1": {
            "name": "Assembly.Core",
            "rootNamespace": "MyProject.Core",
            "references": ["GUID:assembly2"],
            "relativePath": "Assets/Scripts/Core",
        },
        "GUID:assembly2": {
            "name": "Assembly.Utils",
            "rootNamespace": "MyProject.Utils",
            "references": [],
            "relativePath": "Assets/Scripts/Utils",
        },
        "GUID:assembly3": {
            "name": "Assembly.UI",
            "rootNamespace": "MyProject.UI",
            "references": ["GUID:assembly1", "GUID:assembly2"],
            "relativePath": "Assets/Scripts/UI",
        },
        "_metadata": {
            "generated": "2026-01-28",
            "tool": "asmdef_dictionary",
        },
    }


@pytest.fixture
def sample_cyclic_dict() -> dict[str, Any]:
    """Sample asmdef dictionary with cyclic dependencies."""
    return {
        "GUID:a": {
            "name": "AssemblyA",
            "rootNamespace": "A",
            "references": ["GUID:b"],
            "relativePath": "Assets/A",
        },
        "GUID:b": {
            "name": "AssemblyB",
            "rootNamespace": "B",
            "references": ["GUID:c"],
            "relativePath": "Assets/B",
        },
        "GUID:c": {
            "name": "AssemblyC",
            "rootNamespace": "C",
            "references": ["GUID:a"],  # Creates cycle: A -> B -> C -> A
            "relativePath": "Assets/C",
        },
    }


@pytest.fixture
def temp_test_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for test files."""
    test_dir = tmp_path / "test_workspace"
    test_dir.mkdir()
    return test_dir


@pytest.fixture
def sample_cs_file_content() -> str:
    """Sample C# file content with namespace declaration."""
    return """using System;
using UnityEngine;

namespace MyProject.Core
{
    public class TestClass
    {
        public void TestMethod()
        {
            Debug.Log("Test");
        }
    }
}
"""


@pytest.fixture
def sample_cs_file_no_namespace() -> str:
    """Sample C# file content without namespace."""
    return """using System;
using UnityEngine;

public class TestClass
{
    public void TestMethod()
    {
        Debug.Log("Test");
    }
}
"""


@pytest.fixture
def sample_meta_file_content() -> str:
    """Sample .meta file content with GUID."""
    return """fileFormatVersion: 2
guid: abc123def456789
MonoImporter:
  externalObjects: {}
  serializedVersion: 2
  defaultReferences: []
  executionOrder: 0
  icon: {instanceID: 0}
  userData:
  assetBundleName:
  assetBundleVariant:
"""
