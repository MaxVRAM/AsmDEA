"""Reporter for script-first analysis results.

Formats and displays per-script metadata produced by :class:`ScriptAnalyser`,
keyed by Unity script GUID. The JSON shape is the canonical artifact consumed
by downstream tooling (dashboards, cross-validators).

Key classes:
    - ScriptReporter: Formats and outputs the script-first view

Features:
    - Console summary table (counts, orphan and meta warnings)
    - Top-N most-imported namespaces breakdown
    - JSON export with GUID-sorted entries for diff-friendly output
    - Honours ``filepath_type`` for the ``relativePath`` field

Usage:
    from reporting import ScriptReporter

    reporter = ScriptReporter(root_path=project_path)
    reporter.print_console_report(result)
    reporter.save_json_report(result, output_dir / "script_report.json")
"""

from collections import Counter
from pathlib import Path
from typing import Any

from rich.panel import Panel
from rich.table import Table

from common import FilepathType, format_path

from .base import BaseReporter


class ScriptReporter(BaseReporter):
    """Reporter for script-first analysis results."""

    def __init__(
        self,
        verbose: bool = False,
        console: Any = None,
        filepath_type: FilepathType = FilepathType.RELATIVE,
        root_path: Path | None = None,
        top_imports: int = 10,
    ):
        """Initialise script reporter.

        Args:
            verbose: Enable verbose output
            console: Rich Console instance
            filepath_type: Render ``relativePath`` as ABSOLUTE or RELATIVE
                (to ``root_path``).
            root_path: Project root used as the base for RELATIVE formatting.
            top_imports: How many entries to show in the top-imports table.
        """
        super().__init__(
            verbose=verbose,
            console=console,
            filepath_type=filepath_type,
            root_path=root_path,
        )
        self.top_imports = top_imports

    def print_console_report(self, data: dict[str, Any]) -> None:
        """Print formatted script analysis report to console."""
        console = self.console
        stats = data.get("stats", {})
        scripts = data.get("scripts", {})

        total = stats.get("total_scripts", 0)
        with_ns = stats.get("scripts_with_namespace", 0)
        without_ns = stats.get("scripts_without_namespace", 0)
        without_meta = stats.get("scripts_without_meta", 0)
        orphaned = stats.get("orphaned_scripts", 0)
        unique = stats.get("unique_namespaces_imported", 0)
        unique_external = stats.get("unique_external_namespaces", 0)

        panel = Panel(
            f"[count]{total}[/] scripts analysed",
            title="Script Analysis Report",
            border_style="blue",
        )
        console.print(panel)

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style="info")
        table.add_column("Value", style="count", justify="right")
        table.add_row("Total Scripts", str(total))
        table.add_row("With Namespace", str(with_ns))
        table.add_row(
            "Without Namespace",
            f"[warning]{without_ns}[/]" if without_ns else "0",
        )
        table.add_row(
            "Missing .meta",
            f"[warning]{without_meta}[/]" if without_meta else "0",
        )
        table.add_row(
            "Orphaned (no assembly)",
            f"[warning]{orphaned}[/]" if orphaned else "0",
        )
        table.add_row("Unique Namespaces Imported", str(unique))
        table.add_row("Unique External Namespaces", str(unique_external))

        console.print(table)
        console.print()

        counter: Counter[str] = Counter()
        for entry in scripts.values():
            counter.update(entry.get("imports", []))

        if counter:
            top = counter.most_common(self.top_imports)
            tbl = Table(title=f"Top {len(top)} Most-Imported Namespaces")
            tbl.add_column("Namespace", style="info")
            tbl.add_column("Used By", justify="right", style="count")
            for name, count in top:
                tbl.add_row(name, str(count))
            console.print(tbl)
            console.print()

    def generate_json_report(self, data: dict[str, Any]) -> dict[str, Any]:
        """Generate the canonical ``script_report.json`` payload.

        Entries are emitted in GUID-sorted order so JSON byte output is stable
        across runs on unchanged input.
        """
        stats = data.get("stats", {})
        scripts = data.get("scripts", {})

        return {
            "summary": {
                "totalScripts": stats.get("total_scripts", 0),
                "scriptsWithNamespace": stats.get("scripts_with_namespace", 0),
                "scriptsWithoutNamespace": stats.get("scripts_without_namespace", 0),
                "scriptsWithoutMeta": stats.get("scripts_without_meta", 0),
                "orphanedScripts": stats.get("orphaned_scripts", 0),
                "totalImports": stats.get("total_imports", 0),
                "uniqueNamespacesImported": stats.get("unique_namespaces_imported", 0),
                "uniqueExternalNamespaces": stats.get("unique_external_namespaces", 0),
            },
            "scripts": {
                guid: {
                    "name": entry["name"],
                    "relativePath": format_path(
                        entry["path"], self.filepath_type, self.root_path
                    ),
                    "namespace": entry["namespace"],
                    "importCount": len(entry["imports"]),
                    "imports": list(entry["imports"]),
                    "externalImports": list(entry.get("external_imports", [])),
                    "assembly": entry["assembly"],
                }
                for guid, entry in sorted(scripts.items())
            },
        }
