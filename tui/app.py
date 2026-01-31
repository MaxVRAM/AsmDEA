"""Main AsmDEA TUI application.

Provides the main Textual App class with tabbed interface for viewing
cycle reports, namespace analysis, file mappings, and enforcement results.
"""

from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from models import CycleReport, NamespaceAnalysisReport, SortingResult

from .screens import AnalysisScreen


class AsmDEAApp(App[None]):
    """AsmDEA TUI Application.

    A Textual-based interface for viewing Unity Assembly Definition analysis
    results including circular dependencies, namespace compliance, and more.
    """

    TITLE = "AsmDEA - Assembly Dependency Enforcement Agency"
    SUB_TITLE = "Unity Assembly Definition Analyzer"

    CSS = """
    Screen {
        background: $surface;
    }

    TabbedContent {
        height: 100%;
    }

    TabPane {
        padding: 1;
    }

    .summary-panel {
        height: auto;
        margin-bottom: 1;
        padding: 1;
        background: $panel;
        border: solid $primary;
    }

    .stats-label {
        text-style: bold;
        color: $text;
    }

    .success {
        color: $success;
    }

    .warning {
        color: $warning;
    }

    .error {
        color: $error;
    }

    DataTable {
        height: 1fr;
    }

    Tree {
        height: 1fr;
    }

    .empty-message {
        text-align: center;
        padding: 2;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("d", "toggle_dark", "Dark/Light"),
        Binding("r", "refresh", "Refresh"),
        Binding("escape", "back", "Back"),
    ]

    def __init__(
        self,
        project_path: Path | None = None,
        dict_file: Path | None = None,
        allow_child_namespaces: bool = True,
    ) -> None:
        """Initialize the TUI application.

        Args:
            project_path: Path to Unity project Assets directory
            dict_file: Path to assembly dictionary JSON file
            allow_child_namespaces: Whether to allow child namespaces in validation
        """
        super().__init__()
        self.project_path = project_path
        self.dict_file = dict_file
        self.allow_child_namespaces = allow_child_namespaces

        # Analysis data (populated when analyses are run)
        self.asmdef_dict: dict[str, Any] = {}
        self.cycle_report: CycleReport | None = None
        self.namespace_report: NamespaceAnalysisReport | None = None
        self.sorting_result: SortingResult | None = None

    def compose(self) -> ComposeResult:
        """Create the main application layout."""
        yield Header()
        yield AnalysisScreen(
            project_path=self.project_path,
            dict_file=self.dict_file,
            allow_child_namespaces=self.allow_child_namespaces,
        )
        yield Footer()

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.theme = "textual-light" if self.theme == "textual-dark" else "textual-dark"

    def action_refresh(self) -> None:
        """Refresh the current analysis."""
        screen = self.query_one(AnalysisScreen)
        screen.run_analysis()

    def action_back(self) -> None:
        """Go back (close modals, etc.)."""
        pass  # Placeholder for future modal handling


def run_tui(
    project_path: Path | None = None,
    dict_file: Path | None = None,
    allow_child_namespaces: bool = True,
) -> None:
    """Run the TUI application.

    Args:
        project_path: Path to Unity project Assets directory
        dict_file: Path to assembly dictionary JSON file
        allow_child_namespaces: Whether to allow child namespaces in validation
    """
    app = AsmDEAApp(
        project_path=project_path,
        dict_file=dict_file,
        allow_child_namespaces=allow_child_namespaces,
    )
    app.run()
