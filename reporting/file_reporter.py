"""Reporter for file analysis results.

Formats and displays C# file ownership analysis showing which files belong
to which assemblies and identifying orphaned files without assembly assignments.

Key classes:
    - FileAnalysisReporter: Formats and outputs file ownership results

Features:
    - Summary statistics (total files, assignments, orphans)
    - File count per assembly sorted by size
    - Detailed file listings (optional, configurable limit)
    - JSON export with complete file paths

Usage:
    from reporting import FileAnalysisReporter

    reporter = FileAnalysisReporter(verbose=True)
    reporter.print_console_report(analysis_data)
    reporter.print_detailed_report(analysis_data, max_files_per_assembly=20)
"""

from typing import Any

from common import get_logger

from .base import BaseReporter

logger = get_logger(__name__)


class FileAnalysisReporter(BaseReporter):
    """Reporter for C# file ownership analysis results."""

    def print_console_report(self, data: dict[str, Any]) -> None:
        """Print formatted file analysis report to console.

        Args:
            data: Dictionary containing file analysis results
        """
        asmdef_dict = data.get("asmdef_dict", {})
        stats = data.get("stats", {})

        logger.info("\n%s", "=" * 60)
        logger.info("C# FILE ANALYSIS REPORT")
        logger.info("%s\n", "=" * 60)

        logger.info("Total .cs files found: %d", stats.get("total_cs_files", 0))
        logger.info("Files assigned to assemblies: %d", stats.get("assigned_files", 0))
        logger.info("Orphaned files (no owning assembly): %d\n", stats.get("orphaned_files", 0))

        # Show assemblies with file counts
        assemblies = {k: v for k, v in asmdef_dict.items() if not k.startswith("_")}

        if assemblies:
            logger.info("Files per assembly:")
            assembly_list = []
            for guid, assembly_data in assemblies.items():
                name = assembly_data.get("name", guid)
                file_count = len(assembly_data.get("csFiles", []))
                assembly_list.append((name, file_count))

            # Sort by file count (descending)
            assembly_list.sort(key=lambda x: x[1], reverse=True)

            for name, count in assembly_list:
                if count > 0:
                    logger.info("  %s: %d files", name, count)

        logger.info("")

    def generate_json_report(self, data: dict[str, Any]) -> dict[str, Any]:
        """Generate JSON-serializable file analysis report.

        Args:
            data: Dictionary containing file analysis results

        Returns:
            Dictionary ready for JSON serialization
        """
        asmdef_dict = data.get("asmdef_dict", {})
        stats = data.get("stats", {})

        assemblies = {k: v for k, v in asmdef_dict.items() if not k.startswith("_")}

        return {
            "summary": {
                "totalCsFiles": stats.get("total_cs_files", 0),
                "assignedFiles": stats.get("assigned_files", 0),
                "orphanedFiles": stats.get("orphaned_files", 0),
            },
            "assemblies": {
                guid: {
                    "name": assembly_data.get("name", guid),
                    "fileCount": len(assembly_data.get("csFiles", [])),
                    "files": assembly_data.get("csFiles", []),
                    "relativePath": assembly_data.get("relativePath", ""),
                }
                for guid, assembly_data in assemblies.items()
            },
        }

    def print_detailed_report(self, data: dict[str, Any], max_files_per_assembly: int = 10) -> None:
        """Print detailed report showing individual files.

        Args:
            data: Dictionary containing file analysis results
            max_files_per_assembly: Maximum files to show per assembly
        """
        asmdef_dict = data.get("asmdef_dict", {})
        assemblies = {k: v for k, v in asmdef_dict.items() if not k.startswith("_")}

        logger.info("\n%s", "=" * 60)
        logger.info("DETAILED FILE ASSIGNMENTS")
        logger.info("%s\n", "=" * 60)

        for guid, assembly_data in assemblies.items():
            name = assembly_data.get("name", guid)
            cs_files = assembly_data.get("csFiles", [])

            if not cs_files:
                continue

            logger.info("\n%s (%d files):", name, len(cs_files))

            for _i, file_path in enumerate(cs_files[:max_files_per_assembly]):
                logger.info("  - %s", file_path)

            if len(cs_files) > max_files_per_assembly:
                logger.info("  ... and %d more", len(cs_files) - max_files_per_assembly)

        logger.info("")
