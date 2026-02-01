"""Welcome screen for path selection and project introduction.

Provides a two-column interface for browsing and selecting the Unity
project root directory with .asmdef file counting.
"""

from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Static

from ..widgets import AsmdefDirectoryTree


class WelcomeScreen(Screen):
    """Welcome screen with project introduction and path selection.

    Left column: App title, feature list, selected path, Continue button
    Right column: Directory tree browser with .asmdef counts
    """

    CSS = """
    WelcomeScreen {
        align: center middle;
    }

    #welcome-container {
        width: 90%;
        height: 90%;
        border: solid $primary;
        background: $surface;
    }

    #left-panel {
        width: 40%;
        padding: 2;
    }

    #right-panel {
        width: 60%;
        padding: 1;
    }

    #app-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #feature-list {
        margin-bottom: 2;
    }

    #selected-path-container {
        margin-top: 2;
        margin-bottom: 1;
        padding: 1;
        border: solid $primary-lighten-2;
        background: $panel;
    }

    #selected-path-label {
        text-style: bold;
        color: $text;
    }

    #selected-path {
        color: $accent;
        margin-top: 1;
    }

    #continue-button {
        width: 100%;
        margin-top: 1;
    }

    #tree-title {
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    AsmdefDirectoryTree {
        height: 1fr;
    }

    .feature-item {
        margin: 1 0 0 2;
    }
    """

    BINDINGS = [
        ("ctrl+s", "rescan", "Rescan"),
    ]

    def __init__(self, initial_path: Path | None = None) -> None:
        """Initialize the welcome screen.

        Args:
            initial_path: Initial directory path to display
        """
        super().__init__()
        self.initial_path = initial_path or Path.cwd()
        self.selected_path: Path | None = None

    def compose(self) -> ComposeResult:
        """Create the welcome screen layout."""
        with Horizontal(id="welcome-container"):
            # Left column - info and controls
            with Vertical(id="left-panel"):
                yield Static("AsmDEA", id="app-title")
                yield Static(
                    "Assembly Dependency Enforcement Agency\n\nUnity Assembly Definition Analyzer",
                    id="app-subtitle",
                )

                with Vertical(id="feature-list"):
                    yield Static("Features:", classes="feature-header")
                    yield Static("• Detect circular dependencies", classes="feature-item")
                    yield Static("• Validate namespace compliance", classes="feature-item")
                    yield Static("• Map C# files to assemblies", classes="feature-item")
                    yield Static("• Enforce dependency sorting", classes="feature-item")

                with Vertical(id="selected-path-container"):
                    yield Label("Selected Project Path:", id="selected-path-label")
                    yield Label(str(self.initial_path), id="selected-path")

                yield Button("Continue", id="continue-button", variant="primary", disabled=False)

            # Right column - directory tree
            with Vertical(id="right-panel"):
                yield Static("Browse Project Directory", id="tree-title")
                yield AsmdefDirectoryTree(str(self.initial_path))

    def on_mount(self) -> None:
        """Set initial selected path when mounted."""
        self.selected_path = self.initial_path
        # Trigger initial scan of the root path
        tree = self.query_one(AsmdefDirectoryTree)
        tree.scan_directory(self.initial_path)

    @on(AsmdefDirectoryTree.DirectorySelected)
    def on_directory_selected(self, event: AsmdefDirectoryTree.DirectorySelected) -> None:
        """Handle directory selection in the tree.

        Args:
            event: Directory selection event
        """
        self.selected_path = Path(str(event.path))
        # Update the selected path label
        path_label = self.query_one("#selected-path", Label)
        path_label.update(str(self.selected_path))

        # Trigger scan if not already cached
        tree = self.query_one(AsmdefDirectoryTree)
        tree.scan_directory(self.selected_path)

    @on(Button.Pressed, "#continue-button")
    def on_continue_pressed(self) -> None:
        """Handle Continue button press."""
        if self.selected_path:
            # Store selected path on app and transition to analysis screen
            self.app.project_path = self.selected_path  # type: ignore
            # Import here to avoid circular dependency
            from .analysis import AnalysisScreen

            self.app.push_screen(
                AnalysisScreen(
                    project_path=self.selected_path,
                    dict_file=getattr(self.app, "dict_file", None),
                    allow_child_namespaces=getattr(self.app, "allow_child_namespaces", True),
                )
            )

    def action_rescan(self) -> None:
        """Rescan visible directories."""
        tree = self.query_one(AsmdefDirectoryTree)
        tree.rescan_visible()
