#!/usr/bin/env python3
"""Build a dictionary of Unity Assembly Definition files keyed by GUID."""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional


def extract_guid_from_meta(meta_path: Path) -> Optional[str]:
    """Extract GUID from .asmdef.meta file without external dependencies.

    Args:
        meta_path: Path to the .meta file

    Returns:
        GUID string prefixed with "GUID:" or None if extraction fails
    """
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("guid:"):
                    # Extract guid value after 'guid:'
                    guid = line.split(":", 1)[1].strip()
                    guid = "GUID:" + guid
                    return guid
        return None
    except Exception as e:
        print(f"Warning: Failed to read meta file '{meta_path}': {e}", file=sys.stderr)
        return None


def load_asmdef_json(asmdef_path: Path) -> Optional[Dict[str, Any]]:
    """Load and parse .asmdef JSON file.

    Args:
        asmdef_path: Path to the .asmdef file

    Returns:
        Dictionary with assembly definition data or None if loading fails
    """
    try:
        with open(asmdef_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Warning: Invalid JSON in '{asmdef_path}': {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Warning: Failed to read asmdef file '{asmdef_path}': {e}", file=sys.stderr)
        return None


def build_asmdef_dictionary(root_path: str) -> Optional[Dict[str, Dict[str, Any]]]:
    """Build dictionary of assembly definitions keyed by GUID.

    Args:
        root_path: Root directory to search for .asmdef files

    Returns:
        Dictionary mapping GUIDs to assembly definition data, or None on error
    """
    root = Path(root_path).resolve()

    if not root.exists():
        print(f"Error: Root path '{root_path}' does not exist.", file=sys.stderr)
        return None

    if not root.is_dir():
        print(f"Error: Root path '{root_path}' is not a directory.", file=sys.stderr)
        return None

    asmdef_dict = {}
    asmdef_files = list(root.rglob("*.asmdef"))

    print(f"Found {len(asmdef_files)} .asmdef file(s) under '{root_path}'")

    for asmdef_path in asmdef_files:
        # Load assembly definition JSON
        asmdef_data = load_asmdef_json(asmdef_path)
        if asmdef_data is None:
            continue

        # Find corresponding .meta file
        meta_path = Path(str(asmdef_path) + ".meta")
        if not meta_path.exists():
            print(f"Warning: Missing .meta file for '{asmdef_path}'", file=sys.stderr)
            continue

        # Extract GUID from meta file
        guid = extract_guid_from_meta(meta_path)
        if guid is None:
            print(f"Warning: Could not extract GUID from '{meta_path}'", file=sys.stderr)
            continue

        # Calculate relative path from root to the folder containing the asmdef file
        asmdef_folder = asmdef_path.parent
        try:
            relative_path = asmdef_folder.relative_to(root)
            asmdef_data["relativePath"] = str(relative_path).replace("\\", "/")
        except ValueError:
            # If relative_to fails, use the absolute path
            asmdef_data["relativePath"] = str(asmdef_folder)

        # Add to dictionary
        asmdef_dict[guid] = asmdef_data
        # print(f"Added: {asmdef_data.get('name', 'Unknown')} (GUID: {guid})")

    return asmdef_dict


def main() -> None:
    """Main entry point for dictionary builder script."""
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python asmdef_dictionary.py <root_path> [output_file]", file=sys.stderr)
        sys.exit(1)

    root_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) == 3 else "asmdef_dictionary.json"

    # Build the dictionary
    asmdef_dict = build_asmdef_dictionary(root_path)

    if asmdef_dict is None:
        sys.exit(1)

    # Create output directory if it doesn't exist
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Output to JSON file
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(asmdef_dict, f, indent=2, ensure_ascii=False)
        print(f"\nSuccessfully wrote {len(asmdef_dict)} entries to '{output_file}'")
    except Exception as e:
        print(f"Error: Failed to write output file '{output_file}': {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
