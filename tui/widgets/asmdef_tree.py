"""Custom DirectoryTree widget with .asmdef file counting.

Provides a filtered directory tree that shows only folders, with
asynchronous counting of .asmdef files nested within each directory.
"""

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from rich.text import Text
from textual.widgets import DirectoryTree


class AsmdefDirectoryTree(DirectoryTree):
    """DirectoryTree that displays .asmdef file counts for each directory.

    Features:
    - Filters to show directories only (no files)
    - Asynchronously scans directories to count .asmdef files
    - Shows spinner while scanning: FolderName [5] ⠋
    - Shows count after scan: FolderName [3]
    - Shows [?] for unscanned folders
    - Dims folders with [0] .asmdef files
    - Caches results in app-level scan_cache for session persistence
    """

    SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, path: str | Path, *args: Any, **kwargs: Any) -> None:
        """Initialize the directory tree.

        Args:
            path: Root directory to display
            *args: Positional arguments for DirectoryTree
            **kwargs: Keyword arguments for DirectoryTree
        """
        super().__init__(path, *args, **kwargs)
        self.scanning_paths: set[Path] = set()
        self.spinner_frame: int = 0
        self._spinner_timer: Any = None

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        """Filter to show only directories, excluding those with 0 .asmdef files.

        Args:
            paths: Paths to filter

        Returns:
            Iterator of directory paths only, excluding zero-count scanned folders
        """
        cache: dict[Path, int] = getattr(self.app, "asmdef_scan_cache", {})
        result = []
        # Include if not in cache yet, or if count > 0
        for path in paths:
            if path.is_dir() and (path not in cache or cache[path] > 0):
                result.append(path)
        return result

    def render_label(self, node: Any, base_style: Any, style: Any) -> Text:
        """Render tree node label with .asmdef count.

        Args:
            node: Tree node to render
            base_style: Base style for the label
            style: Additional style for the label

        Returns:
            Formatted label
        """
        # Get the DirEntry from the node
        entry = node.data
        if entry is None:
            return Text("")

        # Get path from DirEntry - entry.path gives us the string path
        path = Path(str(entry.path))
        label = path.name

        # Get cache from app
        cache: dict[Path, int] = getattr(self.app, "asmdef_scan_cache", {})

        # Check if currently scanning
        if path in self.scanning_paths:
            count = cache.get(path, 0)
            spinner = self.SPINNER_FRAMES[self.spinner_frame % len(self.SPINNER_FRAMES)]
            result = Text(f"{label} [{count}] {spinner}")
            return result

        # Check cache
        if path in cache:
            count = cache[path]
            # Folders with 0 are filtered out in filter_paths, but show anyway if somehow visible
            return Text(f"{label} [{count}]")

        # Unscanned - show grey with spinner in brackets
        spinner = self.SPINNER_FRAMES[self.spinner_frame % len(self.SPINNER_FRAMES)]
        result = Text(f"{label} [{spinner}]")
        result.stylize("dim")
        return result

    def on_mount(self) -> None:
        """Set up spinner timer when mounted."""
        super().on_mount()
        # Always start spinner for unscanned folders
        self._spinner_timer = self.set_interval(0.1, self._update_spinner)

    def _start_spinner_if_needed(self) -> None:
        """Start spinner timer if there are scanning paths."""
        if self.scanning_paths and self._spinner_timer is None:
            self._spinner_timer = self.set_interval(0.1, self._update_spinner)

    def _stop_spinner_if_done(self) -> None:
        """Stop spinner timer if no paths are scanning."""
        if not self.scanning_paths and self._spinner_timer is not None:
            self._spinner_timer.stop()
            self._spinner_timer = None

    def _update_spinner(self) -> None:
        """Update spinner frame and refresh display."""
        self.spinner_frame += 1
        # Refresh the entire tree to update all spinners
        self.refresh()

    def on_tree_node_expanded(self, event: DirectoryTree.NodeExpanded) -> None:
        """Handle node expansion - trigger scan if not cached.

        Args:
            event: Node expansion event
        """
        node = event.node
        entry = node.data
        if entry is None:
            return

        path = Path(str(entry.path))
        cache: dict[Path, int] = getattr(self.app, "asmdef_scan_cache", {})

        # Scan if not already in cache
        if path not in cache:
            self.scan_directory(path)

    def scan_directory(self, path: Path) -> None:
        """Asynchronously scan directory for .asmdef files.

        Args:
            path: Directory path to scan
        """
        if path in self.scanning_paths:
            return  # Already scanning

        self.scanning_paths.add(path)
        self._start_spinner_if_needed()

        # Run scan in worker thread
        self.run_worker(
            self._scan_worker(path),
            exclusive=False,
            thread=True,
        )

    async def _scan_worker(self, root_path: Path) -> None:
        """Worker function to recursively count .asmdef files.

        Args:
            root_path: Root directory to scan
        """
        cache: dict[Path, int] = getattr(self.app, "asmdef_scan_cache", {})

        def count_asmdef_recursive(path: Path) -> int:
            """Recursively count .asmdef files."""
            count = 0
            try:
                for item in path.iterdir():
                    if item.is_file() and item.suffix == ".asmdef":
                        count += 1
                    elif item.is_dir():
                        # Recursively count in subdirectories
                        subcount = count_asmdef_recursive(item)
                        count += subcount

                        # Update cache for subdirectory
                        cache[item] = subcount
            except (PermissionError, OSError):
                # Skip inaccessible directories
                pass

            return count

        # Count .asmdef files
        total_count = count_asmdef_recursive(root_path)

        # Update cache
        cache[root_path] = total_count

        # Ensure cache is stored on app
        if hasattr(self.app, "asmdef_scan_cache"):
            self.app.asmdef_scan_cache = cache  # type: ignore

        # Remove from scanning set and refresh
        self.scanning_paths.discard(root_path)
        self._stop_spinner_if_done()

        # If count is 0, we need to remove this node from tree and update selection
        if total_count == 0:
            # Check if currently highlighted node is the one being removed
            if self.cursor_line is not None:
                current_node = self.get_node_at_line(self.cursor_line)
                if current_node and current_node.data:
                    current_path = Path(str(current_node.data.path))
                    if current_path == root_path:
                        # Move selection to parent before removing
                        if current_node.parent:
                            self.select_node(current_node.parent)

            # Reload the parent to remove zero-count children
            self._reload_parent_node(root_path)

        self.refresh()

    def rescan_visible(self) -> None:
        """Rescan currently expanded/visible directories.

        Clears cache entries for visible nodes and re-triggers scans.
        """
        cache: dict[Path, int] = getattr(self.app, "asmdef_scan_cache", {})

        # For simplicity, clear the entire cache and rescan root
        # A more sophisticated implementation could track visible nodes
        cache.clear()

        # Rescan the root path
        if self.path:
            root_path = Path(str(self.path))
            self.scan_directory(root_path)

    def _reload_parent_node(self, child_path: Path) -> None:
        """Reload parent node to refresh its children after scan completes.

        Args:
            child_path: Path of the child that was scanned
        """
        # Find the parent node and reload it
        parent_path = child_path.parent
        # Trigger a reload by calling reload_node if we can find it
        # For now, just refresh the tree which will re-filter
        self.reload()
