"""Reporter for cycle detection results."""

from typing import Dict, Any

from .base import BaseReporter
from models import CycleReport, CycleSummary


class CycleReporter(BaseReporter):
    """Reporter for cyclic dependency analysis results."""

    def print_console_report(self, report: CycleReport) -> None:
        """Print formatted cycle report to console.

        Args:
            report: CycleReport containing detected cycles
        """
        if report.total_cycles == 0:
            print("\n✓ No cyclic dependencies found!")
            print(f"Analyzed {report.total_nodes} assemblies.")
            return

        print(f"\n⚠ Found {report.total_cycles} cyclic dependencies!")
        print(f"Total assemblies: {report.total_nodes}")
        print(f"Assemblies in cycles: {len(report.affected_nodes)}\n")

        for i, cycle_detail in enumerate(report.cycles, 1):
            print(f"\nCycle {i} (length {cycle_detail.cycle_length}):")
            print(f"  Path: {cycle_detail.cycle_path.formatted_path}")

            if self.verbose and cycle_detail.dependency_tree:
                print(f"\n  Dependency Tree (from {cycle_detail.root_node}):")
                self._print_dependency_tree(cycle_detail.dependency_tree, indent=4)

        print(f"\n{'=' * 60}")
        print(f"Summary: {report.total_cycles} cycle(s) detected")
        print(f"{'=' * 60}\n")

    def _print_dependency_tree(self, tree: Dict[str, Any], indent: int = 0) -> None:
        """Recursively print dependency tree.

        Args:
            tree: Dependency tree structure
            indent: Current indentation level
        """
        name = tree.get("name", "Unknown")
        in_cycle = tree.get("inCycle", False)
        marker = "🔴" if in_cycle else "○"

        print(f"{' ' * indent}{marker} {name}")

        for dep in tree.get("dependencies", []):
            self._print_dependency_tree(dep, indent + 2)

    def generate_json_report(self, report: CycleReport) -> Dict[str, Any]:
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
        print(f"\n{'=' * 60}")
        print("CYCLE DETECTION SUMMARY")
        print(f"{'=' * 60}")
        print(f"Total Cycles Found: {summary.total_cycles}")
        print(f"Total Assemblies: {summary.total_assemblies}")
        print(f"Affected Assemblies: {summary.affected_assemblies}")

        if summary.total_cycles > 0:
            print(f"Shortest Cycle: {summary.shortest_cycle_length} nodes")
            print(f"Longest Cycle: {summary.longest_cycle_length} nodes")
            print(f"Average Cycle Length: {summary.average_cycle_length:.1f} nodes")

        print(f"{'=' * 60}\n")
