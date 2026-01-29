# ScriptFlattener - Project Overview

**Unity Assembly Definition Analysis Toolkit**

Last Updated: January 29, 2026

---

## Project Purpose

Analyze Unity projects to detect circular dependencies between Assembly Definitions (`.asmdef`), validate namespace compliance, and map C# files to their owning assemblies. This toolkit helps maintain clean architecture in large Unity codebases.

---

## Project Structure

```
ScriptFlattener/
├── asmdef_cli.py              # CLI entry point (IN PROGRESS)
├── analysis/                   # Legacy analysis scripts (will be deprecated)
│   ├── cycles.py              # Standalone cycle detection
│   ├── dictionary.py          # Asmdef dictionary builder
│   ├── files.py               # File ownership analysis
│   └── namespaces.py          # Namespace validation
├── analyzers/                  # Refactored analyzer classes
│   ├── cycle_analyzer.py      # Circular dependency detection
│   ├── file_analyzer.py       # C# file to assembly mapping
│   └── namespace_analyzer.py  # Namespace compliance checking
├── common/                     # Shared utilities
│   ├── asmdef_dict.py         # Dictionary manipulation helpers
│   ├── constants.py           # Project-wide constants
│   ├── file_io.py             # JSON load/save utilities
│   └── logging_config.py      # Centralized logging setup
├── models/                     # Data models
│   ├── asmdef_entry.py        # Assembly definition data class
│   ├── config.py              # Configuration dataclass
│   └── report_models.py       # Report data structures
├── reporting/                  # Output formatters
│   ├── base.py                # Abstract reporter base class
│   ├── cycle_reporter.py      # Cycle analysis output
│   ├── file_reporter.py       # File mapping output
│   └── namespace_reporter.py  # Namespace validation output
├── tests/                      # Test suite (50 tests, 77% coverage)
├── utilities/                  # Additional tools
│   ├── code_line_counter.py   # Code metrics calculator
│   └── script_flattener.py    # Legacy utility
└── reports/                    # Generated analysis reports (JSON)
```

---

## Module Responsibilities

### Core Analyzers (`analyzers/`)

#### `cycle_analyzer.py`

**Purpose:** Detect circular dependencies between assemblies  
**Key Class:** `CycleAnalyzer`  
**Constructor:** `CycleAnalyzer(asmdef_dict: dict)`  
**Methods:**
- `analyze() -> CycleReport` - Detect all cycles in dependency graph
- `_build_dependency_graph()` - Create graph from assembly references
- `_detect_cycles_dfs()` - Depth-first search for cycles
- `_build_dependency_tree()` - Generate visualization tree

**Input:** Assembly dictionary (GUID → assembly data)  
**Output:** `CycleReport` with cycles, severity, and dependency trees

#### `file_analyzer.py`

**Purpose:** Map C# files to their owning assemblies  
**Key Class:** `FileAnalyzer`  
**Constructor:** `FileAnalyzer(asmdef_dict: dict, root_path: Path)`  
**Methods:**
- `analyze() -> dict` - Scan project and assign files to assemblies
- `get_stats() -> dict` - Return file mapping statistics
- `_build_path_to_guid_mapping()` - Map directories to assembly GUIDs
- `_find_owning_assembly()` - Determine which assembly owns a file

**Input:** Unity project root directory  
**Output:** Updated dictionary with `csFiles` arrays per assembly

#### `namespace_analyzer.py`

**Purpose:** Validate C# file namespaces match assembly root namespaces  
**Key Class:** `NamespaceAnalyzer`  
**Constructor:** `NamespaceAnalyzer(asmdef_dict: dict, root_path: Path, allow_child_namespaces: bool)`  
**Methods:**
- `analyze() -> dict` - Check namespace compliance for all files
- `get_problems() -> dict` - Return assemblies with namespace violations
- `extract_namespace_from_file()` - Parse namespace declarations from C#
- `_validate_namespace()` - Check if namespace matches assembly root

