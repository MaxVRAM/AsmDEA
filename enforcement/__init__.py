"""Enforcement modules for modifying asmdef files.

Enforcement modules go beyond analysis to actively modify .asmdef files
to enforce project standards. All modifications use backup/restore safety.

Key modules:
    - DependencySorter: Sort assembly references by configurable strategies
    - BaseEnforcer: Abstract base class for all enforcement operations

Usage:
    from enforcement import DependencySorter, SortingStrategy

    sorter = DependencySorter(asmdef_dict)
    result = sorter.sort(
        strategy=SortingStrategy.ALPHABETICAL_ASC,
        target="MyAssembly",
        dry_run=True
    )
"""

from .base import BaseEnforcer, EnforcementMode
from .dependency_sorter import DependencySorter
from .sorting_strategies import (
    AlphabeticalStrategy,
    CustomPriorityStrategy,
    NamespaceGroupedStrategy,
    SortingStrategy,
    UnityPriorityStrategy,
)

__all__ = [
    "BaseEnforcer",
    "EnforcementMode",
    "DependencySorter",
    "SortingStrategy",
    "AlphabeticalStrategy",
    "NamespaceGroupedStrategy",
    "UnityPriorityStrategy",
    "CustomPriorityStrategy",
]
