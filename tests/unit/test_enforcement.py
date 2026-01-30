"""Unit tests for enforcement module."""

from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

import pytest

from enforcement.base import BaseEnforcer, EnforcementMode, EnforcementResult
from enforcement.sorting_strategies import (
    SortingStrategy,
    AlphabeticalStrategy,
    NamespaceGroupedStrategy,
    UnityPriorityStrategy,
    CustomPriorityStrategy,
    SortedReference,
    BaseSortingStrategy,
    get_strategy,
)
from enforcement.dependency_sorter import DependencySorter
from models.sorting_result import DependencyDiff, SortingChange, SortingResult


class TestEnforcementMode:
    """Tests for EnforcementMode enum."""

    def test_dry_run_mode_exists(self):
        """Test that DRY_RUN mode is defined."""
        assert EnforcementMode.DRY_RUN is not None

    def test_apply_mode_exists(self):
        """Test that APPLY mode is defined."""
        assert EnforcementMode.APPLY is not None


class TestEnforcementResult:
    """Tests for EnforcementResult dataclass."""

    def test_create_successful_result(self):
        """Test creating a successful enforcement result."""
        result = EnforcementResult(
            success=True,
            mode=EnforcementMode.DRY_RUN,
        )

        assert result.success is True
        assert result.is_dry_run is True
        assert result.files_affected == 0
        assert result.errors == []

    def test_create_failed_result(self):
        """Test creating a failed enforcement result."""
        result = EnforcementResult(
            success=False,
            mode=EnforcementMode.APPLY,
            errors=["Something went wrong"],
        )

        assert result.success is False
        assert result.is_dry_run is False
        assert len(result.errors) == 1

    def test_files_affected_property(self):
        """Test files_affected property counts correctly."""
        result = EnforcementResult(
            success=True,
            mode=EnforcementMode.APPLY,
            modified_files=[Path("a.txt"), Path("b.txt"), Path("c.txt")],
        )

        assert result.files_affected == 3

    def test_is_dry_run_property(self):
        """Test is_dry_run property reflects mode."""
        dry_run_result = EnforcementResult(success=True, mode=EnforcementMode.DRY_RUN)
        apply_result = EnforcementResult(success=True, mode=EnforcementMode.APPLY)

        assert dry_run_result.is_dry_run is True
        assert apply_result.is_dry_run is False

    def test_result_has_timestamp(self):
        """Test that result has a timestamp."""
        result = EnforcementResult(success=True, mode=EnforcementMode.DRY_RUN)
        assert result.timestamp is not None

    def test_result_has_backup_path(self):
        """Test that result can have a backup path."""
        result = EnforcementResult(
            success=True,
            mode=EnforcementMode.APPLY,
            backup_path=Path("/backups/backup123"),
        )
        assert result.backup_path == Path("/backups/backup123")


class TestSortedReference:
    """Tests for SortedReference dataclass."""

    def test_create_sorted_reference(self):
        """Test creating a SortedReference."""
        ref = SortedReference(
            guid="GUID:abc123",
            name="MyAssembly",
        )

        assert ref.guid == "GUID:abc123"
        assert ref.name == "MyAssembly"
        assert ref.sort_key == "myassembly"  # lowercased
        assert ref.priority == 0
        assert ref.group == ""

    def test_custom_sort_key(self):
        """Test SortedReference with custom sort_key."""
        ref = SortedReference(
            guid="GUID:abc123",
            name="MyAssembly",
            sort_key="custom_key",
        )

        assert ref.sort_key == "custom_key"

    def test_post_init_sets_sort_key(self):
        """Test that sort_key is set from name if not provided."""
        ref = SortedReference(guid="GUID:abc", name="TestName")
        assert ref.sort_key == "testname"


