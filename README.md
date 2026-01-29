# ScriptFlattener - Unity Assembly Definition Analysis Toolkit

A Python toolkit for analyzing Unity Assembly Definition (`.asmdef`) files, detecting circular dependencies, validating namespace compliance, and mapping C# files to assemblies.

## Features

- 🔍 **Dependency Analysis**: Detect circular dependencies between assemblies
- 📁 **File Mapping**: Assign C# files to their owning assemblies
- 🏷️ **Namespace Validation**: Verify namespace declarations match assembly root namespaces
- 📊 **Comprehensive Reporting**: JSON and console output formats
- 🔧 **Configurable**: Flexible configuration options for different project needs
- ✅ **Well-Tested**: 77% test coverage with 50 unit tests

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)
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
cd ScriptFlattener
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

## Quick Start

```python
from pathlib import Path
from common import setup_logging
from models import AnalysisConfig
from analyzers import CycleAnalyzer, NamespaceAnalyzer, FileAnalyzer
from reporting import CycleReporter, NamespaceReporter, FileAnalysisReporter

# Setup logging
setup_logging(level="INFO", log_file="logs/analysis.log")

# Configure analysis
config = AnalysisConfig(
    root_path=Path("/path/to/unity/project"),
    dict_file=Path("reports/asmdef_dictionary.json"),
    output_dir=Path("reports"),
    allow_child_namespaces=True
)

# Load or build asmdef dictionary
from common import load_asmdef_dict

try:
    asmdef_dict = load_asmdef_dict(config.dict_file)
except SystemExit:
    # Dictionary doesn't exist, need to build it first
    print("Run dictionary builder first")

# Analyze cycles
cycle_analyzer = CycleAnalyzer(config)
cycle_report = cycle_analyzer.analyze(asmdef_dict)

# Print results
reporter = CycleReporter(verbose=True)
reporter.print_console_report(cycle_report)
reporter.save_json_report(cycle_report, config.output_dir / "cycles.json")
```

## Architecture

### Module Structure

```
ScriptFlattener/
├── common/              # Shared utilities
│   ├── constants.py     # Project constants
│   ├── exceptions.py    # Custom exceptions
│   ├── file_io.py       # JSON I/O operations
│   ├── path_utils.py    # Path validation
│   ├── asmdef_dict.py   # Dictionary utilities
│   ├── script_runner.py # Subprocess execution
│   └── logging_config.py # Centralized logging
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
│                     ScriptFlattener                         │
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

## Usage Examples

### Example 1: Detect Circular Dependencies

```python
from pathlib import Path
from common import setup_logging, load_asmdef_dict
from models import AnalysisConfig
from analyzers import CycleAnalyzer
from reporting import CycleReporter

# Setup
setup_logging(level="INFO")
config = AnalysisConfig(
    dict_file=Path("reports/asmdef_dictionary.json")
)

# Load dictionary
asmdef_dict = load_asmdef_dict(config.dict_file)

# Analyze
analyzer = CycleAnalyzer(config)
report = analyzer.analyze(asmdef_dict)

# Report
reporter = CycleReporter(verbose=True)
if report.total_cycles > 0:
    reporter.print_console_report(report)
    reporter.save_json_report(report, Path("reports/cycles.json"))
else:
    print("✓ No circular dependencies found!")
```

### Example 2: Validate Namespace Compliance

```python
from pathlib import Path
from common import setup_logging
from models import AnalysisConfig
from analyzers import NamespaceAnalyzer
from reporting import NamespaceReporter

# Setup with child namespace allowance
setup_logging(level="INFO")
config = AnalysisConfig(
    root_path=Path("/path/to/unity/Assets"),
    allow_child_namespaces=True
)

# Analyze
analyzer = NamespaceAnalyzer(config)
asmdef_dict = {}  # Start with empty dict or load existing
updated_dict = analyzer.analyze(asmdef_dict)

# Generate report
report = analyzer.generate_report()
reporter = NamespaceReporter(
    verbose=True,
    allow_child_namespaces=True
)
reporter.print_console_report(report)
reporter.save_json_report(report, Path("reports/namespaces.json"))
```

### Example 3: Map C# Files to Assemblies

```python
from pathlib import Path
from common import setup_logging
from models import AnalysisConfig
from analyzers import FileAnalyzer
from reporting import FileAnalysisReporter

# Setup
setup_logging(level="INFO")
config = AnalysisConfig(
    root_path=Path("/path/to/unity/Assets")
)

# Analyze
analyzer = FileAnalyzer(config)
asmdef_dict = {}  # Or load existing dictionary
updated_dict = analyzer.analyze(asmdef_dict)
stats = analyzer.get_stats()

# Report
reporter = FileAnalysisReporter(verbose=True)
data = {"asmdef_dict": updated_dict, "stats": stats}
reporter.print_console_report(data)
reporter.save_json_report(data, Path("reports/file_mapping.json"))
```

### Example 4: Complete Analysis Pipeline

```python
from pathlib import Path
from common import setup_logging, load_asmdef_dict, save_json_report
from models import AnalysisConfig
from analyzers import CycleAnalyzer, NamespaceAnalyzer, FileAnalyzer
from reporting import (
    CycleReporter,
    NamespaceReporter,
    FileAnalysisReporter
)

