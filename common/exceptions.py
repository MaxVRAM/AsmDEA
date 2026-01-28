"""Custom exceptions for asmdef analysis toolkit."""


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
