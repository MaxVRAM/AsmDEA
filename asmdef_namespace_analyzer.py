#!/usr/bin/env python3
"""
Analyze C# file namespaces within assembly definitions.
Detects namespace mismatches and files without namespace declarations.
"""

import json
import sys
import argparse
import re
from pathlib import Path
from collections import defaultdict


def load_asmdef_dictionary(filepath):
    """Load the asmdef dictionary from JSON file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error: Failed to load asmdef dictionary: {e}", file=sys.stderr)
        sys.exit(1)


def extract_namespace_from_cs_file(file_path):
    """
    Extract namespace declarations from a C# file.
    Returns a list of namespace strings found in the file.
    Handles both traditional and file-scoped namespace declarations.
    """
    namespaces = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Remove single-line comments to avoid false matches
        # This is a simple approach that handles most cases
        lines = content.split("\n")
        cleaned_lines = []
        for line in lines:
            # Remove single-line comments but keep the rest of the line
            comment_pos = line.find("//")
            if comment_pos >= 0:
                line = line[:comment_pos]
            cleaned_lines.append(line)

        content = "\n".join(cleaned_lines)

        # Pattern for traditional namespace: namespace Foo.Bar (may have { on same line or next)
        # This captures: namespace Identifier.Identifier...
        traditional_pattern = r"^\s*namespace\s+([\w\.]+)\s*(?:\{|$)"
        # Pattern for file-scoped namespace (C# 10+): namespace Foo.Bar;
        file_scoped_pattern = r"^\s*namespace\s+([\w\.]+)\s*;"

        for line in content.split("\n"):
            # Skip empty lines
            stripped = line.strip()
            if not stripped:
                continue

            # Check for file-scoped namespace first (more specific)
            match = re.match(file_scoped_pattern, line)
            if match:
                namespaces.append(match.group(1))
                continue

            # Check for traditional namespace
            match = re.match(traditional_pattern, line)
            if match:
                namespaces.append(match.group(1))
                continue

    except Exception as e:
        print(f"Warning: Failed to read file '{file_path}': {e}", file=sys.stderr)

    return namespaces


def is_namespace_match(file_namespace, root_namespace):
    """
    Check if a file's namespace matches or is a child of the root namespace.
    Returns True if it matches, False otherwise.
    Empty root namespace matches everything.
    """
    if not root_namespace:
        # No root namespace defined, so everything matches
        return True

    if not file_namespace:
        # File has no namespace but assembly expects one
        return False

    # Exact match
    if file_namespace == root_namespace:
        return True

    # Child namespace (e.g., "Foo.Bar.Baz" is child of "Foo.Bar")
    if file_namespace.startswith(root_namespace + "."):
        return True

    return False


def is_child_namespace(namespace, root_namespace):
    """
    Check if a namespace is a child of the root namespace.

    Args:
        namespace: The namespace to check (e.g., "Flaim.Systems.Contracts.Messaging")
        root_namespace: The root namespace (e.g., "Flaim.Systems.Contracts")

    Returns:
        True if namespace is root_namespace or starts with root_namespace + "."
    """
    if not namespace or not root_namespace:
        return False

    if namespace == root_namespace:
        return True

    # Check if it's a child namespace (must be followed by a dot to avoid partial matches)
    # e.g., "Flaim.Systems.Contracts.Messaging" starts with "Flaim.Systems.Contracts."
    return namespace.startswith(root_namespace + ".")


def extract_namespace(file_path):
    """
    Extract the primary namespace declaration from a C# file.
    Returns the first namespace string found, or None if no namespace is found.
    Handles both traditional and file-scoped namespace declarations.
    """
    namespaces = extract_namespace_from_cs_file(file_path)
    # Return the first namespace found, or None if the list is empty
    return namespaces[0] if namespaces else None


def analyze_assembly_namespaces(asmdef_dict, root_path, allow_child_namespaces=True):
    """
    Analyze namespace declarations in C# files for each assembly.

    Args:
        asmdef_dict: The assembly definition dictionary
        root_path: Root path for the project
        allow_child_namespaces: If True, allow namespaces that extend the root namespace

    Returns:
        Tuple of (enhanced_dict, stats)
    """
    root = Path(root_path).resolve()

    if not root.exists():
        print(f"Error: Root path '{root_path}' does not exist.", file=sys.stderr)
        return None

    stats = {
        "total_files_analyzed": 0,
        "files_with_namespaces": 0,
        "files_without_namespaces": 0,
        "namespace_mismatches": 0,
        "assemblies_with_mismatches": 0,
    }

    # Filter out metadata entries
    assemblies = {k: v for k, v in asmdef_dict.items() if not k.startswith("_")}

    for guid, data in assemblies.items():
        cs_files = data.get("csFiles", [])
        root_namespace = data.get("rootNamespace", "")
        assembly_path = Path(root_path) / data.get("relativePath", "")

        if not cs_files:
            continue

        analysis = {
            "rootNamespace": root_namespace,
            "filesAnalyzed": len(cs_files),
            "namespacesByFile": {},
            "mismatchedFiles": [],
            "filesWithoutNamespace": [],
            "uniqueNamespaces": [],
        }

        namespaces_found = set()

        for cs_file in cs_files:
            file_path = assembly_path / cs_file

            if not file_path.exists():
                continue

            # Extract the primary namespace (first one found)
            namespace = extract_namespace(file_path)

            # Store only files that have a namespace
            if namespace:
                analysis["namespacesByFile"][cs_file] = namespace
                namespaces_found.add(namespace)
                stats["files_with_namespaces"] += 1

            # Check for mismatches or missing namespaces
            if namespace is None:
                analysis["filesWithoutNamespace"].append(cs_file)
                stats["files_without_namespaces"] += 1
            elif root_namespace:
                # Determine if this is a mismatch based on allow_child_namespaces setting
                if allow_child_namespaces:
                    is_valid = is_child_namespace(namespace, root_namespace)
                else:
                    is_valid = namespace == root_namespace

                if not is_valid:
                    analysis["mismatchedFiles"].append({"file": cs_file, "namespace": namespace})
                    stats["namespace_mismatches"] += 1

            stats["total_files_analyzed"] += 1

        # Get unique namespaces that don't match root (excluding valid child namespaces if allowed)
        if root_namespace:
            if allow_child_namespaces:
                non_matching = [ns for ns in namespaces_found if not is_child_namespace(ns, root_namespace)]
            else:
                non_matching = [ns for ns in namespaces_found if ns != root_namespace]

            analysis["uniqueNamespaces"] = sorted(non_matching)
        else:
            analysis["uniqueNamespaces"] = sorted(namespaces_found)

        data["namespaceAnalysis"] = analysis

        # Update counts
        if analysis["mismatchedFiles"] or analysis["filesWithoutNamespace"]:
            stats["assemblies_with_mismatches"] += 1

    return asmdef_dict, stats


def print_namespace_report(stats, asmdef_dict, allow_child_namespaces=True):
    """Print a detailed namespace analysis report."""
    print("\n" + "=" * 60)
    print("NAMESPACE ANALYSIS REPORT")
    print("=" * 60)

    child_ns_mode = "ENABLED" if allow_child_namespaces else "DISABLED"
    print(f"Child namespace allowance: {child_ns_mode}")

    print(f"\nTotal files analyzed: {stats['total_files_analyzed']}")
    print(f"Files with namespaces: {stats['files_with_namespaces']}")
    print(f"Files without namespaces: {stats['files_without_namespaces']}")
    print(f"Namespace mismatches: {stats['namespace_mismatches']}")
    print(f"Assemblies with issues: {stats['assemblies_with_mismatches']}")

    # Filter assemblies with issues
    assemblies = {k: v for k, v in asmdef_dict.items() if not k.startswith("_")}
    assemblies_with_issues = []

    for guid, data in assemblies.items():
        ns_analysis = data.get("namespaceAnalysis", {})
        if ns_analysis.get("mismatchedFiles") or ns_analysis.get("filesWithoutNamespace"):
            assemblies_with_issues.append((data.get("name", guid), data))

    if assemblies_with_issues:
        print("\n" + "-" * 60)
        print("ASSEMBLIES WITH NAMESPACE ISSUES:")
        print("-" * 60)

        # Sort by number of issues (descending)
        assemblies_with_issues.sort(
            key=lambda x: len(x[1]["namespaceAnalysis"].get("mismatchedFiles", []))
            + len(x[1]["namespaceAnalysis"].get("filesWithoutNamespace", [])),
            reverse=True,
        )

        for name, data in assemblies_with_issues:
            ns_analysis = data["namespaceAnalysis"]
            root_ns = ns_analysis.get("rootNamespace", "(none)")
            mismatched = len(ns_analysis.get("mismatchedFiles", []))
            no_ns = len(ns_analysis.get("filesWithoutNamespace", []))

            print(f"\n{name}")
            print(f"  Root namespace: {root_ns}")
            print(f"  Mismatched files: {mismatched}")
            print(f"  Files without namespace: {no_ns}")

            # Show unique namespaces found
            unique_ns = ns_analysis.get("uniqueNamespaces", [])
            if unique_ns:
                print(f"  Unique namespaces found: {', '.join(unique_ns)}")

            # Show sample mismatches (max 3)
            mismatched_files = ns_analysis.get("mismatchedFiles", [])
            if mismatched_files:
                print("  Sample mismatches:")
                for mismatch in mismatched_files[:3]:
                    print(f"    - {mismatch['file']}: {mismatch['namespace']}")
                if len(mismatched_files) > 3:
                    print(f"    ... and {len(mismatched_files) - 3} more")
    else:
        print("\nNo namespace issues found! All files use appropriate namespaces.")


def create_namespace_problems_report(asmdef_dict):
    """
    Create a simplified report containing only assemblies with namespace problems.

    Returns a dictionary with structure:
    {
        "assemblyName": {
            "rootNamespace": "Expected.Namespace",
            "uniqueNamespaces": ["Actual.Namespace1", "Actual.Namespace2"],
            "mismatchedFiles": [
                {"file": "path/to/file.cs", "namespace": "Wrong.Namespace"}
            ],
            "filesWithoutNamespace": ["path/to/other.cs"]
        }
    }
    """
    problems_report = {}

    # Filter out metadata entries
    assemblies = {k: v for k, v in asmdef_dict.items() if not k.startswith("_")}

    for guid, data in assemblies.items():
        ns_analysis = data.get("namespaceAnalysis", {})

        # Check if this assembly has any problems
        has_mismatches = bool(ns_analysis.get("mismatchedFiles"))
        has_missing = bool(ns_analysis.get("filesWithoutNamespace"))

        if has_mismatches or has_missing:
            assembly_name = data.get("name", guid)

            problems_report[assembly_name] = {
                "rootNamespace": ns_analysis.get("rootNamespace", ""),
                "uniqueNamespaces": ns_analysis.get("uniqueNamespaces", []),
                "mismatchedFiles": ns_analysis.get("mismatchedFiles", []),
                "filesWithoutNamespace": ns_analysis.get("filesWithoutNamespace", []),
            }

    return problems_report


def main():
    parser = argparse.ArgumentParser(description="Analyze C# namespace declarations in assembly definitions")
    parser.add_argument("--file", default="asmdef_dictionary.json", help="Path to the asmdef dictionary JSON file")
    parser.add_argument("--root", required=True, help="Root path that was used to generate the dictionary")
    parser.add_argument(
        "--output", "-o", help="Write the enhanced dictionary to this file (if not specified, updates the input file)"
    )
    parser.add_argument("--report", action="store_true", help="Print a summary report of namespace analysis")
    parser.add_argument(
        "--allow-child-namespaces",
        action="store_true",
        default=True,
        help="Allow child namespaces that extend the root namespace (default: True)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Disable child namespace allowance (equivalent to --no-allow-child-namespaces)",
    )
    args = parser.parse_args()

    # Handle strict mode
    allow_child_namespaces = args.allow_child_namespaces and not args.strict

    # Load the asmdef dictionary
    asmdef_dict = load_asmdef_dictionary(args.file)

    # Analyze namespaces
    print(f"Analyzing namespaces in C# files...")
    if not allow_child_namespaces:
        print("(Running in strict mode - child namespaces not allowed)")

    enhanced_dict, stats = analyze_assembly_namespaces(asmdef_dict, args.root, allow_child_namespaces)

    if enhanced_dict is None:
        sys.exit(1)

    # Print report if requested
    if args.report:
        print_namespace_report(stats, enhanced_dict, allow_child_namespaces)

    # Add stats to metadata
    if "_metadata" not in enhanced_dict:
        enhanced_dict["_metadata"] = {}
    enhanced_dict["_metadata"]["namespaceAnalysis"] = stats

    # Save the enhanced dictionary
    output_file = args.output if args.output else args.file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(enhanced_dict, f, indent=2, ensure_ascii=False)
        print(f"\nSuccessfully wrote enhanced dictionary to '{output_file}'")
    except Exception as e:
        print(f"Error: Failed to write output file '{output_file}': {e}", file=sys.stderr)
        sys.exit(1)

    # Generate and save the namespace problems report
    problems_report = create_namespace_problems_report(enhanced_dict)

    if problems_report:
        # Determine problems report output path
        problems_output_path = output_path.parent / f"{output_path.stem}_namespace_problems{output_path.suffix}"

        try:
            with open(problems_output_path, "w", encoding="utf-8") as f:
                json.dump(problems_report, f, indent=2, ensure_ascii=False)
            print(f"Namespace problems report written to '{problems_output_path}'")
        except Exception as e:
            print(f"Error: Failed to write namespace problems report: {e}", file=sys.stderr)
    else:
        print("No namespace problems found - skipping problems report generation")


if __name__ == "__main__":
    main()
