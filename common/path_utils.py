"""Path validation utilities.

Provides functions for validating file system paths with consistent error
handling. Ensures paths exist and are of the expected type before processing.

Key functions:
    - validate_directory: Ensures a path exists and is a directory

Usage:
    from common import validate_directory

    root_path = validate_directory("/path/to/project")
"""

import sys
from pathlib import Path

from .logging_config import get_logger

logger = get_logger(__name__)


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
