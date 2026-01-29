"""File I/O utilities for JSON operations."""

import json
import sys
from pathlib import Path
from typing import Any, cast


def load_asmdef_dict(filepath: Path | str) -> dict[str, Any]:
    """
    Load asmdef dictionary from JSON file.

    Args:
        filepath: Path to JSON file

    Returns:
        Dictionary loaded from JSON

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If JSON is malformed
    """
    path = Path(filepath)
    try:
        with open(path, encoding="utf-8") as f:
            return cast(dict[str, Any], json.load(f))
    except FileNotFoundError:
        print(f"Error: Dictionary file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to load asmdef dictionary: {e}", file=sys.stderr)
        sys.exit(1)


def save_json_report(
    data: dict[str, Any], filepath: Path | str, create_dirs: bool = True, verbose: bool = True
) -> None:
    """
    Save JSON report with consistent formatting.

    Args:
        data: Dictionary to serialize
        filepath: Output file path
        create_dirs: Create parent directories if they don't exist
        verbose: Print confirmation message

    Raises:
        OSError: If file cannot be written
    """
    path = Path(filepath)

    if create_dirs:
        path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        if verbose:
            print(f"Report written to {path}")
    except Exception as e:
        print(f"Error: Failed to write output file '{path}': {e}", file=sys.stderr)
        sys.exit(1)
