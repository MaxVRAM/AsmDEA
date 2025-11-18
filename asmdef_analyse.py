#!/usr/bin/env python3
"""
Combined script to analyse assembly definition dependencies.
This script runs asmdef_dictionary.py followed by asmdef_cyclic_report.py sequentially.
Supports configuration via .env file.
"""

import sys
import subprocess
import argparse
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


def load_env_defaults():
    """Load default values from .env file if present."""
    defaults = {}

    if DOTENV_AVAILABLE:
        # Load .env file from the script's directory
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            print(f"Loaded configuration from {env_path}")

    # Read environment variables
    if os.getenv("ROOT_PATH"):
        defaults["root_path"] = os.getenv("ROOT_PATH")

    if os.getenv("DETAILED"):
        defaults["detailed"] = os.getenv("DETAILED").lower() in ("true", "1", "yes")

    if os.getenv("DEPTH"):
        try:
            defaults["depth"] = int(os.getenv("DEPTH"))
        except ValueError:
            print("Warning: Invalid DEPTH value in .env, using default", file=sys.stderr)

    if os.getenv("OUTPUT_PATH"):
        defaults["output"] = os.getenv("OUTPUT_PATH")

    if os.getenv("DICT_FILE"):
        defaults["dict_file"] = os.getenv("DICT_FILE")

    if os.getenv("ANALYSE_FILES"):
        defaults["analyse_files"] = os.getenv("ANALYSE_FILES").lower() in ("true", "1", "yes")

    if os.getenv("ALLOW_CHILD_NAMESPACES"):
        defaults["allow_child_namespaces"] = os.getenv("ALLOW_CHILD_NAMESPACES").lower() in ("true", "1", "yes")

    return defaults


