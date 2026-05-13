#!/usr/bin/env python3
"""Unity Assembly Definition Analysis CLI.

Unified command-line interface for asmdef analysis operations.
Utilizes refactored analyzers and reporters from the project.

Commands:
    analyze (all)       - Run complete analysis pipeline
    build-dict          - Build assembly dictionary only
    detect-cycles       - Detect circular dependencies only
    map-files           - Map C# files to assemblies only
    validate-namespaces - Validate namespace compliance only

Usage:
    python asmdea.py analyze --project-path D:/Unity/MyProject/Assets
    asmdea detect-cycles --dict-file ./reports/asmdef_dictionary.json
    asmdea --help
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# Optional: Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from analysers import CycleAnalyser, FileAnalyser, NamespaceAnalyser
from common import (
    FilepathType,
    apply_filters,
    configure_console,
    get_console,
    get_logger,
    load_asmdef_dict,
    print_analysis_complete,
    print_analysis_header,
    print_section_complete,
    print_section_header,
    save_json_report,
    setup_logging,
)
from common.backup import BackupManager
from common.dictionary import build_asmdef_dictionary
from enforcement import DependencySorter, SortingStrategy
from reporting import CycleReporter, EnforcementReporter, FileAnalysisReporter, NamespaceReporter


def get_env_or_default(key: str, default: str) -> str:
    """Get environment variable or return default."""
    return os.environ.get(key, default)


def get_env_bool(key: str, default: bool) -> bool:
    """Get environment variable as boolean."""
    value = os.environ.get(key)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


def get_env_list(key: str) -> list[str]:
    """Parse a comma-separated env variable into a list of stripped strings."""
    value = os.environ.get(key, "")
    return [s.strip() for s in value.split(",") if s.strip()]


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with all commands."""
    parser = argparse.ArgumentParser(
        prog="asmdea",
        description="AsmDEA - Assembly Dependency Enforcement Agency",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  asmdea analyze --project-path D:/Unity/MyProject/Assets
  asmdea detect-cycles --dict-file ./reports/asmdef_dictionary.json
  asmdea validate-namespaces --project-path ./Assets

Environment Variables (from .env file):
  ROOT_PATH              - Default project path
  OUTPUT_PATH            - Default output directory (default: ./reports)
  DICT_FILE              - Default dictionary file path
  ALLOW_CHILD_NAMESPACES - Allow child namespaces (true/false, default: true)
  SHOW_UNMATCHED_PATHS   - Include unmatchedPaths in namespace_report.json (true/false, default: true)
  FILEPATH_TYPE          - File path format in reports: absolute|relative (default: relative)
    OPEN_DASHBOARD         - Open dashboard after analyze completes (true/false, default: true)
  DETAILED               - Show detailed dependency trees (true/false, default: false)
  DEPTH                  - Max depth for dependency tree visualization (default: 2)
  FILTER_ROOT            - Comma-separated top-level namespace segments to exclude (e.g. Unity,UnityEngine)
  FILTER_ANY             - Comma-separated namespace segments to exclude at any depth (e.g. Editor,Tests)
  FILTER_PATH            - Comma-separated relative path prefixes to exclude entirely (e.g. Library/PackageCache)
  LOG_LEVEL              - Logging level (DEBUG/INFO/WARNING/ERROR)
        """,
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable coloured output (plain text mode)",
    )
    parser.add_argument(
        "--log-level",
        default=get_env_or_default("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Common arguments for commands that need project path
    project_args = argparse.ArgumentParser(add_help=False)
    project_args.add_argument(
        "--project-path",
        "-p",
        type=Path,
        default=Path(get_env_or_default("ROOT_PATH", ".")),
        help="Unity project Assets path",
    )
    project_args.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path(get_env_or_default("OUTPUT_PATH", "./reports")),
        help="Output directory for reports",
    )
    project_args.add_argument(
        "--dict-file",
        "-d",
        type=Path,
        default=Path(get_env_or_default("DICT_FILE", "./reports/asmdef_dictionary.json")),
        help="Dictionary file path",
    )
    project_args.add_argument(
        "--filepath-type",
        choices=["absolute", "relative"],
        default=get_env_or_default("FILEPATH_TYPE", "relative"),
        help="File path format in reports: 'absolute' or 'relative' to the project path (default: relative)",
    )
    project_args.add_argument(
        "--filter-root",
        nargs="*",
        default=get_env_list("FILTER_ROOT"),
        metavar="NS",
        help="Exclude assemblies whose top-level namespace segment matches (e.g. Unity)",
    )
    project_args.add_argument(
        "--filter-any",
        nargs="*",
        default=get_env_list("FILTER_ANY"),
        metavar="NS",
        help="Exclude assemblies where any namespace segment matches (e.g. Editor)",
    )
    project_args.add_argument(
        "--filter-path",
        nargs="*",
        default=get_env_list("FILTER_PATH"),
        metavar="PATH",
        help="Exclude assemblies whose path contains any of these segments, matched anywhere in the path (e.g. Library/PackageCache)",
    )

    # analyze command (full pipeline)
    analyze = subparsers.add_parser(
        "analyze",
        aliases=["all"],
        parents=[project_args],
        help="Run complete analysis pipeline",
    )
    analyze.add_argument(
        "--allow-child-namespaces",
        action="store_true",
        default=get_env_bool("ALLOW_CHILD_NAMESPACES", True),
        help="Allow child namespaces (default: True)",
    )
    analyze.add_argument(
        "--no-child-namespaces",
        dest="allow_child_namespaces",
        action="store_false",
        help="Require exact namespace matches",
    )
    analyze.add_argument(
        "--show-unmatched-paths",
        action="store_true",
        default=get_env_bool("SHOW_UNMATCHED_PATHS", True),
        help="Include unmatched file paths in namespace_report.json (default: True)",
    )
    analyze.add_argument(
        "--no-unmatched-paths",
        dest="show_unmatched_paths",
        action="store_false",
        help="Omit unmatched file paths from namespace_report.json",
    )
    analyze.add_argument(
        "--detailed",
        action="store_true",
        default=get_env_bool("DETAILED", False),
        help="Show detailed dependency trees",
    )
    analyze.add_argument(
        "--depth",
        type=int,
        default=int(get_env_or_default("DEPTH", "2")),
        help="Maximum depth for dependency tree visualization (default: 2)",
    )
    analyze.add_argument(
        "--open-dashboard",
        action="store_true",
        default=get_env_bool("OPEN_DASHBOARD", True),
        help="Open dashboard frontend when analysis completes (default: True)",
    )
    analyze.add_argument(
        "--no-open-dashboard",
        dest="open_dashboard",
        action="store_false",
        help="Do not open dashboard frontend when analysis completes",
    )

    # build-dict command
    subparsers.add_parser(
        "build-dict",
        parents=[project_args],
        help="Build assembly dictionary from project",
    )

    # detect-cycles command
    cycles = subparsers.add_parser(
        "detect-cycles",
        parents=[project_args],
        help="Detect circular dependencies",
    )
    cycles.add_argument(
        "--detailed",
        action="store_true",
        default=get_env_bool("DETAILED", False),
        help="Show detailed dependency trees",
    )
    cycles.add_argument(
        "--depth",
        type=int,
        default=int(get_env_or_default("DEPTH", "2")),
        help="Maximum depth for dependency tree visualization (default: 2)",
    )

    # map-files command
    subparsers.add_parser(
        "map-files",
        parents=[project_args],
        help="Map C# files to assemblies",
    )

    # validate-namespaces command
    ns = subparsers.add_parser(
        "validate-namespaces",
        parents=[project_args],
        help="Validate namespace compliance",
    )
    ns.add_argument(
        "--allow-child-namespaces",
        action="store_true",
        default=get_env_bool("ALLOW_CHILD_NAMESPACES", True),
        help="Allow child namespaces (default: True)",
    )
    ns.add_argument(
        "--no-child-namespaces",
        dest="allow_child_namespaces",
        action="store_false",
        help="Require exact namespace matches",
    )
    ns.add_argument(
        "--show-unmatched-paths",
        action="store_true",
        default=get_env_bool("SHOW_UNMATCHED_PATHS", True),
        help="Include unmatched file paths in namespace_report.json (default: True)",
    )
    ns.add_argument(
        "--no-unmatched-paths",
        dest="show_unmatched_paths",
        action="store_false",
        help="Omit unmatched file paths from namespace_report.json",
    )

    # sort-deps command (enforcement)
    sort_deps = subparsers.add_parser(
        "sort-deps",
        parents=[project_args],
        help="Sort assembly dependencies using configurable strategies",
    )
    sort_deps.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default is dry-run/preview only)",
    )
    sort_deps.add_argument(
        "--target",
        "-t",
        type=str,
        help="Target a specific assembly by name",
    )
    sort_deps.add_argument(
        "--filter",
        "-f",
        type=str,
        help="Filter assemblies by glob pattern (e.g., '*.Tests')",
    )
    sort_deps.add_argument(
        "--all",
        action="store_true",
        dest="all_assemblies",
        help="Sort all assemblies in the project",
    )
    sort_deps.add_argument(
        "--strategy",
        "-s",
        choices=["alpha-asc", "alpha-desc", "namespace", "unity-first", "unity-last"],
        default="alpha-asc",
        help="Sorting strategy (default: alpha-asc)",
    )
    sort_deps.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed before/after diffs",
    )
    sort_deps.add_argument(
        "--backup-dir",
        type=Path,
        default=Path(".asmdea_backups"),
        help="Directory for backup files (default: .asmdea_backups)",
    )

    # restore-backup command
    restore = subparsers.add_parser(
        "restore-backup",
        help="Restore files from a previous backup",
    )
    restore.add_argument(
        "--backup-dir",
        type=Path,
        default=Path(".asmdea_backups"),
        help="Directory containing backups",
    )
    restore.add_argument(
        "--backup-id",
        type=str,
        help="Specific backup ID to restore (default: most recent)",
    )
    restore.add_argument(
        "--list",
        action="store_true",
        dest="list_backups",
        help="List available backups instead of restoring",
    )

    return parser


def validate_project_path(project_path: Path, logger: Any) -> bool:
    """Validate that project path exists and is a directory."""
    console = get_console()
    if not project_path.exists():
        console.print(f"[error]Project path does not exist:[/] [path]{project_path}[/]")
        return False
    if not project_path.is_dir():
        console.print(f"[error]Project path is not a directory:[/] [path]{project_path}[/]")
        return False
    return True


def open_dashboard_frontend(reports_dir: Path) -> None:
    """Start the dashboard dev server in the foreground."""
    console = get_console()
    dashboard_dir = Path(__file__).parent / "dashboard"
    dashboard_url = "http://localhost:5173"

    if not dashboard_dir.exists():
        console.print(f"[warning]Dashboard directory not found:[/] [path]{dashboard_dir}[/]")
        return

    env = os.environ.copy()
    env["ASMDEA_REPORTS_DIR"] = str(reports_dir.resolve())
    console.print(f"[info]Starting dashboard server at [path]{dashboard_url}[/]. Press Ctrl+C to stop.[/]")

    try:
        subprocess.run(
            ["pnpm.cmd", "dev"],
            cwd=dashboard_dir,
            env=env,
            check=False,
        )
    except FileNotFoundError:
        console.print("[warning]Could not start dashboard server: 'pnpm.cmd' was not found on PATH.[/]")
        return
    except KeyboardInterrupt:
        print_section_complete("Dashboard server stopped")
        return
    except Exception as exc:
        console.print(f"[warning]Could not start dashboard server:[/] {exc}")
        return


def cmd_build_dict(args: argparse.Namespace, logger: Any) -> int:
    """Build assembly dictionary from project."""
    if not validate_project_path(args.project_path, logger):
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)

    console = get_console()
    console.print(f"Scanning for assemblies in [path]{args.project_path}[/]...")
    asmdef_dict = build_asmdef_dictionary(str(args.project_path))

    if not asmdef_dict:
        console.print("[error]Failed to build dictionary - no assemblies found[/]")
        return 1

    asmdef_dict = apply_filters(
        asmdef_dict,
        filter_root=getattr(args, "filter_root", None) or [],
        filter_any=getattr(args, "filter_any", None) or [],
        filter_path=getattr(args, "filter_path", None) or [],
    )

    save_json_report(asmdef_dict, args.dict_file)
    print_section_complete(f"Dictionary saved to [path]{args.dict_file}[/] ([count]{len(asmdef_dict)}[/] assemblies)")
    return 0


def cmd_detect_cycles(args: argparse.Namespace, logger: Any) -> int:
    """Detect circular dependencies."""
    console = get_console()
    if not args.dict_file.exists():
        console.print(f"[error]Dictionary file not found:[/] [path]{args.dict_file}[/]")
        console.print("[muted]Run 'build-dict' command first to create the dictionary[/]")
        return 2

    asmdef_dict = load_asmdef_dict(args.dict_file)
    asmdef_dict = apply_filters(
        asmdef_dict,
        filter_root=getattr(args, "filter_root", None) or [],
        filter_any=getattr(args, "filter_any", None) or [],
        filter_path=getattr(args, "filter_path", None) or [],
    )

    analyser = CycleAnalyser(asmdef_dict)
    report = analyser.analyse(max_depth=args.depth)

    reporter = CycleReporter(
        verbose=args.verbose,
        detailed=args.detailed,
        depth=args.depth,
        filepath_type=FilepathType.parse(getattr(args, "filepath_type", None)),
        root_path=getattr(args, "project_path", None),
    )
    reporter.print_console_report(report)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    reporter.save_json_report(report, args.output_dir / "cycle_report.json")

    return 1 if report.total_cycles > 0 else 0


def cmd_map_files(args: argparse.Namespace, logger: Any) -> int:
    """Map C# files to assemblies."""
    if not validate_project_path(args.project_path, logger):
        return 2

    console = get_console()
    if not args.dict_file.exists():
        console.print(f"[error]Dictionary file not found:[/] [path]{args.dict_file}[/]")
        console.print("[muted]Run 'build-dict' command first to create the dictionary[/]")
        return 2

    asmdef_dict = load_asmdef_dict(args.dict_file)
    asmdef_dict = apply_filters(
        asmdef_dict,
        filter_root=getattr(args, "filter_root", None) or [],
        filter_any=getattr(args, "filter_any", None) or [],
        filter_path=getattr(args, "filter_path", None) or [],
    )

    analyser = FileAnalyser(asmdef_dict, args.project_path, filter_paths=getattr(args, "filter_path", None) or [])
    result = analyser.analyse()

    reporter = FileAnalysisReporter(
        verbose=args.verbose,
        filepath_type=FilepathType.parse(getattr(args, "filepath_type", None)),
        root_path=args.project_path,
    )
    reporter.print_console_report(result)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    reporter.save_json_report(result, args.output_dir / "file_report.json")

    # Save updated dictionary with file mappings
    save_json_report(result["asmdef_dict"], args.dict_file)
    print_section_complete(f"Updated dictionary saved to [path]{args.dict_file}[/]")

    return 0


def cmd_validate_namespaces(args: argparse.Namespace, logger: Any) -> int:
    """Validate namespace compliance."""
    if not validate_project_path(args.project_path, logger):
        return 2

    console = get_console()
    if not args.dict_file.exists():
        console.print(f"[error]Dictionary file not found:[/] [path]{args.dict_file}[/]")
        console.print("[muted]Run 'build-dict' and 'map-files' commands first[/]")
        return 2

    asmdef_dict = load_asmdef_dict(args.dict_file)
    asmdef_dict = apply_filters(
        asmdef_dict,
        filter_root=getattr(args, "filter_root", None) or [],
        filter_any=getattr(args, "filter_any", None) or [],
        filter_path=getattr(args, "filter_path", None) or [],
    )

    analyser = NamespaceAnalyser(asmdef_dict, args.project_path, args.allow_child_namespaces)
    report = analyser.analyse()

    reporter = NamespaceReporter(
        verbose=args.verbose,
        allow_child_namespaces=args.allow_child_namespaces,
        show_unmatched_paths=args.show_unmatched_paths,
        filepath_type=FilepathType.parse(getattr(args, "filepath_type", None)),
        root_path=args.project_path,
    )
    reporter.print_console_report(report)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    reporter.save_json_report(report, args.output_dir / "namespace_report.json")

    # Return 1 if there are issues
    has_issues = report.total_mismatched > 0 or report.total_no_namespace > 0
    return 1 if has_issues else 0


def cmd_sort_deps(args: argparse.Namespace, logger: Any) -> int:
    """Sort assembly dependencies."""
    console = get_console()

    if not args.dict_file.exists():
        console.print(f"[error]Dictionary file not found:[/] [path]{args.dict_file}[/]")
        console.print("[muted]Run 'build-dict' command first to create the dictionary[/]")
        return 2

    # Validate scope options
    if not (args.target or args.filter or args.all_assemblies):
        console.print("[error]No scope specified.[/]")
        console.print("[muted]Use --target, --filter, or --all to specify assemblies to sort[/]")
        return 2

    asmdef_dict = load_asmdef_dict(args.dict_file)

    # Map strategy string to enum
    strategy_map = {
        "alpha-asc": SortingStrategy.ALPHABETICAL_ASC,
        "alpha-desc": SortingStrategy.ALPHABETICAL_DESC,
        "namespace": SortingStrategy.NAMESPACE_GROUPED,
        "unity-first": SortingStrategy.UNITY_FIRST,
        "unity-last": SortingStrategy.UNITY_LAST,
    }
    strategy = strategy_map[args.strategy]

    # Create sorter and execute
    sorter = DependencySorter(
        asmdef_dict,
        strategy=strategy,
        backup_dir=args.backup_dir,
    )

    result = sorter.sort(
        apply=args.apply,
        target=args.target,
        filter_pattern=args.filter,
        all_assemblies=args.all_assemblies,
    )

    # Report results
    reporter = EnforcementReporter(
        verbose=args.verbose,
        detailed=getattr(args, "detailed", False),
    )
    reporter.print_console_report(result)

    # Save report if output dir specified
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        reporter.save_json_report(result, args.output_dir / "sorting_report.json")

    return 0 if result.success else 1


def cmd_restore_backup(args: argparse.Namespace, logger: Any) -> int:
    """Restore files from a backup."""
    console = get_console()
    manager = BackupManager(args.backup_dir)

    # List backups mode
    if args.list_backups:
        backups = manager.list_backups()
        if not backups:
            console.print("[muted]No backups found.[/]")
            return 0

        from rich.table import Table

        table = Table(title="Available Backups")
        table.add_column("Backup ID", style="cyan")
        table.add_column("Created", style="green")
        table.add_column("Operation")
        table.add_column("Files", justify="right")

        for backup in backups:
            table.add_row(
                backup.backup_id,
                backup.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                backup.operation,
                str(backup.file_count),
            )

        console.print(table)
        return 0

    # Restore mode
    if args.backup_id:
        backup = manager.get_backup(args.backup_id)
        if not backup:
            console.print(f"[error]Backup not found:[/] {args.backup_id}")
            return 1
        backup_path = backup.path
    else:
        # Use most recent backup
        backups = manager.list_backups()
        if not backups:
            console.print("[error]No backups found.[/]")
            return 1
        backup_path = backups[0].path
        console.print(f"[muted]Restoring most recent backup:[/] {backups[0].backup_id}")

    try:
        restored = manager.restore_backup(backup_path)
        console.print(f"[green]✓[/] Restored {len(restored)} files")
        for path in restored:
            console.print(f"  [path]{path}[/]")
        return 0
    except Exception as e:
        console.print(f"[error]Restore failed:[/] {e}")
        return 1


def cmd_analyze(args: argparse.Namespace, logger: Any) -> int:
    """Run complete analysis pipeline."""
    exit_code = 0

    # Print main header
    print_analysis_header()

    # Step 1: Build dictionary
    print_section_header("Building Assembly Dictionary", step=1, total_steps=4)
    result = cmd_build_dict(args, logger)
    if result != 0:
        return result

    # Step 2: Map files
    print_section_header("Mapping C# Files to Assemblies", step=2, total_steps=4)
    cmd_map_files(args, logger)

    # Step 3: Validate namespaces
    print_section_header("Validating Namespace Compliance", step=3, total_steps=4)
    if cmd_validate_namespaces(args, logger) != 0:
        exit_code = 1

    # Step 4: Detect cycles
    print_section_header("Detecting Circular Dependencies", step=4, total_steps=4)
    if cmd_detect_cycles(args, logger) != 0:
        exit_code = 1

    # Print completion summary
    print_analysis_complete(str(args.output_dir), success=(exit_code == 0))

    if args.open_dashboard:
        open_dashboard_frontend(args.output_dir)

    return exit_code


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 2

    # Configure Rich console before any output
    configure_console(plain=args.no_color)

    setup_logging(level=args.log_level)
    logger = get_logger(__name__)

    commands = {
        "analyze": cmd_analyze,
        "all": cmd_analyze,
        "build-dict": cmd_build_dict,
        "detect-cycles": cmd_detect_cycles,
        "map-files": cmd_map_files,
        "validate-namespaces": cmd_validate_namespaces,
        "sort-deps": cmd_sort_deps,
        "restore-backup": cmd_restore_backup,
    }

    # Console output the command being executed
    console = get_console()
    console.print(f"[info]Executing command:[/] [command]{args.command}[/]")

    try:
        return commands[args.command](args, logger)
    except KeyboardInterrupt:
        console = get_console()
        console.print("\n[warning]Operation cancelled[/]")
        return 130
    except Exception as e:
        console = get_console()
        console.print(f"[error]Error:[/] {e}")
        if args.verbose:
            console.print_exception()
        return 1


if __name__ == "__main__":
    sys.exit(main())
