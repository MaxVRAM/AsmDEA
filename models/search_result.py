"""Search result models for namespace/GUID search functionality.

Data models representing search results when looking up assemblies by
namespace or GUID.

Key classes:
    - MatchType: Enum indicating which field matched the search query
    - SearchResult: Dataclass containing assembly information and match details
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class MatchType(Enum):
    """Type of field that matched the search query."""

    GUID = "guid"
    NAME = "name"
    ROOT_NAMESPACE = "root_namespace"
    SCRIPT_NAMESPACE = "script_namespace"


@dataclass
class SearchResult:
    """Result of searching for an assembly by namespace or GUID.

    Attributes:
        guid: Assembly GUID (with GUID: prefix)
        name: Assembly name from .asmdef file
        root_namespace: Root namespace defined in .asmdef (or None)
        file_path: Path to the .asmdef file
        match_type: Which field matched the query
        matched_value: The actual value that matched the query
    """

    guid: str
    name: str
    root_namespace: str | None
    file_path: Path
    match_type: MatchType
    matched_value: str
