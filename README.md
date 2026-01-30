# AsmDEA: Assembly Definition Enforcement Agency

A Python toolkit for analysing Unity Assembly Definition (`.asmdef`) files, detecting circular dependencies, validating namespace compliance, and mapping C# files to assemblies.

## Features

- 🔍 **Dependency Analysis**: Detect circular dependencies between assemblies
- 📁 **File Mapping**: Assign C# files to their owning assemblies
- 🏷️ **Namespace Validation**: Verify namespace declarations match assembly root namespaces
- 📊 **Comprehensive Reporting**: JSON and console output formats
- 🔧 **Configurable**: Flexible configuration options for different project needs
- ✅ **Well-Tested**: 77% test coverage with 50 unit tests

## Table of Contents

- [Installation](#installation)
- [Quick Start (CLI)](#quick-start-cli)
- [Command-Line Usage](#command-line-usage)
- [Architecture](#architecture)
- [API Reference](#api-reference)
- [Development](#development)

## Installation

### Requirements

- Python 3.11 or higher
- Unity project with Assembly Definition files

### Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd AsmDEA
```

1. Create and activate virtual environment:

```bash
python -m venv .venv

# On Windows (PowerShell)
.venv\Scripts\Activate.ps1

# On macOS/Linux
source .venv/bin/activate
```

1. Install dependencies:

```bash
pip install -r requirements.txt
```

## Quick Start (CLI)

**Recommended for most users** - Analyse your Unity project from the command line:

```bash
# Run complete analysis on your Unity project
asmdea analyse --project-path D:/Unity/MyProject/Assets

# The above command will:
# 1. Map all C# files to their owning assemblies
# 2. Validate namespace compliance
# 3. Detect circular dependencies
# 4. Generate JSON reports in ./reports/

# Use environment variables (create .env from .env.example)
cp .env.example .env
# Edit .env with your project path
asmdea analyse

# Run specific analyses
asmdea detect-cycles --dict-file ./reports/asmdef_dictionary.json
asmdea validate-namespaces --project-path ./Assets
asmdea map-files --project-path ./Assets

# Get help
asmdea --help
asmdea analyse --help
```

## Architecture

### Module Structure

```
AsmDEA/
├── common/              # Shared utilities
│   ├── asmdef_dict.py   # Dictionary utilities
│   ├── console.py       # Rich console configuration
│   ├── constants.py     # Project constants
│   ├── dictionary.py    # Asmdef dictionary builder
│   ├── exceptions.py    # Custom exceptions
│   ├── file_io.py       # JSON I/O operations
│   ├── logging_config.py # Centralized logging
│   └── path_utils.py    # Path validation
│
├── models/              # Data models
│   ├── asmdef_entry.py  # Assembly definition model
│   ├── config.py        # Analysis configuration
│   ├── cycle_report.py  # Cycle detection results
│   └── namespace_analysis.py # Namespace analysis results
│
├── analyzers/           # Business logic
│   ├── cycle_analyzer.py     # Circular dependency detection
│   ├── namespace_analyzer.py # Namespace compliance checking
│   └── file_analyzer.py      # File-to-assembly mapping
│
├── reporting/           # Output formatting
│   ├── base.py          # Abstract reporter base class
│   ├── cycle_reporter.py     # Cycle report formatter
│   ├── namespace_reporter.py # Namespace report formatter
│   └── file_reporter.py      # File analysis formatter
│
└── tests/               # Test suite (50 tests, 77% coverage)
    ├── conftest.py      # Shared fixtures
    └── unit/            # Unit tests
```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        AsmDEA                               │
│                  Unity Asmdef Analysis                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      Entry Point                            │
│                   (User's Python Script)                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 Configuration Layer                         │
│  ┌────────────────────────────────────────────────────┐    │
│  │  models/config.py                                  │    │
│  │  - AnalysisConfig (paths, options)                 │    │
│  └────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  common/logging_config.py                          │    │
│  │  - setup_logging(), get_logger()                   │    │
│  └────────────────────────────────────────────────────┘    │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                   Data Layer                                │
│  ┌─────────────────────┐  ┌──────────────────────┐        │
│  │ common/file_io.py   │  │ models/asmdef_entry.py│       │
│  │ - load/save JSON    │  │ - Assembly Definition │       │
│  └─────────────────────┘  └──────────────────────┘        │
│  ┌─────────────────────────────────────────────────┐       │
│  │ common/asmdef_dict.py                           │       │
│  │ - Dictionary manipulation utilities              │       │
│  └─────────────────────────────────────────────────┘       │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                  Analysis Layer                             │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────┐  │
│  │CycleAnalyzer    │  │NamespaceAnalyzer │  │FileAnalyzer│ │
│  │                 │  │                  │  │           │  │
│  │- Build graph    │  │- Extract NS      │  │- Scan .cs │  │
│  │- Detect cycles  │  │- Validate match  │  │- Map files│  │
│  │- Build trees    │  │- Child NS check  │  │- Find owner│ │
│  └─────────────────┘  └──────────────────┘  └──────────┘  │
│           │                    │                   │        │
│           └────────────────────┴───────────────────┘        │
│                              │                              │
└──────────────────────────────┼──────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Reporting Layer                          │
│  ┌──────────────────┐  ┌─────────────────┐  ┌──────────┐  │
│  │ CycleReporter    │  │NamespaceReporter│  │FileReporter│ │
│  │                  │  │                 │  │           │  │
│  │- Console format  │  │- Console format │  │- Console  │  │
│  │- JSON export     │  │- JSON export    │  │- JSON     │  │
│  │- Severity marks  │  │- Problem detect │  │- Stats    │  │
│  └──────────────────┘  └─────────────────┘  └──────────┘  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
         ┌───────────────┐
         │    Output     │
         │ - Console     │
         │ - JSON files  │
         │ - Log files   │
         └───────────────┘

Flow:
1. User configures analysis (AnalysisConfig + logging)
2. Data loaded from Unity project/JSON dictionary
3. Analyzers process data (cycles, namespaces, files)
4. Reporters format and output results (console + JSON)
```

### Data Flow

1. **Input**: Unity project directory with `.asmdef` and `.cs` files
2. **Processing**:
   - Scan for assembly definitions
   - Build dependency graph
   - Map C# files to assemblies
   - Analyze namespace compliance
   - Detect circular dependencies
3. **Output**: Console reports and JSON files

## Command-Line Usage

The `asmdea` command provides a unified command-line interface for all analysis operations. It supports configuration via command-line arguments or a `.env` file.

### Setup Environment Variables (Optional)

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` with your project settings:

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

Command-line arguments override environment variables.

### Commands

#### Complete Analysis (`analyse`)

Runs the full analysis pipeline: file mapping → namespace validation → cycle detection.

```bash
# Using .env configuration
asmdea analyse

# Using command-line arguments
asmdea analyse \
  --project-path D:/Unity/MyProject/Assets \
  --dict-file ./reports/asmdef_dictionary.json \
  --output-dir ./reports \
  --verbose

# Short form (alias)
asmdea all --project-path ./Assets
```

**Options:**
- `--project-path PATH`: Unity Assets directory (required, or set `ROOT_PATH` in .env)
- `--dict-file PATH`: Assembly dictionary JSON file (default: `./reports/asmdef_dictionary.json`)
- `--output-dir PATH`: Output directory for reports (default: `./reports`)
- `--depth N`: Maximum tree depth in cycle reports (default: 5)
- `--detailed`: Include detailed dependency trees
- `--allow-child-namespaces`: Allow child namespaces in validation
- `--verbose`: Enable verbose logging
- `--no-color`: Disable coloured output (plain text mode for CI/CD)
- `--log-file PATH`: Write logs to file

**Exit codes:**
- `0`: Success (no cycles or validation issues)
- `1`: Analysis completed with errors (cycles found or validation failures)
- `130`: User interrupted (Ctrl+C)

#### Detect Cycles (`detect-cycles`)

Detect circular dependencies only (requires existing dictionary).

```bash
# Using existing dictionary
asmdea detect-cycles \
  --dict-file ./reports/asmdef_dictionary.json \
  --output-dir ./reports \
  --depth 10 \
  --detailed
```

**Options:**
- `--dict-file PATH`: Assembly dictionary JSON (required)
- `--output-dir PATH`: Output directory for cycle reports
- `--depth N`: Maximum tree depth for visualization
- `--detailed`: Include detailed dependency trees

#### Validate Namespaces (`validate-namespaces`)

Check namespace compliance only.

```bash
# Validate namespaces in project
asmdea validate-namespaces \
  --project-path D:/Unity/MyProject/Assets \
  --allow-child-namespaces \
  --verbose

# Update dictionary with namespace analysis
asmdea validate-namespaces \
  --project-path ./Assets \
  --dict-file ./reports/asmdef_dictionary.json
```

**Options:**
- `--project-path PATH`: Unity Assets directory (required)
- `--dict-file PATH`: Dictionary to update (optional)
- `--allow-child-namespaces`: Allow child namespaces
- `--verbose`: Show validation details

#### Map Files (`map-files`)

Map C# files to their owning assemblies.

```bash
# Map files and create/update dictionary
asmdea map-files \
  --project-path D:/Unity/MyProject/Assets \
  --dict-file ./reports/asmdef_dictionary.json \
  --output-dir ./reports
```

**Options:**
- `--project-path PATH`: Unity Assets directory (required)
- `--dict-file PATH`: Dictionary to create/update
- `--output-dir PATH`: Output directory for file mapping report

#### Build Dictionary (`build-dict`)

Create initial assembly dictionary from `.asmdef` files.

```bash
# Create dictionary from Unity project
asmdea build-dict \
  --project-path D:/Unity/MyProject/Assets \
  --dict-file ./reports/asmdef_dictionary.json \
  --verbose
```

**Options:**
- `--project-path PATH`: Unity Assets directory (required)
- `--dict-file PATH`: Dictionary output file
- `--verbose`: Show dictionary building details

### Common Workflows

**First-time analysis:**

```bash
# 1. Create .env file
cp .env.example .env
# Edit .env with your ROOT_PATH

# 2. Run complete analysis
asmdea analyse

# Reports generated in ./reports/:
# - asmdef_dictionary.json
# - cycle_report.json
# - cycle_report_summary.json
# - namespace_validation.json (if issues found)
# - file_mapping.json
```

**Daily development workflow:**

```bash
# Quick check for new circular dependencies
asmdea detect-cycles --dict-file ./reports/asmdef_dictionary.json

# Validate namespaces after refactoring
asmdea validate-namespaces --project-path ./Assets
```

**CI/CD integration:**

```bash
# Exit with error code if cycles detected
asmdea analyse --project-path ./Assets || exit 1
```

### Getting Help

```bash
# General help
asmdea --help

# Command-specific help
asmdea analyse --help
asmdea detect-cycles --help
asmdea validate-namespaces --help
asmdea map-files --help
asmdea build-dict --help
```

## API Reference

### Core Analyzers

#### CycleAnalyzer

Detects circular dependencies between assemblies.

```python
from analyzers import CycleAnalyzer

analyzer = CycleAnalyzer(asmdef_dict)
report = analyzer.analyze()
```

**Methods:**
- `analyze(max_depth)`: Detect cycles and return CycleReport
- `detect_cycles()`: Return list of cycle paths
- `_build_dependency_graph()`: Build internal dependency graph
- `_build_dependency_tree()`: Generate visualization tree

#### NamespaceAnalyzer

Validates C# file namespaces against assembly root namespaces.

```python
from analyzers import NamespaceAnalyzer

analyzer = NamespaceAnalyzer(asmdef_dict, root_path, allow_child_namespaces)
report = analyzer.analyze()
```

**Methods:**
- `analyze()`: Analyze all assemblies, return NamespaceAnalysisReport
- `analyze_assembly(guid, assembly_data)`: Analyze single assembly
- `extract_namespace_from_file(file_path)`: Extract namespace from C# file (static)
- `normalize_namespace(namespace)`: Normalize namespace for comparison (static)

#### FileAnalyzer

Maps C# files to their owning assemblies.

```python
from analyzers import FileAnalyzer

analyzer = FileAnalyzer(asmdef_dict, root_path)
updated_dict = analyzer.analyze()
```

**Methods:**
- `analyze()`: Scan project and assign files to assemblies, return updated dict
- `_build_path_to_guid_mapping()`: Map directories to assembly GUIDs
- `find_owning_assembly(file_path)`: Find assembly for specific file

### Data Models

#### CycleReport

Contains cycle detection results.

**Properties:**
- `total_cycles`: Number of cycles found
- `total_nodes`: Number of assemblies analyzed
- `affected_nodes`: Set of assemblies in cycles
- `cycles`: List of CycleDetail objects

#### NamespaceAnalysisReport

Contains namespace validation results.

**Properties:**
- `total_assemblies`: Number of assemblies analyzed
- `total_files`: Number of C# files checked
- `total_matched`: Files with matching namespaces
- `total_mismatched`: Files with incorrect namespaces
- `assembly_stats`: Dict of per-assembly statistics

**Methods:**
- `get_problem_assemblies()`: Return assemblies with issues

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=common --cov=models --cov=analyzers --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_analyzers.py -v
```

### Code Quality

```bash
# Type checking
mypy common/ models/ analyzers/ --explicit-package-bases

# Code formatting
black common/ models/ analyzers/ reporting/

# Linting
ruff check common/ models/ analyzers/ reporting/ --fix
```

### Project Structure

- **common/**: Shared utilities and configurations
- **models/**: Data classes and configurations
- **analyzers/**: Core analysis logic (business layer)
- **reporting/**: Output formatting and presentation
- **tests/**: Unit and integration tests

### Contributing

1. Write tests for new features
2. Maintain type hints
3. Follow existing code style (black + ruff)
4. Update documentation
5. Ensure all tests pass

## License

[Add license information]

## Support

[Add support/contact information]
