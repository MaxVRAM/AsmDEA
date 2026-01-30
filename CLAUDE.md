# Asm DEA: Assembly Dependency Enforcement Agency - Project Overview

Last Updated: January 29, 2026

---

## Project Purpose

Analyze Unity projects to detect circular dependencies between Assembly Definitions (`.asmdef`), validate namespace compliance, and map C# files to their owning assemblies. This toolkit helps maintain clean architecture in large Unity codebases.

---

## Project Structure

```
AsmDEA/
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
│   ├── console.py             # Rich console configuration
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

#### `console.py`

**Functions:**
- `get_console() -> Console` - Get shared Rich Console instance (singleton)
- `configure_console(plain, width) -> Console` - Configure console settings at startup
- `reset_console()` - Reset console state (for testing)

**Features:**
- Custom AsmDEA theme with semantic colors (success, warning, error, etc.)
- Respects NO_COLOR environment variable
- Plain text fallback mode for CI/CD environments

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
python asmdea.py analyze --project-path D:/Unity/MyProject/Assets
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

## Development Environment

**Important:** Always use a virtual environment for development.

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
# or
.venv/bin/pip install -r requirements.txt       # Linux/Mac
```

---

## Reference Documentation

- **README.md** - User guide, installation, API reference, examples
- **pyproject.toml** - Project metadata and tool configuration
- **.env.example** - Configuration template with all options

---

## Current Work: Rich Console Output Implementation

**Goal:** Replace Python `logging`-based console output with Rich library for enhanced terminal displays (tables, trees, panels, colors).

### Status: ✅ COMPLETED

All tasks completed successfully:

- ✅ Added `rich>=13.0.0` to `pyproject.toml` and `requirements.txt`
- ✅ Created `common/console.py` with Rich Console factory, theme, and configuration functions
- ✅ Updated `common/__init__.py` to export console functions
- ✅ Updated `reporting/base.py` with optional `console` parameter and `console` property
- ✅ Updated `reporting/cycle_reporter.py` with Rich Panel, Table, Tree, and Rule components
- ✅ Updated `reporting/namespace_reporter.py` with Rich Panel and Table components
- ✅ Updated `reporting/file_reporter.py` with Rich Panel and Table components
- ✅ Added `--no-color` flag to `asmdea.py` CLI with `configure_console()` call
- ✅ All 50 tests pass
- ✅ Type checking passes for Rich implementation files (no new mypy errors)
- ✅ Manual verification confirms Rich output displays correctly with colors, panels, and tables
- ✅ Updated CLAUDE.md project structure documentation

The Rich console implementation is fully functional and ready for use.