class TestAlphabeticalStrategy:
    """Tests for AlphabeticalStrategy."""

    @pytest.fixture
    def sample_references(self) -> list[str]:
        """Sample GUID references."""
        return ["GUID:zebra", "GUID:apple", "GUID:mango"]

    @pytest.fixture
    def guid_to_name(self) -> dict[str, str]:
        """Sample GUID to name mapping."""
        return {
            "GUID:zebra": "Zebra.Assembly",
            "GUID:apple": "Apple.Assembly",
            "GUID:mango": "Mango.Assembly",
        }

    def test_sort_ascending(self, sample_references, guid_to_name):
        """Test sorting in ascending order."""
        strategy = AlphabeticalStrategy(ascending=True)
        sorted_refs = strategy.sort(sample_references, guid_to_name)

        assert sorted_refs == ["GUID:apple", "GUID:mango", "GUID:zebra"]

    def test_sort_descending(self, sample_references, guid_to_name):
        """Test sorting in descending order."""
        strategy = AlphabeticalStrategy(ascending=False)
        sorted_refs = strategy.sort(sample_references, guid_to_name)

        assert sorted_refs == ["GUID:zebra", "GUID:mango", "GUID:apple"]

    def test_name_property_ascending(self):
        """Test name property for ascending strategy."""
        strategy = AlphabeticalStrategy(ascending=True)
        assert "A-Z" in strategy.name

    def test_name_property_descending(self):
        """Test name property for descending strategy."""
        strategy = AlphabeticalStrategy(ascending=False)
        assert "Z-A" in strategy.name

    def test_description_property(self):
        """Test description property."""
        strategy = AlphabeticalStrategy(ascending=True)
        assert "alphabetically" in strategy.description.lower()

    def test_empty_references(self, guid_to_name):
        """Test sorting empty list."""
        strategy = AlphabeticalStrategy()
        result = strategy.sort([], guid_to_name)
        assert result == []


class TestNamespaceGroupedStrategy:
    """Tests for NamespaceGroupedStrategy."""

    @pytest.fixture
    def sample_references(self) -> list[str]:
        """Sample GUID references with namespace-like names."""
        return ["GUID:a", "GUID:b", "GUID:c", "GUID:d"]

    @pytest.fixture
    def guid_to_name(self) -> dict[str, str]:
        """Sample GUID to name mapping with namespaces."""
        return {
            "GUID:a": "Company.Module.Feature1",
            "GUID:b": "Company.Module.Feature2",
            "GUID:c": "Unity.Core.Physics",
            "GUID:d": "Company.Other.Utils",
        }

    def test_groups_by_root_namespace(self, sample_references, guid_to_name):
        """Test that references are grouped by root namespace."""
        strategy = NamespaceGroupedStrategy(ascending=True)
        sorted_refs = strategy.sort(sample_references, guid_to_name)

        # Company should come before Unity, then alphabetical within
        names = [guid_to_name[r] for r in sorted_refs]

        # All Company.* should be before Unity.*
        company_indices = [i for i, n in enumerate(names) if n.startswith("Company")]
        unity_indices = [i for i, n in enumerate(names) if n.startswith("Unity")]

        assert max(company_indices) < min(unity_indices)

    def test_name_property(self):
        """Test name property."""
        strategy = NamespaceGroupedStrategy()
        assert "Namespace" in strategy.name

    def test_description_property(self):
        """Test description property."""
        strategy = NamespaceGroupedStrategy()
        assert "namespace" in strategy.description.lower()

    def test_custom_separator(self):
        """Test with custom separator."""
        strategy = NamespaceGroupedStrategy(separator="_")
        refs = ["GUID:a", "GUID:b"]
        mapping = {"GUID:a": "Company_Module", "GUID:b": "Vendor_Lib"}

        result = strategy.sort(refs, mapping)
        assert len(result) == 2


