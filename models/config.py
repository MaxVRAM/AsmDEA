"""Configuration data models for analysis scripts."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AnalysisConfig:
    """Configuration for assembly definition analysis.

    Attributes:
        root_path: Root directory to search for .asmdef files
        output_dir: Directory for output reports
        dict_file: Path to asmdef dictionary JSON file
        allow_child_namespaces: Whether to allow child namespaces
        tree_depth: Maximum depth for dependency tree
        detailed_report: Whether to generate detailed reports
        verbose: Enable verbose output
    """

    root_path: Path
    output_dir: Path = field(default_factory=lambda: Path("reports"))
    dict_file: Path = field(default_factory=lambda: Path("asmdef_dictionary.json"))
    allow_child_namespaces: bool = True
    tree_depth: int = 3
    detailed_report: bool = False
    verbose: bool = False

    def __post_init__(self):
        """Ensure paths are Path objects."""
        if not isinstance(self.root_path, Path):
            self.root_path = Path(self.root_path)
        if not isinstance(self.output_dir, Path):
            self.output_dir = Path(self.output_dir)
        if not isinstance(self.dict_file, Path):
            self.dict_file = Path(self.dict_file)


@dataclass
class FlattenerConfig:
    """Configuration for script flattening utility.

    Attributes:
        source_dir: Source directory containing .cs files
        dest_dir: Destination directory for flattened files
        add_details: Whether to add comments with file details
    """

    source_dir: Path
    dest_dir: Path
    add_details: bool = False

    def __post_init__(self):
        """Ensure paths are Path objects."""
        if not isinstance(self.source_dir, Path):
            self.source_dir = Path(self.source_dir)
        if not isinstance(self.dest_dir, Path):
            self.dest_dir = Path(self.dest_dir)


@dataclass
class CounterConfig:
    """Configuration for code line counter.

    Attributes:
        directory: Directory to count lines in
        extensions: File extensions to count (e.g., ['.cs', '.py'])
        exclude_dirs: Directories to exclude from counting
    """

    directory: Path
    extensions: list[str] = field(default_factory=lambda: [".cs"])
    exclude_dirs: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Ensure path is a Path object."""
        if not isinstance(self.directory, Path):
            self.directory = Path(self.directory)
