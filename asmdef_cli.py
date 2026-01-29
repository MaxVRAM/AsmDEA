#!/usr/bin/env python
"""Command-line interface for Unity Assembly Definition analysis.

This script provides a unified CLI for analyzing Unity projects, detecting
circular dependencies, validating namespaces, and mapping C# files to assemblies.

Usage:
    # Run complete analysis pipeline
    python asmdef_cli.py analyze --project-path ./MyUnityProject

    # Run specific analyses
    python asmdef_cli.py detect-cycles --dict-file assemblies.json
    python asmdef_cli.py validate-namespaces --dict-file assemblies.json
    python asmdef_cli.py map-files --dict-file assemblies.json

Environment Variables:
    Configuration can be loaded from .env file. CLI arguments override .env values.
    See .env.example for available options.
"""

import argparse
import sys
from pathlib import Path
from typing import Any

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

import os

from analyzers import CycleAnalyzer, FileAnalyzer, NamespaceAnalyzer
from common import (
    get_logger,
    load_asmdef_dict,
    save_json_report,
    setup_logging,
)
from models import AnalysisConfig
from reporting import (
    CycleReporter,
    FileAnalysisReporter,
    NamespaceReporter,
)

logger = get_logger(__name__)


def get_from_env(key: str, default: Any = None) -> Any:
    """Get value from environment variable with type conversion."""
    value = os.getenv(key)
    if value is None:
        return default

    # Convert string booleans
    if isinstance(default, bool):
        return value.lower() in ("true", "yes", "1", "on")

    # Convert string integers
    if isinstance(default, int):
        try:
            return int(value)
        except ValueError:
            return default

    # Convert string paths
    if isinstance(default, Path):
        return Path(value)

    return value


def build_dictionary_command(args: argparse.Namespace) -> int:
    """Build assembly definition dictionary from Unity project.

    This is typically the first step - it scans the project for .asmdef files
    and creates a JSON database.

    Returns:
        Exit code (0 for success)
    """
    logger.info("=" * 60)
    logger.info("Building Assembly Definition Dictionary")
    logger.info("=" * 60)
    logger.info("Scanning for .asmdef files in: %s", args.project_path)

    # Import the dictionary builder function
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from analysis.dictionary import build_asmdef_dictionary

    # Build dictionary
    asmdef_dict = build_asmdef_dictionary(str(args.project_path))
    if asmdef_dict is None:
        logger.error("Failed to build dictionary")
        return 1

    # Save dictionary
    save_json_report(asmdef_dict, args.dict_file, verbose=args.verbose)

    # Report stats
    assembly_count = len([k for k in asmdef_dict if not k.startswith("_")])
    logger.info("Found %d assemblies", assembly_count)
    logger.info(f"Dictionary saved to {args.dict_file}")

    return 0


def detect_cycles_command(args: argparse.Namespace) -> int:
    """Detect circular dependencies between assemblies.

    Returns:
        Exit code (0 for success, 1 if cycles found)
    """
    logger.info("=" * 60)
    logger.info("Detecting Circular Dependencies")
    logger.info("=" * 60)

    # Load dictionary
    asmdef_dict = load_asmdef_dict(args.dict_file)

    # Analyze
    analyzer = CycleAnalyzer(asmdef_dict)
    report = analyzer.analyze()

    # Report
    reporter = CycleReporter(verbose=args.verbose, depth=args.depth, detailed=args.detailed)
    reporter.print_console_report(report)

    # Save JSON reports
    output_file = args.output_dir / "cycle_report.json"
    reporter.save_json_report(report, output_file)

    summary_file = args.output_dir / "cycle_report_summary.json"
    reporter.save_summary_report(report, summary_file)

    # Return non-zero if cycles found
    return 1 if report.total_cycles > 0 else 0


def validate_namespaces_command(args: argparse.Namespace) -> int:
    """Validate C# file namespaces against assembly root namespaces.

    Returns:
        Exit code (0 for success)
    """
    logger.info("=" * 60)
    logger.info("Validating Namespace Compliance")
    logger.info("=" * 60)

    # Load dictionary
    asmdef_dict = load_asmdef_dict(args.dict_file)

    # Analyze
    analyzer = NamespaceAnalyzer(asmdef_dict, args.project_path, args.allow_child_namespaces)
    results = analyzer.analyze()
    problems = analyzer.get_problems()

    # Report
    reporter = NamespaceReporter(verbose=args.verbose)
    data = {"asmdef_dict": results, "problems": problems}
    reporter.print_console_report(data)

    # Save JSON if there are problems
    if problems:
        output_file = args.output_dir / "namespace_validation.json"
        reporter.save_json_report(data, output_file)

    # Update dictionary
    if args.dict_file:
        save_json_report(results, args.dict_file, verbose=args.verbose)

    return 0


