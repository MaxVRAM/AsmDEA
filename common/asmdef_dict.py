"""Utilities for working with asmdef dictionary structures."""

from typing import Any, Dict

from .constants import METADATA_KEY


def filter_assemblies(asmdef_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter out metadata entries from asmdef dictionary.

    Metadata entries have keys starting with underscore (e.g., "_metadata").

    Args:
        asmdef_dict: Full dictionary including metadata

    Returns:
        Dictionary with only assembly entries (GUID keys)
    """
    return {k: v for k, v in asmdef_dict.items() if not k.startswith("_")}


def get_metadata(asmdef_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get metadata from asmdef dictionary.

    Args:
        asmdef_dict: Dictionary to extract metadata from

    Returns:
        Metadata dictionary, or empty dict if no metadata exists
    """
    return asmdef_dict.get(METADATA_KEY, {})


def set_metadata(asmdef_dict: Dict[str, Any], key: str, value: Any) -> None:
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
