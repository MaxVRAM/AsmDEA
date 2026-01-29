"""Data models for cycle detection and reporting.

Defines data structures for representing cyclic dependency analysis results,
including detected cycles, dependency trees, and summary statistics.

Model hierarchy:
    - CyclePath: Represents a single circular dependency path
    - CycleDetail: Detailed information about one cycle including dependency tree
    - CycleReport: Complete report with all detected cycles
    - CycleSummary: Aggregate statistics (cycle count, min/max/avg length)

Usage:
    from models import CycleReport, CycleDetail, CyclePath

    report = CycleReport(cycles=[...], graph={...})
    summary = report.generate_summary()
    json_report = report.to_dict()
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CyclePath:
    """Represents a single cyclic dependency path.

    Attributes:
        nodes: List of node names in the cycle (first and last are the same)
        length: Number of unique nodes in the cycle
        formatted_path: Human-readable representation of the cycle
    """

    nodes: list[str]

    @property
    def length(self) -> int:
        """Get the number of unique nodes in the cycle."""
        return len(self.nodes) - 1 if self.nodes else 0

    @property
    def formatted_path(self) -> str:
        """Get formatted string representation of cycle path."""
        return " -> ".join(self.nodes)

    def __str__(self) -> str:
        """String representation of the cycle."""
        return self.formatted_path


@dataclass
class DependencyNode:
    """Represents a node in the dependency tree.

    Attributes:
        name: Node name (assembly name)
        is_in_cycle: Whether this node is part of a cycle
        dependencies: List of child dependency nodes
        depth: Depth in the tree (0 = root)
    """

    name: str
    is_in_cycle: bool = False
    dependencies: list["DependencyNode"] = field(default_factory=list)
    depth: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "inCycle": self.is_in_cycle,
            "dependencies": [dep.to_dict() for dep in self.dependencies],
        }


@dataclass
class CycleDetails:
    """Detailed information about a specific cycle.

    Attributes:
        cycle_id: Unique identifier for this cycle
        cycle_path: The CyclePath object
        affected_assemblies: List of assembly names in cycle
        dependency_tree: Nested structure showing dependencies
        root_node: Starting point for dependency analysis
    """

    cycle_id: int
    cycle_path: CyclePath
    affected_assemblies: list[str] = field(default_factory=list)
    dependency_tree: dict[str, Any] | None = None
    root_node: str | None = None

    @property
    def cycle_length(self) -> int:
        """Get the length of the cycle."""
        return self.cycle_path.length


@dataclass
class CycleReport:
    """Complete cycle analysis report.

    Attributes:
        cycles: List of detected cycles with details
        total_cycles: Number of cycles detected
        total_nodes: Total nodes in the dependency graph
        affected_nodes: Nodes that are part of at least one cycle
        graph: The dependency graph (adjacency list)
        guid_to_name: Mapping from GUID to assembly name
        name_to_guid: Mapping from assembly name to GUID
    """

    cycles: list[CycleDetails] = field(default_factory=list)
    total_cycles: int = 0
    total_nodes: int = 0
    affected_nodes: list[str] = field(default_factory=list)
    graph: dict[str, list[str]] = field(default_factory=dict)
    guid_to_name: dict[str, str] = field(default_factory=dict)
    name_to_guid: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate derived fields."""
        self.total_cycles = len(self.cycles)
        if self.graph:
            self.total_nodes = len(self.graph)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "totalCycles": self.total_cycles,
            "totalNodes": self.total_nodes,
            "affectedNodes": self.affected_nodes,
            "cycles": [
                {
                    "cycleId": cycle.cycle_id,
                    "cyclePath": cycle.cycle_path.nodes,
                    "cycleLength": cycle.cycle_length,
                    "dependencyTree": cycle.dependency_tree,
                }
                for cycle in self.cycles
            ],
        }


@dataclass
class CycleSummary:
    """Summary statistics for cycle analysis.

    Attributes:
        total_cycles: Total number of cycles found
        total_assemblies: Total assemblies analyzed
        affected_assemblies: Number of assemblies in cycles
        shortest_cycle_length: Length of shortest cycle
        longest_cycle_length: Length of longest cycle
        average_cycle_length: Average cycle length
    """

    total_cycles: int
    total_assemblies: int
    affected_assemblies: int
    shortest_cycle_length: int = 0
    longest_cycle_length: int = 0
    average_cycle_length: float = 0.0

    @classmethod
    def from_report(cls, report: CycleReport) -> "CycleSummary":
        """Create summary from a full cycle report.

        Args:
            report: The CycleReport to summarize

        Returns:
            CycleSummary instance
        """
        if not report.cycles:
            return cls(
                total_cycles=0,
                total_assemblies=report.total_nodes,
                affected_assemblies=0,
            )

        cycle_lengths = [cycle.cycle_length for cycle in report.cycles]

        return cls(
            total_cycles=report.total_cycles,
            total_assemblies=report.total_nodes,
            affected_assemblies=len(report.affected_nodes),
            shortest_cycle_length=min(cycle_lengths),
            longest_cycle_length=max(cycle_lengths),
            average_cycle_length=sum(cycle_lengths) / len(cycle_lengths),
        )
