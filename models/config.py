"""Configuration data models for analysis scripts.

Defines the AnalysisConfig class for managing analysis parameters and
settings across different analysis tools.

Key models:
    - AnalysisConfig: Centralized configuration for analysis runs
        - root_path: Unity project root directory
        - dict_file: Path to asmdef dictionary
        - output_dir: Output directory for reports
        - verbose: Enable detailed logging
        - allow_child_namespaces: Accept child namespace declarations

Usage:
    from models import AnalysisConfig

    config = AnalysisConfig(
        root_path="/path/to/unity/project",
        dict_file="asmdef_dictionary.json",
        verbose=True
    )
"""

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
