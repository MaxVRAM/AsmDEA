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

from .screens import ConfirmModal, WelcomeScreen


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
        Binding("ctrl+r", "restart", "Restart"),
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

        # Scan cache for .asmdef file counts (persists across restarts)
        self.asmdef_scan_cache: dict[Path, int] = {}

    def compose(self) -> ComposeResult:
        """Create the main application layout."""
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        """Push welcome screen when app starts."""
        self.push_screen(WelcomeScreen(initial_path=self.project_path))

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.theme = "textual-light" if self.theme == "textual-dark" else "textual-dark"

    def action_refresh(self) -> None:
        """Refresh the current analysis."""
        from .screens import AnalysisScreen

        # Only refresh if we're on the analysis screen
        try:
            screen = self.query_one(AnalysisScreen)
            screen.run_analysis()
        except Exception:
            pass  # Not on analysis screen

    async def action_restart(self) -> None:
        """Restart the application (return to welcome screen)."""
        # Show confirmation modal
        confirmed = await self.push_screen_wait(ConfirmModal("Restart AsmDEA and return to welcome screen?"))

        if confirmed:
            # Clear analysis data but preserve scan cache
            self.asmdef_dict = {}
            self.cycle_report = None
            self.namespace_report = None
            self.sorting_result = None

            # Pop all screens and return to welcome
            self.pop_screen()
            while len(self.screen_stack) > 1:
                self.pop_screen()
            self.push_screen(WelcomeScreen(initial_path=self.project_path))

    def action_back(self) -> None:
        """Go back (close modals, etc.)."""
        if len(self.screen_stack) > 1:
            self.pop_screen()


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
