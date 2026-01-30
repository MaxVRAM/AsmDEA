"""Backup and restore functionality for safe file modifications.

Provides a comprehensive backup system to protect against data loss when
modifying .asmdef files. Creates timestamped backups with manifests for
easy restoration.

Key classes:
    - BackupManager: Handles backup creation, manifest tracking, and restoration

Usage:
    from common.backup import BackupManager

    manager = BackupManager(backup_dir=Path(".asmdea_backups"))

    # Create backup before modifications
    backup_path = manager.create_backup(
        files=[Path("Assembly.asmdef")],
        operation="sort-deps"
    )

    # Later, restore if needed
    manager.restore_backup(backup_path)

    # List available backups
    backups = manager.list_backups()
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class BackupManifest:
    """Manifest describing a backup operation.

    Attributes:
        backup_id: Unique identifier for this backup
        created_at: Timestamp when backup was created
        operation: Name of the operation that triggered the backup
        files: List of backed up files with their original paths
        description: Optional description of the backup
        asmdea_version: Version of AsmDEA that created the backup
    """

    backup_id: str
    created_at: str
    operation: str
    files: list[dict[str, str]]
    description: str = ""
    asmdea_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert manifest to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BackupManifest:
        """Create manifest from dictionary."""
        return cls(
            backup_id=data["backup_id"],
            created_at=data["created_at"],
            operation=data["operation"],
            files=data["files"],
            description=data.get("description", ""),
            asmdea_version=data.get("asmdea_version", "unknown"),
        )


@dataclass
class BackupInfo:
    """Summary information about a backup.

    Attributes:
        backup_id: Unique identifier
        path: Path to backup directory
        created_at: When the backup was created
        operation: What operation created the backup
        file_count: Number of files in the backup
        description: Optional description
    """

    backup_id: str
    path: Path
    created_at: datetime
    operation: str
    file_count: int
    description: str = ""


class BackupManager:
    """Manages backup and restore operations for asmdef files.

    Creates timestamped backup directories containing:
    - Copies of all modified files
    - A manifest.json describing the backup
    - Original file paths for restoration

    Attributes:
        backup_dir: Root directory for all backups
    """

    MANIFEST_FILENAME = "manifest.json"
    TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

    def __init__(self, backup_dir: Path | str):
        """Initialize backup manager.

        Args:
            backup_dir: Root directory where backups will be stored
        """
        self.backup_dir = Path(backup_dir)

    def create_backup(
        self,
        files: list[Path],
        operation: str,
        description: str = "",
    ) -> Path:
        """Create a backup of the specified files.

        Args:
            files: List of file paths to back up
            operation: Name of the operation triggering the backup
            description: Optional description of why backup was created

        Returns:
            Path to the backup directory

        Raises:
            FileNotFoundError: If any source file doesn't exist
            OSError: If backup directory cannot be created
        """
        # Generate backup ID and create directory
        timestamp = datetime.now()
        backup_id = f"{operation}_{timestamp.strftime(self.TIMESTAMP_FORMAT)}"
        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(parents=True, exist_ok=True)

        # Track backed up files for manifest
        backed_up_files: list[dict[str, str]] = []

        for source_file in files:
            if not source_file.exists():
                raise FileNotFoundError(f"Cannot backup non-existent file: {source_file}")

            # Create a unique filename preserving the original name
            # Use hash of full path to handle files with same name in different dirs
            path_hash = hex(hash(str(source_file.resolve())))[-8:]
            backup_filename = f"{path_hash}_{source_file.name}"
            dest_file = backup_path / backup_filename

            # Copy the file
            shutil.copy2(source_file, dest_file)

            backed_up_files.append(
                {
                    "original_path": str(source_file.resolve()),
                    "backup_filename": backup_filename,
                }
            )

            logger.debug("Backed up %s -> %s", source_file, dest_file)

        # Create and save manifest
        manifest = BackupManifest(
            backup_id=backup_id,
            created_at=timestamp.isoformat(),
            operation=operation,
            files=backed_up_files,
            description=description,
        )

        manifest_path = backup_path / self.MANIFEST_FILENAME
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2)

        logger.info("Created backup: %s (%d files)", backup_id, len(files))
        return backup_path

    def restore_backup(self, backup_path: Path | str) -> list[Path]:
        """Restore files from a backup.

        Args:
            backup_path: Path to the backup directory

        Returns:
            List of restored file paths

        Raises:
            FileNotFoundError: If backup directory or manifest doesn't exist
            ValueError: If manifest is invalid
        """
        backup_path = Path(backup_path)

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup directory not found: {backup_path}")

        manifest_path = backup_path / self.MANIFEST_FILENAME
        if not manifest_path.exists():
            raise FileNotFoundError(f"Backup manifest not found: {manifest_path}")

        # Load manifest
        with open(manifest_path, encoding="utf-8") as f:
            manifest_data = json.load(f)

        manifest = BackupManifest.from_dict(manifest_data)
        restored_files: list[Path] = []

        for file_info in manifest.files:
            original_path = Path(file_info["original_path"])
            backup_filename = file_info["backup_filename"]
            backup_file = backup_path / backup_filename

            if not backup_file.exists():
                logger.warning("Backup file missing: %s", backup_file)
                continue

            # Restore the file
            shutil.copy2(backup_file, original_path)
            restored_files.append(original_path)
            logger.debug("Restored %s -> %s", backup_file, original_path)

        logger.info(
            "Restored backup %s (%d files)",
            manifest.backup_id,
            len(restored_files),
        )
        return restored_files

    def list_backups(self) -> list[BackupInfo]:
        """List all available backups.

        Returns:
            List of BackupInfo objects, sorted by creation time (newest first)
        """
        if not self.backup_dir.exists():
            return []

        backups: list[BackupInfo] = []

        for entry in self.backup_dir.iterdir():
            if not entry.is_dir():
                continue

            manifest_path = entry / self.MANIFEST_FILENAME
            if not manifest_path.exists():
                continue

            try:
                with open(manifest_path, encoding="utf-8") as f:
                    manifest_data = json.load(f)

                manifest = BackupManifest.from_dict(manifest_data)
                created_at = datetime.fromisoformat(manifest.created_at)

                backups.append(
                    BackupInfo(
                        backup_id=manifest.backup_id,
                        path=entry,
                        created_at=created_at,
                        operation=manifest.operation,
                        file_count=len(manifest.files),
                        description=manifest.description,
                    )
                )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning("Invalid backup manifest in %s: %s", entry, e)
                continue

        # Sort by creation time, newest first
        backups.sort(key=lambda b: b.created_at, reverse=True)
        return backups

    def get_backup(self, backup_id: str) -> BackupInfo | None:
        """Get information about a specific backup.

        Args:
            backup_id: The backup identifier

        Returns:
            BackupInfo if found, None otherwise
        """
        for backup in self.list_backups():
            if backup.backup_id == backup_id:
                return backup
        return None

    def delete_backup(self, backup_path: Path | str) -> bool:
        """Delete a backup directory.

        Args:
            backup_path: Path to the backup directory

        Returns:
            True if deleted, False if not found
        """
        backup_path = Path(backup_path)

        if not backup_path.exists():
            return False

        shutil.rmtree(backup_path)
        logger.info("Deleted backup: %s", backup_path.name)
        return True

    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """Remove old backups, keeping only the most recent ones.

        Args:
            keep_count: Number of backups to keep

        Returns:
            Number of backups deleted
        """
        backups = self.list_backups()

        if len(backups) <= keep_count:
            return 0

        deleted = 0
        for backup in backups[keep_count:]:
            if self.delete_backup(backup.path):
                deleted += 1

        logger.info("Cleaned up %d old backups", deleted)
        return deleted
