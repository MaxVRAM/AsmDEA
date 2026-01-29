"""Reporter for cycle detection results.

Formats and displays cyclic dependency analysis results in console and JSON
formats. Provides detailed cycle information including paths, dependency trees,
and summary statistics.

Key classes:
    - CycleReporter: Formats and outputs cycle detection results

Features:
    - Console output with colored indicators (✓ for success, ⚠ for warnings)
    - Detailed cycle paths showing reference chains
    - Optional dependency tree visualization
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

from common import get_logger
from models import CycleReport, CycleSummary

from .base import BaseReporter

logger = get_logger(__name__)


class CycleReporter(BaseReporter):
    """Reporter for cyclic dependency analysis results."""

    def print_console_report(self, report: CycleReport) -> None:
        """Print formatted cycle report to console.

        Args:
            report: CycleReport containing detected cycles
        """
        if report.total_cycles == 0:
            logger.info("✓ No cyclic dependencies found!")
            logger.info("Analyzed %d assemblies.", report.total_nodes)
            return

        logger.warning("⚠ Found %d cyclic dependencies!", report.total_cycles)
        logger.info("Total assemblies: %d", report.total_nodes)
        logger.info("Assemblies in cycles: %d\n", len(report.affected_nodes))

        for i, cycle_detail in enumerate(report.cycles, 1):
            logger.info("\nCycle %d (length %d):", i, cycle_detail.cycle_length)
            logger.info("  Path: %s", cycle_detail.cycle_path.formatted_path)

            if self.verbose and cycle_detail.dependency_tree:
                logger.info("\n  Dependency Tree (from %s):", cycle_detail.root_node)
                self._print_dependency_tree(cycle_detail.dependency_tree, indent=4)

        logger.info("\n%s", "=" * 60)
        logger.info("Summary: %d cycle(s) detected", report.total_cycles)
        logger.info("%s\n", "=" * 60)

    def _print_dependency_tree(self, tree: dict[str, Any], indent: int = 0) -> None:
        """Recursively print dependency tree.

        Args:
            tree: Dependency tree structure
            indent: Current indentation level
        """
        name = tree.get("name", "Unknown")
        in_cycle = tree.get("inCycle", False)
        marker = "🔴" if in_cycle else "○"

        logger.info("%s%s %s", " " * indent, marker, name)

        for dep in tree.get("dependencies", []):
            self._print_dependency_tree(dep, indent + 2)

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
        logger.info("\n%s", "=" * 60)
        logger.info("CYCLE DETECTION SUMMARY")
        logger.info("%s", "=" * 60)
        logger.info("Total Cycles Found: %d", summary.total_cycles)
        logger.info("Total Assemblies: %d", summary.total_assemblies)
        logger.info("Affected Assemblies: %d", summary.affected_assemblies)

        if summary.total_cycles > 0:
            logger.info("Shortest Cycle: %d nodes", summary.shortest_cycle_length)
            logger.info("Longest Cycle: %d nodes", summary.longest_cycle_length)
            logger.info("Average Cycle Length: %.1f nodes", summary.average_cycle_length)

        logger.info("%s\n", "=" * 60)