def main():
    # Configure
    setup_logging(
        level="INFO",
        log_file="logs/analysis.log",
        file_level="DEBUG"
    )
    
    config = AnalysisConfig(
        root_path=Path("/path/to/unity/Assets"),
        dict_file=Path("reports/asmdef_dictionary.json"),
        output_dir=Path("reports"),
        allow_child_namespaces=True,
        verbose=True
    )
    
    # Build/load assembly dictionary
    asmdef_dict = {}
    
    # Step 1: Map files to assemblies
    print("\n=== Step 1: File Analysis ===")
    file_analyzer = FileAnalyzer(config)
    asmdef_dict = file_analyzer.analyze(asmdef_dict)
    
    file_reporter = FileAnalysisReporter(verbose=True)
    file_data = {
        "asmdef_dict": asmdef_dict,
        "stats": file_analyzer.get_stats()
    }
    file_reporter.print_console_report(file_data)
    
    # Step 2: Validate namespaces
    print("\n=== Step 2: Namespace Analysis ===")
    ns_analyzer = NamespaceAnalyzer(config)
    asmdef_dict = ns_analyzer.analyze(asmdef_dict)
    ns_report = ns_analyzer.generate_report()
    
    ns_reporter = NamespaceReporter(
        verbose=True,
        allow_child_namespaces=config.allow_child_namespaces
    )
    ns_reporter.print_console_report(ns_report)
    
    # Step 3: Detect cycles
    print("\n=== Step 3: Cycle Detection ===")
    cycle_analyzer = CycleAnalyzer(config)
    cycle_report = cycle_analyzer.analyze(asmdef_dict)
    
    cycle_reporter = CycleReporter(verbose=True)
    cycle_reporter.print_console_report(cycle_report)
    
    # Save all results
    save_json_report(asmdef_dict, config.dict_file)
    save_json_report(
        ns_reporter.generate_json_report(ns_report),
        config.output_dir / "namespace_analysis.json"
    )
    save_json_report(
        cycle_report.to_dict(),
        config.output_dir / "cycle_report.json"
    )
    
    print("\n✓ Analysis complete!")

if __name__ == "__main__":
    main()
```

## Configuration

### AnalysisConfig

The main configuration class for all analyzers:

```python
from models import AnalysisConfig
from pathlib import Path

config = AnalysisConfig(
    # Unity project root path (required for file/namespace analysis)
    root_path=Path("/path/to/unity/Assets"),
    
    # Assembly dictionary file path
    dict_file=Path("reports/asmdef_dictionary.json"),
    
    # Output directory for reports
    output_dir=Path("reports"),
    
    # Reports directory (legacy, use output_dir instead)
    reports_dir=Path("reports"),
    
    # Maximum tree depth for cycle visualization
    tree_depth=3,
    
    # Allow child namespaces (MyProject.Core.Utilities is valid for MyProject.Core)
    allow_child_namespaces=True,
    
    # Enable verbose output
    verbose=True
)
```

### Logging Configuration

Control logging behavior:

```python
from common import setup_logging, get_logger

# Basic setup (console only)
setup_logging(level="INFO")

# Console + file logging
setup_logging(
    level="INFO",              # Console level
    log_file="logs/app.log",   # Optional log file
    file_level="DEBUG",        # File level (more detailed)
    console=True               # Enable console output
)

# Get logger in your module
logger = get_logger(__name__)
logger.info("Processing started")
logger.warning("Potential issue detected")
logger.error("Failed to process", exc_info=True)
```

**Log Levels:**
- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages (default)
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failures
- `CRITICAL`: Critical failures

### Reporter Configuration

Control output formatting:

```python
from reporting import CycleReporter, NamespaceReporter

# Verbose reporter (shows detailed information)
reporter = CycleReporter(verbose=True)

# Quiet reporter (summary only)
reporter = CycleReporter(verbose=False)

# Namespace reporter with child namespace allowance
ns_reporter = NamespaceReporter(
    verbose=True,
    allow_child_namespaces=True
)
```

## API Reference

### Core Analyzers

#### CycleAnalyzer

Detects circular dependencies between assemblies.

```python
from analyzers import CycleAnalyzer

analyzer = CycleAnalyzer(config)
report = analyzer.analyze(asmdef_dict)
summary = analyzer.get_summary()
```

**Methods:**
- `analyze(asmdef_dict)`: Detect cycles and return CycleReport
- `get_summary()`: Get CycleSummary with statistics
- `detect_cycles()`: Return list of cycle paths
- `build_dependency_graph()`: Build internal dependency graph

#### NamespaceAnalyzer

Validates C# file namespaces against assembly root namespaces.

```python
from analyzers import NamespaceAnalyzer

analyzer = NamespaceAnalyzer(config)
updated_dict = analyzer.analyze(asmdef_dict)
report = analyzer.generate_report()
```

**Methods:**
- `analyze(asmdef_dict)`: Analyze all assemblies, return updated dict
- `analyze_assembly(guid, assembly_data)`: Analyze single assembly
- `generate_report()`: Create NamespaceAnalysisReport
- `extract_namespace(code)`: Extract namespace from C# code

#### FileAnalyzer

Maps C# files to their owning assemblies.

```python
from analyzers import FileAnalyzer

analyzer = FileAnalyzer(config)
updated_dict = analyzer.analyze(asmdef_dict)
stats = analyzer.get_stats()
```

**Methods:**
- `analyze(asmdef_dict)`: Scan and map files, return updated dict
- `get_stats()`: Get file mapping statistics
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

### Utilities

#### File I/O

```python
from common import load_asmdef_dict, save_json_report

# Load dictionary
data = load_asmdef_dict("path/to/dict.json")

# Save report
save_json_report(data, "output.json", verbose=True)
```

#### Path Validation

```python
from common import validate_directory

# Validate and resolve path
path = validate_directory("/path/to/dir", error_prefix="Unity Assets")
```

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
