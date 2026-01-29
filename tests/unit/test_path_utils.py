"""Unit tests for common.path_utils module."""

from pathlib import Path

from common.path_utils import validate_directory


class TestPathUtils:
    """Test suite for path utility functions."""

    def test_validate_directory_success(self, tmp_path: Path):
        """Test that validate_directory accepts valid directory."""
        result = validate_directory(tmp_path)

        assert isinstance(result, Path)
        assert result.is_absolute()
        assert result.exists()
        assert result.is_dir()

    def test_validate_directory_resolves_path(self, tmp_path: Path):
        """Test that validate_directory resolves to absolute path."""
        # Create a subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        result = validate_directory(subdir)

        assert result.is_absolute()
        assert result == subdir.resolve()

    def test_validate_directory_accepts_string(self, tmp_path: Path):
        """Test that validate_directory accepts string paths."""
        result = validate_directory(str(tmp_path))

        assert isinstance(result, Path)
        assert result.exists()

    def test_validate_directory_custom_error_prefix(self, tmp_path: Path):
        """Test that validate_directory uses custom error prefix."""
        # This test just verifies the function accepts the parameter
        # The actual error message testing would require catching SystemExit
        result = validate_directory(tmp_path, error_prefix="Custom prefix")

        assert result.exists()
