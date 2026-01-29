"""Custom exceptions for asmdef analysis toolkit.

Defines a hierarchy of exceptions for different error conditions that can
occur during Unity Assembly Definition analysis.

Exception hierarchy:
    AsmdefError (base)
    ├── AsmdefFileNotFoundError: Missing .asmdef file
    ├── InvalidFormatError: Malformed .asmdef or .meta file
    ├── ConfigurationError: Invalid configuration parameters
    └── CyclicDependencyError: Circular assembly references detected

Usage:
    from common import AsmdefFileNotFoundError

    if not asmdef_path.exists():
        raise AsmdefFileNotFoundError(f"File not found: {asmdef_path}")
"""


class AsmdefError(Exception):
    """Base exception for asmdef analysis errors."""

    pass


class AsmdefFileNotFoundError(AsmdefError):
    """Raised when required asmdef files are missing."""

    pass


class InvalidFormatError(AsmdefError):
    """Raised when file format is invalid (e.g., malformed JSON)."""

    pass


class ConfigurationError(AsmdefError):
    """Raised when configuration is invalid."""

    pass


class CyclicDependencyError(AsmdefError):
    """Raised when circular dependencies are detected (if treating as error)."""

    pass
