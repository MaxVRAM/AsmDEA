# Script Flattener

A utility to flatten directory structures by copying all C# (.cs) files from a source directory to a destination directory, removing the nested folder hierarchy.

## Purpose

This tool is useful when you need to collect all C# source files from a complex project structure into a single flat directory. This can be helpful for:
- Code analysis tools that work better with flat structures
- Creating simplified project views
- Preparing code for processing by external tools

## Usage

### Basic Usage

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
