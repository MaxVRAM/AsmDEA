"""Common utilities for asmdef analysis."""

from .asmdef_dict import filter_assemblies, get_metadata, set_metadata
from .backup import BackupInfo, BackupManager, BackupManifest
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
from .console import (
    configure_console,
    get_console,
    print_analysis_complete,
    print_analysis_header,
    print_section_complete,
    print_section_header,
    reset_console,
)
from .logging_config import get_logger, setup_logging
from .path_utils import FilepathType, format_path, validate_directory
from .dictionary import build_asmdef_dictionary

__all__ = [
    # Backup
    "BackupManager",
    "BackupManifest",
    "BackupInfo",
    # Constants
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
    "FilepathType",
    "format_path",
    "filter_assemblies",
    "get_metadata",
    "set_metadata",
    "get_logger",
    "setup_logging",
    "get_console",
    "configure_console",
    "reset_console",
    "print_section_header",
    "print_section_complete",
    "print_analysis_header",
    "print_analysis_complete",
    "build_asmdef_dictionary",
]