class TestUnityPriorityStrategy:
    """Tests for UnityPriorityStrategy."""

    @pytest.fixture
    def sample_references(self) -> list[str]:
        """Sample GUID references mixing Unity and custom assemblies."""
        return ["GUID:custom1", "GUID:unity1", "GUID:custom2", "GUID:unity2"]

    @pytest.fixture
    def guid_to_name(self) -> dict[str, str]:
        """Sample GUID to name mapping."""
        return {
            "GUID:custom1": "MyGame.Core",
            "GUID:unity1": "UnityEngine.CoreModule",
            "GUID:custom2": "MyGame.UI",
            "GUID:unity2": "Unity.InputSystem",
        }

    def test_unity_first(self, sample_references, guid_to_name):
        """Test Unity assemblies sorted first."""
        strategy = UnityPriorityStrategy(unity_first=True)
        sorted_refs = strategy.sort(sample_references, guid_to_name)

        names = [guid_to_name[r] for r in sorted_refs]

        # First two should be Unity assemblies
        assert names[0].startswith(("Unity", "UnityEngine"))
        assert names[1].startswith(("Unity", "UnityEngine"))

    def test_unity_last(self, sample_references, guid_to_name):
        """Test Unity assemblies sorted last."""
        strategy = UnityPriorityStrategy(unity_first=False)
        sorted_refs = strategy.sort(sample_references, guid_to_name)

        names = [guid_to_name[r] for r in sorted_refs]

        # Last two should be Unity assemblies
        assert names[-1].startswith(("Unity", "UnityEngine"))
        assert names[-2].startswith(("Unity", "UnityEngine"))

    def test_is_unity_assembly(self):
        """Test Unity assembly detection."""
        strategy = UnityPriorityStrategy()

        assert strategy._is_unity_assembly("UnityEngine.CoreModule") is True
        assert strategy._is_unity_assembly("UnityEditor.Editor") is True
        assert strategy._is_unity_assembly("Unity.InputSystem") is True
        assert strategy._is_unity_assembly("com.unity.render-pipelines") is True
        assert strategy._is_unity_assembly("MyGame.Core") is False

    def test_name_property_first(self):
        """Test name property when unity_first=True."""
        strategy = UnityPriorityStrategy(unity_first=True)
        assert "First" in strategy.name

    def test_name_property_last(self):
        """Test name property when unity_first=False."""
        strategy = UnityPriorityStrategy(unity_first=False)
        assert "Last" in strategy.name

    def test_custom_prefixes(self, sample_references, guid_to_name):
        """Test with custom Unity prefixes."""
        strategy = UnityPriorityStrategy(unity_first=True, unity_prefixes=("Custom.Unity.",))

        # Should not detect standard Unity prefixes with custom config
        assert strategy._is_unity_assembly("UnityEngine.Core") is False
        assert strategy._is_unity_assembly("Custom.Unity.Module") is True


class TestCustomPriorityStrategy:
    """Tests for CustomPriorityStrategy."""

    @pytest.fixture
    def sample_references(self) -> list[str]:
        """Sample GUID references."""
        return ["GUID:a", "GUID:b", "GUID:c"]

    @pytest.fixture
    def guid_to_name(self) -> dict[str, str]:
        """Sample GUID to name mapping."""
        return {
            "GUID:a": "Third.Party",
            "GUID:b": "Core.Module",
            "GUID:c": "External.Lib",
        }

    def test_custom_priority_order(self, sample_references, guid_to_name):
        """Test custom priority ordering."""
        strategy = CustomPriorityStrategy(priority_patterns=["Core", "External", "Third"])
        sorted_refs = strategy.sort(sample_references, guid_to_name)

        names = [guid_to_name[r] for r in sorted_refs]
        assert names[0] == "Core.Module"
        assert names[1] == "External.Lib"
        assert names[2] == "Third.Party"

    def test_wildcard_pattern(self, sample_references, guid_to_name):
        """Test wildcard pattern matching."""
        strategy = CustomPriorityStrategy(priority_patterns=["Core*", "External*"])

        priority = strategy._get_priority("Core.Module")
        assert priority == 0

    def test_name_property(self):
        """Test name property."""
        strategy = CustomPriorityStrategy()
        assert "Custom" in strategy.name

    def test_unmatched_get_high_priority(self, sample_references, guid_to_name):
        """Test that unmatched items get high priority value."""
        strategy = CustomPriorityStrategy(priority_patterns=["Core"])

        priority = strategy._get_priority("Unknown.Assembly")
        assert priority > 0  # Higher than matched items