def map_files_command(args: argparse.Namespace) -> int:
    """Map C# files to their owning assemblies.

    Returns:
        Exit code (0 for success)
    """
    logger.info("=" * 60)
    logger.info("Mapping C# Files to Assemblies")
    logger.info("=" * 60)

    # Load or create dictionary
    try:
        asmdef_dict = load_asmdef_dict(args.dict_file)
    except SystemExit:
        logger.info("Dictionary not found, creating new one...")
        # Import the dictionary builder function
        import sys

        sys.path.insert(0, str(Path(__file__).parent))
        from analysis.dictionary import build_asmdef_dictionary

        asmdef_dict = build_asmdef_dictionary(str(args.project_path))
        if asmdef_dict is None:
            logger.error("Failed to build dictionary")
            return 1
        save_json_report(asmdef_dict, args.dict_file, verbose=args.verbose)
        logger.info(f"Dictionary saved to {args.dict_file}")

    # Analyze
    analyzer = FileAnalyzer(asmdef_dict, args.project_path)
    updated_dict = analyzer.analyze()
    stats = analyzer.get_stats()

    # Report
    reporter = FileAnalysisReporter(verbose=args.verbose)
    data = {"asmdef_dict": updated_dict, "stats": stats}
    reporter.print_console_report(data)

    # Save JSON
    output_file = args.output_dir / "file_mapping.json"
    reporter.save_json_report(data, output_file)

    # Update dictionary with file mappings
    save_json_report(updated_dict, args.dict_file, verbose=args.verbose)

    return 0


def analyze_all_command(args: argparse.Namespace) -> int:
    """Run complete analysis pipeline.

    Executes all analysis steps in sequence:
    1. Map files to assemblies (builds dictionary)
    2. Validate namespace compliance
    3. Detect circular dependencies

    Returns:
        Exit code (0 for success, 1 if cycles found)
    """
    logger.info("=" * 70)
    logger.info("COMPLETE UNITY PROJECT ANALYSIS")
    logger.info("=" * 70)
    logger.info("Project: %s", args.project_path)
    logger.info("Output: %s", args.output_dir)
    logger.info("")

    # Step 1: Map files (this also builds initial dictionary)
    logger.info("STEP 1: Mapping C# Files to Assemblies")
    logger.info("-" * 70)
    exit_code = map_files_command(args)
    if exit_code != 0:
        return exit_code

    logger.info("")

    # Step 2: Validate namespaces
    logger.info("STEP 2: Validating Namespace Compliance")
    logger.info("-" * 70)
    exit_code = validate_namespaces_command(args)
    if exit_code != 0:
        return exit_code

    logger.info("")

    # Step 3: Detect cycles
    logger.info("STEP 3: Detecting Circular Dependencies")
    logger.info("-" * 70)
    exit_code = detect_cycles_command(args)

    # Print final summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("ANALYSIS COMPLETE")
    logger.info("=" * 70)
    logger.info("Reports saved to: %s", args.output_dir)
    logger.info("  - file_mapping.json")
    logger.info("  - namespace_analysis.json")
    logger.info("  - cycle_report.json")
    logger.info("  - %s", args.dict_file.name)

    return exit_code


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        description="Unity Assembly Definition Analysis Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run complete analysis on Unity project
  python asmdef_cli.py analyze --project-path D:/Unity/MyProject/Assets

  # Just detect cycles in existing dictionary
  python asmdef_cli.py detect-cycles --dict-file assemblies.json

  # Validate namespaces with detailed output
  python asmdef_cli.py validate-namespaces --project-path ./Assets --verbose

  # Map files and allow child namespaces
  python asmdef_cli.py map-files --project-path ./Assets --allow-child-namespaces

Environment Variables (.env file):
  ROOT_PATH                 - Default project path
  DICT_FILE                 - Dictionary file path
  OUTPUT_PATH               - Output directory for reports
  DEPTH                     - Max tree depth for cycle visualization
  DETAILED                  - Show detailed cycle trees
  ALLOW_CHILD_NAMESPACES    - Allow child namespace matching

