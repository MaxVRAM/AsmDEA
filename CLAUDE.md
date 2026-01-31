# Asm DEA: Assembly Dependency Enforcement Agency - Project Overview

Last Updated: January 29, 2026

---

## Important Rule: Use Virtual Environment

Always use the provided virtual environment for development to ensure dependency consistency.

Run the following command from the project root to ensure you're using the correct Python version:

```bash
# Windows PowerShell
.venv/Scripts/Activate.ps1; python --version
# Linux/Mac
source .venv/bin/activate; python --version
```

## Project Purpose

Analyze Unity projects to detect circular dependencies between Assembly Definitions (`.asmdef`), validate namespace compliance, and map C# files to their owning assemblies. This toolkit helps maintain clean architecture in large Unity codebases.

---

## Project Structure

```
AsmDEA/
├── asmdea.py                  # CLI entry point
├── analysers/                  # Analyser classes
│   ├── cycle_analyser.py      # Circular dependency detection
│   ├── file_analyser.py       # C# file to assembly mapping
│   └── namespace_analyser.py  # Namespace compliance checking
├── common/                     # Shared utilities
│   ├── asmdef_dict.py         # Dictionary manipulation helpers
│   ├── console.py             # Rich console configuration
│   ├── constants.py           # Project-wide constants
│   ├── dictionary.py          # Asmdef dictionary builder
│   ├── exceptions.py          # Custom exception classes
│   ├── file_io.py             # JSON load/save utilities
│   ├── logging_config.py      # Centralized logging setup
│   └── path_utils.py          # Path validation utilities
├── models/                     # Data models
│   ├── asmdef_entry.py        # Assembly definition data class
│   ├── config.py              # Configuration dataclass
│   ├── cycle_report.py        # Cycle detection results
│   └── namespace_analysis.py  # Namespace validation results
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

### Core Analysers (`analysers/`)

#### `cycle_analyser.py`

**Purpose:** Detect circular dependencies between assemblies  
**Key Class:** `CycleAnalyser`  
**Constructor:** `CycleAnalyser(asmdef_dict: dict)`  
**Methods:**
- `analyse() -> CycleReport` - Detect all cycles in dependency graph
- `_build_dependency_graph()` - Create graph from assembly references
- `detect_cycles()` - Find all cycles in the dependency graph
- `_build_dependency_tree()` - Generate visualization tree

**Input:** Assembly dictionary (GUID → assembly data)  
**Output:** `CycleReport` with cycles, severity, and dependency trees

#### `file_analyser.py`

**Purpose:** Map C# files to their owning assemblies  
**Key Class:** `FileAnalyser`  
**Constructor:** `FileAnalyser(asmdef_dict: dict, root_path: Path)`  
**Methods:**
- `analyse() -> dict` - Scan project and assign files to assemblies
- `_build_path_to_guid_mapping()` - Map directories to assembly GUIDs
- `find_owning_assembly()` - Determine which assembly owns a file

**Input:** Unity project root directory  
**Output:** Updated dictionary with `csFiles` arrays per assembly

#### `namespace_analyser.py`

**Purpose:** Validate C# file namespaces match assembly root namespaces  
**Key Class:** `NamespaceAnalyser`  
**Constructor:** `NamespaceAnalyser(asmdef_dict: dict, root_path: Path, allow_child_namespaces: bool)`  
**Methods:**
- `analyse() -> NamespaceAnalysis` - Check namespace compliance for all files
- `extract_namespace_from_file()` - Parse namespace declarations from C# (static)
- `normalize_namespace()` - Normalize namespace for comparison (static)

**Input:** Assembly dictionary with file mappings  
**Output:** `NamespaceAnalysis` dataclass with results and violations

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

#### `cycle_report.py`

**Class:** `CycleReport`  
**Purpose:** Cycle detection results with cycles list, severity, and dependency trees

#### `namespace_analysis.py`

**Class:** `NamespaceAnalysis`  
**Purpose:** Namespace validation results with violations and statistics

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
- `namespace_report.json` - Namespace compliance issues (if any)

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
