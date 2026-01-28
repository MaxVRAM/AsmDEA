"""Path validation utilities."""

import sys
from pathlib import Path
from typing import Union


def validate_directory(path: Union[Path, str], error_prefix: str = "Root path") -> Path:
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
        print(f"Error: {error_prefix} '{path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    
    if not resolved.is_dir():
        print(f"Error: {error_prefix} '{path}' is not a directory.", file=sys.stderr)
        sys.exit(1)
    
    return resolved
