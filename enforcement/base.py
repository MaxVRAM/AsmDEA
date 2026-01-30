"""Base enforcer class for modification operations.

Provides an abstract base class that all enforcement modules inherit from,
ensuring consistent backup handling, dry-run support, and modification tracking.

Key classes:
    - BaseEnforcer: Abstract base for all enforcement implementations
    - EnforcementMode: Enum for dry-run vs apply modes

Subclasses must implement:
    - _validate: Validate preconditions before enforcement
    - _execute: Perform the actual enforcement operation
    - _generate_preview: Generate a preview of changes

Usage:
    from enforcement import BaseEnforcer

    class MyEnforcer(BaseEnforcer):
        def _validate(self):
            return True

        def _execute(self, dry_run):
            # Perform modifications
            pass

        def _generate_preview(self):
            return {"changes": [...]}
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any

from common import get_logger
from common.backup import BackupManager

logger = get_logger(__name__)


class EnforcementMode(Enum):
    """Mode for enforcement operations."""

    DRY_RUN = auto()  # Preview changes only, no modifications
    APPLY = auto()  # Apply changes to files


@dataclass
class EnforcementResult:
    """Result of an enforcement operation.

    Attributes:
        success: Whether the operation completed successfully
        mode: The enforcement mode used (dry-run or apply)
        modified_files: List of files that were (or would be) modified
        backup_path: Path to backup directory (if changes were applied)
        changes: List of change descriptions
        errors: List of error messages
        timestamp: When the operation was performed
    """

    success: bool
    mode: EnforcementMode
    modified_files: list[Path] = field(default_factory=list)
    backup_path: Path | None = None
    changes: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def is_dry_run(self) -> bool:
        """Check if this was a dry-run operation."""
        return self.mode == EnforcementMode.DRY_RUN

    @property
    def files_affected(self) -> int:
        """Number of files affected by this operation."""
        return len(self.modified_files)


class BaseEnforcer(ABC):
    """Base class for all enforcement operations.

    Provides common functionality for backup management, dry-run support,
    and consistent result reporting.

    Attributes:
        asmdef_dict: The loaded asmdef dictionary
        backup_manager: Manager for backup/restore operations
    """

    def __init__(
        self,
        asmdef_dict: dict[str, Any],
        backup_dir: Path | None = None,
    ):
        """Initialize enforcer.

        Args:
            asmdef_dict: Loaded asmdef dictionary with assembly data
            backup_dir: Directory for backups (default: .asmdea_backups)
        """
        self.asmdef_dict = asmdef_dict
        self._backup_dir = backup_dir or Path(".asmdea_backups")
        self._backup_manager: BackupManager | None = None

    @property
    def backup_manager(self) -> BackupManager:
        """Get or create the backup manager."""
        if self._backup_manager is None:
            self._backup_manager = BackupManager(self._backup_dir)
        return self._backup_manager

    @abstractmethod
    def _validate(self) -> tuple[bool, list[str]]:
        """Validate preconditions before enforcement.

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        pass

    @abstractmethod
    def _execute(self, dry_run: bool = True) -> EnforcementResult:
        """Execute the enforcement operation.

        Args:
            dry_run: If True, only preview changes without modifying files

        Returns:
            EnforcementResult with operation details
        """
        pass

    @abstractmethod
    def _generate_preview(self) -> dict[str, Any]:
        """Generate a preview of changes that would be made.

        Returns:
            Dictionary describing the proposed changes
        """
        pass

    def enforce(self, apply: bool = False) -> EnforcementResult:
        """Run the enforcement operation.

        This is the main entry point for enforcement. By default, runs in
        dry-run mode (preview only). Pass apply=True to make actual changes.

        Args:
            apply: If True, apply changes. If False (default), dry-run only.

        Returns:
            EnforcementResult with operation outcome
        """
        mode = EnforcementMode.APPLY if apply else EnforcementMode.DRY_RUN

        # Validate preconditions
        is_valid, errors = self._validate()
        if not is_valid:
            return EnforcementResult(
                success=False,
                mode=mode,
                errors=errors,
            )

        # Execute the operation
        try:
            result = self._execute(dry_run=not apply)
            return result
        except Exception as e:
            logger.exception("Enforcement operation failed")
            return EnforcementResult(
                success=False,
                mode=mode,
                errors=[f"Enforcement failed: {e}"],
            )

    def preview(self) -> dict[str, Any]:
        """Get a preview of changes without executing.

        Returns:
            Dictionary describing proposed changes
        """
        is_valid, errors = self._validate()
        if not is_valid:
            return {"valid": False, "errors": errors}

        preview = self._generate_preview()
        preview["valid"] = True
        return preview

    def _build_guid_mappings(self) -> tuple[dict[str, str], dict[str, str]]:
        """Build GUID to name and name to GUID mappings.

        Returns:
            Tuple of (guid_to_name, name_to_guid) dictionaries
        """
        from common import METADATA_KEY

        guid_to_name: dict[str, str] = {}
        name_to_guid: dict[str, str] = {}

        for guid, data in self.asmdef_dict.items():
            if guid == METADATA_KEY:
                continue
            if isinstance(data, dict):
                name = data.get("name", guid)
                guid_to_name[guid] = name
                name_to_guid[name] = guid

        return guid_to_name, name_to_guid
