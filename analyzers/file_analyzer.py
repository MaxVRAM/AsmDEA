"""File ownership analyzer - assigns C# files to their owning assemblies.

Scans a Unity project directory to find all .cs files and determines which
Assembly Definition owns each file based on directory hierarchy. Files
belong to the nearest .asmdef file in their parent directory chain.

Key classes:
    - FileAnalyzer: Main analyzer for C# file-to-assembly mapping

Features:
    - Recursively scans for .cs files
    - Maps files to owning assemblies by directory proximity
    - Ignores Unity-generated Temp folders
    - Identifies orphaned files (no owning assembly)
    - Generates statistics (total files, assignments, orphans)

Usage:
    from analyzers import FileAnalyzer
    from models import AnalysisConfig

    config = AnalysisConfig(root_path="/path/to/unity")
    analyzer = FileAnalyzer(config)
    updated_dict = analyzer.analyze(asmdef_dict)
"""

from collections import defaultdict
from pathlib import Path
from typing import Any


class FileAnalyzer:
    """Analyzes C# file ownership by assemblies."""

    def __init__(self, asmdef_dict: dict[str, Any], root_path: Path):
        """Initialize file analyzer.

        Args:
            asmdef_dict: Dictionary of assembly definitions
            root_path: Root directory path
        """
        self.asmdef_dict = asmdef_dict
        self.root_path = Path(root_path).resolve()
        self.path_to_guid = self._build_path_to_guid_mapping()

    def _build_path_to_guid_mapping(self) -> dict[Path, str]:
        """Build mapping from folder paths to assembly GUIDs.

        Returns:
            Dictionary mapping directory paths to GUIDs
        """
        path_to_guid = {}

        for guid, data in self.asmdef_dict.items():
            if guid.startswith("_"):
                continue

            relative_path = data.get("relativePath")
            if relative_path:
                abs_path = self.root_path / relative_path
                path_to_guid[abs_path] = guid

        return path_to_guid

    def find_owning_assembly(self, file_path: Path) -> str | None:
        """Find which assembly owns a given C# file.

        Args:
            file_path: Path to the .cs file

        Returns:
            GUID of owning assembly or None
        """
        current_path = file_path.parent

        while True:
            if current_path in self.path_to_guid:
                return self.path_to_guid[current_path]

            parent = current_path.parent
            if parent == current_path:
                # Reached root
                return None
            current_path = parent

    @staticmethod
    def should_ignore_path(path: Path) -> bool:
        """Check if path should be ignored (Unity ignores ~).

        Args:
            path: Path to check

        Returns:
            True if path should be ignored
        """
        return any("~" in part for part in path.parts)

    def analyze(self) -> dict[str, Any]:
        """Perform complete file ownership analysis.

        Returns:
            Dictionary with analysis results and statistics
        """
        # Find all .cs files
        all_cs_files = self.root_path.rglob("*.cs")
        cs_files = [f for f in all_cs_files if not self.should_ignore_path(f.relative_to(self.root_path))]

        # Assign files to assemblies
        assembly_files = defaultdict(list)
        orphaned_files = []

        for cs_file in cs_files:
            owner_guid = self.find_owning_assembly(cs_file)

            if owner_guid:
                # Store relative path from assembly root
                assembly_root = None
                for path, guid in self.path_to_guid.items():
                    if guid == owner_guid:
                        assembly_root = path
                        break

                if assembly_root:
                    relative = cs_file.relative_to(assembly_root)
                    assembly_files[owner_guid].append(str(relative))
            else:
                orphaned_files.append(cs_file)

        # Update asmdef_dict with file assignments
        updated_dict = dict(self.asmdef_dict)
        for guid, files in assembly_files.items():
            if guid in updated_dict:
                updated_dict[guid]["csFiles"] = sorted(files)

        # Compile statistics
        stats = {
            "total_cs_files": len(cs_files),
            "assigned_files": sum(len(files) for files in assembly_files.values()),
            "orphaned_files": len(orphaned_files),
        }

        return {
            "asmdef_dict": updated_dict,
            "stats": stats,
            "orphaned_file_paths": orphaned_files,
        }
