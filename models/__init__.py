"""Data models for assembly definitions and analysis results."""

from .asmdef_entry import AsmdefEntry
from .config import AnalysisConfig
from .cycle_report import (
    CycleDetails,
    CyclePath,
    CycleReport,
    CycleSummary,
    DependencyNode,
)
from .namespace_analysis import (
    AssemblyNamespaceStats,
    NamespaceAnalysisReport,
    NamespaceMatch,
)
from .search_result import (
    MatchType,
    SearchResult,
)
from .sorting_result import (
    DependencyDiff,
    SortingChange,
    SortingResult,
)

__all__ = [
    # Assembly entry
    "AsmdefEntry",
    # Configuration
    "AnalysisConfig",
    # Namespace analysis
    "NamespaceMatch",
    "AssemblyNamespaceStats",
    "NamespaceAnalysisReport",
    # Cycle detection
    "CyclePath",
    "DependencyNode",
    "CycleDetails",
    "CycleReport",
    "CycleSummary",
    # Search
    "MatchType",
    "SearchResult",
    # Sorting
    "DependencyDiff",
    "SortingChange",
    "SortingResult",
]
