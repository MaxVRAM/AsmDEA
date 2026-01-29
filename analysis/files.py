#!/usr/bin/env python3
"""
Analyse .cs files contained in each assembly definition.
Respects nested asmdef boundaries - scripts belong to the nearest parent asmdef.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_asmdef_dictionary(filepath: str) -> dict[str, Any]:
    """Load the asmdef dictionary from JSON file.

    Args:
        filepath: Path to the JSON dictionary file

    Returns:
        Dictionary mapping GUIDs to assembly data
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error: Failed to load asmdef dictionary: {e}", file=sys.stderr)
        sys.exit(1)


def build_path_to_guid_mapping(asmdef_dict: dict[str, Any], root_path: str) -> dict[Path, str]:
    """Build a mapping from folder paths to GUIDs.

    Args:
        asmdef_dict: Dictionary of assembly definitions
        root_path: Root directory path

    Returns:
        Dictionary mapping directory paths to assembly GUIDs
    """
    path_to_guid = {}
    root = Path(root_path).resolve()

    for guid, data in asmdef_dict.items():
        if "relativePath" in data:
            # Convert relative path back to absolute path
            abs_path = root / data["relativePath"]
            path_to_guid[abs_path] = guid
        else:
            print(f"Warning: No relativePath found for {data.get('name', guid)}", file=sys.stderr)

    return path_to_guid


def find_owning_assembly(file_path: Path, path_to_guid: dict[Path, str]) -> str | None:
    """Find which assembly owns a given .cs file.

    Args:
        file_path: Path to the .cs file
        path_to_guid: Mapping of directory paths to assembly GUIDs

    Returns:
        GUID of the owning assembly, or None if not found

    The owning assembly is the one in the nearest parent directory
    that contains an asmdef file.
    """
    current_path = file_path.parent

    # Walk up the directory tree
    while True:
        # Check if this directory has an asmdef
        if current_path in path_to_guid:
            return path_to_guid[current_path]

        # Move to parent directory
        parent = current_path.parent
        if parent == current_path:
            # Reached the root without finding an asmdef
            return None
        current_path = parent


def should_ignore_path(path):
    """
    Check if a path should be ignored (Unity ignores folders ending with ~).
    Returns True if any part of the path contains `~`.
    """
    return any("~" in part for part in path.parts)


def analyse_assembly_files(asmdef_dict, root_path):
    """
    Analyse all .cs files and assign them to their owning assemblies.
    Returns a dictionary mapping GUIDs to lists of .cs file paths.
    """
    root = Path(root_path).resolve()

    if not root.exists():
        print(f"Error: Root path '{root_path}' does not exist.", file=sys.stderr)
        return None

    # Build mapping of assembly folder paths to GUIDs
    path_to_guid = build_path_to_guid_mapping(asmdef_dict, root_path)

    # Build reverse mapping: GUID to assembly folder path
    guid_to_path = {guid: path for path, guid in path_to_guid.items()}

    # Dictionary to hold cs files for each assembly
    assembly_files = defaultdict(list)

    # Find all .cs files, excluding those in folders ending with ~
    all_cs_files = root.rglob("*.cs")
    cs_files = [f for f in all_cs_files if not should_ignore_path(f.relative_to(root))]

    print(f"Found {len(cs_files)} .cs file(s) under '{root_path}' (excluding ~ folders)")

    # Assign each .cs file to its owning assembly
    unassigned_files = []
    for cs_file in cs_files:
        owning_guid = find_owning_assembly(cs_file, path_to_guid)

        if owning_guid:
            # Calculate relative path from the assembly's directory, not root
            try:
                assembly_path = guid_to_path[owning_guid]
                relative_cs_path = cs_file.relative_to(assembly_path)
                assembly_files[owning_guid].append(str(relative_cs_path).replace("\\", "/"))
            except ValueError:
                print(f"Warning: Could not calculate relative path for '{cs_file}'", file=sys.stderr)
        else:
            # File is not under any assembly definition
            try:
                relative_cs_path = cs_file.relative_to(root)
                unassigned_files.append(str(relative_cs_path).replace("\\", "/"))
            except ValueError:
                pass

    # Report statistics
    print(
        f"\nAssigned {sum(len(files) for files in assembly_files.values())} files to {len(assembly_files)} assemblies"
    )
    if unassigned_files:
        print(f"Found {len(unassigned_files)} .cs files not under any assembly definition")

    return dict(assembly_files), unassigned_files


def add_files_to_dictionary(asmdef_dict, assembly_files, unassigned_files):
    """Add the csFiles property to each assembly in the dictionary."""
    for guid, data in asmdef_dict.items():
        # Add the list of cs files (empty list if none)
        data["csFiles"] = assembly_files.get(guid, [])
        data["fileCount"] = len(data["csFiles"])

    # Add unassigned files as metadata in a special key
    if unassigned_files:
        asmdef_dict["_metadata"] = {"unassignedFiles": unassigned_files, "unassignedFileCount": len(unassigned_files)}

    return asmdef_dict


def main():
    parser = argparse.ArgumentParser(description="Analyse .cs files contained in each assembly definition")
    parser.add_argument("--file", default="asmdef_dictionary.json", help="Path to the asmdef dictionary JSON file")
    parser.add_argument("--root", required=True, help="Root path that was used to generate the dictionary")
    parser.add_argument(
        "--output", "-o", help="Write the enhanced dictionary to this file (if not specified, updates the input file)"
    )
    parser.add_argument("--report", action="store_true", help="Print a summary report of files per assembly")
    args = parser.parse_args()

    # Load the asmdef dictionary
    asmdef_dict = load_asmdef_dictionary(args.file)

    # Analyse the files
    assembly_files, unassigned_files = analyse_assembly_files(asmdef_dict, args.root)

    if assembly_files is None:
        sys.exit(1)

    # Add files to dictionary
    enhanced_dict = add_files_to_dictionary(asmdef_dict, assembly_files, unassigned_files)

    # Print report if requested
    if args.report:
        print("\n" + "=" * 60)
        print("ASSEMBLY FILE COUNT REPORT")
        print("=" * 60)

        # Filter out metadata entries (those starting with underscore)
        assemblies = {k: v for k, v in enhanced_dict.items() if not k.startswith("_")}
        sorted_assemblies = sorted(assemblies.items(), key=lambda x: x[1].get("fileCount", 0), reverse=True)

        for guid, data in sorted_assemblies:
            name = data.get("name", guid)
            count = data.get("fileCount", 0)
            rel_path = data.get("relativePath", "N/A")
            print(f"{name:50} {count:5} files  ({rel_path})")

        if "_metadata" in enhanced_dict and enhanced_dict["_metadata"].get("unassignedFiles"):
            unassigned_count = enhanced_dict["_metadata"]["unassignedFileCount"]
            print(f"\n{unassigned_count} unassigned files (not under any assembly)")

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


if __name__ == "__main__":
    main()
