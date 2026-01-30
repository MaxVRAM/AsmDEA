"""Models for sorting and enforcement operations.

Data classes representing sorting operation results, change tracking,
and enforcement outcomes.

Key models:
    - SortingChange: Represents a single file's before/after state
    - SortingResult: Complete result of a sorting operation
    - DependencyDiff: Diff information for a single assembly

Usage:
    from models import SortingResult, SortingChange

    change = SortingChange(
        assembly_name="MyAssembly",
        file_path=Path("MyAssembly.asmdef"),
        before=["GUID:a", "GUID:b"],
        after=["GUID:b", "GUID:a"],
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class DependencyDiff:
    """Diff information for a dependency list change.

    Attributes:
        guid: The GUID reference
        name: Resolved assembly name
        old_position: Previous position in list (0-indexed)
        new_position: New position in list (0-indexed)
        moved: Whether this reference moved
    """

    guid: str
    name: str
    old_position: int
    new_position: int

    @property
    def moved(self) -> bool:
        """Check if this reference position changed."""
        return self.old_position != self.new_position

    @property
    def movement(self) -> int:
        """How many positions this reference moved (negative = up, positive = down)."""
        return self.new_position - self.old_position


@dataclass
class SortingChange:
    """Represents a sorting change for a single assembly.

    Attributes:
        assembly_name: Name of the assembly being sorted
        assembly_guid: GUID of the assembly
        file_path: Path to the .asmdef file
        before: Original reference order (GUIDs)
        after: New reference order (GUIDs)
        before_names: Original order with resolved names
        after_names: New order with resolved names
        diffs: Detailed diff information for each reference
    """

    assembly_name: str
    assembly_guid: str
    file_path: Path
    before: list[str] = field(default_factory=list)
    after: list[str] = field(default_factory=list)
    before_names: list[str] = field(default_factory=list)
    after_names: list[str] = field(default_factory=list)
    diffs: list[DependencyDiff] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """Check if the sort order actually changed."""
        return self.before != self.after

    @property
    def reference_count(self) -> int:
        """Number of references in this assembly."""
        return len(self.before)

    @property
    def moves_count(self) -> int:
        """Number of references that moved position."""
        return sum(1 for d in self.diffs if d.moved)


@dataclass
class SortingResult:
    """Complete result of a sorting operation.

    Attributes:
        success: Whether the operation completed successfully
        dry_run: Whether this was a dry-run (preview only)
        strategy_name: Name of the sorting strategy used
        strategy_description: Description of the strategy
        changes: List of changes for each assembly
        backup_path: Path to backup (if changes were applied)
        errors: List of error messages
        timestamp: When the operation was performed
        target_filter: Target filter that was applied (if any)
    """

    success: bool
    dry_run: bool
    strategy_name: str
    strategy_description: str
    changes: list[SortingChange] = field(default_factory=list)
    backup_path: Path | None = None
    errors: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    target_filter: str | None = None

    @property
    def total_assemblies(self) -> int:
        """Total number of assemblies processed."""
        return len(self.changes)

    @property
    def assemblies_modified(self) -> int:
        """Number of assemblies with actual changes."""
        return sum(1 for c in self.changes if c.has_changes)

    @property
    def assemblies_unchanged(self) -> int:
        """Number of assemblies already in correct order."""
        return self.total_assemblies - self.assemblies_modified

    @property
    def total_references_moved(self) -> int:
        """Total number of references that moved across all assemblies."""
        return sum(c.moves_count for c in self.changes)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "dry_run": self.dry_run,
            "strategy": {
                "name": self.strategy_name,
                "description": self.strategy_description,
            },
            "summary": {
                "total_assemblies": self.total_assemblies,
                "assemblies_modified": self.assemblies_modified,
                "assemblies_unchanged": self.assemblies_unchanged,
                "total_references_moved": self.total_references_moved,
            },
            "changes": [
                {
                    "assembly_name": c.assembly_name,
                    "assembly_guid": c.assembly_guid,
                    "file_path": str(c.file_path),
                    "has_changes": c.has_changes,
                    "reference_count": c.reference_count,
                    "moves_count": c.moves_count,
                    "before": c.before_names,
                    "after": c.after_names,
                }
                for c in self.changes
            ],
            "backup_path": str(self.backup_path) if self.backup_path else None,
            "errors": self.errors,
            "timestamp": self.timestamp.isoformat(),
            "target_filter": self.target_filter,
        }
