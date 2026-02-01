"""Main analysis screen for TUI application.

Contains the tabbed interface for viewing different analysis results:
- Cycles: Circular dependency detection
- Namespaces: Namespace compliance validation
- Files: C# file to assembly mapping
- Enforcement: Dependency sorting results
"""

from pathlib import Path
from typing import Any

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import (
    Label,
    LoadingIndicator,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
)

from models import CycleReport, NamespaceAnalysisReport, SortingResult
from tui.views import CycleView, EnforcementView, FileView, NamespaceView


class AnalysisScreen(Screen):
    """Main analysis screen with tabbed content.

    Displays analysis results in tabs for Cycles, Namespaces, Files,
    and Enforcement. Runs analysis asynchronously with progress feedback.
    """

    CSS = """
    AnalysisScreen {
        layout: vertical;
    }

    #loading-container {
        width: 100%;
        height: 100%;
        align: center middle;
        display: none;
    }

    #loading-container.visible {
        display: block;
    }

    #main-content {
        width: 100%;
        height: 100%;
    }

    #main-content.hidden {
        display: none;
    }

    #activity-panel {
        height: 10;
        border: solid $secondary;
        margin-top: 1;
    }

    #activity-log {
        height: 100%;
    }

    .status-bar {
        height: 3;
        padding: 1;
        background: $panel;
        border: solid $primary;
    }

    .path-info {
        color: $text-muted;
    }
    """

    def __init__(
        self,
        project_path: Path | None = None,
        dict_file: Path | None = None,
        allow_child_namespaces: bool = True,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the analysis screen.

        Args:
            project_path: Path to Unity project Assets directory
            dict_file: Path to assembly dictionary JSON file
            allow_child_namespaces: Whether to allow child namespaces
            name: Widget name
            id: Widget ID
            classes: CSS classes
        """
        super().__init__(name=name, id=id, classes=classes)
        self.project_path = project_path
        self.dict_file = dict_file
        self.allow_child_namespaces = allow_child_namespaces

        # Analysis results
        self.asmdef_dict: dict[str, Any] = {}
        self.cycle_report: CycleReport | None = None
        self.namespace_report: NamespaceAnalysisReport | None = None
        self.sorting_result: SortingResult | None = None

    def compose(self) -> ComposeResult:
        """Create the screen layout."""
        # Loading overlay
        with Container(id="loading-container"):
            yield LoadingIndicator()
            yield Label("Running analysis...", id="loading-label")

        # Main tabbed content
        with Container(id="main-content"):
            # Status bar showing current paths
            with Horizontal(classes="status-bar"):
                yield Static(
                    f"📁 Project: {self.project_path or 'Not set'}",
                    classes="path-info",
                )
                yield Static(
                    f"📄 Dictionary: {self.dict_file or 'Not set'}",
                    classes="path-info",
                )

            # Tabbed content for different views
            with TabbedContent():
                with TabPane("🔄 Cycles", id="tab-cycles"):
                    yield CycleView(id="cycle-view")

                with TabPane("📛 Namespaces", id="tab-namespaces"):
                    yield NamespaceView(id="namespace-view")

                with TabPane("📂 Files", id="tab-files"):
                    yield FileView(id="file-view")

                with TabPane("🔧 Enforcement", id="tab-enforcement"):
                    yield EnforcementView(id="enforcement-view")

            # Activity log panel
            with Container(id="activity-panel"):
                yield RichLog(id="activity-log", highlight=True, markup=True)

    def on_mount(self) -> None:
        """Handle screen mount - start analysis if paths are set."""
        if self.dict_file and self.dict_file.exists():
            self.run_analysis()
        else:
            self._log_activity("[yellow]No dictionary file loaded. Use 'r' to refresh after setting paths.[/]")

    def _log_activity(self, message: str) -> None:
        """Log a message to the activity panel."""
        try:
            log = self.query_one("#activity-log", RichLog)
            log.write(message)
        except Exception:
            pass  # Log widget might not be mounted yet

    def _show_loading(self, show: bool = True) -> None:
        """Show or hide the loading indicator."""
        loading = self.query_one("#loading-container")
        content = self.query_one("#main-content")
        if show:
            loading.add_class("visible")
            content.add_class("hidden")
        else:
            loading.remove_class("visible")
            content.remove_class("hidden")

    @work(exclusive=True)
    async def run_analysis(self) -> None:
        """Run the analysis pipeline asynchronously."""
        self._show_loading(True)
        self._log_activity("[blue]Starting analysis...[/]")

        try:
            # Load dictionary
            if self.dict_file and self.dict_file.exists():
                self._log_activity(f"[blue]Loading dictionary from {self.dict_file}...[/]")
                await self._load_dictionary()

            # Run cycle analysis
            if self.asmdef_dict:
                self._log_activity("[blue]Detecting cycles...[/]")
                await self._run_cycle_analysis()

            # Run namespace analysis
            if self.asmdef_dict and self.project_path:
                self._log_activity("[blue]Validating namespaces...[/]")
                await self._run_namespace_analysis()

            # Update views with results
            self._update_views()
            self._log_activity("[green]Analysis complete![/]")

        except Exception as e:
            self._log_activity(f"[red]Error during analysis: {e}[/]")
        finally:
            self._show_loading(False)

    async def _load_dictionary(self) -> None:
        """Load the assembly dictionary from file."""
        from common import load_asmdef_dict

        if self.dict_file:
            self.asmdef_dict = load_asmdef_dict(self.dict_file)
            assembly_count = sum(1 for k in self.asmdef_dict if not k.startswith("_"))
            self._log_activity(f"[green]Loaded {assembly_count} assemblies[/]")

    async def _run_cycle_analysis(self) -> None:
        """Run cycle detection analysis."""
        from analysers import CycleAnalyser

        analyser = CycleAnalyser(self.asmdef_dict)
        self.cycle_report = analyser.analyse()

        cycle_count = self.cycle_report.total_cycles if self.cycle_report else 0
        if cycle_count > 0:
            self._log_activity(f"[yellow]Found {cycle_count} cycles[/]")
        else:
            self._log_activity("[green]No cycles detected[/]")

    async def _run_namespace_analysis(self) -> None:
        """Run namespace validation analysis."""
        from analysers import NamespaceAnalyser

        if not self.project_path:
            return

        analyser = NamespaceAnalyser(
            self.asmdef_dict,
            self.project_path,
            self.allow_child_namespaces,
        )
        self.namespace_report = analyser.analyse()

        if self.namespace_report:
            mismatched = self.namespace_report.total_mismatched
            if mismatched > 0:
                self._log_activity(f"[yellow]Found {mismatched} namespace mismatches[/]")
            else:
                self._log_activity("[green]All namespaces compliant[/]")

    def _update_views(self) -> None:
        """Update all views with analysis results."""
        # Update cycle view
        try:
            cycle_view = self.query_one("#cycle-view", CycleView)
            cycle_view.update_data(self.cycle_report)
        except Exception:
            pass

        # Update namespace view
        try:
            namespace_view = self.query_one("#namespace-view", NamespaceView)
            namespace_view.update_data(self.namespace_report)
        except Exception:
            pass

        # Update file view
        try:
            file_view = self.query_one("#file-view", FileView)
            file_view.update_data(self.asmdef_dict)
        except Exception:
            pass

        # Update enforcement view
        try:
            enforcement_view = self.query_one("#enforcement-view", EnforcementView)
            enforcement_view.update_data(self.sorting_result)
        except Exception:
            pass
