"""Reporter for prefab-first analysis results.

Formats and displays per-prefab metadata produced by :class:`PrefabAnalyser`,
keyed by Unity prefab GUID. The JSON shape mirrors ``script_report.json`` and is
the canonical artifact consumed by downstream tooling (dashboards).

Key classes:
    - PrefabReporter: Formats and outputs the prefab-first view

Features:
    - Console summary table (counts, missing-meta and unresolved warnings)
    - Top-N most-referenced scripts breakdown
    - JSON export with GUID-sorted entries for diff-friendly output
    - Honours ``filepath_type`` for the ``relativePath`` fields

Usage:
    from reporting import PrefabReporter

    reporter = PrefabReporter(root_path=project_path)
    reporter.print_console_report(result)
    reporter.save_json_report(result, output_dir / "prefab_report.json")
"""

from collections import Counter
from pathlib import Path
from typing import Any

from rich.panel import Panel
from rich.table import Table

from common import FilepathType, format_path

from .base import BaseReporter


class PrefabReporter(BaseReporter):
    """Reporter for prefab-first analysis results."""

    def __init__(
        self,
        verbose: bool = False,
        console: Any = None,
        filepath_type: FilepathType = FilepathType.RELATIVE,
        root_path: Path | None = None,
        top_refs: int = 10,
    ):
        """Initialise prefab reporter.

        Args:
            verbose: Enable verbose output
            console: Rich Console instance
            filepath_type: Render path fields as ABSOLUTE or RELATIVE
                (to ``root_path``).
            root_path: Project root used as the base for RELATIVE formatting.
            top_refs: How many entries to show in the top-referenced-scripts table.
        """
        super().__init__(
            verbose=verbose,
            console=console,
            filepath_type=filepath_type,
            root_path=root_path,
        )
        self.top_refs = top_refs

    def _fmt(self, path: Path | None) -> str | None:
        """Format an optional path via ``filepath_type`` (``None`` passes through)."""
        if path is None:
            return None
        return format_path(path, self.filepath_type, self.root_path)

    def print_console_report(self, data: dict[str, Any]) -> None:
        """Print formatted prefab analysis report to console."""
        console = self.console
        stats = data.get("stats", {})
        prefabs = data.get("prefabs", {})

        total = stats.get("total_prefabs", 0)
        without_meta = stats.get("prefabs_without_meta", 0)
        with_scripts = stats.get("prefabs_with_scripts", 0)
        with_nested = stats.get("prefabs_with_nested", 0)
        total_refs = stats.get("total_script_refs", 0)
        unique_scripts = stats.get("unique_scripts_referenced", 0)
        unresolved = stats.get("unresolved_script_refs", 0)
        nested_edges = stats.get("nested_prefab_edges", 0)

        panel = Panel(
            f"[count]{total}[/] prefabs analysed",
            title="Prefab Analysis Report",
            border_style="blue",
        )
        console.print(panel)

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style="info")
        table.add_column("Value", style="count", justify="right")
        table.add_row("Total Prefabs", str(total))
        table.add_row("Missing .meta", f"[warning]{without_meta}[/]" if without_meta else "0")
        table.add_row("With Component Scripts", str(with_scripts))
        table.add_row("With Nested Prefabs", str(with_nested))
        table.add_row("Total Script References", str(total_refs))
        table.add_row("Unique Scripts Referenced", str(unique_scripts))
        table.add_row(
            "Unresolved Script Refs",
            f"[warning]{unresolved}[/]" if unresolved else "0",
        )
        table.add_row("Nested Prefab Edges", str(nested_edges))

        console.print(table)
        console.print()

        counter: Counter[str] = Counter()
        for entry in prefabs.values():
            for script in entry.get("scripts", []):
                label = script.get("name") or script.get("guid", "?")
                counter[label] += script.get("count", 0)

        if counter:
            top = counter.most_common(self.top_refs)
            tbl = Table(title=f"Top {len(top)} Most-Referenced Scripts")
            tbl.add_column("Script", style="info")
            tbl.add_column("References", justify="right", style="count")
            for name, count in top:
                tbl.add_row(name, str(count))
            console.print(tbl)
            console.print()

    def generate_json_report(self, data: dict[str, Any]) -> dict[str, Any]:
        """Generate the canonical ``prefab_report.json`` payload.

        Entries are emitted in GUID-sorted order (with sorted inner lists) so
        JSON byte output is stable across runs on unchanged input.
        """
        stats = data.get("stats", {})
        prefabs = data.get("prefabs", {})

        return {
            "summary": {
                "totalPrefabs": stats.get("total_prefabs", 0),
                "prefabsWithoutMeta": stats.get("prefabs_without_meta", 0),
                "prefabsWithScripts": stats.get("prefabs_with_scripts", 0),
                "prefabsWithNested": stats.get("prefabs_with_nested", 0),
                "totalScriptRefs": stats.get("total_script_refs", 0),
                "uniqueScriptsReferenced": stats.get("unique_scripts_referenced", 0),
                "unresolvedScriptRefs": stats.get("unresolved_script_refs", 0),
                "nestedPrefabEdges": stats.get("nested_prefab_edges", 0),
            },
            "prefabs": {
                guid: {
                    "name": entry["name"],
                    "relativePath": self._fmt(entry["path"]),
                    "rootObject": entry["root_object"],
                    "gameObjectCount": entry["game_object_count"],
                    "assembly": entry["assembly"],
                    "scriptCount": len(entry["scripts"]),
                    "scripts": sorted(
                        (
                            {
                                "guid": s["guid"],
                                "name": s["name"],
                                "namespace": s["namespace"],
                                "assembly": s["assembly"],
                                "count": s["count"],
                                "instances": list(s["instances"]),
                                "resolved": s["resolved"],
                            }
                            for s in entry["scripts"]
                        ),
                        key=lambda s: s["guid"],
                    ),
                    "childPrefabs": sorted(
                        (
                            {
                                "guid": c["guid"],
                                "name": c["name"],
                                "relativePath": self._fmt(c["path"]),
                                "count": c["count"],
                            }
                            for c in entry["child_prefabs"]
                        ),
                        key=lambda c: c["guid"],
                    ),
                    "parentPrefabs": sorted(
                        (
                            {
                                "guid": p["guid"],
                                "name": p["name"],
                                "relativePath": self._fmt(p["path"]),
                            }
                            for p in entry.get("parent_prefabs", [])
                        ),
                        key=lambda p: p["guid"],
                    ),
                    "referencedAssemblies": list(entry["referenced_assemblies"]),
                }
                for guid, entry in sorted(prefabs.items())
            },
        }
