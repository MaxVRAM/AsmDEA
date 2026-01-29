"""Common utilities for asmdef analysis."""

from .asmdef_dict import filter_assemblies, get_metadata, set_metadata
from .constants import (
    ASMDEF_EXTENSION,
    CS_EXTENSION,
    DEFAULT_ALLOW_CHILD_NAMESPACES,
    DEFAULT_DICT_FILE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_REPORTS_DIR,
    DEFAULT_TREE_DEPTH,
    GUID_META_KEY,
    GUID_PREFIX,
    META_EXTENSION,
    METADATA_KEY,
    NodeState,
)
from .exceptions import (
    AsmdefError,
    AsmdefFileNotFoundError,
    ConfigurationError,
    CyclicDependencyError,
    InvalidFormatError,
)
from .file_io import load_asmdef_dict, save_json_report
from .console import configure_console, get_console, reset_console
from .logging_config import get_logger, setup_logging
from .path_utils import validate_directory
from .dictionary import build_asmdef_dictionary

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
    "AsmdefError",
    "AsmdefFileNotFoundError",
    "InvalidFormatError",
    "ConfigurationError",
    "CyclicDependencyError",
    "load_asmdef_dict",
    "save_json_report",
    "validate_directory",
    "filter_assemblies",
    "get_metadata",
    "set_metadata",
    "get_logger",
    "setup_logging",
    "get_console",
    "configure_console",
    "reset_console",
    "build_asmdef_dictionary",
]
