"""Constants used throughout the asmdef analysis toolkit."""

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
