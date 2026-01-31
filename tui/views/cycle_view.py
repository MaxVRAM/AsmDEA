"""Cycle analysis view for TUI.

Displays circular dependency detection results using:
- Tree widget for dependency paths
- DataTable for cycle statistics
"""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Label, Static, Tree

from models import CycleReport, CycleSummary


class CycleView(Static):
    """View for displaying cycle analysis results.

    Shows detected circular dependencies with:
    - Summary statistics panel
    - Tree visualization of dependency cycles
    - DataTable with cycle details
    """

    CSS = """
    CycleView {
        layout: vertical;
        height: 100%;
    }

    .cycle-summary {
        height: auto;
        padding: 1;
        margin-bottom: 1;
        background: $panel;
        border: solid $primary;
    }

    .cycle-content {
        height: 1fr;
    }

    .cycle-tree-panel {
        width: 1fr;
        height: 100%;
        border: solid $secondary;
        margin-right: 1;
    }

    .cycle-table-panel {
        width: 1fr;
        height: 100%;
        border: solid $secondary;
    }

    .panel-title {
        dock: top;
        padding: 0 1;
        background: $secondary;
        text-style: bold;
    }

    .stat-value {
        text-style: bold;
    }

    .stat-ok {
        color: $success;
    }

    .stat-warn {
        color: $warning;
    }

    .stat-error {
        color: $error;
    }
    """

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the cycle view."""
        super().__init__(name=name, id=id, classes=classes)
        self._report: CycleReport | None = None

    def compose(self) -> ComposeResult:
        """Create the view layout."""
        # Summary panel
        with Vertical(classes="cycle-summary"):
            yield Label("🔄 Cycle Analysis Summary", classes="panel-title")
            with Horizontal():
                yield Static("Total Cycles: ", classes="stat-label")
                yield Static("0", id="stat-cycles", classes="stat-value stat-ok")
                yield Static("  |  Affected Assemblies: ")
                yield Static("0", id="stat-affected", classes="stat-value")
                yield Static("  |  Total Assemblies: ")
                yield Static("0", id="stat-total", classes="stat-value")

        # Main content area with tree and table
        with Horizontal(classes="cycle-content"):
            # Dependency tree panel
            with Vertical(classes="cycle-tree-panel"):
                yield Label("Dependency Paths", classes="panel-title")
                yield Tree("Cycles", id="cycle-tree")

            # Cycle details table
            with Vertical(classes="cycle-table-panel"):
                yield Label("Cycle Details", classes="panel-title")
                yield DataTable(id="cycle-table")

    def on_mount(self) -> None:
        """Initialize table columns on mount."""
        table = self.query_one("#cycle-table", DataTable)
        table.add_columns("ID", "Length", "Path")
        table.cursor_type = "row"

        tree = self.query_one("#cycle-tree", Tree)
        tree.root.expand()

    def update_data(self, report: CycleReport | None) -> None:
        """Update the view with new cycle report data.

        Args:
            report: CycleReport with cycle detection results
        """
        self._report = report
        self._update_summary()
        self._update_tree()
        self._update_table()

    def _update_summary(self) -> None:
        """Update the summary statistics."""
        if not self._report:
            return

        # Get summary
        summary = CycleSummary.from_report(self._report)

        # Update cycle count with color coding
        cycles_stat = self.query_one("#stat-cycles", Static)
        cycles_stat.update(str(summary.total_cycles))
        cycles_stat.remove_class("stat-ok", "stat-warn", "stat-error")
        if summary.total_cycles == 0:
            cycles_stat.add_class("stat-ok")
        elif summary.total_cycles <= 5:
            cycles_stat.add_class("stat-warn")
        else:
            cycles_stat.add_class("stat-error")

        # Update affected assemblies
        affected_stat = self.query_one("#stat-affected", Static)
        affected_stat.update(str(summary.affected_assemblies))

        # Update total assemblies
        total_stat = self.query_one("#stat-total", Static)
        total_stat.update(str(summary.total_assemblies))

    def _update_tree(self) -> None:
        """Update the cycle dependency tree."""
        tree = self.query_one("#cycle-tree", Tree)
        tree.clear()
        tree.root.set_label("Detected Cycles")

        if not self._report or not self._report.cycles:
            tree.root.add_leaf("✅ No cycles detected")
            tree.root.expand()
            return

        for cycle in self._report.cycles:
            # Add cycle as branch
            cycle_label = f"🔴 Cycle {cycle.cycle_id} ({cycle.cycle_length} assemblies)"
            cycle_node = tree.root.add(cycle_label)

            # Add each node in the cycle path
            for i, node in enumerate(cycle.cycle_path.nodes[:-1]):
                arrow = " → " if i < len(cycle.cycle_path.nodes) - 2 else " ⟳ "
                next_node = cycle.cycle_path.nodes[i + 1]
                cycle_node.add_leaf(f"{node}{arrow}{next_node}")

            cycle_node.expand()

        tree.root.expand()

    def _update_table(self) -> None:
        """Update the cycle details table."""
        table = self.query_one("#cycle-table", DataTable)
        table.clear()

        if not self._report or not self._report.cycles:
            table.add_row("—", "—", "No cycles detected")
            return

        for cycle in self._report.cycles:
            # Truncate path if too long
            path_str = cycle.cycle_path.formatted_path
            if len(path_str) > 60:
                path_str = path_str[:57] + "..."

            table.add_row(
                str(cycle.cycle_id),
                str(cycle.cycle_length),
                path_str,
            )
