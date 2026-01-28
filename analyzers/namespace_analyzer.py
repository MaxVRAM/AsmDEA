"""Namespace analysis - pure analysis without reporting."""

from typing import Dict, Any, List
from pathlib import Path
import re

from models import NamespaceAnalysisReport, AssemblyNamespaceStats


class NamespaceAnalyzer:
    """Analyzes C# file namespaces within assemblies."""

    def __init__(self, asmdef_dict: Dict[str, Any], root_path: Path, allow_child_namespaces: bool = True):
        """Initialize namespace analyzer.

        Args:
            asmdef_dict: Dictionary of assembly definitions
            root_path: Root directory path
            allow_child_namespaces: Whether to allow child namespaces
        """
        self.asmdef_dict = asmdef_dict
        self.root_path = Path(root_path).resolve()
        self.allow_child_namespaces = allow_child_namespaces

    @staticmethod
    def extract_namespace_from_file(file_path: Path) -> List[str]:
        """Extract namespace declarations from a C# file.

        Args:
            file_path: Path to the C# file

        Returns:
            List of namespace strings found
        """
        namespaces = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Remove single-line comments
            lines = content.split("\n")
            cleaned_lines = []
            for line in lines:
                comment_pos = line.find("//")
                if comment_pos >= 0:
                    line = line[:comment_pos]
                cleaned_lines.append(line)

            content = "\n".join(cleaned_lines)

            # Patterns for namespace declarations
            file_scoped_pattern = r"^\s*namespace\s+([\w\.]+)\s*;"
            traditional_pattern = r"^\s*namespace\s+([\w\.]+)\s*(?:\{|$)"

            for line in content.split("\n"):
                stripped = line.strip()
                if not stripped:
                    continue

                # Check file-scoped first
                match = re.match(file_scoped_pattern, line)
                if match:
                    namespaces.append(match.group(1))
                    continue

                # Check traditional
                match = re.match(traditional_pattern, line)
                if match:
                    namespaces.append(match.group(1))

        except Exception:
            pass

        return namespaces

    @staticmethod
    def is_child_namespace(namespace: str, root_namespace: str) -> bool:
        """Check if namespace is a child of root namespace.

        Args:
            namespace: Namespace to check
            root_namespace: Root namespace

        Returns:
            True if namespace is child of root
        """
        if not root_namespace:
            return False
        return namespace.startswith(root_namespace + ".")

    def analyze_assembly(self, guid: str, assembly_data: Dict[str, Any]) -> AssemblyNamespaceStats:
        """Analyze namespaces for a single assembly.

        Args:
            guid: Assembly GUID
            assembly_data: Assembly data dictionary

        Returns:
            AssemblyNamespaceStats for this assembly
        """
        assembly_name = assembly_data.get("name", guid)
        root_namespace = assembly_data.get("rootNamespace", "")
        cs_files = assembly_data.get("csFiles", [])
        relative_path = assembly_data.get("relativePath", "")

        stats = AssemblyNamespaceStats(
            assembly_name=assembly_name,
            assembly_guid=guid,
            root_namespace=root_namespace,
            total_files=len(cs_files),
        )

        if not cs_files:
            return stats

        assembly_path = self.root_path / relative_path

        for cs_file in cs_files:
            file_path = assembly_path / cs_file

            if not file_path.exists():
                continue

            namespaces = self.extract_namespace_from_file(file_path)

            if not namespaces:
                stats.no_namespace_files += 1
                stats.no_namespace_paths.append(file_path)
                continue

            primary_namespace = namespaces[0]

            # Check if namespace matches
            if primary_namespace == root_namespace:
                stats.matched_files += 1
                stats.matched_file_paths.append(file_path)
            elif self.allow_child_namespaces and self.is_child_namespace(primary_namespace, root_namespace):
                stats.child_namespace_files += 1
                stats.child_namespace_paths.append(file_path)
            else:
                stats.unmatched_files += 1
                stats.unmatched_file_paths.append(file_path)
                if primary_namespace not in stats.namespace_mismatches:
                    stats.namespace_mismatches[primary_namespace] = []
                stats.namespace_mismatches[primary_namespace].append(str(file_path))

        return stats

    def analyze(self) -> NamespaceAnalysisReport:
        """Perform complete namespace analysis.

        Returns:
            NamespaceAnalysisReport with all results
        """
        assemblies = {k: v for k, v in self.asmdef_dict.items() if not k.startswith("_")}

        report = NamespaceAnalysisReport(allow_child_namespaces=self.allow_child_namespaces)

        for guid, assembly_data in assemblies.items():
            stats = self.analyze_assembly(guid, assembly_data)
            report.assembly_stats[guid] = stats

            # Update totals
            report.total_files += stats.total_files
            report.total_matched += stats.matched_files
            report.total_mismatched += stats.unmatched_files
            report.total_no_namespace += stats.no_namespace_files

        report.total_assemblies = len(assemblies)

        return report