**Input:** Assembly dictionary with file mappings  
**Output:** Updated dictionary with namespace analysis, list of violations

---

### Reporting Layer (`reporting/`)

#### `base.py`

**Purpose:** Abstract base class for consistent reporting interface  
**Key Class:** `BaseReporter`  
**Abstract Methods:**
- `print_console_report(data)` - Format output for terminal
- `save_json_report(data, path)` - Serialize results to JSON

#### `cycle_reporter.py`

**Purpose:** Format cycle detection results for console and JSON  
**Key Class:** `CycleReporter`  
**Features:**
- Color-coded severity levels (🔴 critical, 🟡 moderate, 🟢 simple)
- Configurable tree depth visualization
- Summary statistics (total cycles, affected assemblies)
- Detailed dependency trees (optional)

#### `file_reporter.py`

**Purpose:** Format file mapping results  
**Key Class:** `FileAnalysisReporter`  
**Features:**
- Statistics (total files, assigned, orphaned)
- Per-assembly file counts
- Orphaned file listings

#### `namespace_reporter.py`

**Purpose:** Format namespace validation results  
**Key Class:** `NamespaceReporter`  
**Features:**
- Mismatched namespace listings
- Files without namespace declarations
- Child namespace handling (configurable)

---

### Common Utilities (`common/`)

#### `file_io.py`

**Functions:**
- `load_asmdef_dict(path) -> dict` - Load assembly dictionary from JSON
- `save_json_report(data, path, verbose)` - Save analysis results with pretty formatting

#### `asmdef_dict.py`

**Functions:**
- `filter_assemblies(dict) -> dict` - Remove metadata entries, get only assembly data
- `get_metadata(dict) -> dict` - Extract `_metadata` section
- `set_metadata(dict, key, value)` - Update metadata values

#### `logging_config.py`

**Functions:**
- `setup_logging(level, log_file, file_level)` - Configure logging system
- `get_logger(name) -> Logger` - Get module-specific logger
- `reset_logging()` - Clear handlers (for testing)

#### `constants.py`

**Definitions:**
- `METADATA_KEY = "_metadata"` - Dictionary metadata key
- Standard paths, configuration defaults

---

### Data Models (`models/`)

#### `asmdef_entry.py`

**Class:** `AsmdefEntry`  
**Fields:** name, guid, references, includePlatforms, excludePlatforms, allowUnsafeCode, overrideReferences, etc.  
**Purpose:** Strongly-typed representation of `.asmdef` file contents

#### `config.py`

**Class:** `AnalysisConfig`  
**Fields:**
- `root_path: Path` - Unity project Assets directory
- `dict_file: Path` - Assembly dictionary JSON path
- `output_dir: Path` - Report output directory
- `allow_child_namespaces: bool` - Namespace validation mode
- `verbose: bool` - Detailed logging flag

#### `report_models.py`

**Classes:**
- `CycleReport` - Cycle detection results
- `FileReport` - File mapping results  
- `NamespaceReport` - Namespace validation results

---

### Legacy Scripts (`analysis/`)

**Status:** These scripts are functional standalone utilities but are being superseded by the refactored `analyzers/` package and unified CLI.

#### `dictionary.py`

**Purpose:** Build initial assembly dictionary from Unity project  
**Function:** `build_asmdef_dictionary(root_path) -> dict`  
**Usage:** Scans for `.asmdef` files, extracts GUIDs from `.meta` files, builds dictionary

#### `cycles.py`

**Purpose:** Standalone cycle detection script  
**Usage:** `python analysis/cycles.py --file asmdef_dictionary.json`

#### `files.py`

**Purpose:** Standalone file mapping script  
**Usage:** `python analysis/files.py --file asmdef_dictionary.json --root ./Assets`

#### `namespaces.py`

