"""Sorting strategies for dependency ordering.

Provides pluggable sorting strategies for organizing assembly references.
Each strategy implements a different ordering approach based on assembly
names, namespaces, or custom priority rules.

Key classes:
    - SortingStrategy: Enum of available strategies
    - BaseSortingStrategy: Abstract base for strategy implementations
    - AlphabeticalStrategy: Sort A-Z or Z-A by assembly name
    - NamespaceGroupedStrategy: Group by namespace prefix, then alphabetical
    - UnityPriorityStrategy: Unity assemblies first/last, then alphabetical
    - CustomPriorityStrategy: User-defined priority list

Usage:
    from enforcement.sorting_strategies import (
        SortingStrategy,
        AlphabeticalStrategy,
        UnityPriorityStrategy,
    )

    strategy = AlphabeticalStrategy(ascending=True)
    sorted_refs = strategy.sort(references, guid_to_name)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto


class SortingStrategy(Enum):
    """Available sorting strategies for dependencies."""

    ALPHABETICAL_ASC = auto()  # A to Z by assembly name
    ALPHABETICAL_DESC = auto()  # Z to A by assembly name
    NAMESPACE_GROUPED = auto()  # Group by root namespace, then alphabetical
    UNITY_FIRST = auto()  # Unity assemblies first, then alphabetical
    UNITY_LAST = auto()  # Unity assemblies last, then alphabetical
    CUSTOM_PRIORITY = auto()  # Custom priority list


@dataclass
class SortedReference:
    """A reference with its resolved name for sorting.

    Attributes:
        guid: The original GUID reference
        name: Resolved assembly name
        sort_key: Key used for sorting
        priority: Priority value (lower = higher priority)
        group: Optional group identifier for grouped sorting
    """

    guid: str
    name: str
    sort_key: str = ""
    priority: int = 0
    group: str = ""

    def __post_init__(self) -> None:
        if not self.sort_key:
            self.sort_key = self.name.lower()


class BaseSortingStrategy(ABC):
    """Abstract base class for sorting strategies.

    Subclasses implement the sort() method to provide custom ordering logic.
    """

    @abstractmethod
    def sort(
        self,
        references: list[str],
        guid_to_name: dict[str, str],
    ) -> list[str]:
        """Sort the references according to the strategy.

        Args:
            references: List of GUID references to sort
            guid_to_name: Mapping of GUIDs to assembly names

        Returns:
            Sorted list of GUID references
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this strategy."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of how this strategy sorts."""
        pass

    def _resolve_references(
        self,
        references: list[str],
        guid_to_name: dict[str, str],
    ) -> list[SortedReference]:
        """Convert GUIDs to SortedReference objects.

        Args:
            references: List of GUID references
            guid_to_name: GUID to name mapping

        Returns:
            List of SortedReference objects
        """
        return [
            SortedReference(
                guid=ref,
                name=guid_to_name.get(ref, ref),
            )
            for ref in references
        ]


class AlphabeticalStrategy(BaseSortingStrategy):
    """Sort references alphabetically by assembly name.

    Attributes:
        ascending: If True, sort A-Z. If False, sort Z-A.
    """

    def __init__(self, ascending: bool = True):
        self.ascending = ascending

    @property
    def name(self) -> str:
        return "Alphabetical (A-Z)" if self.ascending else "Alphabetical (Z-A)"

    @property
    def description(self) -> str:
        direction = "ascending" if self.ascending else "descending"
        return f"Sort references alphabetically in {direction} order by assembly name"

    def sort(
        self,
        references: list[str],
        guid_to_name: dict[str, str],
    ) -> list[str]:
        """Sort references alphabetically."""
        resolved = self._resolve_references(references, guid_to_name)
        resolved.sort(key=lambda r: r.sort_key, reverse=not self.ascending)
        return [r.guid for r in resolved]


class NamespaceGroupedStrategy(BaseSortingStrategy):
    """Group references by namespace prefix, then sort alphabetically within groups.

    Groups are sorted alphabetically, and references within each group
    are sorted alphabetically by full name.

    Attributes:
        ascending: If True, sort groups and items A-Z. If False, Z-A.
        separator: Namespace separator (default: ".")
    """

    def __init__(self, ascending: bool = True, separator: str = "."):
        self.ascending = ascending
        self.separator = separator

    @property
    def name(self) -> str:
        return "Namespace Grouped"

    @property
    def description(self) -> str:
        return "Group by root namespace prefix, then sort alphabetically within groups"

    def _get_namespace_prefix(self, name: str) -> str:
        """Extract the root namespace prefix from an assembly name."""
        parts = name.split(self.separator)
        return parts[0] if parts else name

    def sort(
        self,
        references: list[str],
        guid_to_name: dict[str, str],
    ) -> list[str]:
        """Sort references by namespace group, then alphabetically."""
        resolved = self._resolve_references(references, guid_to_name)

        # Assign groups
        for ref in resolved:
            ref.group = self._get_namespace_prefix(ref.name)

        # Sort by group first, then by name within group
        resolved.sort(
            key=lambda r: (r.group.lower(), r.sort_key),
            reverse=not self.ascending,
        )

        return [r.guid for r in resolved]