CLI arguments override environment variables.
        """,
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=get_from_env("LOG_LEVEL", "INFO"),
        help="Logging level (default: INFO)",
    )

    parser.add_argument("--log-file", type=Path, help="Optional log file path")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Common arguments for all subcommands
    def add_common_args(subparser: argparse.ArgumentParser) -> None:
        """Add arguments common to multiple subcommands."""
        subparser.add_argument(
            "--dict-file",
            type=Path,
            default=get_from_env("DICT_FILE", Path("./reports/asmdef_dictionary.json")),
            help="Path to assembly dictionary JSON file (default: ./reports/asmdef_dictionary.json)",
        )
        subparser.add_argument(
            "--output-dir",
            type=Path,
            default=get_from_env("OUTPUT_PATH", Path("./reports")),
            help="Output directory for reports (default: ./reports)",
        )
        subparser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    # analyze (all) command
    analyze_parser = subparsers.add_parser(
        "analyze",
        aliases=["all"],
        help="Run complete analysis pipeline (recommended)",
        description="Analyze Unity project: map files, validate namespaces, detect cycles",
    )
    analyze_parser.add_argument(
        "--project-path",
        type=Path,
        required=False,
        default=get_from_env("ROOT_PATH"),
        help="Path to Unity project (Assets folder)",
    )
    add_common_args(analyze_parser)
    analyze_parser.add_argument(
        "--depth",
        type=int,
        default=get_from_env("DEPTH", 3),
        help="Maximum tree depth for cycle visualization (default: 3)",
    )
    analyze_parser.add_argument(
        "--detailed",
        action="store_true",
        default=get_from_env("DETAILED", False),
        help="Show detailed dependency trees in cycle reports",
    )
    analyze_parser.add_argument(
        "--allow-child-namespaces",
        action="store_true",
        default=get_from_env("ALLOW_CHILD_NAMESPACES", True),
        help="Allow child namespaces (e.g., Foo.Bar under Foo)",
    )
    analyze_parser.set_defaults(func=analyze_all_command)

    # build-dict command
    build_parser = subparsers.add_parser(
        "build-dict",
        help="Build assembly definition dictionary",
        description="Scan Unity project and create assembly dictionary JSON",
    )
    build_parser.add_argument(
        "--project-path",
        type=Path,
        required=False,
        default=get_from_env("ROOT_PATH"),
        help="Path to Unity project (Assets folder)",
    )
    add_common_args(build_parser)
    build_parser.set_defaults(func=build_dictionary_command)

    # detect-cycles command
    cycles_parser = subparsers.add_parser(
        "detect-cycles",
        help="Detect circular dependencies",
        description="Find circular dependencies between assemblies",
    )
    add_common_args(cycles_parser)
    cycles_parser.add_argument(
        "--depth",
        type=int,
        default=get_from_env("DEPTH", 3),
        help="Maximum tree depth for visualization (default: 3)",
    )
    cycles_parser.add_argument(
        "--detailed",
        action="store_true",
        default=get_from_env("DETAILED", False),
        help="Show detailed dependency trees",
    )
    cycles_parser.set_defaults(func=detect_cycles_command)

    # validate-namespaces command
    ns_parser = subparsers.add_parser(
        "validate-namespaces",
        help="Validate namespace compliance",
        description="Check if C# file namespaces match assembly root namespaces",
    )
    ns_parser.add_argument(
        "--project-path",
        type=Path,
        required=False,
        default=get_from_env("ROOT_PATH"),
        help="Path to Unity project (Assets folder)",
    )
    add_common_args(ns_parser)
    ns_parser.add_argument(
        "--allow-child-namespaces",
        action="store_true",
        default=get_from_env("ALLOW_CHILD_NAMESPACES", True),
        help="Allow child namespaces (default: True)",
    )
    ns_parser.set_defaults(func=validate_namespaces_command)

    # map-files command
    files_parser = subparsers.add_parser(
        "map-files",
        help="Map C# files to assemblies",
        description="Assign C# files to their owning assemblies",
    )
    files_parser.add_argument(
        "--project-path",
        type=Path,
        required=False,
        default=get_from_env("ROOT_PATH"),
        help="Path to Unity project (Assets folder)",
    )
    add_common_args(files_parser)
    files_parser.set_defaults(func=map_files_command)

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Setup logging
    setup_logging(level=args.log_level, log_file=args.log_file)

    # Check if command was provided
    if not args.command:
        parser.print_help()
        return 1

    # Validate project path if required
    if hasattr(args, "project_path") and args.project_path:
        args.project_path = Path(args.project_path).resolve()
        if not args.project_path.exists():
            logger.error("Project path does not exist: %s", args.project_path)
            return 1
        if not args.project_path.is_dir():
            logger.error("Project path is not a directory: %s", args.project_path)
            return 1
    elif hasattr(args, "project_path") and not args.project_path:
        logger.error("Project path is required. Provide --project-path or set ROOT_PATH in .env")
        return 1

    # Create output directory if needed
    if hasattr(args, "output_dir"):
        args.output_dir = Path(args.output_dir).resolve()
        args.output_dir.mkdir(parents=True, exist_ok=True)

    # Run command
    try:
        return args.func(args)
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        return 130
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
