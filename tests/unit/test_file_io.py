"""Unit tests for common.file_io module."""

import json
from pathlib import Path

from common.file_io import load_asmdef_dict, save_json_report


class TestFileIO:
    """Test suite for file I/O utilities."""

    def test_load_asmdef_dict_success(self, tmp_path: Path):
        """Test reading a valid JSON file."""
        # Create a test JSON file
        test_file = tmp_path / "test.json"
        test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        test_file.write_text(json.dumps(test_data))

        # Read the file
        result = load_asmdef_dict(test_file)

        assert result == test_data
        assert result["key"] == "value"
        assert result["number"] == 42
        assert result["list"] == [1, 2, 3]

    def test_load_asmdef_dict_with_string_path(self, tmp_path: Path):
        """Test that function accepts string paths."""
        test_file = tmp_path / "test.json"
        test_data = {"name": "Assembly"}
        test_file.write_text(json.dumps(test_data))

        # Pass as string
        result = load_asmdef_dict(str(test_file))

        assert result == test_data

    def test_save_json_report_success(self, tmp_path: Path):
        """Test writing JSON data to a file."""
        test_file = tmp_path / "output.json"
        test_data = {"name": "test", "values": [1, 2, 3]}

        save_json_report(test_data, test_file, verbose=False)

        # Verify the file was created and contains the correct data
        assert test_file.exists()
        with open(test_file) as f:
            loaded_data = json.load(f)
        assert loaded_data == test_data

    def test_save_json_report_creates_directory(self, tmp_path: Path):
        """Test that save_json_report creates parent directories if needed."""
        nested_dir = tmp_path / "nested" / "path"
        test_file = nested_dir / "test.json"
        test_data = {"created": True}

        save_json_report(test_data, test_file, create_dirs=True, verbose=False)

        assert nested_dir.exists()
        assert test_file.exists()
        with open(test_file) as f:
            loaded_data = json.load(f)
        assert loaded_data == test_data

    def test_save_json_report_pretty_format(self, tmp_path: Path):
        """Test that JSON is written with pretty formatting."""
        test_file = tmp_path / "pretty.json"
        test_data = {"key1": "value1", "key2": "value2"}

        save_json_report(test_data, test_file, verbose=False)

        content = test_file.read_text()
        # Pretty-printed JSON should have newlines and indentation
        assert "\n" in content
        assert "  " in content or "\t" in content

    def test_save_json_report_with_string_path(self, tmp_path: Path):
        """Test that function accepts string paths."""
        test_file = tmp_path / "string_path.json"
        test_data = {"type": "string_path"}

        save_json_report(test_data, str(test_file), verbose=False)

        assert test_file.exists()
