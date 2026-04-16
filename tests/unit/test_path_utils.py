"""Unit tests for common.path_utils module."""

from pathlib import Path

from common.path_utils import FilepathType, format_path, validate_directory


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


class TestFilepathType:
    """Test suite for FilepathType enum parsing."""

    def test_parse_relative(self):
        assert FilepathType.parse("relative") == FilepathType.RELATIVE

    def test_parse_absolute(self):
        assert FilepathType.parse("absolute") == FilepathType.ABSOLUTE

    def test_parse_case_insensitive(self):
        assert FilepathType.parse("ABSOLUTE") == FilepathType.ABSOLUTE
        assert FilepathType.parse(" Relative ") == FilepathType.RELATIVE

    def test_parse_none_uses_default(self):
        assert FilepathType.parse(None) == FilepathType.RELATIVE
        assert FilepathType.parse(None, default=FilepathType.ABSOLUTE) == FilepathType.ABSOLUTE

    def test_parse_empty_uses_default(self):
        assert FilepathType.parse("") == FilepathType.RELATIVE

    def test_parse_unknown_falls_back(self):
        assert FilepathType.parse("bogus") == FilepathType.RELATIVE
        assert (
            FilepathType.parse("bogus", default=FilepathType.ABSOLUTE) == FilepathType.ABSOLUTE
        )


class TestFormatPath:
    """Test suite for format_path()."""

    def test_relative_under_root(self, tmp_path: Path):
        root = tmp_path
        sub = root / "a" / "b" / "file.cs"
        sub.parent.mkdir(parents=True)
        sub.write_text("")

        result = format_path(sub, FilepathType.RELATIVE, root)

        assert result == "a/b/file.cs"

    def test_absolute_returns_posix_absolute(self, tmp_path: Path):
        root = tmp_path
        sub = root / "file.cs"
        sub.write_text("")

        result = format_path(sub, FilepathType.ABSOLUTE, root)

        assert result == sub.resolve().as_posix()
        # Forward slashes, no backslashes.
        assert "\\" not in result

    def test_relative_outside_root_falls_back_to_absolute(self, tmp_path: Path):
        root = tmp_path / "project"
        root.mkdir()
        outside = tmp_path / "outside.cs"
        outside.write_text("")

        result = format_path(outside, FilepathType.RELATIVE, root)

        # Outside paths should not raise; they should be emitted as absolute.
        assert result == outside.resolve().as_posix()

    def test_relative_with_no_root_returns_absolute(self, tmp_path: Path):
        p = tmp_path / "x.cs"
        p.write_text("")

        result = format_path(p, FilepathType.RELATIVE, None)

        assert result == p.resolve().as_posix()

    def test_accepts_string_input(self, tmp_path: Path):
        root = tmp_path
        sub = root / "dir" / "file.cs"
        sub.parent.mkdir()
        sub.write_text("")

        result = format_path(str(sub), FilepathType.RELATIVE, root)

        assert result == "dir/file.cs"

    def test_windows_backslash_input_produces_posix_output(self, tmp_path: Path):
        root = tmp_path
        sub = root / "dir" / "file.cs"
        sub.parent.mkdir()
        sub.write_text("")

        # Simulate a backslash-style string input.
        backslash_input = str(sub).replace("/", "\\")

        result = format_path(backslash_input, FilepathType.RELATIVE, root)

        assert "\\" not in result
        assert result.endswith("dir/file.cs")