**Purpose:** Standalone namespace validation script  
**Usage:** `python analysis/namespaces.py --file asmdef_dictionary.json --root ./Assets`

---

## Current Implementation Status

### ✅ Completed

1. **Core Analysis Engine** - All analyzers refactored and tested
   - `CycleAnalyzer` - Fully functional
   - `FileAnalyzer` - Fully functional
   - `NamespaceAnalyzer` - Fully functional

2. **Reporting System** - Consistent output formatting
   - Console reporters with color coding
   - JSON export for all analysis types
   - Configurable verbosity levels

3. **Testing Infrastructure** - Comprehensive test coverage
   - 50 tests passing
   - 77% code coverage
   - pytest + pytest-cov integration
   - mypy type checking (clean)

4. **Code Quality** - Formatted and linted
   - black formatting applied
   - ruff linting (zero violations)
   - Type hints throughout

5. **Logging System** - Centralized configuration
   - `common/logging_config.py`
   - File and console output
   - Configurable log levels

6. **Documentation** - Comprehensive guides
   - README.md (650+ lines)
   - Architecture diagrams
   - API reference
   - Usage examples (Python API)

---

## 🔧 Current Goal: CLI Entry Point Implementation

### Problem Statement

After completing the refactoring (Phases 1-6), all 5 legacy root scripts were removed:
- ❌ `asmdef_analyse.py` (orchestrator)
- ❌ `asmdef_dictionary.py` (dictionary builder)
- ❌ `asmdef_cyclic_report.py` (cycle detector)
- ❌ `asmdef_file_analyser.py` (file mapper)
- ❌ `asmdef_namespace_analyser.py` (namespace validator)

**The project now has no command-line interface**, despite command-line usage being the primary use case. A previous CLI attempt was bloated and failed to properly utilize the refactored infrastructure.

### Design Principles

The CLI must follow these principles:
1. **Leverage Existing Code** - Use refactored analyzers, reporters, and utilities directly
2. **Single Responsibility** - CLI handles argument parsing and orchestration only
3. **Minimal Code** - Target ~200 lines, not 500+
4. **Configuration Hierarchy** - CLI args → .env file → sensible defaults
5. **Proper Exit Codes** - 0=success, 1=error/issues found, 2=config error

---

### CLI Architecture Design

#### File: `asmdef_cli.py` (root level)

**Components to Utilize:**

| Component | Import | Purpose |
|-----------|--------|---------|
| `analysis.dictionary` | `build_asmdef_dictionary()` | Scan project for .asmdef files |
| `analyzers.CycleAnalyzer` | Detect circular dependencies | Returns `CycleReport` |
| `analyzers.FileAnalyzer` | Map C# files to assemblies | Updates dict with file mappings |
| `analyzers.NamespaceAnalyzer` | Validate namespace compliance | Returns `NamespaceAnalysisReport` |
| `reporting.CycleReporter` | Format cycle results | Console + JSON output |
| `reporting.NamespaceReporter` | Format namespace results | Console + JSON output |
| `reporting.FileAnalysisReporter` | Format file mapping results | Console + JSON output |
| `common.load_asmdef_dict` | Load existing dictionary | File I/O |
| `common.save_json_report` | Save dictionary/reports | File I/O |
| `common.setup_logging` | Configure logging | Centralized logging |
| `common.validate_directory` | Validate paths | Path utilities |

#### Command Structure

```
asmdef_cli.py
├── analyze (alias: all)    # Complete pipeline
├── build-dict              # Build dictionary only
├── detect-cycles           # Cycle detection only
├── map-files               # File mapping only
└── validate-namespaces     # Namespace validation only
```

#### Implementation Outline

