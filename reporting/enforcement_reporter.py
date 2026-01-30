"""Reporter for enforcement operations.

Provides Rich console output for enforcement results, including
diff previews, before/after comparisons, and backup information.

Key class:
    - EnforcementReporter: Console and JSON reporting for enforcement results

Usage:
    from reporting import EnforcementReporter
    from enforcement import DependencySorter

    result = sorter.sort(strategy=SortingStrategy.ALPHABETICAL_ASC)
    reporter = EnforcementReporter(verbose=True)
    reporter.print_console_report(result)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from common import get_logger

from .base import BaseReporter

if TYPE_CHECKING:
    from models.sorting_result import SortingChange, SortingResult

logger = get_logger(__name__)


class EnforcementReporter(BaseReporter):
    """Reporter for enforcement operation results.

    Provides formatted console output for sorting operations,
    including diff views, summary statistics, and backup information.
    """

    def __init__(
        self,
        verbose: bool = False,
        detailed: bool = False,
        depth: int = 3,
        console=None,
        show_unchanged: bool = False,
    ):
        """Initialize reporter.

        Args:
            verbose: Enable verbose output
            detailed: Enable detailed diff output
            depth: Maximum items to show in lists
            console: Rich Console instance
            show_unchanged: Show assemblies that weren't modified
        """
        super().__init__(verbose, detailed, depth, console)
        self.show_unchanged = show_unchanged

    def print_console_report(self, data: SortingResult) -> None:
        """Print formatted sorting result to console.

        Args:
            data: SortingResult from sorting operation
        """
        # Header panel
        self._print_header(data)

        # Strategy info
        self._print_strategy_info(data)

        # Summary statistics
        self._print_summary(data)

        # Changes table
        if data.changes:
            self._print_changes_table(data)

        # Detailed diffs (if verbose)
        if self.detailed and data.changes:
            self._print_detailed_diffs(data)

        # Backup info
        if data.backup_path:
            self._print_backup_info(data)

        # Errors
        if data.errors:
            self._print_errors(data)

        # Footer
        self._print_footer(data)

    def _print_header(self, data: SortingResult) -> None:
        """Print the header panel."""
        if data.dry_run:
            title = "[bold yellow]Dependency Sorting Preview (Dry Run)[/]"
            subtitle = "[dim]No files were modified. Use --apply to commit changes.[/]"
        else:
            title = "[bold green]Dependency Sorting Complete[/]"
            subtitle = "[dim]Files have been modified.[/]"

        panel = Panel(
            subtitle,
            title=title,
            border_style="blue" if data.dry_run else "green",
        )
        self.console.print(panel)
        self.console.print()

    def _print_strategy_info(self, data: SortingResult) -> None:
        """Print sorting strategy information."""
        self.console.print(f"[bold]Strategy:[/] {data.strategy_name}")
        self.console.print(f"[dim]{data.strategy_description}[/]")
        if data.target_filter:
            self.console.print(f"[bold]Filter:[/] {data.target_filter}")
        self.console.print()

    def _print_summary(self, data: SortingResult) -> None:
        """Print summary statistics."""
        table = Table(title="Summary", show_header=False, box=None)
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Assemblies processed", str(data.total_assemblies))
        table.add_row(
            "Assemblies modified" if not data.dry_run else "Assemblies to modify",
            f"[yellow]{data.assemblies_modified}[/]" if data.assemblies_modified else "0",
        )
        table.add_row("Already sorted", str(data.assemblies_unchanged))
        table.add_row("References moved", str(data.total_references_moved))

        self.console.print(table)
        self.console.print()

    def _print_changes_table(self, data: SortingResult) -> None:
        """Print table of changes."""
        # Filter changes based on show_unchanged setting
        changes_to_show = data.changes
        if not self.show_unchanged:
            changes_to_show = [c for c in data.changes if c.has_changes]

        if not changes_to_show:
            self.console.print("[dim]No changes to display.[/]")
            return

        table = Table(title="Changes")
        table.add_column("Assembly", style="cyan")
        table.add_column("References", justify="right")
        table.add_column("Moved", justify="right")
        table.add_column("Status")

        for change in changes_to_show:
            if change.has_changes:
                status = "[yellow]Modified[/]" if not data.dry_run else "[blue]Will modify[/]"
                moved = f"[yellow]{change.moves_count}[/]"
            else:
                status = "[dim]Unchanged[/]"
                moved = "[dim]0[/]"

            table.add_row(
                change.assembly_name,
                str(change.reference_count),
                moved,
                status,
            )

        self.console.print(table)
        self.console.print()

    def _print_detailed_diffs(self, data: SortingResult) -> None:
        """Print detailed before/after diffs."""
        changes_with_modifications = [c for c in data.changes if c.has_changes]

        if not changes_with_modifications:
            return

        self.console.print("[bold]Detailed Changes:[/]")
        self.console.print()

        for change in changes_with_modifications[: self.depth]:
            self._print_single_diff(change)

        remaining = len(changes_with_modifications) - self.depth
        if remaining > 0:
            self.console.print(f"[dim]... and {remaining} more assemblies[/]")
        self.console.print()

    def _print_single_diff(self, change: SortingChange) -> None:
        """Print diff for a single assembly."""
        tree = Tree(f"[bold cyan]{change.assembly_name}[/]")

        before_branch = tree.add("[red]Before:[/]")
        for i, name in enumerate(change.before_names):
            before_branch.add(f"[dim]{i + 1}.[/] {name}")

        after_branch = tree.add("[green]After:[/]")
        for i, name in enumerate(change.after_names):
            # Highlight if position changed
            old_pos = change.before_names.index(name) if name in change.before_names else -1
            if old_pos != i:
                after_branch.add(f"[dim]{i + 1}.[/] [bold]{name}[/] [dim](was #{old_pos + 1})[/]")
            else:
                after_branch.add(f"[dim]{i + 1}.[/] {name}")

        self.console.print(tree)
        self.console.print()

    def _print_backup_info(self, data: SortingResult) -> None:
        """Print backup information."""
        self.console.print(
            Panel(
                f"[bold]Backup created:[/] {data.backup_path}\n"
                "[dim]Use 'asmdea restore-backup' to restore if needed.[/]",
                title="[green]Backup[/]",
                border_style="green",
            )
        )
        self.console.print()

    def _print_errors(self, data: SortingResult) -> None:
        """Print error messages."""
        error_text = "\n".join(f"• {e}" for e in data.errors)
        self.console.print(
            Panel(
                error_text,
                title="[red]Errors[/]",
                border_style="red",
            )
        )
        self.console.print()

    def _print_footer(self, data: SortingResult) -> None:
        """Print footer with next steps."""
        if data.dry_run and data.assemblies_modified > 0:
            self.console.print("[dim]To apply these changes, run the command again with [bold]--apply[/][/]")
        elif not data.dry_run and data.success:
            self.console.print("[green]✓[/] Changes applied successfully")

    def generate_json_report(self, data: SortingResult) -> dict[str, Any]:
        """Generate JSON-serializable report.

        Args:
            data: SortingResult from sorting operation

        Returns:
            Dictionary ready for JSON serialization
        """
        return data.to_dict()

    def save_json_report(self, data: SortingResult, output_path: Path) -> None:
        """Save JSON report to file.

        Args:
            data: SortingResult to save
            output_path: Path for output file
        """
        import json

        report = self.generate_json_report(data)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info("Report saved to %s", output_path)
