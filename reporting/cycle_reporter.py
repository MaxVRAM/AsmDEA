"""Reporter for cycle detection results.

Formats and displays cyclic dependency analysis results in console and JSON
formats. Provides detailed cycle information including paths, dependency trees,
and summary statistics.

Key classes:
    - CycleReporter: Formats and outputs cycle detection results

Features:
    - Rich console output with colored panels, tables, and trees
    - Detailed cycle paths showing reference chains
    - Optional dependency tree visualization using Rich Tree
    - Summary statistics (cycle count, affected assemblies, cycle lengths)
    - JSON export for programmatic processing

Usage:
    from reporting import CycleReporter
    from models import CycleReport

    reporter = CycleReporter(verbose=True)
    reporter.print_console_report(cycle_report)
    reporter.save_json_report(cycle_report, "cycles.json")
"""

from typing import Any

from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.tree import Tree

from models import CycleReport, CycleSummary

from .base import BaseReporter


class CycleReporter(BaseReporter):
    """Reporter for cyclic dependency analysis results."""

    def print_console_report(self, report: CycleReport) -> None:
        """Print formatted cycle report to console.

        Args:
            report: CycleReport containing detected cycles
        """
        console = self.console

        if report.total_cycles == 0:
            # Success panel
            panel = Panel(
                "[success]No cyclic dependencies found![/]",
                title="Cycle Detection",
                border_style="green",
            )
            console.print(panel)
            console.print(f"Analyzed [count]{report.total_nodes}[/] assemblies.")
            return

        # Warning panel for cycles found
        panel = Panel(
            f"[error]Found {report.total_cycles} cyclic dependencies![/]",
            title="Cycle Detection",
            border_style="red",
        )
        console.print(panel)

        # Statistics table
        stats_table = Table(show_header=False, box=None, padding=(0, 2))
        stats_table.add_column("Metric", style="info")
        stats_table.add_column("Value", style="count", justify="right")
        stats_table.add_row("Total Assemblies", str(report.total_nodes))
        stats_table.add_row("Assemblies in Cycles", str(len(report.affected_nodes)))
        stats_table.add_row("Total Cycles", str(report.total_cycles))
        console.print(stats_table)
        console.print()

        # Each cycle
        for i, cycle_detail in enumerate(report.cycles, 1):
            console.print(f"[bold]Cycle {i}[/] (length {cycle_detail.cycle_length})")
            console.print(f"  Path: [warning]{cycle_detail.cycle_path.formatted_path}[/]")

            if self.verbose and cycle_detail.dependency_tree:
                console.print(f"  Dependency Tree (from [assembly]{cycle_detail.root_node}[/]):")
                tree = self._build_rich_tree(cycle_detail.dependency_tree)
                console.print(tree)

            console.print()

        # Summary rule
        console.print(Rule(f"Summary: {report.total_cycles} cycle(s) detected", style="muted"))

    def _build_rich_tree(self, tree_data: dict[str, Any], parent: Tree | None = None) -> Tree:
        """Build a Rich Tree from dependency tree data.

        Args:
            tree_data: Dependency tree structure dict
            parent: Parent Tree node (None for root)

        Returns:
            Rich Tree object for display
        """
        name = tree_data.get("name", "Unknown")
        in_cycle = tree_data.get("inCycle", False)

        # Style based on whether node is in cycle
        if in_cycle:
            label = f"[cycle]X[/] [cycle]{name}[/]"
        else:
            label = f"[no_cycle]o[/] [no_cycle]{name}[/]"

        if parent is None:
            tree = Tree(label)
        else:
            tree = parent.add(label)

        for dep in tree_data.get("dependencies", []):
            self._build_rich_tree(dep, tree)

        return tree

    def generate_json_report(self, report: CycleReport) -> dict[str, Any]:
        """Generate JSON-serializable cycle report.

        Args:
            report: CycleReport to convert

        Returns:
            Dictionary ready for JSON serialization
        """
        return report.to_dict()

    def print_summary_report(self, summary: CycleSummary) -> None:
        """Print summary statistics for cycles.

        Args:
            summary: CycleSummary with statistics
        """
        console = self.console

        console.print(Rule("Cycle Detection Summary", style="info"))

        # Summary table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style="info")
        table.add_column("Value", style="count", justify="right")
        table.add_row("Total Cycles Found", str(summary.total_cycles))
        table.add_row("Total Assemblies", str(summary.total_assemblies))
        table.add_row("Affected Assemblies", str(summary.affected_assemblies))

        if summary.total_cycles > 0:
            table.add_row("Shortest Cycle", f"{summary.shortest_cycle_length} nodes")
            table.add_row("Longest Cycle", f"{summary.longest_cycle_length} nodes")
            table.add_row("Average Cycle Length", f"{summary.average_cycle_length:.1f} nodes")

        console.print(table)
        console.print()
