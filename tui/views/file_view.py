"""File mapping view for TUI.

Displays C# file to assembly mapping results using:
- DataTable showing assembly file counts
"""

from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Label, Static


class FileView(Static):
    """View for displaying file mapping results.

    Shows C# file to assembly mappings with:
    - Summary statistics panel
    - DataTable with assembly file counts
    """

    CSS = """
    FileView {
        layout: vertical;
        height: 100%;
    }

    .file-summary {
        height: auto;
        padding: 1;
        margin-bottom: 1;
        background: $panel;
        border: solid $primary;
    }

    .file-content {
        height: 1fr;
    }

    .panel-title {
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the file view."""
        super().__init__(name=name, id=id, classes=classes)
        self._asmdef_dict: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        """Create the view layout."""
        # Summary panel
        with Vertical(classes="file-summary"):
            yield Label("📂 File Mapping Summary", classes="panel-title")
            with Horizontal():
                yield Static("Total Assemblies: ")
                yield Static("0", id="stat-assemblies", classes="stat-value")
                yield Static("  |  Total Files: ")
                yield Static("0", id="stat-files", classes="stat-value")
                yield Static("  |  Avg Files/Assembly: ")
                yield Static("0", id="stat-avg", classes="stat-value")

        # Assembly file table
        with Vertical(classes="file-content"):
            yield Label("Assembly File Counts", classes="panel-title")
            yield DataTable(id="file-table")

    def on_mount(self) -> None:
        """Initialize table columns on mount."""
        table = self.query_one("#file-table", DataTable)
        table.add_columns(
            "Assembly Name",
            "GUID",
            "Root Namespace",
            "C# Files",
            "Path",
        )
        table.cursor_type = "row"

    def update_data(self, asmdef_dict: dict[str, Any] | None) -> None:
        """Update the view with assembly dictionary data.

        Args:
            asmdef_dict: Assembly dictionary with file mappings
        """
        self._asmdef_dict = asmdef_dict or {}
        self._update_summary()
        self._update_table()

    def _get_assemblies(self) -> list[tuple[str, dict[str, Any]]]:
        """Get assembly entries from the dictionary (excluding metadata)."""
        return [
            (guid, data)
            for guid, data in self._asmdef_dict.items()
            if not guid.startswith("_") and isinstance(data, dict)
        ]

    def _update_summary(self) -> None:
        """Update the summary statistics."""
        assemblies = self._get_assemblies()
        total_assemblies = len(assemblies)
        total_files = sum(len(data.get("csFiles", [])) for _, data in assemblies)
        avg_files = total_files / total_assemblies if total_assemblies > 0 else 0

        # Update stats
        self.query_one("#stat-assemblies", Static).update(str(total_assemblies))
        self.query_one("#stat-files", Static).update(str(total_files))
        self.query_one("#stat-avg", Static).update(f"{avg_files:.1f}")

    def _update_table(self) -> None:
        """Update the assembly file table."""
        table = self.query_one("#file-table", DataTable)
        table.clear()

        assemblies = self._get_assemblies()

        if not assemblies:
            table.add_row("—", "—", "—", "—", "—")
            return

        # Sort by file count descending
        sorted_assemblies = sorted(
            assemblies,
            key=lambda x: len(x[1].get("csFiles", [])),
            reverse=True,
        )

        for guid, data in sorted_assemblies:
            name = data.get("name", "Unknown")
            root_ns = data.get("rootNamespace", "") or "(none)"
            cs_files = len(data.get("csFiles", []))
            rel_path = data.get("relativePath", "")

            # Truncate path if too long
            if len(rel_path) > 40:
                rel_path = "..." + rel_path[-37:]

            # Truncate GUID for display
            short_guid = guid[:12] + "..." if len(guid) > 15 else guid

            table.add_row(
                name,
                short_guid,
                root_ns,
                str(cs_files),
                rel_path,
            )
