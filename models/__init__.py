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
    # Sorting
    "DependencyDiff",
    "SortingChange",
    "SortingResult",
]
