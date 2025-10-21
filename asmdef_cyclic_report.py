#!/usr/bin/env python3
import json
import sys
import argparse
from collections import defaultdict
from pathlib import Path


def load_asmdef_dictionary(filepath):
    """Load the asmdef dictionary from JSON file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error: Failed to load asmdef dictionary: {e}", file=sys.stderr)
        sys.exit(1)


def build_dependency_graph(asmdef_dict):
    """Build a dependency graph from the asmdef dictionary."""
    # Filter out metadata entries (those starting with underscore)
    assemblies = {k: v for k, v in asmdef_dict.items() if not k.startswith("_")}

    # Map GUIDs to assembly names for easier reading
    guid_to_name = {guid: data.get("name", guid) for guid, data in assemblies.items()}

    # Create reverse mapping: name to GUID
    name_to_guid = {data.get("name", guid): guid for guid, data in assemblies.items()}

    # Create graph as adjacency list (name -> [dependencies])
    graph = defaultdict(list)

    # Map assembly names to their references
    for guid, data in assemblies.items():
        assembly_name = data.get("name", guid)
        references = data.get("references", [])

        for ref in references:
            # Convert GUID references to names if possible
            if ref in guid_to_name:
                ref_name = guid_to_name[ref]
            else:
                ref_name = ref

            graph[assembly_name].append(ref_name)

    return graph, guid_to_name, name_to_guid


def detect_cycles(graph):
    """Detect cycles in the dependency graph using DFS."""
    # Track node states: 0 = unvisited, 1 = visiting, 2 = visited
    states = {node: 0 for node in graph}
    cycles = []

    def dfs(node, path):
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
        for neighbor in graph.get(node, []):
            if neighbor in graph:  # Only follow if the neighbor exists in our graph
                dfs(neighbor, path.copy())

        # Mark as visited
        states[node] = 2

    # Run DFS from each unvisited node
    for node in graph:
        if states[node] == 0:
            dfs(node, [])

    return cycles


def format_cycle_path(cycle):
    """Format a cycle path for display."""
    return " → ".join(cycle)


def generate_cycle_focused_tree(graph, root, cycle_nodes, max_depth=3, visited=None, depth=0, path=None):
    """Generate a tree visualisation focusing only on paths related to cycles."""
    if visited is None:
        visited = set()
    if path is None:
        path = []

    # Stop conditions
    if depth > max_depth:
        return [f"{'  ' * depth}{root} ..."]

    if root in path:
        return [f"{'  ' * depth}{root} [CYCLE]"]

    if root in visited:
        return [f"{'  ' * depth}{root} (already visited)"]

    visited.add(root)
    path.append(root)

    # Show if this node is part of a cycle
    cycle_marker = " [IN CYCLE]" if root in cycle_nodes else ""
    lines = [f"{'  ' * depth}{root}{cycle_marker}"]

    # Sort dependencies to show cycle-related nodes first
    deps = sorted(graph.get(root, []), key=lambda x: (0 if x in cycle_nodes else 1, x))

    # Only explore relevant dependencies
    for dep in deps:
        if dep in graph and (dep in cycle_nodes or depth < 1):
            lines.extend(
                generate_cycle_focused_tree(graph, dep, cycle_nodes, max_depth, visited.copy(), depth + 1, path.copy())
            )

    return lines


def create_cycle_report(cycles, graph, name_to_guid, detailed=False, max_depth=3):
    """Create a focused report of the dependency cycles."""
    if not cycles:
        return "No cyclic dependencies found."

    # Get all nodes involved in any cycle
    all_cycle_nodes = set()
    for cycle in cycles:
        all_cycle_nodes.update(cycle)

    report = [f"Found {len(cycles)} cyclic dependencies:"]

    for i, cycle in enumerate(cycles, 1):
        report.append(f"\nCYCLE {i}: {format_cycle_path(cycle)}")

        # Show GUIDs for assemblies in this cycle
        report.append("\nAssembly GUIDs in this cycle:")
        for node in cycle[:-1]:  # Exclude the duplicate last node
            guid = name_to_guid.get(node, "GUID not found")
            report.append(f"  {node}: {guid}")

        # Show direct dependencies between cycle nodes
        report.append("\nDirect dependencies within this cycle:")
        for node in cycle:
            cycle_deps = [d for d in graph.get(node, []) if d in cycle]
            if cycle_deps:
                report.append(f"  {node} → {', '.join(cycle_deps)}")

        if detailed:
            # Show a focused tree for the first node in cycle
            report.append("\nFocused dependency tree:")
            tree = generate_cycle_focused_tree(graph, cycle[0], all_cycle_nodes, max_depth)
            report.extend(tree)

        report.append("\n" + "-" * 40)

    # Add summary information
    nodes_in_multiple_cycles = [n for n in all_cycle_nodes if sum(n in c for c in cycles) > 1]
    if nodes_in_multiple_cycles:
        report.append("\nAssemblies involved in multiple cycles:")
        report.append("  " + ", ".join(sorted(nodes_in_multiple_cycles)))

    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Detect cyclic dependencies in assembly definitions")
    parser.add_argument("--file", default="asmdef_dictionary.json", help="Path to the asmdef dictionary JSON file")
    parser.add_argument("--detailed", action="store_true", help="Show detailed dependency trees for cycles")
    parser.add_argument("--depth", type=int, default=3, help="Maximum depth for dependency trees (default: 3)")
    parser.add_argument("--output", "-o", help="Write report to this file")
    args = parser.parse_args()

    # Load asmdef dictionary
    asmdef_dict = load_asmdef_dictionary(args.file)

    # Build dependency graph
    graph, guid_to_name, name_to_guid = build_dependency_graph(asmdef_dict)

    # Detect cycles
    cycles = detect_cycles(graph)

    # Generate the report
    report = create_cycle_report(cycles, graph, name_to_guid, args.detailed, args.depth)

    # Output the report
    if args.output:
        # Create output directory if it doesn't exist
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
            f.write(f"\n\nAnalysed {len(graph)} assemblies.")
        print(f"Report written to {args.output}")
    else:
        print(report)
        print(f"\nAnalysed {len(graph)} assemblies.")


if __name__ == "__main__":
    main()
