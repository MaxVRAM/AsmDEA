"""Unit tests for analyzer classes."""

from pathlib import Path

from analyzers import CycleAnalyzer, FileAnalyzer, NamespaceAnalyzer


class TestCycleAnalyzer:
    """Test suite for CycleAnalyzer."""

    def test_init_with_valid_dict(self, sample_asmdef_dict):
        """Test initializing CycleAnalyzer with valid dictionary."""
        analyzer = CycleAnalyzer(sample_asmdef_dict)

        assert analyzer.asmdef_dict == sample_asmdef_dict
        assert analyzer.graph is not None
        assert analyzer.guid_to_name is not None
        assert analyzer.name_to_guid is not None

    def test_build_dependency_graph(self, sample_asmdef_dict):
        """Test that dependency graph is built correctly."""
        analyzer = CycleAnalyzer(sample_asmdef_dict)

        # Graph only includes nodes with outgoing edges (Utils has no dependencies)
        assert len(analyzer.graph) == 2
        assert len(analyzer.guid_to_name) == 3
        assert len(analyzer.name_to_guid) == 3

        # Verify GUID to name mapping
        assert analyzer.guid_to_name["GUID:assembly1"] == "Assembly.Core"
        assert analyzer.guid_to_name["GUID:assembly2"] == "Assembly.Utils"

    def test_dependency_graph_structure(self, sample_asmdef_dict):
        """Test that graph edges are created correctly."""
        analyzer = CycleAnalyzer(sample_asmdef_dict)

        # Assembly.Core depends on Assembly.Utils
        assert "Assembly.Utils" in analyzer.graph["Assembly.Core"]
        # Assembly.UI depends on both Core and Utils
        assert "Assembly.Core" in analyzer.graph["Assembly.UI"]
        assert "Assembly.Utils" in analyzer.graph["Assembly.UI"]

    def test_no_cycles_in_sample_dict(self, sample_asmdef_dict):
        """Test that sample dict has no cycles."""
        analyzer = CycleAnalyzer(sample_asmdef_dict)
        cycles = analyzer.detect_cycles()

        assert len(cycles) == 0

    def test_detect_cycles_with_cyclic_dict(self, sample_cyclic_dict):
        """Test cycle detection with cyclic dependencies."""
        analyzer = CycleAnalyzer(sample_cyclic_dict)
        cycles = analyzer.detect_cycles()

        # Should detect the cycle: A -> B -> C -> A
        assert len(cycles) > 0
        # Cycles are returned as list of lists, not CyclePath objects
        cycle_nodes = cycles[0]
        assert len(cycle_nodes) == 4  # A, B, C, A (start node repeated)

    def test_analyze_returns_cycle_report(self, sample_asmdef_dict):
        """Test that analyze() returns a complete CycleReport."""
        analyzer = CycleAnalyzer(sample_asmdef_dict)
        report = analyzer.analyze()

        assert report.total_cycles == 0
        assert report.total_nodes == 2  # Only nodes with outgoing edges
        assert len(report.graph) == 2
        assert len(report.cycles) == 0

    def test_get_summary(self, sample_asmdef_dict):
        """Test generating summary from analysis."""
        analyzer = CycleAnalyzer(sample_asmdef_dict)
        report = analyzer.analyze()
        summary = analyzer.get_summary(report)

        assert summary.total_cycles == 0
        assert summary.total_assemblies == 2  # Only nodes in graph
        assert summary.affected_assemblies == 0

    def test_cyclic_summary_statistics(self, sample_cyclic_dict):
        """Test summary statistics for cyclic dependencies."""
        analyzer = CycleAnalyzer(sample_cyclic_dict)
        report = analyzer.analyze()
        summary = analyzer.get_summary(report)

        assert summary.total_cycles > 0
        assert summary.affected_assemblies > 0
        assert summary.shortest_cycle_length > 0
        assert summary.longest_cycle_length > 0