def main():
    # Load defaults from .env file
    env_defaults = load_env_defaults()

    parser = argparse.ArgumentParser(
        description="Analyse assembly definitions for cyclic dependencies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Configuration can be provided via .env file with variables:\n"
        "  ROOT_PATH, DETAILED, DEPTH, OUTPUT_PATH, DICT_FILE, ANALYSE_FILES, ALLOW_CHILD_NAMESPACES",
    )
    parser.add_argument(
        "root_path",
        nargs="?" if "root_path" in env_defaults else None,
        default=env_defaults.get("root_path"),
        help="Root path to search for .asmdef files",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        default=env_defaults.get("detailed", False),
        help="Show detailed dependency trees for cycles",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=env_defaults.get("depth", 3),
        help="Maximum depth for dependency trees (default: 3)",
    )
    parser.add_argument("--output", "-o", default=env_defaults.get("output"), help="Write cycle report to this file")
    parser.add_argument(
        "--dict-file",
        default=env_defaults.get("dict_file", "./.work/asmdef_dictionary.json"),
        help="Name of the intermediate dictionary file (default: ./.work/asmdef_dictionary.json)",
    )
    parser.add_argument(
        "--analyse-files",
        action="store_true",
        default=env_defaults.get("analyse_files", False),
        help="Analyse and list all .cs files for each assembly",
    )
    parser.add_argument(
        "--file-report",
        action="store_true",
        help="Print a summary report of files per assembly (requires --analyse-files)",
    )
    parser.add_argument(
        "--allow-child-namespaces",
        action="store_true",
        default=env_defaults.get("allow_child_namespaces", True),
        help="Allow child namespaces that extend the root namespace (default: True)",
    )
    parser.add_argument(
        "--strict", action="store_true", help="Disable child namespace allowance for namespace analysis"
    )
    args = parser.parse_args()

    # Validate root_path is provided
    if not args.root_path:
        parser.error("root_path is required (provide as argument or ROOT_PATH in .env)")

    # Print note if dotenv is not available but .env file exists
    if not DOTENV_AVAILABLE:
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            print("Note: .env file detected but python-dotenv not installed.", file=sys.stderr)
            print("Install with: pip install python-dotenv", file=sys.stderr)
            print()

    script_dir = Path(__file__).parent
    dict_script = script_dir / "asmdef_dictionary.py"
    cyclic_script = script_dir / "asmdef_cyclic_report.py"
    file_analyser_script = script_dir / "asmdef_file_analyser.py"

    # Verify scripts exist
    if not dict_script.exists():
        print(f"Error: Script not found: {dict_script}", file=sys.stderr)
        sys.exit(1)

    if not cyclic_script.exists():
        print(f"Error: Script not found: {cyclic_script}", file=sys.stderr)
        sys.exit(1)

    if args.analyse_files and not file_analyser_script.exists():
        print(f"Error: Script not found: {file_analyser_script}", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("STEP 1: Building assembly definition dictionary")
    print("=" * 60)

    # Run asmdef_dictionary.py with output file path
    try:
        subprocess.run(
            [sys.executable, str(dict_script), args.root_path, args.dict_file],
            check=True,
            capture_output=False,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"\nError: Failed to build dictionary (exit code {e.returncode})", file=sys.stderr)
        sys.exit(1)

    # Verify the dictionary file was created
    dict_file_path = Path(args.dict_file)
    if not dict_file_path.exists():
        print(f"\nError: Dictionary file '{args.dict_file}' was not created", file=sys.stderr)
        sys.exit(1)

    # Optional: Analyse .cs files for each assembly
    if args.analyse_files:
        print("\n" + "=" * 60)
        print("STEP 2: Analysing .cs files for each assembly")
        print("=" * 60)

        # Build command for asmdef_file_analyser.py
        file_analyser_cmd = [
            sys.executable,
            str(file_analyser_script),
            "--file",
            args.dict_file,
            "--root",
            args.root_path,
        ]

        if args.file_report:
            file_analyser_cmd.append("--report")

        # Run asmdef_file_analyser.py
        try:
            subprocess.run(file_analyser_cmd, check=True, capture_output=False, text=True)
        except subprocess.CalledProcessError as e:
            print(f"\nError: Failed to analyse files (exit code {e.returncode})", file=sys.stderr)
            sys.exit(1)

        # NEW: Analyse namespaces
        print("\n" + "=" * 60)
        print("STEP 3: Analysing namespaces in C# files")
        print("=" * 60)

        namespace_analyser_script = script_dir / "asmdef_namespace_analyser.py"
        if not namespace_analyser_script.exists():
            print(f"Error: Script not found: {namespace_analyser_script}", file=sys.stderr)
            sys.exit(1)

        namespace_cmd = [
            sys.executable,
            str(namespace_analyser_script),
            "--file",
            args.dict_file,
            "--root",
            args.root_path,
            "--report",  # Always show report for namespace analysis
        ]

        # Add child namespace option
        if args.strict:
            namespace_cmd.append("--strict")
        elif not args.allow_child_namespaces:
            # Explicitly disable if not using default
            namespace_cmd.append("--strict")

        try:
            subprocess.run(namespace_cmd, check=True, capture_output=False, text=True)
        except subprocess.CalledProcessError as e:
            print(f"\nError: Failed to analyse namespaces (exit code {e.returncode})", file=sys.stderr)
            sys.exit(1)

    print("\n" + "=" * 60)
    step_num = 4 if args.analyse_files else 2
    print(f"STEP {step_num}: Analysing cyclic dependencies")
    print("=" * 60)

    # Build command for asmdef_cyclic_report.py
    cyclic_cmd = [sys.executable, str(cyclic_script), "--file", args.dict_file]

    if args.detailed:
        cyclic_cmd.append("--detailed")

    if args.depth != 3:
        cyclic_cmd.extend(["--depth", str(args.depth)])

    if args.output:
        cyclic_cmd.extend(["--output", args.output])
    else:
        # Use default output path
        cyclic_cmd.extend(["--output", "./output/cycle_report.json"])

    # Run asmdef_cyclic_report.py
    try:
        subprocess.run(cyclic_cmd, check=True, capture_output=False, text=True)
    except subprocess.CalledProcessError as e:
        print(f"\nError: Failed to generate cycle report (exit code {e.returncode})", file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Analysis complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
