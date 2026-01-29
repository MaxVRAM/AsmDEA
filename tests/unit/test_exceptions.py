"""Unit tests for common.exceptions module."""

import pytest

from common.exceptions import (
    AsmdefError,
    AsmdefFileNotFoundError,
    ConfigurationError,
    CyclicDependencyError,
    InvalidFormatError,
)


class TestExceptions:
    """Test suite for custom exceptions."""

    def test_asmdef_error_is_base(self):
        """Test that AsmdefError is the base exception."""
        error = AsmdefError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_file_not_found_error_inheritance(self):
        """Test that AsmdefFileNotFoundError inherits from AsmdefError."""
        error = AsmdefFileNotFoundError("test.asmdef not found")
        assert isinstance(error, AsmdefError)
        assert isinstance(error, Exception)
        assert "test.asmdef" in str(error)

    def test_invalid_format_error_inheritance(self):
        """Test that InvalidFormatError inherits from AsmdefError."""
        error = InvalidFormatError("Invalid JSON format")
        assert isinstance(error, AsmdefError)
        assert isinstance(error, Exception)
        assert "Invalid JSON" in str(error)

    def test_configuration_error_inheritance(self):
        """Test that ConfigurationError inherits from AsmdefError."""
        error = ConfigurationError("Invalid configuration")
        assert isinstance(error, AsmdefError)
        assert isinstance(error, Exception)
        assert "configuration" in str(error)

    def test_cyclic_dependency_error_inheritance(self):
        """Test that CyclicDependencyError inherits from AsmdefError."""
        error = CyclicDependencyError("Cycle detected: A -> B -> C -> A")
        assert isinstance(error, AsmdefError)
        assert isinstance(error, Exception)
        assert "Cycle" in str(error)

    def test_can_catch_specific_exceptions(self):
        """Test that specific exceptions can be caught."""
        with pytest.raises(AsmdefFileNotFoundError):
            raise AsmdefFileNotFoundError("test.asmdef")

        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Invalid config")

    def test_can_catch_base_exception(self):
        """Test that base exception can catch all custom exceptions."""
        with pytest.raises(AsmdefError):
            raise AsmdefFileNotFoundError("test.asmdef")

        with pytest.raises(AsmdefError):
            raise InvalidFormatError("Bad format")

        with pytest.raises(AsmdefError):
            raise CyclicDependencyError("Cycle found")
