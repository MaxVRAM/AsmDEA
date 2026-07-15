"""File I/O utilities for JSON operations.

Provides functions for loading and saving asmdef dictionary files and
analysis reports. Handles JSON serialization with consistent formatting
and error handling.

Key functions:
    - load_asmdef_dict: Load asmdef dictionary from JSON file
    - save_json_report: Save analysis results to JSON with pretty formatting

Usage:
    from common import load_asmdef_dict, save_json_report

    asmdef_dict = load_asmdef_dict("asmdef_dictionary.json")
    save_json_report(results, "output/report.json")
"""

import json
import sys
from pathlib import Path
from typing import Any, cast

from .logging_config import get_logger

logger = get_logger(__name__)


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
        # utf-8-sig transparently strips a leading BOM if one is present.
        with open(path, encoding="utf-8-sig") as f:
            return cast(dict[str, Any], json.load(f))
    except FileNotFoundError:
        logger.error("Dictionary file not found: %s", path)
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in %s: %s", path, e)
        sys.exit(1)
    except Exception as e:
        logger.error("Failed to load asmdef dictionary: %s", e)
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
            logger.info("Report written to %s", path)
    except Exception as e:
        logger.error("Failed to write output file '%s': %s", path, e)
        sys.exit(1)
