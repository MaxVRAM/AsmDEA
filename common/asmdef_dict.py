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


def apply_filters(
    asmdef_dict: dict[str, Any],
    filter_root: list[str],
    filter_any: list[str],
    filter_path: list[str],
) -> dict[str, Any]:
    """Filter out assemblies by namespace segment or relative path prefix.

    Args:
        asmdef_dict: Full dictionary including metadata
        filter_root: Exclude assemblies whose top-level namespace segment is in this list
        filter_any: Exclude assemblies where any namespace segment is in this list
        filter_path: Exclude assemblies whose relativePath starts with any of these prefixes

    Returns:
        Filtered dictionary (metadata entries are always preserved)
    """
    if not filter_root and not filter_any and not filter_path:
        return asmdef_dict

    # Normalise filter_path entries to forward-slash, no trailing slash
    normalised_paths = [p.replace("\\", "/").rstrip("/") for p in filter_path]

    result: dict[str, Any] = {}
    for key, value in asmdef_dict.items():
        if key.startswith("_"):
            result[key] = value
            continue

        # --- path filter ---
        if normalised_paths:
            relative_path = (value.get("relativePath") or "").replace("\\", "/")
            if any(relative_path == p or relative_path.startswith(p + "/") for p in normalised_paths):
                continue

        # --- namespace filters ---
        if filter_root or filter_any:
            namespace_source: str = (
                (value.get("rootNamespace") or "").strip()
                or (value.get("name") or "").strip()
            )
            if namespace_source:
                segments = namespace_source.split(".")
                if filter_root and segments[0] in filter_root:
                    continue
                if filter_any and any(seg in filter_any for seg in segments):
                    continue

        result[key] = value

    return result


# Backward-compatible alias
apply_namespace_filters = apply_filters


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