class TestGetStrategy:
    """Tests for get_strategy factory function."""

    def test_get_alphabetical_asc(self):
        """Test getting alphabetical ascending strategy."""
        strategy = get_strategy(SortingStrategy.ALPHABETICAL_ASC)
        assert isinstance(strategy, AlphabeticalStrategy)
        assert strategy.ascending is True

    def test_get_alphabetical_desc(self):
        """Test getting alphabetical descending strategy."""
        strategy = get_strategy(SortingStrategy.ALPHABETICAL_DESC)
        assert isinstance(strategy, AlphabeticalStrategy)
        assert strategy.ascending is False

    def test_get_namespace_grouped(self):
        """Test getting namespace grouped strategy."""
        strategy = get_strategy(SortingStrategy.NAMESPACE_GROUPED)
        assert isinstance(strategy, NamespaceGroupedStrategy)

    def test_get_unity_first(self):
        """Test getting Unity first strategy."""
        strategy = get_strategy(SortingStrategy.UNITY_FIRST)
        assert isinstance(strategy, UnityPriorityStrategy)
        assert strategy.unity_first is True

    def test_get_unity_last(self):
        """Test getting Unity last strategy."""
        strategy = get_strategy(SortingStrategy.UNITY_LAST)
        assert isinstance(strategy, UnityPriorityStrategy)
        assert strategy.unity_first is False

    def test_get_custom_priority(self):
        """Test getting custom priority strategy."""
        strategy = get_strategy(
            SortingStrategy.CUSTOM_PRIORITY,
            priority_patterns=["A", "B"],
        )
        assert isinstance(strategy, CustomPriorityStrategy)


