"""Common utilities for asmdef analysis."""

from .constants import (
    ASMDEF_EXTENSION,
    CS_EXTENSION,
    META_EXTENSION,
    GUID_PREFIX,
    GUID_META_KEY,
    DEFAULT_DICT_FILE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_REPORTS_DIR,
    DEFAULT_TREE_DEPTH,
    DEFAULT_ALLOW_CHILD_NAMESPACES,
    METADATA_KEY,
    NodeState,
)
from .file_io import load_asmdef_dict, save_json_report
from .path_utils import validate_directory

__all__ = [
    "ASMDEF_EXTENSION",
    "CS_EXTENSION",
    "META_EXTENSION",
    "GUID_PREFIX",
    "GUID_META_KEY",
    "DEFAULT_DICT_FILE",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_REPORTS_DIR",
    "DEFAULT_TREE_DEPTH",
    "DEFAULT_ALLOW_CHILD_NAMESPACES",
    "METADATA_KEY",
    "NodeState",
    "load_asmdef_dict",
    "save_json_report",
    "validate_directory",
]
