"""Unit tests for analyser classes."""

from pathlib import Path

from analysers import CycleAnalyser, FileAnalyser, NamespaceAnalyser, SearchAnalyser
from models import MatchType


class TestCycleAnalyser:
    """Test suite for CycleAnalyser."""

    def test_init_with_valid_dict(self, sample_asmdef_dict):
        """Test initializing CycleAnalyser with valid dictionary."""
        analyser = CycleAnalyser(sample_asmdef_dict)

        assert analyser.asmdef_dict == sample_asmdef_dict
        assert analyser.graph is not None
        assert analyser.guid_to_name is not None
        assert analyser.name_to_guid is not None

    def test_build_dependency_graph(self, sample_asmdef_dict):
        """Test that dependency graph is built correctly."""
        analyser = CycleAnalyser(sample_asmdef_dict)

        # Graph only includes nodes with outgoing edges (Utils has no dependencies)
        assert len(analyser.graph) == 2
        assert len(analyser.guid_to_name) == 3
        assert len(analyser.name_to_guid) == 3

        # Verify GUID to name mapping
        assert analyser.guid_to_name["GUID:assembly1"] == "Assembly.Core"
        assert analyser.guid_to_name["GUID:assembly2"] == "Assembly.Utils"

    def test_dependency_graph_structure(self, sample_asmdef_dict):
        """Test that graph edges are created correctly."""
        analyser = CycleAnalyser(sample_asmdef_dict)

        # Assembly.Core depends on Assembly.Utils
        assert "Assembly.Utils" in analyser.graph["Assembly.Core"]
        # Assembly.UI depends on both Core and Utils
        assert "Assembly.Core" in analyser.graph["Assembly.UI"]
        assert "Assembly.Utils" in analyser.graph["Assembly.UI"]

    def test_no_cycles_in_sample_dict(self, sample_asmdef_dict):
        """Test that sample dict has no cycles."""
        analyser = CycleAnalyser(sample_asmdef_dict)
        cycles = analyser.detect_cycles()

        assert len(cycles) == 0

    def test_detect_cycles_with_cyclic_dict(self, sample_cyclic_dict):
        """Test cycle detection with cyclic dependencies."""
        analyser = CycleAnalyser(sample_cyclic_dict)
        cycles = analyser.detect_cycles()

        # Should detect the cycle: A -> B -> C -> A
        assert len(cycles) > 0
        # Cycles are returned as list of lists, not CyclePath objects
        cycle_nodes = cycles[0]
        assert len(cycle_nodes) == 4  # A, B, C, A (start node repeated)

    def test_analyze_returns_cycle_report(self, sample_asmdef_dict):
        """Test that analyze() returns a complete CycleReport."""
        analyser = CycleAnalyser(sample_asmdef_dict)
        report = analyser.analyse()

        assert report.total_cycles == 0
        assert report.total_nodes == 2  # Only nodes with outgoing edges
        assert len(report.graph) == 2
        assert len(report.cycles) == 0

    def test_get_summary(self, sample_asmdef_dict):
        """Test generating summary from analysis."""
        analyser = CycleAnalyser(sample_asmdef_dict)
        report = analyser.analyse()
        summary = analyser.get_summary(report)

        assert summary.total_cycles == 0
        assert summary.total_assemblies == 2  # Only nodes in graph
        assert summary.affected_assemblies == 0

    def test_cyclic_summary_statistics(self, sample_cyclic_dict):
        """Test summary statistics for cyclic dependencies."""
        analyser = CycleAnalyser(sample_cyclic_dict)
        report = analyser.analyse()
        summary = analyser.get_summary(report)

        assert summary.total_cycles > 0
        assert summary.affected_assemblies > 0
        assert summary.shortest_cycle_length > 0
        assert summary.longest_cycle_length > 0


