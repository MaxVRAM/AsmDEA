"""Path validation utilities.

Provides functions for validating file system paths with consistent error
handling. Ensures paths exist and are of the expected type before processing.

Key functions:
    - validate_directory: Ensures a path exists and is a directory
    - format_path: Format a path as absolute or relative-to-root for reporting

Usage:
    from common import validate_directory

    root_path = validate_directory("/path/to/project")
"""

import sys
from enum import Enum
from pathlib import Path

from .logging_config import get_logger

logger = get_logger(__name__)


class FilepathType(str, Enum):
    """How file paths should be rendered in reporter outputs."""

    ABSOLUTE = "absolute"
    RELATIVE = "relative"

    @classmethod
    def parse(cls, value: str | None, default: "FilepathType" = None) -> "FilepathType":
        """Parse a string value (from env/CLI) to FilepathType.

        Falls back to ``default`` on None/empty/unknown values (with a warning
        for unknown values). ``default`` itself defaults to RELATIVE.
        """
        if default is None:
            default = cls.RELATIVE
        if value is None or value == "":
            return default
        normalized = value.strip().lower()
        try:
            return cls(normalized)
        except ValueError:
            logger.warning(
                "Unknown filepath type '%s'; falling back to '%s'.", value, default.value
            )
            return default


def format_path(
    path: Path | str,
    filepath_type: FilepathType,
    root_path: Path | None,
) -> str:
    """Format ``path`` for reporting as absolute or relative-to-root.

    Always emits forward slashes for stable cross-platform output.

    Args:
        path: The path to format. Absolute or relative; strings are accepted.
        filepath_type: ABSOLUTE returns a resolved absolute path; RELATIVE
            returns the path made relative to ``root_path``.
        root_path: Project root used as the base for RELATIVE formatting. If
            ``None``, the path is returned resolved+absolute regardless of type.

    Returns:
        POSIX-style string representation of the path.
    """
    p = Path(path)

    # ABSOLUTE, or RELATIVE with no root to relativise against: return resolved absolute.
    if filepath_type == FilepathType.ABSOLUTE or root_path is None:
        try:
            return p.resolve().as_posix()
        except OSError:
            return p.as_posix()

    # RELATIVE: make absolute first, then relativise under root_path.
    root_abs = Path(root_path).resolve()
    try:
        absolute = p if p.is_absolute() else (root_abs / p).resolve()
    except OSError:
        absolute = p if p.is_absolute() else root_abs / p

    try:
        return absolute.relative_to(root_abs).as_posix()
    except ValueError:
        # Path is outside root — fall back to absolute so we never raise at
        # format time. Caller can still read the JSON/console output.
        logger.debug(
            "Path '%s' is not under root '%s'; emitting absolute form.", absolute, root_abs
        )
        return absolute.as_posix()


def validate_directory(path: Path | str, error_prefix: str = "Root path") -> Path:
    """
    Validate that path exists and is a directory.

    Args:
        path: Path to validate
        error_prefix: Prefix for error messages

    Returns:
        Resolved absolute Path object

    Raises:
        SystemExit: If path doesn't exist or is not a directory
    """
    resolved = Path(path).resolve()

    if not resolved.exists():
        logger.error("%s '%s' does not exist.", error_prefix, path)
        sys.exit(1)

    if not resolved.is_dir():
        logger.error("%s '%s' is not a directory.", error_prefix, path)
        sys.exit(1)

    return resolved
