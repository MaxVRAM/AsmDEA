"""Reporter for namespace analysis results."""

from typing import Dict, Any

from .base import BaseReporter
from models import NamespaceAnalysisReport, AssemblyNamespaceStats


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
        print(f"\n{'=' * 70}")
        print("NAMESPACE ANALYSIS REPORT")
        print(f"{'=' * 70}\n")

        print(f"Assemblies Analyzed: {report.total_assemblies}")
        print(f"Total Files Analyzed: {report.total_files}")
        print(f"Files with Matching Namespaces: {report.total_matched}")
        print(f"Files with Mismatched Namespaces: {report.total_mismatched}")
        print(f"Files without Namespaces: {report.total_no_namespace}")
        print(f"Overall Match Rate: {report.overall_match_percentage:.1f}%\n")

        # Show problem assemblies
        problem_assemblies = report.get_problem_assemblies()

        if not problem_assemblies:
            print("✓ All assemblies have perfect namespace compliance!\n")
            return

        print(f"⚠ {len(problem_assemblies)} assemblies have namespace issues:\n")

        for stats in problem_assemblies:
            self._print_assembly_stats(stats)

    def _print_assembly_stats(self, stats: AssemblyNamespaceStats) -> None:
        """Print statistics for a single assembly.

        Args:
            stats: AssemblyNamespaceStats for one assembly
        """
        print(f"Assembly: {stats.assembly_name}")
        print(f"  Root Namespace: {stats.root_namespace or '(none)'}")
        print(f"  Total Files: {stats.total_files}")
        print(f"  Matched: {stats.matched_files}")

        if self.allow_child_namespaces:
            print(f"  Child Namespaces: {stats.child_namespace_files}")
            print(f"  Compliance: {stats.compliance_percentage:.1f}%")
        else:
            print(f"  Match Rate: {stats.match_percentage:.1f}%")

        if stats.unmatched_files > 0:
            print(f"  ⚠ Mismatched: {stats.unmatched_files}")
            if self.verbose and stats.unmatched_file_paths:
                for path in stats.unmatched_file_paths[:5]:  # Show max 5
                    print(f"     - {path}")
                if len(stats.unmatched_file_paths) > 5:
                    print(f"     ... and {len(stats.unmatched_file_paths) - 5} more")

        if stats.no_namespace_files > 0:
            print(f"  ⚠ No Namespace: {stats.no_namespace_files}")
            if self.verbose and stats.no_namespace_paths:
                for path in stats.no_namespace_paths[:5]:
                    print(f"     - {path}")
                if len(stats.no_namespace_paths) > 5:
                    print(f"     ... and {len(stats.no_namespace_paths) - 5} more")

        print()

    def generate_json_report(self, report: NamespaceAnalysisReport) -> Dict[str, Any]:
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
        print(f"\n{'=' * 60}")
        print("NAMESPACE ANALYSIS SUMMARY")
        print(f"{'=' * 60}")
        print(f"Files Analyzed: {report.total_files}")
        print(f"Match Rate: {report.overall_match_percentage:.1f}%")
        print(f"Problem Assemblies: {len(report.get_problem_assemblies())}/{report.total_assemblies}")
        print(f"{'=' * 60}\n")