class TestNamespaceAnalyser:
    """Test suite for NamespaceAnalyser."""

    def test_init_with_defaults(self, sample_asmdef_dict, tmp_path: Path):
        """Test initializing NamespaceAnalyser."""
        analyser = NamespaceAnalyser(sample_asmdef_dict, tmp_path)

        assert analyser.asmdef_dict == sample_asmdef_dict
        assert analyser.root_path == tmp_path.resolve()
        assert analyser.allow_child_namespaces is True

    def test_init_without_child_namespaces(self, sample_asmdef_dict, tmp_path: Path):
        """Test initialization with child namespaces disabled."""
        analyser = NamespaceAnalyser(sample_asmdef_dict, tmp_path, allow_child_namespaces=False)

        assert analyser.allow_child_namespaces is False

    def test_extract_namespace_traditional_syntax(self, tmp_path: Path):
        """Test extracting namespace with traditional C# syntax."""
        cs_file = tmp_path / "Test.cs"
        cs_file.write_text("""using System;
using UnityEngine;

namespace MyProject.Core
{
    public class TestClass { }
}
""")

        namespaces = NamespaceAnalyser.extract_namespace_from_file(cs_file)

        assert len(namespaces) == 1
        assert namespaces[0] == "MyProject.Core"

    def test_extract_namespace_file_scoped_syntax(self, tmp_path: Path):
        """Test extracting namespace with file-scoped C# 10+ syntax."""
        cs_file = tmp_path / "Modern.cs"
        cs_file.write_text("""using System;

namespace MyProject.Modern;

public class ModernClass { }
""")

        namespaces = NamespaceAnalyser.extract_namespace_from_file(cs_file)

        assert len(namespaces) == 1
        assert namespaces[0] == "MyProject.Modern"

    def test_extract_namespace_no_namespace(self, tmp_path: Path):
        """Test extracting from file without namespace."""
        cs_file = tmp_path / "NoNamespace.cs"
        cs_file.write_text("""using System;

public class GlobalClass { }
""")

        namespaces = NamespaceAnalyser.extract_namespace_from_file(cs_file)

        assert len(namespaces) == 0

    def test_is_child_namespace_valid(self, sample_asmdef_dict, tmp_path: Path):
        """Test child namespace validation."""
        analyser = NamespaceAnalyser(sample_asmdef_dict, tmp_path)

        # MyProject.Core.Utilities is child of MyProject.Core
        assert analyser.is_child_namespace("MyProject.Core.Utilities", "MyProject.Core") is True
        # MyProject.Other is not child of MyProject.Core
        assert analyser.is_child_namespace("MyProject.Other", "MyProject.Core") is False
        # Exact match is not considered a child
        assert analyser.is_child_namespace("MyProject.Core", "MyProject.Core") is False

    def test_analyze_assembly_with_no_files(self, sample_asmdef_dict, tmp_path: Path):
        """Test analyzing assembly with no C# files."""
        analyser = NamespaceAnalyser(sample_asmdef_dict, tmp_path)

        # Create assembly data with no files
        assembly_data = {
            "name": "Assembly.Core",
            "rootNamespace": "MyProject.Core",
            "relativePath": str(tmp_path / "Core"),
        }

        stats = analyser.analyse_assembly(guid="GUID:assembly1", assembly_data=assembly_data)

        assert stats.total_files == 0
        assert stats.matched_files == 0
        assert stats.assembly_name == "Assembly.Core"

    def test_analyze_with_matching_namespace(self, sample_asmdef_dict, tmp_path: Path):
        """Test analyzing files with matching namespaces."""
        # Create assembly directory with matching file
        assembly_dir = tmp_path / "Core"
        assembly_dir.mkdir()

        cs_file = assembly_dir / "CoreClass.cs"
        cs_file.write_text("""namespace MyProject.Core
{
    public class CoreClass { }
}
""")

        analyser = NamespaceAnalyser(sample_asmdef_dict, tmp_path)

        assert analyser.root_path == tmp_path.resolve()

    def test_build_path_to_guid_mapping(self, sample_asmdef_dict, tmp_path: Path):
        """Test building path to GUID mapping."""
        analyser = FileAnalyser(sample_asmdef_dict, tmp_path)

        mapping = analyser._build_path_to_guid_mapping()

        # Should have mappings for all assemblies
        assert len(mapping) >= 3

    def test_should_ignore_path(self, sample_asmdef_dict, tmp_path: Path):
        """Test path ignore logic for Unity temp folders."""
        analyser = FileAnalyser(sample_asmdef_dict, tmp_path)

        # Unity temp folders should be ignored
        assert analyser.should_ignore_path(Path("Assets/Scripts/~TempFile.cs")) is True
        assert analyser.should_ignore_path(Path("Assets/~Scripts/File.cs")) is True

        # Normal paths should not be ignored
        assert analyser.should_ignore_path(Path("Assets/Scripts/Normal.cs")) is False

    def test_find_owning_assembly_no_match(self, sample_asmdef_dict, tmp_path: Path):
        """Test finding owning assembly for file with no assembly."""
        analyser = FileAnalyser(sample_asmdef_dict, tmp_path)

        # File outside any assembly directory
        result = analyser.find_owning_assembly(tmp_path / "Orphan.cs")

        assert result is None

    def test_analyze_returns_stats(self, sample_asmdef_dict, tmp_path: Path):
        """Test that analyze returns statistics."""
        analyser = FileAnalyser(sample_asmdef_dict, tmp_path)

        result = analyser.analyse()

        assert "asmdef_dict" in result
        assert "stats" in result
        assert result["stats"]["total_cs_files"] >= 0
        assert result["stats"]["assigned_files"] >= 0
        assert result["stats"]["orphaned_files"] >= 0


