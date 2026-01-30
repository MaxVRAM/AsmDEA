"""Cycle detection analyser - detects circular dependencies in assembly references.

Analyses Unity Assembly Definition dependencies to find circular reference chains
that can cause compilation issues. Uses depth-first search with state tracking
to detect cycles in the dependency graph.

Key classes:
    - CycleAnalyser: Main analyser for detecting dependency cycles

Features:
    - Builds dependency graph from assembly references
    - Detects all cycles using DFS traversal
    - Generates detailed reports with cycle paths
    - Builds dependency trees showing cycle context

Usage:
    from analysers import CycleAnalyser
    from models import AnalysisConfig

    config = AnalysisConfig(dict_file="asmdef_dictionary.json")
    analyser = CycleAnalyser(config)
    report = analyser.analyse(asmdef_dict)
    print(f"Found {report.total_cycles} cycles")
"""

from collections import defaultdict
from typing import Any

from models import CycleDetails, CyclePath, CycleReport, CycleSummary


class CycleAnalyser:
    """Analyses assembly dependencies to detect cycles."""

    def __init__(self, asmdef_dict: dict[str, Any]):
        """Initialize cycle analyser.

        Args:
            asmdef_dict: Dictionary of assembly definitions keyed by GUID
        """
        self.asmdef_dict = asmdef_dict
        self.graph, self.guid_to_name, self.name_to_guid = self._build_dependency_graph()

    def _build_dependency_graph(
        self,
    ) -> tuple[dict[str, list[str]], dict[str, str], dict[str, str]]:
        """Build dependency graph from assembly data.

        Returns:
            Tuple of (graph, guid_to_name, name_to_guid)
        """
        # Filter out metadata entries
        assemblies = {k: v for k, v in self.asmdef_dict.items() if not k.startswith("_")}

        # Map GUIDs to assembly names
        guid_to_name = {guid: data.get("name", guid) for guid, data in assemblies.items()}

        # Create reverse mapping
        name_to_guid = {data.get("name", guid): guid for guid, data in assemblies.items()}

        # Create graph as adjacency list
        graph = defaultdict(list)

        for guid, data in assemblies.items():
            assembly_name = data.get("name", guid)
            references = data.get("references", [])

            for ref in references:
                ref_name = guid_to_name.get(ref, ref)
                graph[assembly_name].append(ref_name)

        return dict(graph), guid_to_name, name_to_guid

    def detect_cycles(self) -> list[list[str]]:
        """Detect all cycles in the dependency graph using DFS.

        Returns:
            List of cycles, where each cycle is a list of node names
        """
        # Track node states: 0 = unvisited, 1 = visiting, 2 = visited
        states = dict.fromkeys(self.graph, 0)
        cycles = []

        def dfs(node: str, path: list[str]) -> None:
            if states[node] == 1:
                # Found a cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return

            if states[node] == 2:
                # Already fully explored
                return

            # Mark as visiting
            states[node] = 1
            path.append(node)

            # Explore neighbors
            for neighbour in self.graph.get(node, []):
                if neighbour in self.graph:
                    dfs(neighbour, path.copy())

            # Mark as visited
            states[node] = 2

        # Run DFS from each unvisited node
        for node in self.graph:
            if states[node] == 0:
                dfs(node, [])

        return cycles

    def _build_dependency_tree(self, root: str, cycle_nodes: set[str], max_depth: int = 2) -> dict[str, Any]:
        """Build a dependency tree from a root node.

        Args:
            root: Root node to start from
            cycle_nodes: Set of nodes that are part of the cycle
            max_depth: Maximum depth to traverse

        Returns:
            Nested dictionary representing the dependency tree
        """

        def build_node(node: str, depth: int, visited: set[str]) -> dict[str, Any]:
            in_cycle = node in cycle_nodes
            result: dict[str, Any] = {
                "name": node,
                "inCycle": in_cycle,
                "dependencies": [],
            }

            if depth >= max_depth or node in visited:
                return result

            visited = visited | {node}
            for dep in self.graph.get(node, []):
                result["dependencies"].append(build_node(dep, depth + 1, visited))

            return result

        return build_node(root, 0, set())

    def analyse(self, max_depth: int = 3) -> CycleReport:
        """Perform complete cycle analysis.

        Args:
            max_depth: Maximum depth for dependency tree visualization

        Returns:
            CycleReport with detected cycles and metadata
        """
        cycles = self.detect_cycles()

        # Convert raw cycle lists to CycleDetails objects
        cycle_details = []
        all_affected_nodes = set()

        for i, cycle_nodes in enumerate(cycles, 1):
            cycle_path = CyclePath(nodes=cycle_nodes)
            affected = cycle_nodes[:-1]  # Exclude duplicate last node
            all_affected_nodes.update(affected)

            # Build dependency tree from the root node
            root_node = cycle_nodes[0] if cycle_nodes else None
            dependency_tree = None
            if root_node:
                dependency_tree = self._build_dependency_tree(root_node, set(affected), max_depth=max_depth)

            details = CycleDetails(
                cycle_id=i,
                cycle_path=cycle_path,
                affected_assemblies=affected,
                root_node=root_node,
                dependency_tree=dependency_tree,
            )
            cycle_details.append(details)

        report = CycleReport(
            cycles=cycle_details,
            total_cycles=len(cycles),
            total_nodes=len(self.graph),
            affected_nodes=list(all_affected_nodes),
            graph=self.graph,
            guid_to_name=self.guid_to_name,
            name_to_guid=self.name_to_guid,
        )

        return report

    def get_summary(self, report: CycleReport) -> CycleSummary:
        """Generate summary statistics from cycle report.

        Args:
            report: CycleReport to summarize

        Returns:
            CycleSummary with statistics
        """
        return CycleSummary.from_report(report)
