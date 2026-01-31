"""Namespace analysis view for TUI.

Displays namespace compliance validation results using:
- DataTable for problem assemblies
- Collapsible sections for file lists
"""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Label, Static

from models import NamespaceAnalysisReport


class NamespaceView(Static):
    """View for displaying namespace analysis results.

    Shows namespace compliance validation with:
    - Summary statistics panel
    - DataTable with problem assemblies
    - Collapsible sections for file details
    """

    CSS = """
    NamespaceView {
        layout: vertical;
        height: 100%;
    }

    .namespace-summary {
        height: auto;
        padding: 1;
        margin-bottom: 1;
        background: $panel;
        border: solid $primary;
    }

    .namespace-content {
        height: 1fr;
        overflow-y: auto;
    }

    .assembly-section {
        margin-bottom: 1;
        border: solid $secondary;
    }

    .section-header {
        padding: 0 1;
        background: $secondary;
    }

    .file-list {
        padding: 0 2;
        height: auto;
    }

    .file-entry {
        color: $text-muted;
    }

    .mismatch-file {
        color: $error;
    }

    .missing-namespace {
        color: $warning;
    }
    """

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the namespace view."""
        super().__init__(name=name, id=id, classes=classes)
        self._report: NamespaceAnalysisReport | None = None

    def compose(self) -> ComposeResult:
        """Create the view layout."""
        # Summary panel
        with Vertical(classes="namespace-summary"):
            yield Label("📛 Namespace Analysis Summary", classes="panel-title")
            with Horizontal():
                yield Static("Total Files: ")
                yield Static("0", id="stat-total-files", classes="stat-value")
                yield Static("  |  Matched: ")
                yield Static("0", id="stat-matched", classes="stat-value stat-ok")
                yield Static("  |  Mismatched: ")
                yield Static("0", id="stat-mismatched", classes="stat-value")
                yield Static("  |  No Namespace: ")
                yield Static("0", id="stat-no-ns", classes="stat-value")

        # Problem assemblies table
        with Vertical(classes="namespace-content"):
            yield Label("Problem Assemblies", classes="panel-title")
            yield DataTable(id="namespace-table")

    def on_mount(self) -> None:
        """Initialize table columns on mount."""
        table = self.query_one("#namespace-table", DataTable)
        table.add_columns(
            "Assembly",
            "Root NS",
            "Total",
            "Matched",
            "Mismatched",
            "No NS",
            "Compliance %",
        )
        table.cursor_type = "row"

    def update_data(self, report: NamespaceAnalysisReport | None) -> None:
        """Update the view with new namespace report data.

        Args:
            report: NamespaceAnalysisReport with validation results
        """
        self._report = report
        self._update_summary()
        self._update_table()

    def _update_summary(self) -> None:
        """Update the summary statistics."""
        if not self._report:
            return

        # Update total files
        total_stat = self.query_one("#stat-total-files", Static)
        total_stat.update(str(self._report.total_files))

        # Update matched count
        matched_stat = self.query_one("#stat-matched", Static)
        matched_stat.update(str(self._report.total_matched))

        # Update mismatched count with color coding
        mismatched_stat = self.query_one("#stat-mismatched", Static)
        mismatched_stat.update(str(self._report.total_mismatched))
        mismatched_stat.remove_class("stat-ok", "stat-warn", "stat-error")
        if self._report.total_mismatched == 0:
            mismatched_stat.add_class("stat-ok")
        elif self._report.total_mismatched <= 10:
            mismatched_stat.add_class("stat-warn")
        else:
            mismatched_stat.add_class("stat-error")

        # Update no namespace count
        no_ns_stat = self.query_one("#stat-no-ns", Static)
        no_ns_stat.update(str(self._report.total_no_namespace))

    def _update_table(self) -> None:
        """Update the problem assemblies table."""
        table = self.query_one("#namespace-table", DataTable)
        table.clear()

        if not self._report:
            table.add_row("—", "—", "—", "—", "—", "—", "—")
            return

        # Get problem assemblies
        problem_assemblies = self._report.get_problem_assemblies()

        if not problem_assemblies:
            table.add_row("✅", "All assemblies compliant", "—", "—", "—", "—", "100%")
            return

        for stats in problem_assemblies:
            compliance = f"{stats.compliance_percentage:.1f}%"
            table.add_row(
                stats.assembly_name,
                stats.root_namespace or "(none)",
                str(stats.total_files),
                str(stats.matched_files),
                str(stats.unmatched_files),
                str(stats.no_namespace_files),
                compliance,
            )