class UnityPriorityStrategy(BaseSortingStrategy):
    """Prioritize Unity assemblies at the start or end of the list.

    Unity assemblies are identified by common prefixes (Unity., UnityEngine.,
    UnityEditor., etc.). Within each section, assemblies are sorted alphabetically.

    Attributes:
        unity_first: If True, Unity assemblies come first. If False, last.
        unity_prefixes: Prefixes that identify Unity assemblies
    """

    DEFAULT_UNITY_PREFIXES = (
        "Unity.",
        "UnityEngine.",
        "UnityEditor.",
        "Unity ",
        "com.unity.",
    )

    def __init__(
        self,
        unity_first: bool = True,
        unity_prefixes: tuple[str, ...] | None = None,
    ):
        self.unity_first = unity_first
        self.unity_prefixes = unity_prefixes or self.DEFAULT_UNITY_PREFIXES

    @property
    def name(self) -> str:
        return "Unity First" if self.unity_first else "Unity Last"

    @property
    def description(self) -> str:
        position = "first" if self.unity_first else "last"
        return f"Place Unity assemblies {position}, then sort alphabetically"

    def _is_unity_assembly(self, name: str) -> bool:
        """Check if an assembly name indicates a Unity package."""
        return any(name.startswith(prefix) for prefix in self.unity_prefixes)

    def sort(
        self,
        references: list[str],
        guid_to_name: dict[str, str],
    ) -> list[str]:
        """Sort with Unity assemblies prioritized."""
        resolved = self._resolve_references(references, guid_to_name)

        # Assign priority based on Unity status
        for ref in resolved:
            is_unity = self._is_unity_assembly(ref.name)
            if self.unity_first:
                ref.priority = 0 if is_unity else 1
            else:
                ref.priority = 1 if is_unity else 0

        # Sort by priority, then alphabetically
        resolved.sort(key=lambda r: (r.priority, r.sort_key))

        return [r.guid for r in resolved]


@dataclass
class CustomPriorityStrategy(BaseSortingStrategy):
    """Sort using a custom priority list with pattern matching.

    Assemblies matching patterns in the priority list are sorted first
    in the order specified. Remaining assemblies are sorted alphabetically.

    Attributes:
        priority_patterns: Ordered list of patterns (prefix match or exact)
        unmatched_position: Where to place unmatched items ("end" or "start")
    """

    priority_patterns: list[str] = field(default_factory=list)
    unmatched_position: str = "end"

    @property
    def name(self) -> str:
        return "Custom Priority"

    @property
    def description(self) -> str:
        return "Sort by custom priority patterns, then alphabetically"

    def _get_priority(self, name: str) -> int:
        """Get priority value for an assembly name (lower = higher priority)."""
        for i, pattern in enumerate(self.priority_patterns):
            # Support prefix matching with * wildcard
            if pattern.endswith("*"):
                if name.startswith(pattern[:-1]):
                    return i
            elif name == pattern or name.startswith(pattern + "."):
                return i

        # Unmatched items get a high priority value
        return len(self.priority_patterns) + 1

    def sort(
        self,
        references: list[str],
        guid_to_name: dict[str, str],
    ) -> list[str]:
        """Sort using custom priority patterns."""
        resolved = self._resolve_references(references, guid_to_name)

        for ref in resolved:
            ref.priority = self._get_priority(ref.name)

        # Sort by priority, then alphabetically
        resolved.sort(key=lambda r: (r.priority, r.sort_key))

        if self.unmatched_position == "start":
            # Move unmatched to the front while preserving their relative order
            unmatched = [r for r in resolved if r.priority > len(self.priority_patterns)]
            matched = [r for r in resolved if r.priority <= len(self.priority_patterns)]
            resolved = unmatched + matched

        return [r.guid for r in resolved]


def get_strategy(
    strategy: SortingStrategy,
    **kwargs,
) -> BaseSortingStrategy:
    """Factory function to create a sorting strategy.

    Args:
        strategy: The strategy enum value
        **kwargs: Additional arguments for strategy initialization

    Returns:
        Configured sorting strategy instance
    """
    strategy_map = {
        SortingStrategy.ALPHABETICAL_ASC: lambda: AlphabeticalStrategy(ascending=True),
        SortingStrategy.ALPHABETICAL_DESC: lambda: AlphabeticalStrategy(ascending=False),
        SortingStrategy.NAMESPACE_GROUPED: lambda: NamespaceGroupedStrategy(**kwargs),
        SortingStrategy.UNITY_FIRST: lambda: UnityPriorityStrategy(unity_first=True, **kwargs),
        SortingStrategy.UNITY_LAST: lambda: UnityPriorityStrategy(unity_first=False, **kwargs),
        SortingStrategy.CUSTOM_PRIORITY: lambda: CustomPriorityStrategy(**kwargs),
    }

    return strategy_map[strategy]()