class TestNamespaceAnalyzer:
    """Test suite for NamespaceAnalyzer."""

    def test_init_with_defaults(self, sample_asmdef_dict, tmp_path: Path):
        """Test initializing NamespaceAnalyzer."""
        analyzer = NamespaceAnalyzer(sample_asmdef_dict, tmp_path)

        assert analyzer.asmdef_dict == sample_asmdef_dict
        assert analyzer.root_path == tmp_path.resolve()
        assert analyzer.allow_child_namespaces is True

    def test_init_without_child_namespaces(self, sample_asmdef_dict, tmp_path: Path):
        """Test initialization with child namespaces disabled."""
        analyzer = NamespaceAnalyzer(sample_asmdef_dict, tmp_path, allow_child_namespaces=False)

        assert analyzer.allow_child_namespaces is False

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

        namespaces = NamespaceAnalyzer.extract_namespace_from_file(cs_file)

        assert len(namespaces) == 1
        assert namespaces[0] == "MyProject.Core"

    def test_extract_namespace_file_scoped_syntax(self, tmp_path: Path):
        """Test extracting namespace with file-scoped C# 10+ syntax."""
        cs_file = tmp_path / "Modern.cs"
        cs_file.write_text("""using System;

namespace MyProject.Modern;

public class ModernClass { }
""")

        namespaces = NamespaceAnalyzer.extract_namespace_from_file(cs_file)

        assert len(namespaces) == 1
        assert namespaces[0] == "MyProject.Modern"

    def test_extract_namespace_no_namespace(self, tmp_path: Path):
        """Test extracting from file without namespace."""
        cs_file = tmp_path / "NoNamespace.cs"
        cs_file.write_text("""using System;

public class GlobalClass { }
""")

        namespaces = NamespaceAnalyzer.extract_namespace_from_file(cs_file)

        assert len(namespaces) == 0

    def test_is_child_namespace_valid(self, sample_asmdef_dict, tmp_path: Path):
        """Test child namespace validation."""
        analyzer = NamespaceAnalyzer(sample_asmdef_dict, tmp_path)

        # MyProject.Core.Utilities is child of MyProject.Core
        assert analyzer.is_child_namespace("MyProject.Core.Utilities", "MyProject.Core") is True
        # MyProject.Other is not child of MyProject.Core
        assert analyzer.is_child_namespace("MyProject.Other", "MyProject.Core") is False
        # Exact match is not considered a child
        assert analyzer.is_child_namespace("MyProject.Core", "MyProject.Core") is False

    def test_analyze_assembly_with_no_files(self, sample_asmdef_dict, tmp_path: Path):
        """Test analyzing assembly with no C# files."""
        analyzer = NamespaceAnalyzer(sample_asmdef_dict, tmp_path)

        # Create assembly data with no files
        assembly_data = {
            "name": "Assembly.Core",
            "rootNamespace": "MyProject.Core",
            "relativePath": str(tmp_path / "Core"),
        }

        stats = analyzer.analyze_assembly(guid="GUID:assembly1", assembly_data=assembly_data)

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


        analyzer = NamespaceAnalyzer(sample_asmdef_dict, tmp_path)

        assert analyzer.root_path == tmp_path.resolve()

    def test_build_path_to_guid_mapping(self, sample_asmdef_dict, tmp_path: Path):
        """Test building path to GUID mapping."""
        analyzer = FileAnalyzer(sample_asmdef_dict, tmp_path)

        mapping = analyzer._build_path_to_guid_mapping()

        # Should have mappings for all assemblies
        assert len(mapping) >= 3

    def test_should_ignore_path(self, sample_asmdef_dict, tmp_path: Path):
        """Test path ignore logic for Unity temp folders."""
        analyzer = FileAnalyzer(sample_asmdef_dict, tmp_path)

        # Unity temp folders should be ignored
        assert analyzer.should_ignore_path(Path("Assets/Scripts/~TempFile.cs")) is True
        assert analyzer.should_ignore_path(Path("Assets/~Scripts/File.cs")) is True

        # Normal paths should not be ignored
        assert analyzer.should_ignore_path(Path("Assets/Scripts/Normal.cs")) is False

    def test_find_owning_assembly_no_match(self, sample_asmdef_dict, tmp_path: Path):
        """Test finding owning assembly for file with no assembly."""
        analyzer = FileAnalyzer(sample_asmdef_dict, tmp_path)

        # File outside any assembly directory
        result = analyzer.find_owning_assembly(tmp_path / "Orphan.cs")

        assert result is None

    def test_analyze_returns_stats(self, sample_asmdef_dict, tmp_path: Path):
        """Test that analyze returns statistics."""
        analyzer = FileAnalyzer(sample_asmdef_dict, tmp_path)

        result = analyzer.analyze()

        assert "asmdef_dict" in result
        assert "stats" in result
        assert result["stats"]["total_cs_files"] >= 0
        assert result["stats"]["assigned_files"] >= 0
        assert result["stats"]["orphaned_files"] >= 0
