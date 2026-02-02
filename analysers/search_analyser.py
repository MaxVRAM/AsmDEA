"""Search analyser - lookup assemblies by namespace or GUID.

Provides functionality to search assembly definitions by either GUID or
namespace, with support for case-insensitive partial matching.

Key classes:
    - SearchAnalyser: Main analyser for namespace/GUID lookups

Features:
    - Auto-detects search type (GUID vs namespace) by GUID: prefix
    - Exact GUID matching
    - Case-insensitive partial namespace matching
    - Searches assembly name, root namespace, and script namespaces
    - Returns all matches with match type information

Usage:
    from analysers import SearchAnalyser
    
    analyser = SearchAnalyser(asmdef_dict)
    results = analyser.search("MyNamespace")
    for result in results:
        print(f"{result.name}: {result.guid}")
"""

from pathlib import Path
from typing import Any

from common.constants import GUID_PREFIX
from models.search_result import MatchType, SearchResult


class SearchAnalyser:
    """Analyses assemblies to find matches by namespace or GUID."""

    def __init__(self, asmdef_dict: dict[str, Any], root_path: Path | None = None):
        """Initialize search analyser.

        Args:
            asmdef_dict: Dictionary of assembly definitions
            root_path: Root directory path (optional, used for resolving file paths)
        """
        self.asmdef_dict = asmdef_dict
        self.root_path = Path(root_path).resolve() if root_path else None

    def search(self, query: str) -> list[SearchResult]:
        """Search for assemblies by GUID or namespace.

        Auto-detects whether the query is a GUID (starts with GUID:) or
        a namespace string. Returns all matching assemblies.

        Args:
            query: GUID or namespace to search for

        Returns:
            List of SearchResult objects for all matches
        """
        if query.startswith(GUID_PREFIX):
            return self._search_by_guid(query)
        else:
            return self._search_by_namespace(query)

    def _search_by_guid(self, guid: str) -> list[SearchResult]:
        """Search for an assembly by exact GUID match.

        Args:
            guid: GUID string (with GUID: prefix)

        Returns:
            List containing single SearchResult if found, empty list otherwise
        """
        results = []

        for entry_guid, data in self.asmdef_dict.items():
            if entry_guid.startswith("_"):
                continue

            if entry_guid == guid:
                result = self._create_search_result(
                    guid=entry_guid,
                    data=data,
                    match_type=MatchType.GUID,
                    matched_value=guid,
                )
                if result:
                    results.append(result)
                break

        return results

    def _search_by_namespace(self, query: str) -> list[SearchResult]:
        """Search for assemblies by namespace (case-insensitive partial match).

        Searches in order:
        1. Assembly name
        2. Root namespace
        3. Script namespaces

        Returns all matches found.

        Args:
            query: Namespace string to search for

        Returns:
            List of SearchResult objects for all matches
        """
        results = []
        query_lower = query.lower()

        for guid, data in self.asmdef_dict.items():
            if guid.startswith("_"):
                continue

            # Track all matches for this assembly
            assembly_matches = []

            # Check assembly name
            name = data.get("name", "")
            if name and query_lower in name.lower():
                assembly_matches.append((MatchType.NAME, name))

            # Check root namespace
            root_namespace = data.get("rootNamespace")
            if root_namespace and query_lower in root_namespace.lower():
                assembly_matches.append((MatchType.ROOT_NAMESPACE, root_namespace))

            # Check script namespaces
            script_namespaces = data.get("scriptNamespaces", [])
            for namespace in script_namespaces:
                if query_lower in namespace.lower():
                    assembly_matches.append((MatchType.SCRIPT_NAMESPACE, namespace))

            # Create a SearchResult for each match type found
            for match_type, matched_value in assembly_matches:
                result = self._create_search_result(
                    guid=guid,
                    data=data,
                    match_type=match_type,
                    matched_value=matched_value,
                )
                if result:
                    results.append(result)

        return results

    def _create_search_result(
        self,
        guid: str,
        data: dict[str, Any],
        match_type: MatchType,
        matched_value: str,
    ) -> SearchResult | None:
        """Create a SearchResult from assembly data.

        Args:
            guid: Assembly GUID
            data: Assembly data dictionary
            match_type: Type of match that occurred
            matched_value: The value that matched the query

        Returns:
            SearchResult object or None if required data is missing
        """
        name = data.get("name")
        if not name:
            return None

        root_namespace = data.get("rootNamespace")
        relative_path = data.get("relativePath", "")

        # Construct absolute file path if root_path is available
        if self.root_path and relative_path:
            file_path = self.root_path / relative_path
        else:
            file_path = Path(relative_path) if relative_path else Path(".")

        return SearchResult(
            guid=guid,
            name=name,
            root_namespace=root_namespace,
            file_path=file_path,
            match_type=match_type,
            matched_value=matched_value,
        )
