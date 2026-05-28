"""Data models for namespace analysis results.

Defines data structures for tracking C# namespace compliance against
Unity Assembly Definition root namespaces.

Key models:
    - NamespaceMatch: Individual file namespace analysis result
    - AssemblyNamespaceStats: Aggregate statistics per assembly
    - NamespaceAnalysisReport: Complete analysis report with summary stats

Usage:
    from models import NamespaceAnalysisReport, AssemblyNamespaceStats

    report = NamespaceAnalysisReport()
    report.add_assembly_stats(guid, AssemblyNamespaceStats(...))
    problem_assemblies = report.get_problem_assemblies()
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class NamespaceMatch:
    """Result of namespace matching analysis for a file.

    Attributes:
        file_path: Path to the C# file
        namespaces: List of namespaces declared in the file
        expected_namespace: Expected root namespace from assembly
        is_match: Whether any namespace matches expected
        is_child: Whether namespace is a valid child namespace
        has_namespace: Whether file declares any namespace
    """

    file_path: Path
    namespaces: list[str]
    expected_namespace: str
    is_match: bool = False
    is_child: bool = False
    has_namespace: bool = False


@dataclass
class AssemblyNamespaceStats:
    """Statistics for namespace analysis of an assembly.

    Attributes:
        assembly_name: Name of the assembly
        assembly_guid: GUID of the assembly
        root_namespace: Expected root namespace
        total_files: Total C# files in assembly
        matched_files: Files with matching namespace
        child_namespace_files: Files with valid child namespaces
        unmatched_files: Files with wrong namespace
        no_namespace_files: Files without namespace declaration
        matched_file_paths: Paths of files with matching namespace
        child_namespace_paths: Paths of files with child namespaces
        unmatched_file_paths: Paths of unmatched files
        no_namespace_paths: Paths of files without namespace
        namespace_mismatches: Details of namespace mismatches
    """

    assembly_name: str
    assembly_guid: str
    root_namespace: str
    total_files: int = 0
    matched_files: int = 0
    child_namespace_files: int = 0
    unmatched_files: int = 0
    no_namespace_files: int = 0
    matched_file_paths: list[Path] = field(default_factory=list)
    child_namespace_paths: list[Path] = field(default_factory=list)
    unmatched_file_paths: list[Path] = field(default_factory=list)
    no_namespace_paths: list[Path] = field(default_factory=list)
    namespace_mismatches: dict[str, list[str]] = field(default_factory=dict)

    @property
    def match_percentage(self) -> float:
        """Calculate percentage of files with matching namespace."""
        if self.total_files == 0:
            return 0.0
        return (self.matched_files / self.total_files) * 100

    @property
    def compliance_percentage(self) -> float:
        """Calculate percentage of compliant files (matched + child)."""
        if self.total_files == 0:
            return 0.0
        return ((self.matched_files + self.child_namespace_files) / self.total_files) * 100


@dataclass
class NamespaceAnalysisReport:
    """Complete namespace analysis report for all assemblies.

    Attributes:
        assembly_stats: Dictionary mapping assembly GUID to its statistics
        total_assemblies: Total number of assemblies analysed
        total_files: Total C# files across all assemblies
        total_matched: Total files with matching namespaces
        total_child_namespaces: Total files with valid child namespaces
        total_mismatched: Total files with wrong namespaces
        total_no_namespace: Total files without namespace
        allow_child_namespaces: Whether child namespaces were allowed
    """

    assembly_stats: dict[str, AssemblyNamespaceStats] = field(default_factory=dict)
    total_assemblies: int = 0
    total_files: int = 0
    total_matched: int = 0
    total_child_namespaces: int = 0
    total_mismatched: int = 0
    total_no_namespace: int = 0
    allow_child_namespaces: bool = True

    @property
    def overall_match_percentage(self) -> float:
        """Calculate strict-match percentage across all files (exact namespace matches only)."""
        if self.total_files == 0:
            return 0.0
        return (self.total_matched / self.total_files) * 100

    @property
    def overall_compliance_percentage(self) -> float:
        """Calculate compliance percentage across all files (matched + child namespaces)."""
        if self.total_files == 0:
            return 0.0
        return ((self.total_matched + self.total_child_namespaces) / self.total_files) * 100

    def get_problem_assemblies(self) -> list[AssemblyNamespaceStats]:
        """Get assemblies that have namespace problems.

        Returns:
            List of assemblies with mismatches or missing namespaces
        """
        return [
            stats for stats in self.assembly_stats.values() if stats.unmatched_files > 0 or stats.no_namespace_files > 0
        ]
