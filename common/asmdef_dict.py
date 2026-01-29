"""Utilities for working with asmdef dictionary structures.

Provides functions for manipulating asmdef dictionaries - the central data
structure mapping assembly GUIDs to their definitions, dependencies, and
file assignments.

An asmdef dictionary has:
    - Assembly entries: GUID -> {name, references, csFiles, ...}
    - Metadata entry: "_metadata" -> {rootPath, analysisDate, ...}

Key functions:
    - filter_assemblies: Remove metadata entries, get only assembly data
    - get_metadata: Extract metadata section
    - set_metadata: Update metadata section

Usage:
    from common import filter_assemblies, get_metadata

    assemblies = filter_assemblies(asmdef_dict)
    metadata = get_metadata(asmdef_dict)
"""

from typing import Any, cast

from .constants import METADATA_KEY


def filter_assemblies(asmdef_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Filter out metadata entries from asmdef dictionary.

    Metadata entries have keys starting with underscore (e.g., "_metadata").

    Args:
        asmdef_dict: Full dictionary including metadata

    Returns:
        Dictionary with only assembly entries (GUID keys)
    """
    return {k: v for k, v in asmdef_dict.items() if not k.startswith("_")}


def get_metadata(asmdef_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Get metadata from asmdef dictionary.

    Args:
        asmdef_dict: Dictionary to extract metadata from

    Returns:
        Metadata dictionary, or empty dict if no metadata exists
    """
    return cast(dict[str, Any], asmdef_dict.get(METADATA_KEY, {}))


def set_metadata(asmdef_dict: dict[str, Any], key: str, value: Any) -> None:
    """
    Set metadata value in asmdef dictionary.

    Args:
        asmdef_dict: Dictionary to modify
        key: Metadata key to set
        value: Value to assign
    """
    if METADATA_KEY not in asmdef_dict:
        asmdef_dict[METADATA_KEY] = {}
    asmdef_dict[METADATA_KEY][key] = value
