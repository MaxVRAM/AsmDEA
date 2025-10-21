# Script Flattener

A collection of utilities for analyzing Unity assembly definitions (.asmdef) and flattening directory structures.

## Tools

### 1. Assembly Definition Analysis (`asmdef_analyse.py`)

Comprehensive tool for analyzing Unity assembly definitions, detecting cyclic dependencies, and optionally analyzing C# file distribution across assemblies.

#### Features

- Builds a dictionary of all assembly definitions with their metadata
- Detects and reports cyclic dependencies between assemblies
- Optionally analyzes which .cs files belong to each assembly
- Respects nested assembly boundaries (scripts belong to nearest parent asmdef)
- Generates detailed reports with GUID information

#### Usage

```bash
# Basic analysis
python asmdef_analyse.py path/to/unity/project

# With .env configuration
python asmdef_analyse.py

# Analyze with file listing
python asmdef_analyse.py path/to/unity/project --analyze-files --file-report

# Full detailed analysis with output file
python asmdef_analyse.py path/to/unity/project --detailed --analyze-files --file-report --output ./output/report.txt
```

#### Environment Configuration

Create a `.env` file (see `.env.example`):

```env
ROOT_PATH=D:/Development/MyUnityProject
DETAILED=true
DEPTH=3
OUTPUT_PATH=./output/cycle_report.txt
DICT_FILE=./.work/asmdef_dictionary.json
ANALYZE_FILES=true
```

### 2. Assembly File Analyzer (`asmdef_file_analyzer.py`)

Analyzes which .cs files belong to each assembly definition, respecting nested assembly boundaries.

#### Usage

```bash
python asmdef_file_analyzer.py --file asmdef_dictionary.json --root path/to/unity/project --report
```

### 3. Script Flattener (`script_flattener.py`)

```bash
python script_flattener.py
```

This will copy all `.cs` files from the `source/` directory to the `flattened/` directory.

### Custom Directories

```bash
python script_flattener.py --src_dir path/to/source --dest_dir path/to/destination
```

### Arguments

- `--src_dir`: Source directory containing .CS files (default: `source`)
- `--dest_dir`: Destination directory for flattened .CS files (default: `flattened`)

## Requirements

- Python 3.x
- No external dependencies (uses only standard library)

## Example

```bash
# Create source directory and add some C# files in nested folders
mkdir -p source/project1/controllers
mkdir -p source/project2/models
echo "// Controller code" > source/project1/controllers/UserController.cs
echo "// Model code" > source/project2/models/User.cs

# Run the flattener
python script_flattener.py

# Result: both files will be copied to flattened/UserController.cs and flattened/User.cs
```

## Note

If files with the same name exist in different source directories, the last one processed will overwrite the previous ones in the destination directory.
