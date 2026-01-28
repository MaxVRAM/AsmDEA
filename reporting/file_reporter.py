"""Reporter for file analysis results."""

from typing import Dict, Any

from .base import BaseReporter


class FileAnalysisReporter(BaseReporter):
    """Reporter for C# file ownership analysis results."""

    def print_console_report(self, data: Dict[str, Any]) -> None:
        """Print formatted file analysis report to console.

        Args:
            data: Dictionary containing file analysis results
        """
        asmdef_dict = data.get("asmdef_dict", {})
        stats = data.get("stats", {})

        print(f"\n{'=' * 60}")
        print("C# FILE ANALYSIS REPORT")
        print(f"{'=' * 60}\n")

        print(f"Total .cs files found: {stats.get('total_cs_files', 0)}")
        print(f"Files assigned to assemblies: {stats.get('assigned_files', 0)}")
        print(f"Orphaned files (no owning assembly): {stats.get('orphaned_files', 0)}\n")

        # Show assemblies with file counts
        assemblies = {k: v for k, v in asmdef_dict.items() if not k.startswith("_")}

        if assemblies:
            print("Files per assembly:")
            assembly_list = []
            for guid, assembly_data in assemblies.items():
                name = assembly_data.get("name", guid)
                file_count = len(assembly_data.get("csFiles", []))
                assembly_list.append((name, file_count))

            # Sort by file count (descending)
            assembly_list.sort(key=lambda x: x[1], reverse=True)

            for name, count in assembly_list:
                if count > 0:
                    print(f"  {name}: {count} files")

        print()

    def generate_json_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate JSON-serializable file analysis report.

        Args:
            data: Dictionary containing file analysis results

        Returns:
            Dictionary ready for JSON serialization
        """
        asmdef_dict = data.get("asmdef_dict", {})
        stats = data.get("stats", {})

        assemblies = {k: v for k, v in asmdef_dict.items() if not k.startswith("_")}

        return {
            "summary": {
                "totalCsFiles": stats.get("total_cs_files", 0),
                "assignedFiles": stats.get("assigned_files", 0),
                "orphanedFiles": stats.get("orphaned_files", 0),
            },
            "assemblies": {
                guid: {
                    "name": assembly_data.get("name", guid),
                    "fileCount": len(assembly_data.get("csFiles", [])),
                    "files": assembly_data.get("csFiles", []),
                    "relativePath": assembly_data.get("relativePath", ""),
                }
                for guid, assembly_data in assemblies.items()
            },
        }

    def print_detailed_report(self, data: Dict[str, Any], max_files_per_assembly: int = 10) -> None:
        """Print detailed report showing individual files.

        Args:
            data: Dictionary containing file analysis results
            max_files_per_assembly: Maximum files to show per assembly
        """
        asmdef_dict = data.get("asmdef_dict", {})
        assemblies = {k: v for k, v in asmdef_dict.items() if not k.startswith("_")}

        print(f"\n{'=' * 60}")
        print("DETAILED FILE ASSIGNMENTS")
        print(f"{'=' * 60}\n")

        for guid, assembly_data in assemblies.items():
            name = assembly_data.get("name", guid)
            cs_files = assembly_data.get("csFiles", [])

            if not cs_files:
                continue

            print(f"\n{name} ({len(cs_files)} files):")

            for i, file_path in enumerate(cs_files[:max_files_per_assembly]):
                print(f"  - {file_path}")

            if len(cs_files) > max_files_per_assembly:
                print(f"  ... and {len(cs_files) - max_files_per_assembly} more")

        print()
