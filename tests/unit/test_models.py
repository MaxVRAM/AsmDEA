"""Unit tests for models package."""

from pathlib import Path

from models import AnalysisConfig, AsmdefEntry, CycleReport, NamespaceAnalysisReport


class TestAsmdefEntry:
    """Test suite for AsmdefEntry dataclass."""

    def test_from_dict_basic(self):
        """Test creating AsmdefEntry from dictionary."""
        data = {
            "name": "TestAssembly",
            "rootNamespace": "Test.Namespace",
            "references": ["GUID:abc123"],
        }

        entry = AsmdefEntry.from_dict("GUID:test123", data, Path("Assets/Scripts"))

        assert entry.guid == "GUID:test123"
        assert entry.name == "TestAssembly"
        assert entry.root_namespace == "Test.Namespace"
        assert entry.references == ["GUID:abc123"]
        assert entry.file_path == Path("Assets/Scripts")

    def test_from_dict_with_all_fields(self):
        """Test creating AsmdefEntry with all optional fields."""
        data = {
            "name": "FullAssembly",
            "rootNamespace": "Full.Namespace",
            "references": ["GUID:ref1", "GUID:ref2"],
            "includePlatforms": ["Editor"],
            "excludePlatforms": ["Android"],
            "allowUnsafeCode": True,
            "overrideReferences": True,
            "precompiledReferences": ["Plugin.dll"],
            "autoReferenced": False,
            "defineConstraints": ["UNITY_EDITOR"],
            "versionDefines": [],
            "noEngineReferences": True,
        }

        entry = AsmdefEntry.from_dict("GUID:full", data, Path("Assets"))

        assert entry.name == "FullAssembly"
        assert entry.allow_unsafe_code is True
        assert entry.auto_referenced is False
        assert entry.no_engine_references is True
        assert "Editor" in entry.include_platforms
        assert "UNITY_EDITOR" in entry.define_constraints

    def test_to_dict(self):
        """Test converting AsmdefEntry to dictionary."""
        entry = AsmdefEntry(
            guid="GUID:test",
            name="MyAssembly",
            root_namespace="My.Namespace",
            references=["GUID:ref1"],
            file_path=Path("Assets/Scripts/MyAssembly.asmdef"),
            include_platforms=[],
            exclude_platforms=[],
            allow_unsafe_code=False,
            override_references=False,
            precompiled_references=[],
            auto_referenced=True,
            define_constraints=[],
            version_defines=[],
            no_engine_references=False,
        )

        result = entry.to_dict()

        assert result["name"] == "MyAssembly"
        assert result["rootNamespace"] == "My.Namespace"
        assert result["references"] == ["GUID:ref1"]
        # Fields with False/empty values are excluded by to_dict()
        assert "allowUnsafeCode" not in result
        assert "autoReferenced" not in result  # True is default, excluded


class TestAnalysisConfig:
    """Test suite for AnalysisConfig dataclass."""

    def test_analysis_config_creation(self):
        """Test creating AnalysisConfig."""
        config = AnalysisConfig(
            root_path=Path("/project"),
            output_dir=Path("/output"),
            dict_file=Path("/dict.json"),
            allow_child_namespaces=True,
            tree_depth=5,
        )

        assert config.root_path == Path("/project")
        assert config.output_dir == Path("/output")
        assert config.dict_file == Path("/dict.json")
        assert config.allow_child_namespaces is True
        assert config.tree_depth == 5

    def test_analysis_config_defaults(self):
        """Test AnalysisConfig with default values."""
        config = AnalysisConfig(
            root_path=Path("/project"),
        )

        assert config.root_path == Path("/project")
        # Check that defaults from constants are used
        assert config.output_dir is not None
        assert config.dict_file is not None


class TestCycleReport:
    """Test suite for CycleReport dataclass."""

    def test_cycle_report_to_dict(self):
        """Test converting CycleReport to dictionary."""
        report = CycleReport(
            cycles=[],
            total_cycles=0,
            affected_nodes=[],
        )

        result = report.to_dict()

        assert "cycles" in result
        assert "totalCycles" in result
        assert "affectedNodes" in result
        assert result["totalCycles"] == 0
        assert isinstance(result["affectedNodes"], list)


class TestNamespaceAnalysisReport:
    """Test suite for NamespaceAnalysisReport dataclass."""

    def test_get_problem_assemblies(self, sample_asmdef_dict):
        """Test identifying assemblies with namespace problems."""
        from models import AssemblyNamespaceStats

        # Create a report with one assembly having problems
        stats1 = AssemblyNamespaceStats(
            assembly_name="Assembly.Core",
            assembly_guid="GUID:assembly1",
            root_namespace="MyProject.Core",
            total_files=10,
            matched_files=10,
            unmatched_files=0,
            no_namespace_files=0,
        )

        stats2 = AssemblyNamespaceStats(
            assembly_name="Assembly.Bad",
            assembly_guid="GUID:assembly2",
            root_namespace="MyProject.Bad",
            total_files=10,
            matched_files=5,
            unmatched_files=5,
            no_namespace_files=0,
        )

        report = NamespaceAnalysisReport(
            assembly_stats={
                "GUID:assembly1": stats1,
                "GUID:assembly2": stats2,
            },
            total_assemblies=2,
        )

        problems = report.get_problem_assemblies()

        assert len(problems) == 1
        assert problems[0].assembly_name == "Assembly.Bad"
        assert problems[0].unmatched_files == 5
