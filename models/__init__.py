"""Data models for assembly definitions and analysis results."""

from .asmdef_entry import AsmdefEntry
from .config import AnalysisConfig, FlattenerConfig, CounterConfig
from .namespace_analysis import (
    NamespaceMatch,
    AssemblyNamespaceStats,
    NamespaceAnalysisReport,
)
from .cycle_report import (
    CyclePath,
    DependencyNode,
    CycleDetails,
    CycleReport,
    CycleSummary,
)

__all__ = [
    # Assembly entry
    "AsmdefEntry",
    # Configuration
    "AnalysisConfig",
    "FlattenerConfig",
    "CounterConfig",
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
]