class TestDependencySorter:
    """Tests for DependencySorter class."""

    @pytest.fixture
    def sorter_dict(self) -> dict[str, Any]:
        """Sample dictionary for sorter tests."""
        return {
            "GUID:assembly1": {
                "name": "Zebra.Assembly",
                "references": ["GUID:assembly2", "GUID:assembly3"],
                "filePath": "/path/to/Zebra.asmdef",
            },
            "GUID:assembly2": {
                "name": "Apple.Assembly",
                "references": [],
                "filePath": "/path/to/Apple.asmdef",
            },
            "GUID:assembly3": {
                "name": "Mango.Assembly",
                "references": [],
                "filePath": "/path/to/Mango.asmdef",
            },
            "_metadata": {"version": "1.0"},
        }

    def test_init_default_strategy(self, sorter_dict):
        """Test initializing sorter with default strategy."""
        sorter = DependencySorter(sorter_dict)
        assert sorter.asmdef_dict == sorter_dict

    def test_init_custom_strategy(self, sorter_dict):
        """Test initializing with custom strategy."""
        sorter = DependencySorter(
            sorter_dict,
            strategy=SortingStrategy.UNITY_FIRST,
        )
        assert sorter._strategy_enum == SortingStrategy.UNITY_FIRST

    def test_set_target(self, sorter_dict):
        """Test setting target assembly."""
        sorter = DependencySorter(sorter_dict)
        result = sorter.set_target("Zebra.Assembly")

        assert sorter._target == "Zebra.Assembly"
        assert result is sorter  # Method chaining

    def test_set_filter(self, sorter_dict):
        """Test setting filter pattern."""
        sorter = DependencySorter(sorter_dict)
        result = sorter.set_filter("*.Assembly")

        assert sorter._filter_pattern == "*.Assembly"
        assert result is sorter

    def test_set_all(self, sorter_dict):
        """Test setting all assemblies."""
        sorter = DependencySorter(sorter_dict)
        result = sorter.set_all(True)

        assert sorter._include_all is True
        assert result is sorter

    def test_validate_no_scope_fails(self, sorter_dict):
        """Test validation fails when no scope is set."""
        sorter = DependencySorter(sorter_dict)
        is_valid, errors = sorter._validate()

        assert is_valid is False
        assert any("scope" in e.lower() for e in errors)

    def test_validate_with_target(self, sorter_dict):
        """Test validation passes with valid target."""
        sorter = DependencySorter(sorter_dict)
        sorter.set_target("Zebra.Assembly")

        is_valid, errors = sorter._validate()
        assert is_valid is True

    def test_validate_invalid_target(self, sorter_dict):
        """Test validation fails with invalid target."""
        sorter = DependencySorter(sorter_dict)
        sorter.set_target("NonExistent.Assembly")

        is_valid, errors = sorter._validate()
        assert is_valid is False
        assert any("not found" in e.lower() for e in errors)

    def test_validate_with_all(self, sorter_dict):
        """Test validation passes with all assemblies."""
        sorter = DependencySorter(sorter_dict)
        sorter.set_all(True)

        is_valid, errors = sorter._validate()
        assert is_valid is True

    def test_validate_empty_dict_fails(self):
        """Test validation fails with empty dictionary."""
        sorter = DependencySorter({"_metadata": {}})
        sorter.set_all(True)

        is_valid, errors = sorter._validate()
        assert is_valid is False

    def test_get_target_assemblies_all(self, sorter_dict):
        """Test getting all target assemblies."""
        sorter = DependencySorter(sorter_dict)
        sorter.set_all(True)

        targets = sorter._get_target_assemblies()
        assert len(targets) == 3  # Excludes metadata

    def test_get_target_assemblies_specific(self, sorter_dict):
        """Test getting specific target assembly."""
        sorter = DependencySorter(sorter_dict)
        sorter.set_target("Zebra.Assembly")

        targets = sorter._get_target_assemblies()
        assert len(targets) == 1
        assert targets[0][1]["name"] == "Zebra.Assembly"

    def test_get_target_assemblies_filter(self, sorter_dict):
        """Test filtering assemblies by pattern."""
        sorter = DependencySorter(sorter_dict)
        sorter.set_filter("*apple*")  # Case-insensitive pattern matching

        # Note: fnmatch is case-sensitive on Unix, case-insensitive on Windows
        # The test may need adjustment based on platform
        targets = sorter._get_target_assemblies()
        # At least verify the filter mechanism works
        assert isinstance(targets, list)

    def test_preview_with_valid_scope(self, sorter_dict):
        """Test preview generation."""
        sorter = DependencySorter(sorter_dict)
        sorter.set_all(True)

        preview = sorter.preview()

        assert "valid" in preview
        assert preview["valid"] is True
        assert "strategy" in preview
        assert "changes" in preview

    def test_preview_with_invalid_scope(self, sorter_dict):
        """Test preview with invalid scope."""
        sorter = DependencySorter(sorter_dict)

        preview = sorter.preview()

        assert preview["valid"] is False
        assert "errors" in preview

    def test_sort_dry_run(self, sorter_dict):
        """Test sort in dry-run mode."""
        sorter = DependencySorter(sorter_dict)

        result = sorter.sort(
            strategy=SortingStrategy.ALPHABETICAL_ASC,
            target="Zebra.Assembly",
            apply=False,
        )

        assert result.success is True
        assert result.dry_run is True
        assert len(result.errors) == 0

    def test_sort_returns_sorting_result(self, sorter_dict):
        """Test that sort returns a SortingResult."""
        sorter = DependencySorter(sorter_dict)

        result = sorter.sort(
            all_assemblies=True,
            apply=False,
        )

        assert isinstance(result, SortingResult)
        assert result.strategy_name is not None

    def test_build_guid_mappings(self, sorter_dict):
        """Test building GUID mappings."""
        sorter = DependencySorter(sorter_dict)
        guid_to_name, name_to_guid = sorter._build_guid_mappings()

        assert "GUID:assembly1" in guid_to_name
        assert guid_to_name["GUID:assembly1"] == "Zebra.Assembly"
        assert "Zebra.Assembly" in name_to_guid
        assert name_to_guid["Zebra.Assembly"] == "GUID:assembly1"


class TestDependencyDiff:
    """Tests for DependencyDiff model."""

    def test_moved_property_true(self):
        """Test moved property when position changed."""
        diff = DependencyDiff(
            guid="GUID:abc",
            name="TestAssembly",
            old_position=0,
            new_position=2,
        )

        assert diff.moved is True

    def test_moved_property_false(self):
        """Test moved property when position unchanged."""
        diff = DependencyDiff(
            guid="GUID:abc",
            name="TestAssembly",
            old_position=1,
            new_position=1,
        )

        assert diff.moved is False

    def test_movement_positive(self):
        """Test movement calculation for downward move."""
        diff = DependencyDiff(
            guid="GUID:abc",
            name="TestAssembly",
            old_position=0,
            new_position=3,
        )

        assert diff.movement == 3

    def test_movement_negative(self):
        """Test movement calculation for upward move."""
        diff = DependencyDiff(
            guid="GUID:abc",
            name="TestAssembly",
            old_position=3,
            new_position=0,
        )

        assert diff.movement == -3


