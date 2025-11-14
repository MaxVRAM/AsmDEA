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


def build_nested_dependency_structure(graph, start_node, cycle_nodes, visited=None, max_depth=10):
    """
    Build a nested dependency structure for JSON visualisation.
    Returns a nested dictionary showing the dependency tree.
    """
    if visited is None:
        visited = set()

    if max_depth <= 0:
        return {"name": start_node, "truncated": True}

    if start_node in visited:
        return {"name": start_node, "circular_reference": True}

    visited.add(start_node)

    node_info = {"name": start_node, "in_cycle": start_node in cycle_nodes}

    dependencies = graph.get(start_node, [])
    if dependencies:
        node_info["dependencies"] = []
        for dep in dependencies:
            if dep in graph:  # Only include dependencies that exist in our graph
                dep_structure = build_nested_dependency_structure(
                    graph, dep, cycle_nodes, visited.copy(), max_depth - 1
                )
                node_info["dependencies"].append(dep_structure)

    return node_info


def create_cycle_report(cycles, graph, name_to_guid, detailed=False, max_depth=3):
    """
    Create a JSON-formatted report of the dependency cycles with nested structures.

    Output structure:
    - summary: Overview of cycles found
    - cycles: List of cycle details including:
      - cycle_number: Sequential identifier
      - path: List of assembly names in cycle
      - path_display: Human-readable cycle path
      - assemblies: Dict of assembly names to their GUIDs and metadata
      - dependency_chain: Nested structure showing the circular dependency
    - assemblies_in_multiple_cycles: (optional) List of assemblies appearing in >1 cycle
    - metadata: Analysis statistics
    """
    if not cycles:
        report_data = {"summary": {"cyclic_dependencies_found": 0, "message": "No cyclic dependencies found."}}
        return report_data

    # Get all nodes involved in any cycle
    all_cycle_nodes = set()
    for cycle in cycles:
        all_cycle_nodes.update(cycle)

    # Build the report as a dictionary structure
    report_data = {
        "summary": {"cyclic_dependencies_found": len(cycles), "total_assemblies_in_cycles": len(all_cycle_nodes)},
        "cycles": [],
    }

    for i, cycle in enumerate(cycles, 1):
        cycle_info = {"cycle_number": i, "path": cycle, "path_display": format_cycle_path(cycle), "assemblies": {}}

        # Add GUIDs and metadata for assemblies in this cycle
        for node in cycle[:-1]:  # Exclude the duplicate last node
            guid = name_to_guid.get(node, "GUID not found")
            cycle_info["assemblies"][node] = {
                "guid": guid,
                "direct_dependencies_in_cycle": [d for d in graph.get(node, []) if d in cycle],
            }

        # Build nested dependency chain starting from the first node in the cycle
        if detailed and cycle:
            cycle_set = set(cycle)
            cycle_info["dependency_chain"] = build_nested_dependency_structure(
                graph, cycle[0], cycle_set, max_depth=max_depth
            )

        report_data["cycles"].append(cycle_info)

    # Add assemblies involved in multiple cycles
    nodes_in_multiple_cycles = [n for n in all_cycle_nodes if sum(n in c for c in cycles) > 1]
    if nodes_in_multiple_cycles:
        report_data["assemblies_in_multiple_cycles"] = sorted(nodes_in_multiple_cycles)

    return report_data


def create_summary_report(report_data):
    """
    Create a simplified version of the cycle report without dependency chains.

    This removes the 'dependency_chain' field from each cycle while keeping
    all other information (summary, cycles metadata, assemblies).
    """
    summary_report = {"summary": report_data["summary"], "cycles": []}

    for cycle in report_data.get("cycles", []):
        summary_cycle = {
            "cycle_number": cycle["cycle_number"],
            "path": cycle["path"],
            "path_display": cycle["path_display"],
            "assemblies": cycle["assemblies"],
        }
        summary_report["cycles"].append(summary_cycle)

    # Include assemblies_in_multiple_cycles if present
    if "assemblies_in_multiple_cycles" in report_data:
        summary_report["assemblies_in_multiple_cycles"] = report_data["assemblies_in_multiple_cycles"]

    # Include metadata
    if "metadata" in report_data:
        summary_report["metadata"] = report_data["metadata"]

    return summary_report


def main():
    parser = argparse.ArgumentParser(description="Detect cyclic dependencies in assembly definitions")
    parser.add_argument("--file", default="asmdef_dictionary.json", help="Path to the asmdef dictionary JSON file")
    parser.add_argument("--detailed", action="store_true", help="Show nested dependency chains for cycles")
    parser.add_argument("--depth", type=int, default=3, help="Maximum depth for dependency chains (default: 3)")
    parser.add_argument("--output", "-o", help="Write report to this file (JSON format)")
    args = parser.parse_args()

    # Load asmdef dictionary
    asmdef_dict = load_asmdef_dictionary(args.file)

    # Build dependency graph
    graph, guid_to_name, name_to_guid = build_dependency_graph(asmdef_dict)

    # Detect cycles
    cycles = detect_cycles(graph)

    # Generate the report
    report_data = create_cycle_report(cycles, graph, name_to_guid, args.detailed, args.depth)

    # Add metadata
    report_data["metadata"] = {"total_assemblies_analysed": len(graph)}

    # Determine output paths
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path("./output/cycle_report.json")

    # Create summary output path based on main output
    summary_output_path = output_path.parent / f"{output_path.stem}_summary{output_path.suffix}"

    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write main report
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    print(f"JSON report written to {output_path}")

    # Always generate summary report
    summary_report = create_summary_report(report_data)
    with open(summary_output_path, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2, ensure_ascii=False)
    print(f"Summary report written to {summary_output_path}")


if __name__ == "__main__":
    main()
