"""Reporter for namespace analysis results.

Formats and displays namespace compliance analysis results showing how well
C# file namespaces match their assembly's root namespace definitions.

Key classes:
    - NamespaceReporter: Formats and outputs namespace analysis results

Features:
    - Rich console output with panels, tables, and styled text
    - Summary statistics (total files, match rates, compliance percentages)
    - Per-assembly breakdown of matched/mismatched/missing namespaces
    - Optional verbose mode showing specific file paths
    - Highlights problem assemblies with warnings
    - Supports both exact matching and child namespace allowance modes
    - JSON export with detailed file-level information

Usage:
    from reporting import NamespaceReporter
    from models import NamespaceAnalysisReport

    reporter = NamespaceReporter(verbose=True, allow_child_namespaces=True)
    reporter.print_console_report(analysis_report)
    reporter.print_summary(analysis_report)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from common import FilepathType, format_path
from models import AssemblyNamespaceStats, NamespaceAnalysisReport

from .base import BaseReporter

if TYPE_CHECKING:
    from rich.console import Console


class NamespaceReporter(BaseReporter):
    """Reporter for namespace analysis results."""

    def __init__(
        self,
        verbose: bool = False,
        allow_child_namespaces: bool = True,
        show_unmatched_paths: bool = True,
        console: Console | None = None,
        filepath_type: FilepathType = FilepathType.RELATIVE,
        root_path: Path | None = None,
    ):
        """Initialize namespace reporter.

        Args:
            verbose: Enable verbose output
            allow_child_namespaces: Whether child namespaces are considered valid
            show_unmatched_paths: Include the `unmatchedPaths` list in the JSON report
                (default: True). Set False to keep the JSON compact.
            console: Rich Console instance (uses shared instance if not provided)
            filepath_type: Render paths as ABSOLUTE or RELATIVE (to ``root_path``).
            root_path: Project root used as the base for RELATIVE path formatting.
        """
        super().__init__(
            verbose=verbose,
            console=console,
            filepath_type=filepath_type,
            root_path=root_path,
        )
        self.allow_child_namespaces = allow_child_namespaces
        self.show_unmatched_paths = show_unmatched_paths

    def _fmt(self, path: Path | str) -> str:
        """Format a path per the reporter's filepath_type/root_path settings."""
        return format_path(path, self.filepath_type, self.root_path)

    def print_console_report(self, report: NamespaceAnalysisReport) -> None:
        """Print formatted namespace report to console.

        Args:
            report: NamespaceAnalysisReport with analysis results
        """
        console = self.console

        # Determine status color based on match rate
        if report.overall_match_percentage >= 95:
            status_style = "green"
            status_text = "success"
        elif report.overall_match_percentage >= 70:
            status_style = "yellow"
            status_text = "warning"
        else:
            status_style = "red"
            status_text = "error"

        # Header panel
        panel = Panel(
            f"[{status_text}]Overall Match Rate: {report.overall_match_percentage:.1f}%[/]",
            title="Namespace Analysis Report",
            border_style=status_style,
        )
        console.print(panel)

        # Summary table
        summary_table = Table(show_header=False, box=None, padding=(0, 2))
        summary_table.add_column("Metric", style="info")
        summary_table.add_column("Value", style="count", justify="right")
        summary_table.add_row("Assemblies Analyzed", str(report.total_assemblies))
        summary_table.add_row("Total Files", str(report.total_files))
        summary_table.add_row("Matching Namespaces", str(report.total_matched))
        summary_table.add_row("Mismatched Namespaces", str(report.total_mismatched))
        summary_table.add_row("Files without Namespace", str(report.total_no_namespace))
        console.print(summary_table)
        console.print()

        # Show problem assemblies
        problem_assemblies = report.get_problem_assemblies()

        if not problem_assemblies:
            console.print("[success]All assemblies have perfect namespace compliance![/]")
            console.print()
            return

        console.print(f"[warning]{len(problem_assemblies)} assemblies have namespace issues:[/]")
        console.print()

        # Problem assemblies table
        problem_table = Table(title="Problem Assemblies")
        problem_table.add_column("Assembly", style="assembly")
        problem_table.add_column("Root Namespace", style="muted")
        problem_table.add_column("Total", justify="right")
        problem_table.add_column("Matched", justify="right", style="success")
        problem_table.add_column("Mismatched", justify="right", style="error")
        problem_table.add_column("No NS", justify="right", style="warning")
        if self.allow_child_namespaces:
            problem_table.add_column("Compliance", justify="right")
        else:
            problem_table.add_column("Match %", justify="right")

        for stats in problem_assemblies:
            rate = (
                f"{stats.compliance_percentage:.1f}%"
                if self.allow_child_namespaces
                else f"{stats.match_percentage:.1f}%"
            )
            problem_table.add_row(
                stats.assembly_name,
                stats.root_namespace or "(none)",
                str(stats.total_files),
                str(stats.matched_files),
                str(stats.unmatched_files),
                str(stats.no_namespace_files),
                rate,
            )

        console.print(problem_table)
        console.print()

        # Verbose file listings
        if self.verbose:
            for stats in problem_assemblies:
                self._print_file_details(stats)

    def _print_file_details(self, stats: AssemblyNamespaceStats) -> None:
        """Print detailed file paths for an assembly with issues.

        Args:
            stats: AssemblyNamespaceStats for one assembly
        """
        console = self.console

        if stats.unmatched_files > 0 and stats.unmatched_file_paths:
            console.print(f"[assembly]{stats.assembly_name}[/] - Mismatched files:")
            for path in stats.unmatched_file_paths[:5]:
                console.print(f"  [path]{self._fmt(path)}[/]")
            if len(stats.unmatched_file_paths) > 5:
                remaining = len(stats.unmatched_file_paths) - 5
                console.print(f"  [muted]... and {remaining} more[/]")
            console.print()

        if stats.no_namespace_files > 0 and stats.no_namespace_paths:
            console.print(f"[assembly]{stats.assembly_name}[/] - Files without namespace:")
            for path in stats.no_namespace_paths[:5]:
                console.print(f"  [path]{self._fmt(path)}[/]")
            if len(stats.no_namespace_paths) > 5:
                remaining = len(stats.no_namespace_paths) - 5
                console.print(f"  [muted]... and {remaining} more[/]")
            console.print()

    def generate_json_report(self, report: NamespaceAnalysisReport) -> dict[str, Any]:
        """Generate JSON-serializable namespace report.

        Args:
            report: NamespaceAnalysisReport to convert

        Returns:
            Dictionary ready for JSON serialization
        """
        def _assembly_entry(stats: AssemblyNamespaceStats) -> dict[str, Any]:
            entry: dict[str, Any] = {
                "name": stats.assembly_name,
                "rootNamespace": stats.root_namespace,
                "totalFiles": stats.total_files,
                "matchedFiles": stats.matched_files,
                "childNamespaceFiles": stats.child_namespace_files,
                "unmatchedFiles": stats.unmatched_files,
                "noNamespaceFiles": stats.no_namespace_files,
                "matchPercentage": round(stats.match_percentage, 2),
                "compliancePercentage": round(stats.compliance_percentage, 2),
                "noNamespacePaths": [self._fmt(p) for p in stats.no_namespace_paths],
                "namespaceMismatches": {
                    ns: [self._fmt(p) for p in paths]
                    for ns, paths in stats.namespace_mismatches.items()
                },
            }
            if self.show_unmatched_paths:
                entry["unmatchedPaths"] = [self._fmt(p) for p in stats.unmatched_file_paths]
            return entry

        return {
            "summary": {
                "totalAssemblies": report.total_assemblies,
                "totalFiles": report.total_files,
                "matchedFiles": report.total_matched,
                "mismatchedFiles": report.total_mismatched,
                "filesWithoutNamespace": report.total_no_namespace,
                "overallMatchPercentage": round(report.overall_match_percentage, 2),
                "allowChildNamespaces": report.allow_child_namespaces,
            },
            "assemblies": {
                guid: _assembly_entry(stats) for guid, stats in report.assembly_stats.items()
            },
            "problemAssemblies": [stats.assembly_name for stats in report.get_problem_assemblies()],
        }

    def print_summary(self, report: NamespaceAnalysisReport) -> None:
        """Print brief summary statistics.

        Args:
            report: NamespaceAnalysisReport to summarize
        """
        console = self.console

        console.print(Rule("Namespace Analysis Summary", style="info"))

        # Summary table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style="info")
        table.add_column("Value", style="count", justify="right")
        table.add_row("Files Analyzed", str(report.total_files))
        table.add_row("Match Rate", f"{report.overall_match_percentage:.1f}%")
        table.add_row(
            "Problem Assemblies",
            f"{len(report.get_problem_assemblies())}/{report.total_assemblies}",
        )

        console.print(table)
        console.print()