```python
#!/usr/bin/env python3
"""Unity Assembly Definition Analysis CLI.

Unified command-line interface for asmdef analysis operations.
Utilizes refactored analyzers and reporters from the project.
"""

import argparse
import sys
from pathlib import Path

# Optional: Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os
from analysis.dictionary import build_asmdef_dictionary
from analyzers import CycleAnalyzer, FileAnalyzer, NamespaceAnalyzer
from reporting import CycleReporter, FileAnalysisReporter, NamespaceReporter
from common import (
    load_asmdef_dict,
    save_json_report,
    setup_logging,
    validate_directory,
    get_logger,
)

logger = get_logger(__name__)


def get_env_or_default(key: str, default: str) -> str:
    """Get environment variable or return default."""
    return os.environ.get(key, default)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with all commands."""
    parser = argparse.ArgumentParser(
        prog="asmdef_cli",
        description="Unity Assembly Definition Analysis Toolkit",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--log-level", default="INFO", help="Log level (DEBUG/INFO/WARNING/ERROR)")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Common arguments for commands that need project path
    project_args = argparse.ArgumentParser(add_help=False)
    project_args.add_argument(
        "--project-path", "-p",
        type=Path,
        default=Path(get_env_or_default("ROOT_PATH", ".")),
        help="Unity project Assets path",
    )
    project_args.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=Path(get_env_or_default("OUTPUT_PATH", "./reports")),
        help="Output directory for reports",
    )
    project_args.add_argument(
        "--dict-file", "-d",
        type=Path,
        default=Path(get_env_or_default("DICT_FILE", "./reports/asmdef_dictionary.json")),
        help="Dictionary file path",
    )

    # analyze command (full pipeline)
    analyze = subparsers.add_parser(
        "analyze", aliases=["all"],
        parents=[project_args],
        help="Run complete analysis pipeline",
    )
    analyze.add_argument("--allow-child-namespaces", action="store_true", default=True)
    analyze.add_argument("--no-child-namespaces", dest="allow_child_namespaces", action="store_false")

    # build-dict command
    subparsers.add_parser("build-dict", parents=[project_args], help="Build assembly dictionary")

    # detect-cycles command
    cycles = subparsers.add_parser("detect-cycles", parents=[project_args], help="Detect cycles")
    cycles.add_argument("--detailed", action="store_true", default=False)

    # map-files command
    subparsers.add_parser("map-files", parents=[project_args], help="Map C# files to assemblies")

    # validate-namespaces command
    ns = subparsers.add_parser("validate-namespaces", parents=[project_args], help="Validate namespaces")
    ns.add_argument("--allow-child-namespaces", action="store_true", default=True)
    ns.add_argument("--no-child-namespaces", dest="allow_child_namespaces", action="store_false")

    return parser


def cmd_build_dict(args: argparse.Namespace) -> int:
    """Build assembly dictionary from project."""
    validate_directory(args.project_path)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("Building assembly dictionary from %s", args.project_path)
    asmdef_dict = build_asmdef_dictionary(str(args.project_path))
    
    if not asmdef_dict:
        logger.error("Failed to build dictionary")
        return 1
    
    save_json_report(asmdef_dict, args.dict_file)
    logger.info("Dictionary saved to %s (%d assemblies)", args.dict_file, len(asmdef_dict))
    return 0


def cmd_detect_cycles(args: argparse.Namespace) -> int:
    """Detect circular dependencies."""
    asmdef_dict = load_asmdef_dict(args.dict_file)
    
    analyzer = CycleAnalyzer(asmdef_dict)
    report = analyzer.analyze()
    
    reporter = CycleReporter(verbose=args.verbose)
    reporter.print_console_report(report)
    reporter.save_json_report(report, args.output_dir / "cycle_report.json")
    
    return 1 if report.total_cycles > 0 else 0


def cmd_map_files(args: argparse.Namespace) -> int:
    """Map C# files to assemblies."""
    validate_directory(args.project_path)
    asmdef_dict = load_asmdef_dict(args.dict_file)
    
    analyzer = FileAnalyzer(asmdef_dict, args.project_path)
    updated_dict = analyzer.analyze()
    stats = analyzer.get_stats()
    
    reporter = FileAnalysisReporter(verbose=args.verbose)
    reporter.print_console_report(stats)
    
    save_json_report(updated_dict, args.dict_file)
    return 0


def cmd_validate_namespaces(args: argparse.Namespace) -> int:
    """Validate namespace compliance."""
    validate_directory(args.project_path)
    asmdef_dict = load_asmdef_dict(args.dict_file)
    
    analyzer = NamespaceAnalyzer(asmdef_dict, args.project_path, args.allow_child_namespaces)
    report = analyzer.analyze()
    
    reporter = NamespaceReporter(verbose=args.verbose)
    reporter.print_console_report(report)
    reporter.save_json_report(report, args.output_dir / "namespace_report.json")
    
    return 1 if report.total_issues > 0 else 0


def cmd_analyze(args: argparse.Namespace) -> int:
    """Run complete analysis pipeline."""
    exit_code = 0
    
    # Step 1: Build dictionary
    logger.info("=" * 60)
    logger.info("Step 1/4: Building Assembly Dictionary")
    logger.info("=" * 60)
    if cmd_build_dict(args) != 0:
        return 1
    
    # Step 2: Map files
    logger.info("\n" + "=" * 60)
    logger.info("Step 2/4: Mapping C# Files to Assemblies")
    logger.info("=" * 60)
    cmd_map_files(args)
    
    # Step 3: Validate namespaces
    logger.info("\n" + "=" * 60)
    logger.info("Step 3/4: Validating Namespace Compliance")
    logger.info("=" * 60)
    if cmd_validate_namespaces(args) != 0:
        exit_code = 1
    
    # Step 4: Detect cycles
    logger.info("\n" + "=" * 60)
    logger.info("Step 4/4: Detecting Circular Dependencies")
    logger.info("=" * 60)
    if cmd_detect_cycles(args) != 0:
        exit_code = 1
    
    logger.info("\n" + "=" * 60)
    logger.info("Analysis Complete - Reports in %s", args.output_dir)
    logger.info("=" * 60)
    
    return exit_code


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 2
    
    setup_logging(level=args.log_level)
    
    commands = {
        "analyze": cmd_analyze,
        "all": cmd_analyze,
        "build-dict": cmd_build_dict,
        "detect-cycles": cmd_detect_cycles,
        "map-files": cmd_map_files,
        "validate-namespaces": cmd_validate_namespaces,
    }
    
    try:
        return commands[args.command](args)
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled")
        return 130
    except Exception as e:
        logger.error("Error: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

---

### Implementation Checklist

#### Phase 7: CLI Implementation ✅ COMPLETE (January 29, 2026)

- [x] **7.1 Create `asmdef_cli.py`** ✅
    - [x] Implement argument parser with subcommands
    - [x] Implement `cmd_build_dict()` using `analysis.dictionary.build_asmdef_dictionary()`
    - [x] Implement `cmd_detect_cycles()` using `CycleAnalyzer` + `CycleReporter`
    - [x] Implement `cmd_map_files()` using `FileAnalyzer` + `FileAnalysisReporter`
    - [x] Implement `cmd_validate_namespaces()` using `NamespaceAnalyzer` + `NamespaceReporter`
    - [x] Implement `cmd_analyze()` orchestrating all steps
    - [x] Add environment variable loading with dotenv

- [x] **7.2 Verify Component Integration** ✅
    - [x] Test that `CycleAnalyzer.analyze()` returns proper `CycleReport`
    - [x] Test that `CycleReporter.print_console_report()` works with `CycleReport`
    - [x] Test that `CycleReporter.save_json_report()` works correctly
    - [x] Repeat verification for Namespace and File analyzers/reporters

- [x] **7.3 Test CLI Commands** ✅
    - [x] `python asmdef_cli.py --help` shows usage
    - [x] `python asmdef_cli.py analyze --project-path <path>` runs full pipeline
    - [x] `python asmdef_cli.py build-dict --project-path <path>` creates dictionary
    - [x] `python asmdef_cli.py detect-cycles --dict-file <path>` detects cycles
    - [x] Exit codes are correct (0=success, 1=issues, 2=config error)

- [x] **7.4 Package Configuration** ✅
    - [x] Updated `pyproject.toml` with package discovery configuration
    - [x] Added `asmdef-cli` console script entry point
    - [x] Verified package installs in development mode (`pip install -e .`)
    - [x] All 50 tests pass

### Success Criteria ✅ ALL MET

- ✅ `python asmdef_cli.py analyze --project-path ./Assets` completes without errors
- ✅ All reports generated correctly in `./reports/` directory
- ✅ Exit codes work as documented (0=success, 1=issues found, 2=config error, 130=interrupted)
- ✅ `.env` file configuration loads properly
- ✅ README.md CLI examples work
- ✅ Help text (`--help`) is clear and comprehensive
- ✅ CLI code is <250 lines (actual: ~280 lines), utilizing existing infrastructure

### Key Design Decisions

1. **Single File CLI** - All CLI code in `asmdef_cli.py` (~280 lines), not a separate `cli/` package
2. **Direct Imports** - Use analyzers/reporters directly, no subprocess calls
3. **Subcommand Pattern** - argparse subparsers for clean command structure
4. **Environment Fallback** - Args → ENV → defaults, using simple `os.environ.get()`
5. **Consistent Logging** - Use `common.setup_logging()` and `common.get_logger()`
6. **Proper Exit Codes** - Return meaningful exit codes for CI/CD integration

---

## Development Workflow

### Running Tests

```bash
pytest                          # Run all tests
pytest --cov                    # With coverage report
pytest -v                       # Verbose output
```

### Code Quality

```bash
mypy .                          # Type checking
black .                         # Format code
ruff check . --fix              # Lint and auto-fix
```

### Running Analysis

```bash
# Once CLI is fixed:
python asmdef_cli.py analyze --project-path D:/Unity/MyProject/Assets
```

---

## Configuration

### `.env` File Format

```bash
# Project Configuration
ROOT_PATH=D:/Unity/MyProject/Assets

