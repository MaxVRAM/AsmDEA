"""Dependency Sorter enforcement module.

Sorts assembly definition references using configurable strategies.
Operates on GUID-based references but sorts using resolved human-readable
names, then writes the reordered GUIDs back to the .asmdef files.

Key class:
    - DependencySorter: Main enforcer for sorting dependencies

Usage:
    from enforcement import DependencySorter, SortingStrategy

    sorter = DependencySorter(asmdef_dict)

    # Preview changes (dry-run)
    result = sorter.sort(strategy=SortingStrategy.ALPHABETICAL_ASC)

    # Apply changes
    result = sorter.sort(
        strategy=SortingStrategy.UNITY_FIRST,
        apply=True,
        target="MyAssembly"
    )
"""

from __future__ import annotations

import fnmatch
import json
from pathlib import Path
from typing import Any

from common import METADATA_KEY, get_logger
from models.sorting_result import DependencyDiff, SortingChange, SortingResult

from .base import BaseEnforcer, EnforcementMode, EnforcementResult
from .sorting_strategies import (
    SortingStrategy,
    get_strategy,
)

logger = get_logger(__name__)


class DependencySorter(BaseEnforcer):
    """Sorts assembly references using configurable strategies.

    This enforcer reads assembly definitions from the asmdef dictionary,
    resolves GUID references to names for sorting, applies the chosen
    sorting strategy, and writes the reordered references back.

    Attributes:
        strategy: The sorting strategy to use
        target: Optional target assembly name or pattern
        filter_pattern: Optional glob pattern for filtering assemblies
    """

    def __init__(
        self,
        asmdef_dict: dict[str, Any],
        strategy: SortingStrategy = SortingStrategy.ALPHABETICAL_ASC,
        backup_dir: Path | None = None,
        **strategy_kwargs,
    ):
        """Initialize the dependency sorter.

        Args:
            asmdef_dict: Loaded asmdef dictionary
            strategy: Sorting strategy to use
            backup_dir: Directory for backups
            **strategy_kwargs: Additional arguments for strategy initialization
        """
        super().__init__(asmdef_dict, backup_dir)
        self._strategy_enum = strategy
        self._strategy = get_strategy(strategy, **strategy_kwargs)
        self._strategy_kwargs = strategy_kwargs
        self._target: str | None = None
        self._filter_pattern: str | None = None
        self._include_all: bool = False

    def set_target(self, target: str | None) -> DependencySorter:
        """Set a specific assembly target by name.

        Args:
            target: Exact assembly name to sort

        Returns:
            Self for method chaining
        """
        self._target = target
        return self

    def set_filter(self, pattern: str | None) -> DependencySorter:
        """Set a glob pattern to filter assemblies.

        Args:
            pattern: Glob pattern (e.g., "*.Tests", "MyCompany.*")

        Returns:
            Self for method chaining
        """
        self._filter_pattern = pattern
        return self

    def set_all(self, include_all: bool = True) -> DependencySorter:
        """Include all assemblies in sorting.

        Args:
            include_all: Whether to sort all assemblies

        Returns:
            Self for method chaining
        """
        self._include_all = include_all
        return self

    def _validate(self) -> tuple[bool, list[str]]:
        """Validate preconditions for sorting."""
        errors: list[str] = []

        # Check that we have assemblies to sort
        assembly_count = sum(
            1 for k in self.asmdef_dict if k != METADATA_KEY
        )
        if assembly_count == 0:
            errors.append("No assemblies found in dictionary")

        # Check that at least one scope option is set
        if not (self._target or self._filter_pattern or self._include_all):
            errors.append(
                "No scope specified. Use --target, --filter, or --all to specify assemblies to sort"
            )

        # If target specified, verify it exists
        if self._target:
            guid_to_name, name_to_guid = self._build_guid_mappings()
            if self._target not in name_to_guid:
                errors.append(f"Target assembly not found: {self._target}")

        return len(errors) == 0, errors

    def _get_target_assemblies(self) -> list[tuple[str, dict[str, Any]]]:
        """Get the list of assemblies to process based on scope settings.

        Returns:
            List of (guid, data) tuples for assemblies to sort
        """
        guid_to_name, name_to_guid = self._build_guid_mappings()
        targets: list[tuple[str, dict[str, Any]]] = []

        for guid, data in self.asmdef_dict.items():
            if guid == METADATA_KEY:
                continue
            if not isinstance(data, dict):
                continue

            name = data.get("name", guid)

            # Apply filters
            if self._target:
                if name != self._target:
                    continue
            elif self._filter_pattern:
                if not fnmatch.fnmatch(name, self._filter_pattern):
                    continue
            elif not self._include_all:
                continue

            targets.append((guid, data))

        return targets

    def _compute_changes(
        self,
        targets: list[tuple[str, dict[str, Any]]],
    ) -> list[SortingChange]:
        """Compute the sorting changes for target assemblies.

        Args:
            targets: List of (guid, data) tuples to process

        Returns:
            List of SortingChange objects
        """
        guid_to_name, _ = self._build_guid_mappings()
        changes: list[SortingChange] = []

        for guid, data in targets:
            name = data.get("name", guid)
            references = data.get("references", [])
            file_path_str = data.get("file_path", data.get("filePath", ""))
            file_path = Path(file_path_str) if file_path_str else Path()

            if not references:
                # No references to sort
                continue

            # Apply sorting strategy
            sorted_refs = self._strategy.sort(references, guid_to_name)

            # Build diff information
            before_names = [guid_to_name.get(r, r) for r in references]
            after_names = [guid_to_name.get(r, r) for r in sorted_refs]

            diffs: list[DependencyDiff] = []
            for i, ref in enumerate(references):
                new_pos = sorted_refs.index(ref)
                diffs.append(
                    DependencyDiff(
                        guid=ref,
                        name=guid_to_name.get(ref, ref),
                        old_position=i,
                        new_position=new_pos,
                    )
                )

            changes.append(
                SortingChange(
                    assembly_name=name,
                    assembly_guid=guid,
                    file_path=file_path,
                    before=references.copy(),
                    after=sorted_refs,
                    before_names=before_names,
                    after_names=after_names,
                    diffs=diffs,
                )
            )

        return changes

    def _execute(self, dry_run: bool = True) -> EnforcementResult:
        """Execute the sorting operation.

        Args:
            dry_run: If True, only preview changes

        Returns:
            EnforcementResult with operation details
        """
        mode = EnforcementMode.DRY_RUN if dry_run else EnforcementMode.APPLY
        targets = self._get_target_assemblies()
        changes = self._compute_changes(targets)

        # Filter to only assemblies with actual changes
        modified_changes = [c for c in changes if c.has_changes]

        if not modified_changes:
            return EnforcementResult(
                success=True,
                mode=mode,
                changes=[
                    {
                        "assembly": c.assembly_name,
                        "status": "unchanged",
                        "references": c.reference_count,
                    }
                    for c in changes
                ],
            )

        backup_path: Path | None = None
        modified_files: list[Path] = []

        if not dry_run:
            # Create backup before modifications
            files_to_backup = [c.file_path for c in modified_changes if c.file_path.exists()]
            if files_to_backup:
                backup_path = self.backup_manager.create_backup(
                    files=files_to_backup,
                    operation="sort-deps",
                    description=f"Before sorting with strategy: {self._strategy.name}",
                )

            # Apply changes to files
            for change in modified_changes:
                if not change.file_path.exists():
                    logger.warning("File not found: %s", change.file_path)
                    continue

                try:
                    self._write_sorted_references(change)
                    modified_files.append(change.file_path)
                except Exception as e:
                    logger.error("Failed to write %s: %s", change.file_path, e)
                    # Attempt restore on failure
                    if backup_path:
                        self.backup_manager.restore_backup(backup_path)
                    return EnforcementResult(
                        success=False,
                        mode=mode,
                        errors=[f"Failed to write {change.file_path}: {e}"],
                        backup_path=backup_path,
                    )

        return EnforcementResult(
            success=True,
            mode=mode,
            modified_files=modified_files,
            backup_path=backup_path,
            changes=[
                {
                    "assembly": c.assembly_name,
                    "status": "modified" if c.has_changes else "unchanged",
                    "references": c.reference_count,
                    "moves": c.moves_count,
                }
                for c in changes
            ],
        )

    def _write_sorted_references(self, change: SortingChange) -> None:
        """Write sorted references back to the asmdef file.

        Preserves the original file structure and only modifies the
        references array order.

        Args:
            change: The SortingChange with new reference order
        """
        file_path = change.file_path

        # Read original file content
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Parse JSON
        data = json.loads(content)

        # Update references with sorted order
        data["references"] = change.after

        # Write back with consistent formatting
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")  # Trailing newline

        logger.debug("Updated references in %s", file_path)

    def _generate_preview(self) -> dict[str, Any]:
        """Generate a preview of sorting changes."""
        targets = self._get_target_assemblies()
        changes = self._compute_changes(targets)

        return {
            "strategy": {
                "name": self._strategy.name,
                "description": self._strategy.description,
            },
            "scope": {
                "target": self._target,
                "filter": self._filter_pattern,
                "all": self._include_all,
            },
            "summary": {
                "total_assemblies": len(changes),
                "will_modify": sum(1 for c in changes if c.has_changes),
                "already_sorted": sum(1 for c in changes if not c.has_changes),
            },
            "changes": [
                {
                    "assembly": c.assembly_name,
                    "file": str(c.file_path),
                    "has_changes": c.has_changes,
                    "before": c.before_names,
                    "after": c.after_names,
                }
                for c in changes
            ],
        }

    def sort(
        self,
        strategy: SortingStrategy | None = None,
        apply: bool = False,
        target: str | None = None,
        filter_pattern: str | None = None,
        all_assemblies: bool = False,
        **strategy_kwargs,
    ) -> SortingResult:
        """Execute the sorting operation with the given parameters.

        This is the main public API for sorting dependencies.

        Args:
            strategy: Override the sorting strategy
            apply: If True, apply changes. If False (default), dry-run.
            target: Specific assembly name to sort
            filter_pattern: Glob pattern for filtering assemblies
            all_assemblies: Sort all assemblies
            **strategy_kwargs: Additional strategy configuration

        Returns:
            SortingResult with complete operation details
        """
        # Update strategy if provided
        if strategy is not None:
            self._strategy_enum = strategy
            kwargs = {**self._strategy_kwargs, **strategy_kwargs}
            self._strategy = get_strategy(strategy, **kwargs)

        # Update scope
        if target:
            self.set_target(target)
        if filter_pattern:
            self.set_filter(filter_pattern)
        if all_assemblies:
            self.set_all(True)

        # Validate
        is_valid, errors = self._validate()
        if not is_valid:
            return SortingResult(
                success=False,
                dry_run=not apply,
                strategy_name=self._strategy.name,
                strategy_description=self._strategy.description,
                errors=errors,
                target_filter=target or filter_pattern,
            )

        # Compute changes
        targets = self._get_target_assemblies()
        changes = self._compute_changes(targets)

        # Execute
        result = self._execute(dry_run=not apply)

        return SortingResult(
            success=result.success,
            dry_run=not apply,
            strategy_name=self._strategy.name,
            strategy_description=self._strategy.description,
            changes=changes,
            backup_path=result.backup_path,
            errors=result.errors,
            target_filter=target or filter_pattern,
        )
