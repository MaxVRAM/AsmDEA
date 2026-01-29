"""Unit tests for common.constants module."""

import pytest
from pathlib import Path
from common.constants import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_DICT_FILE,
    DEFAULT_REPORTS_DIR,
    ASMDEF_EXTENSION,
    CS_EXTENSION,
    META_EXTENSION,
    GUID_PREFIX,
    NodeState,
)


class TestConstants:
    """Test suite for common constants."""

    def test_default_output_dir_exists(self):
        """Test that DEFAULT_OUTPUT_DIR constant is defined."""
        assert DEFAULT_OUTPUT_DIR is not None
        assert isinstance(DEFAULT_OUTPUT_DIR, Path)
        assert str(DEFAULT_OUTPUT_DIR) == "output"

    def test_default_reports_dir_exists(self):
        """Test that DEFAULT_REPORTS_DIR constant is defined."""
        assert DEFAULT_REPORTS_DIR is not None
        assert isinstance(DEFAULT_REPORTS_DIR, Path)
        assert str(DEFAULT_REPORTS_DIR) == "reports"

    def test_default_dict_file_exists(self):
        """Test that DEFAULT_DICT_FILE constant is defined."""
        assert DEFAULT_DICT_FILE is not None
        assert isinstance(DEFAULT_DICT_FILE, Path)

    def test_file_extensions_defined(self):
        """Test that file extension constants are defined."""
        assert ASMDEF_EXTENSION == ".asmdef"
        assert CS_EXTENSION == ".cs"
        assert META_EXTENSION == ".meta"

    def test_guid_prefix_defined(self):
        """Test that GUID_PREFIX constant is defined."""
        assert GUID_PREFIX is not None
        assert isinstance(GUID_PREFIX, str)
        assert GUID_PREFIX == "GUID:"

    def test_node_state_enum_values(self):
        """Test that NodeState enum has correct values."""
        assert NodeState.UNVISITED.value == 0
        assert NodeState.VISITING.value == 1
        assert NodeState.VISITED.value == 2
