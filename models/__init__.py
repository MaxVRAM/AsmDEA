"""Data models for assembly definitions and analysis results."""

from .asmdef_entry import AsmdefEntry
from .config import AnalysisConfig, CounterConfig, FlattenerConfig
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
