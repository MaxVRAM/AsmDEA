"""Enforcement view for TUI.

Displays dependency sorting results using:
- DataTable for changes
- Tree for before/after diffs
"""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Label, Static, Tree

from models import SortingResult


class EnforcementView(Static):
    """View for displaying enforcement/sorting results.

    Shows dependency sorting operations with:
    - Summary statistics panel
    - DataTable with assembly changes
    - Tree showing before/after diffs
    """

    CSS = """
    EnforcementView {
        layout: vertical;
        height: 100%;
    }

    .enforcement-summary {
        height: auto;
        padding: 1;
        margin-bottom: 1;
        background: $panel;
        border: solid $primary;
    }

    .enforcement-content {
        height: 1fr;
    }

    .changes-panel {
        width: 2fr;
        height: 100%;
        border: solid $secondary;
        margin-right: 1;
    }

    .diff-panel {
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

    .dry-run-badge {
        background: $warning;
        color: $text;
        padding: 0 1;
    }

    .applied-badge {
        background: $success;
        color: $text;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the enforcement view."""
        super().__init__(name=name, id=id, classes=classes)
        self._result: SortingResult | None = None

    def compose(self) -> ComposeResult:
        """Create the view layout."""
        # Summary panel
        with Vertical(classes="enforcement-summary"):
            yield Label("🔧 Enforcement Summary", classes="panel-title")
            with Horizontal():
                yield Static("Strategy: ")
                yield Static("—", id="stat-strategy", classes="stat-value")
                yield Static("  |  Mode: ")
                yield Static("—", id="stat-mode", classes="stat-value")
                yield Static("  |  Assemblies Modified: ")
                yield Static("0", id="stat-modified", classes="stat-value")
                yield Static(" / ")
                yield Static("0", id="stat-total", classes="stat-value")

        # Main content area
        with Horizontal(classes="enforcement-content"):
            # Changes table
            with Vertical(classes="changes-panel"):
                yield Label("Changes", classes="panel-title")
                yield DataTable(id="changes-table")

            # Diff tree
            with Vertical(classes="diff-panel"):
                yield Label("Diff Details", classes="panel-title")
                yield Tree("Diffs", id="diff-tree")

    def on_mount(self) -> None:
        """Initialize widgets on mount."""
        table = self.query_one("#changes-table", DataTable)
        table.add_columns(
            "Assembly",
            "References",
            "Moves",
            "Status",
        )
        table.cursor_type = "row"

        tree = self.query_one("#diff-tree", Tree)
        tree.root.expand()

    def update_data(self, result: SortingResult | None) -> None:
        """Update the view with sorting result data.

        Args:
            result: SortingResult with sorting operation details
        """
        self._result = result
        self._update_summary()
        self._update_table()
        self._update_tree()

    def _update_summary(self) -> None:
        """Update the summary statistics."""
        if not self._result:
            self.query_one("#stat-strategy", Static).update("—")
            self.query_one("#stat-mode", Static).update("—")
            self.query_one("#stat-modified", Static).update("0")
            self.query_one("#stat-total", Static).update("0")
            return

        # Update strategy
        strategy_stat = self.query_one("#stat-strategy", Static)
        strategy_stat.update(self._result.strategy_name)

        # Update mode (dry-run vs applied)
        mode_stat = self.query_one("#stat-mode", Static)
        if self._result.dry_run:
            mode_stat.update("🔍 Dry Run")
        else:
            mode_stat.update("✅ Applied")

        # Update counts
        self.query_one("#stat-modified", Static).update(str(self._result.assemblies_modified))
        self.query_one("#stat-total", Static).update(str(self._result.total_assemblies))

    def _update_table(self) -> None:
        """Update the changes table."""
        table = self.query_one("#changes-table", DataTable)
        table.clear()

        if not self._result or not self._result.changes:
            table.add_row("—", "—", "—", "No changes")
            return

        for change in self._result.changes:
            status = "✏️ Modified" if change.has_changes else "✓ Unchanged"
            table.add_row(
                change.assembly_name,
                str(change.reference_count),
                str(change.moves_count),
                status,
            )

    def _update_tree(self) -> None:
        """Update the diff tree."""
        tree = self.query_one("#diff-tree", Tree)
        tree.clear()
        tree.root.set_label("Sorting Diffs")

        if not self._result or not self._result.changes:
            tree.root.add_leaf("No sorting results available")
            tree.root.expand()
            return

        # Only show assemblies with changes
        changed = [c for c in self._result.changes if c.has_changes]

        if not changed:
            tree.root.add_leaf("✅ All assemblies already in correct order")
            tree.root.expand()
            return

        for change in changed:
            # Add assembly as branch
            assembly_node = tree.root.add(f"📦 {change.assembly_name} ({change.moves_count} moves)")

            # Add before section
            before_node = assembly_node.add("Before:")
            for i, name in enumerate(change.before_names[:5]):  # Limit to 5
                before_node.add_leaf(f"  {i + 1}. {name}")
            if len(change.before_names) > 5:
                before_node.add_leaf(f"  ... ({len(change.before_names) - 5} more)")

            # Add after section
            after_node = assembly_node.add("After:")
            for i, name in enumerate(change.after_names[:5]):  # Limit to 5
                after_node.add_leaf(f"  {i + 1}. {name}")
            if len(change.after_names) > 5:
                after_node.add_leaf(f"  ... ({len(change.after_names) - 5} more)")

            assembly_node.expand()

        tree.root.expand()