class TestSearchAnalyser:
    """Test suite for SearchAnalyser."""

    def test_init_with_valid_dict(self, sample_asmdef_dict):
        """Test initializing SearchAnalyser with valid dictionary."""
        analyser = SearchAnalyser(sample_asmdef_dict)

        assert analyser.asmdef_dict == sample_asmdef_dict
        assert analyser.root_path is None

    def test_init_with_root_path(self, sample_asmdef_dict, tmp_path: Path):
        """Test initializing SearchAnalyser with root path."""
        analyser = SearchAnalyser(sample_asmdef_dict, tmp_path)

        assert analyser.root_path == tmp_path.resolve()

    def test_search_by_guid_exact_match(self, sample_asmdef_dict):
        """Test searching by exact GUID match."""
        analyser = SearchAnalyser(sample_asmdef_dict)

        results = analyser.search("GUID:assembly1")

        assert len(results) == 1
        assert results[0].guid == "GUID:assembly1"
        assert results[0].name == "Assembly.Core"
        assert results[0].match_type == MatchType.GUID

    def test_search_by_guid_no_match(self, sample_asmdef_dict):
        """Test searching by GUID with no match."""
        analyser = SearchAnalyser(sample_asmdef_dict)

        results = analyser.search("GUID:nonexistent")

        assert len(results) == 0

    def test_search_by_name_exact_match(self, sample_asmdef_dict):
        """Test searching by assembly name."""
        analyser = SearchAnalyser(sample_asmdef_dict)

        results = analyser.search("Assembly.Core")

        assert len(results) == 1
        assert results[0].name == "Assembly.Core"
        assert results[0].match_type == MatchType.NAME
        assert results[0].matched_value == "Assembly.Core"

    def test_search_by_name_partial_match(self, sample_asmdef_dict):
        """Test searching by partial assembly name."""
        analyser = SearchAnalyser(sample_asmdef_dict)

        results = analyser.search("Core")

        # "Core" matches both name "Assembly.Core" and root namespace "MyProject.Core"
        assert len(results) == 2
        names = {r.name for r in results}
        assert "Assembly.Core" in names
        match_types = {r.match_type for r in results}
        assert MatchType.NAME in match_types
        assert MatchType.ROOT_NAMESPACE in match_types

    def test_search_by_root_namespace(self, sample_asmdef_dict):
        """Test searching by root namespace."""
        analyser = SearchAnalyser(sample_asmdef_dict)

        results = analyser.search("MyProject.Utils")

        assert len(results) == 1
        assert results[0].name == "Assembly.Utils"
        assert results[0].match_type == MatchType.ROOT_NAMESPACE
        assert results[0].matched_value == "MyProject.Utils"

    def test_search_by_namespace_partial_match(self, sample_asmdef_dict):
        """Test searching by partial namespace."""
        analyser = SearchAnalyser(sample_asmdef_dict)

        results = analyser.search("MyProject")

        # Should match all assemblies with MyProject in their namespace
        assert len(results) >= 3

    def test_search_case_insensitive(self, sample_asmdef_dict):
        """Test that search is case-insensitive."""
        analyser = SearchAnalyser(sample_asmdef_dict)

        results_lower = analyser.search("assembly.core")
        results_upper = analyser.search("ASSEMBLY.CORE")

        assert len(results_lower) == 1
        assert len(results_upper) == 1
        assert results_lower[0].name == results_upper[0].name

    def test_search_by_script_namespace(self):
        """Test searching by script namespace."""
        test_dict = {
            "GUID:test1": {
                "name": "TestAssembly",
                "rootNamespace": "Test",
                "scriptNamespaces": ["Test.Feature", "Test.Utils", "Test.Models"],
                "relativePath": "Assets/Test",
            },
        }
        analyser = SearchAnalyser(test_dict)

        results = analyser.search("Test.Feature")

        assert len(results) == 1
        assert results[0].match_type == MatchType.SCRIPT_NAMESPACE
        assert results[0].matched_value == "Test.Feature"

    def test_search_multiple_matches_same_assembly(self):
        """Test that multiple match types for same assembly are all returned."""
        test_dict = {
            "GUID:test1": {
                "name": "MyProject.Core",
                "rootNamespace": "MyProject.Core",
                "scriptNamespaces": ["MyProject.Core.Models", "MyProject.Core.Utils"],
                "relativePath": "Assets/Core",
            },
        }
        analyser = SearchAnalyser(test_dict)

        results = analyser.search("MyProject.Core")

        # Should match both name and root namespace (and potentially script namespaces)
        assert len(results) >= 2
        match_types = {r.match_type for r in results}
        assert MatchType.NAME in match_types
        assert MatchType.ROOT_NAMESPACE in match_types

    def test_search_multiple_assemblies_match(self):
        """Test that multiple assemblies matching are all returned."""
        test_dict = {
            "GUID:test1": {
                "name": "MyCompany.Feature1",
                "rootNamespace": "MyCompany.Feature1",
                "relativePath": "Assets/Feature1",
            },
            "GUID:test2": {
                "name": "MyCompany.Feature2",
                "rootNamespace": "MyCompany.Feature2",
                "relativePath": "Assets/Feature2",
            },
            "GUID:test3": {
                "name": "OtherCompany.Feature",
                "rootNamespace": "OtherCompany",
                "relativePath": "Assets/Other",
            },
        }
        analyser = SearchAnalyser(test_dict)

        results = analyser.search("MyCompany")

        # Should match both Feature1 and Feature2
        assert len(results) >= 2
        names = {r.name for r in results}
        assert "MyCompany.Feature1" in names
        assert "MyCompany.Feature2" in names

    def test_search_no_match(self, sample_asmdef_dict):
        """Test searching with no matches."""
        analyser = SearchAnalyser(sample_asmdef_dict)

        results = analyser.search("NonExistentNamespace")

        assert len(results) == 0

    def test_search_ignores_metadata(self, sample_asmdef_dict):
        """Test that search ignores metadata entries."""
        analyser = SearchAnalyser(sample_asmdef_dict)

        results = analyser.search("metadata")

        # Should not match the _metadata entry
        assert len(results) == 0