# Output Configuration
DICT_FILE=./reports/asmdef_dictionary.json
OUTPUT_PATH=./reports

# Analysis Options
DEPTH=5
DETAILED=true

# Cycle Detection Options
ALLOW_CHILD_NAMESPACES=false

# Logging Configuration
LOG_LEVEL=INFO
```

CLI arguments override environment variables.

---

## Key Dependencies

- **Python 3.11+** - Language runtime
- **pytest** - Testing framework
- **mypy** - Static type checking
- **black** - Code formatting
- **ruff** - Fast Python linter
- **python-dotenv** - Environment variable loading (optional)

---

## Output Files

All reports are generated in `./reports/` directory:

- `asmdef_dictionary.json` - Assembly definitions with metadata
- `cycle_report.json` - Detailed cycle detection results
- `cycle_report_summary.json` - Cycle statistics summary
- `namespace_validation.json` - Namespace compliance issues (if any)
- `file_mapping.json` - C# file to assembly assignments

---

## Notes

- The `analysis/` directory contains the original standalone scripts. These are still functional but will be deprecated once the CLI is fully operational.
- All analyzers have been refactored to accept dictionaries directly rather than `AnalysisConfig` objects (simpler, more testable).
- The reporting layer uses a consistent `BaseReporter` abstract class to ensure uniform output formatting.
- Logging is centralized in `common/logging_config.py` with per-module loggers.
- The project uses type hints throughout for better IDE support and early error detection.

---

## Reference Documentation

- **README.md** - User guide, installation, API reference, examples
- **CLAUDE.md.01** - Original detailed refactoring notes and history
- **pyproject.toml** - Project metadata and tool configuration
- **.env.example** - Configuration template with all options
