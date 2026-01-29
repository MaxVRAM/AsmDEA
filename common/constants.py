"""Constants used throughout the asmdef analysis toolkit.

Defines file extensions, default paths, GUID patterns, and enums used across
the Unity Assembly Definition (.asmdef) analysis tools.

Constant categories:
    - File Extensions: ASMDEF_EXTENSION, CS_EXTENSION, META_EXTENSION
    - GUID Patterns: GUID_PREFIX, GUID_META_KEY
    - Default Paths: DEFAULT_DICT_FILE, DEFAULT_OUTPUT_DIR, DEFAULT_REPORTS_DIR
    - Analysis Settings: DEFAULT_TREE_DEPTH, DEFAULT_ALLOW_CHILD_NAMESPACES
    - Metadata: METADATA_KEY
    - Enums: NodeState (for cycle detection states)

Usage:
    from common import ASMDEF_EXTENSION, DEFAULT_DICT_FILE, NodeState

    if file.endswith(ASMDEF_EXTENSION):
        process_asmdef(file)
"""

from enum import Enum
from pathlib import Path

# File extensions
ASMDEF_EXTENSION = ".asmdef"
CS_EXTENSION = ".cs"
META_EXTENSION = ".meta"

# GUID handling
GUID_PREFIX = "GUID:"
GUID_META_KEY = "guid:"

# Default paths
DEFAULT_DICT_FILE = Path("./.work/asmdef_dictionary.json")
DEFAULT_OUTPUT_DIR = Path("./output")
DEFAULT_REPORTS_DIR = Path("./reports")

# Analysis defaults
DEFAULT_TREE_DEPTH = 3
DEFAULT_ALLOW_CHILD_NAMESPACES = True

# Special dictionary keys
METADATA_KEY = "_metadata"


# Node states for cycle detection
class NodeState(Enum):
    """States for DFS cycle detection algorithm."""

    UNVISITED = 0
    VISITING = 1
    VISITED = 2
