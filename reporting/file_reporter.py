"""Reporter for file analysis results.

Formats and displays C# file ownership analysis showing which files belong
to which assemblies and identifying orphaned files without assembly assignments.

Key classes:
    - FileAnalysisReporter: Formats and outputs file ownership results

Features:
    - Rich console output with panels and tables
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

from pathlib import Path
from typing import Any

from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from common import FilepathType, format_path

from .base import BaseReporter


class FileAnalysisReporter(BaseReporter):
    """Reporter for C# file ownership analysis results."""

    def __init__(
        self,
        verbose: bool = False,
        detailed: bool = False,
        depth: int = 3,
        console: Any = None,
        filepath_type: FilepathType = FilepathType.RELATIVE,
        root_path: Path | None = None,
    ):
        """Initialize file analysis reporter.

        Args:
            verbose: Enable verbose output
            detailed: Enable detailed output
            depth: Maximum depth (unused here; inherited)
            console: Rich Console instance
            filepath_type: Render paths as ABSOLUTE or RELATIVE (to ``root_path``).
            root_path: Project root used as the base for RELATIVE formatting and
                for reassembling absolute paths from per-assembly relative ``csFiles``.
        """
        super().__init__(
            verbose=verbose,
            detailed=detailed,
            depth=depth,
            console=console,
            filepath_type=filepath_type,
            root_path=root_path,
        )

    def _format_assembly_files(self, assembly_data: dict[str, Any]) -> list[str]:
        """Format the csFiles list for one assembly per filepath_type.

        ``csFiles`` are stored by :class:`FileAnalyser` as paths relative to
        each assembly root. Combine with the assembly's ``relativePath`` and
        (if known) ``self.root_path`` to reassemble an absolute path, then
        hand off to :func:`format_path` for final rendering.
        """
        cs_files: list[str] = assembly_data.get("csFiles", []) or []
        assembly_rel = assembly_data.get("relativePath", "")

        if self.root_path is None:
            # No root known — fall back to the stored (assembly-relative) string.
            return list(cs_files)

        assembly_root = (self.root_path / assembly_rel) if assembly_rel else self.root_path
        return [
            format_path(assembly_root / cs_file, self.filepath_type, self.root_path)
            for cs_file in cs_files
        ]

    def print_console_report(self, data: dict[str, Any]) -> None:
        """Print formatted file analysis report to console.

        Args:
            data: Dictionary containing file analysis results
        """
        console = self.console
        asmdef_dict = data.get("asmdef_dict", {})
        stats = data.get("stats", {})

        total_files = stats.get("total_cs_files", 0)
        assigned = stats.get("assigned_files", 0)
        orphaned = stats.get("orphaned_files", 0)

        # Header panel
        panel = Panel(
            f"[count]{total_files}[/] C# files analyzed",
            title="File Analysis Report",
            border_style="blue",
        )
        console.print(panel)

        # Summary table
        summary_table = Table(show_header=False, box=None, padding=(0, 2))
        summary_table.add_column("Metric", style="info")
        summary_table.add_column("Value", style="count", justify="right")
        summary_table.add_row("Total .cs Files", str(total_files))
        summary_table.add_row("Assigned to Assemblies", str(assigned))

        if orphaned > 0:
            summary_table.add_row("Orphaned Files", f"[warning]{orphaned}[/]")
        else:
            summary_table.add_row("Orphaned Files", str(orphaned))

        console.print(summary_table)
        console.print()

        # Show assemblies with file counts
        assemblies = {k: v for k, v in asmdef_dict.items() if not k.startswith("_")}

        if assemblies:
            # Build list of assemblies with file counts
            assembly_list = []
            for guid, assembly_data in assemblies.items():
                name = assembly_data.get("name", guid)
                file_count = len(assembly_data.get("csFiles", []))
                if file_count > 0:
                    assembly_list.append((name, file_count))

            # Sort by file count (descending)
            assembly_list.sort(key=lambda x: x[1], reverse=True)

            if assembly_list:
                # Assembly table
                assembly_table = Table(title="Files per Assembly")
                assembly_table.add_column("Assembly", style="assembly")
                assembly_table.add_column("Files", justify="right", style="count")

                for name, count in assembly_list:
                    assembly_table.add_row(name, str(count))

                console.print(assembly_table)
                console.print()

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
                    "files": self._format_assembly_files(assembly_data),
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
        console = self.console
        asmdef_dict = data.get("asmdef_dict", {})
        assemblies = {k: v for k, v in asmdef_dict.items() if not k.startswith("_")}

        console.print(Rule("Detailed File Assignments", style="info"))
        console.print()

        for guid, assembly_data in assemblies.items():
            name = assembly_data.get("name", guid)
            formatted_files = self._format_assembly_files(assembly_data)

            if not formatted_files:
                continue

            console.print(f"[assembly]{name}[/] ({len(formatted_files)} files):")

            for file_path in formatted_files[:max_files_per_assembly]:
                console.print(f"  [path]{file_path}[/]")

            if len(formatted_files) > max_files_per_assembly:
                remaining = len(formatted_files) - max_files_per_assembly
                console.print(f"  [muted]... and {remaining} more[/]")

            console.print()