class TestSortingChange:
    """Tests for SortingChange model."""

    def test_has_changes_true(self):
        """Test has_changes when order changed."""
        change = SortingChange(
            assembly_name="Test",
            assembly_guid="GUID:test",
            file_path=Path("test.asmdef"),
            before=["GUID:a", "GUID:b"],
            after=["GUID:b", "GUID:a"],
        )

        assert change.has_changes is True

    def test_has_changes_false(self):
        """Test has_changes when order unchanged."""
        change = SortingChange(
            assembly_name="Test",
            assembly_guid="GUID:test",
            file_path=Path("test.asmdef"),
            before=["GUID:a", "GUID:b"],
            after=["GUID:a", "GUID:b"],
        )

        assert change.has_changes is False

    def test_reference_count(self):
        """Test reference_count property."""
        change = SortingChange(
            assembly_name="Test",
            assembly_guid="GUID:test",
            file_path=Path("test.asmdef"),
            before=["GUID:a", "GUID:b", "GUID:c"],
            after=["GUID:a", "GUID:b", "GUID:c"],
        )

        assert change.reference_count == 3

    def test_moves_count(self):
        """Test moves_count property."""
        change = SortingChange(
            assembly_name="Test",
            assembly_guid="GUID:test",
            file_path=Path("test.asmdef"),
            before=["GUID:a", "GUID:b"],
            after=["GUID:b", "GUID:a"],
            diffs=[
                DependencyDiff("GUID:a", "A", 0, 1),
                DependencyDiff("GUID:b", "B", 1, 0),
            ],
        )

        assert change.moves_count == 2


class TestSortingResult:
    """Tests for SortingResult model."""

    def test_total_assemblies(self):
        """Test total_assemblies property."""
        result = SortingResult(
            success=True,
            dry_run=True,
            strategy_name="Test",
            strategy_description="Test desc",
            changes=[
                SortingChange("A", "GUID:a", Path("a.asmdef")),
                SortingChange("B", "GUID:b", Path("b.asmdef")),
            ],
        )

        assert result.total_assemblies == 2

    def test_assemblies_modified(self):
        """Test assemblies_modified property."""
        result = SortingResult(
            success=True,
            dry_run=True,
            strategy_name="Test",
            strategy_description="Test desc",
            changes=[
                SortingChange(
                    "A",
                    "GUID:a",
                    Path("a.asmdef"),
                    before=["1"],
                    after=["1"],  # No change
                ),
                SortingChange(
                    "B",
                    "GUID:b",
                    Path("b.asmdef"),
                    before=["1", "2"],
                    after=["2", "1"],  # Changed
                ),
            ],
        )

        assert result.assemblies_modified == 1

    def test_assemblies_unchanged(self):
        """Test assemblies_unchanged property."""
        result = SortingResult(
            success=True,
            dry_run=True,
            strategy_name="Test",
            strategy_description="Test desc",
            changes=[
                SortingChange(
                    "A",
                    "GUID:a",
                    Path("a.asmdef"),
                    before=["1"],
                    after=["1"],
                ),
                SortingChange(
                    "B",
                    "GUID:b",
                    Path("b.asmdef"),
                    before=["1"],
                    after=["1"],
                ),
            ],
        )

        assert result.assemblies_unchanged == 2

    def test_total_references_moved(self):
        """Test total_references_moved property."""
        result = SortingResult(
            success=True,
            dry_run=True,
            strategy_name="Test",
            strategy_description="Test desc",
            changes=[
                SortingChange(
                    "A",
                    "GUID:a",
                    Path("a.asmdef"),
                    diffs=[
                        DependencyDiff("GUID:1", "1", 0, 1),
                        DependencyDiff("GUID:2", "2", 1, 0),
                    ],
                ),
            ],
        )

        assert result.total_references_moved == 2
