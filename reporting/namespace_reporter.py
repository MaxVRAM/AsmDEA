"""Reporter for namespace analysis results.

Formats and displays namespace compliance analysis results showing how well
C# file namespaces match their assembly's root namespace definitions.

Key classes:
    - NamespaceReporter: Formats and outputs namespace analysis results

Features:
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

from typing import Any

from common import get_logger
from models import AssemblyNamespaceStats, NamespaceAnalysisReport

from .base import BaseReporter

logger = get_logger(__name__)


class NamespaceReporter(BaseReporter):
    """Reporter for namespace analysis results."""

    def __init__(self, verbose: bool = False, allow_child_namespaces: bool = True):
        """Initialize namespace reporter.

        Args:
            verbose: Enable verbose output
            allow_child_namespaces: Whether child namespaces are considered valid
        """
        super().__init__(verbose)
        self.allow_child_namespaces = allow_child_namespaces

    def print_console_report(self, report: NamespaceAnalysisReport) -> None:
        """Print formatted namespace report to console.

        Args:
            report: NamespaceAnalysisReport with analysis results
        """
        logger.info("\n%s", "=" * 70)
        logger.info("NAMESPACE ANALYSIS REPORT")
        logger.info("%s\n", "=" * 70)

        logger.info("Assemblies Analyzed: %d", report.total_assemblies)
        logger.info("Total Files Analyzed: %d", report.total_files)
        logger.info("Files with Matching Namespaces: %d", report.total_matched)
        logger.info("Files with Mismatched Namespaces: %d", report.total_mismatched)
        logger.info("Files without Namespaces: %d", report.total_no_namespace)
        logger.info("Overall Match Rate: %.1f%%\n", report.overall_match_percentage)

        # Show problem assemblies
        problem_assemblies = report.get_problem_assemblies()

        if not problem_assemblies:
            logger.info("✓ All assemblies have perfect namespace compliance!\n")
            return

        logger.warning("⚠ %d assemblies have namespace issues:\n", len(problem_assemblies))

        for stats in problem_assemblies:
            self._print_assembly_stats(stats)

    def _print_assembly_stats(self, stats: AssemblyNamespaceStats) -> None:
        """Print statistics for a single assembly.

        Args:
            stats: AssemblyNamespaceStats for one assembly
        """
        logger.info("Assembly: %s", stats.assembly_name)
        logger.info("  Root Namespace: %s", stats.root_namespace or "(none)")
        logger.info("  Total Files: %d", stats.total_files)
        logger.info("  Matched: %d", stats.matched_files)

        if self.allow_child_namespaces:
            logger.info("  Child Namespaces: %d", stats.child_namespace_files)
            logger.info("  Compliance: %.1f%%", stats.compliance_percentage)
        else:
            logger.info("  Match Rate: %.1f%%", stats.match_percentage)

        if stats.unmatched_files > 0:
            logger.warning("  ⚠ Mismatched: %d", stats.unmatched_files)
            if self.verbose and stats.unmatched_file_paths:
                for path in stats.unmatched_file_paths[:5]:  # Show max 5
                    logger.info("     - %s", path)
                if len(stats.unmatched_file_paths) > 5:
                    logger.info("     ... and %d more", len(stats.unmatched_file_paths) - 5)

        if stats.no_namespace_files > 0:
            logger.warning("  ⚠ No Namespace: %d", stats.no_namespace_files)
            if self.verbose and stats.no_namespace_paths:
                for path in stats.no_namespace_paths[:5]:
                    logger.info("     - %s", path)
                if len(stats.no_namespace_paths) > 5:
                    logger.info("     ... and %d more", len(stats.no_namespace_paths) - 5)

        logger.info("")

    def generate_json_report(self, report: NamespaceAnalysisReport) -> dict[str, Any]:
        """Generate JSON-serializable namespace report.

        Args:
            report: NamespaceAnalysisReport to convert

        Returns:
            Dictionary ready for JSON serialization
        """
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
                guid: {
                    "name": stats.assembly_name,
                    "rootNamespace": stats.root_namespace,
                    "totalFiles": stats.total_files,
                    "matchedFiles": stats.matched_files,
                    "childNamespaceFiles": stats.child_namespace_files,
                    "unmatchedFiles": stats.unmatched_files,
                    "noNamespaceFiles": stats.no_namespace_files,
                    "matchPercentage": round(stats.match_percentage, 2),
                    "compliancePercentage": round(stats.compliance_percentage, 2),
                    "unmatchedPaths": [str(p) for p in stats.unmatched_file_paths],
                    "noNamespacePaths": [str(p) for p in stats.no_namespace_paths],
                    "namespaceMismatches": stats.namespace_mismatches,
                }
                for guid, stats in report.assembly_stats.items()
            },
            "problemAssemblies": [stats.assembly_name for stats in report.get_problem_assemblies()],
        }

    def print_summary(self, report: NamespaceAnalysisReport) -> None:
        """Print brief summary statistics.

        Args:
            report: NamespaceAnalysisReport to summarize
        """
        logger.info("\n%s", "=" * 60)
        logger.info("NAMESPACE ANALYSIS SUMMARY")
        logger.info("%s", "=" * 60)
        logger.info("Files Analyzed: %d", report.total_files)
        logger.info("Match Rate: %.1f%%", report.overall_match_percentage)
        logger.info(
            "Problem Assemblies: %d/%d",
            len(report.get_problem_assemblies()),
            report.total_assemblies,
        )
        logger.info("%s\n", "=" * 60)
