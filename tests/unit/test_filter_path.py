"""Tests for FILTER_PATH segment matching in apply_filters and FileAnalyser."""

from pathlib import Path
from typing import Any

import pytest

from common.asmdef_dict import apply_filters
from analysers.file_analyser import FileAnalyser


def _make_dict(*entries: tuple[str, str, str]) -> dict[str, Any]:
    """Build a minimal asmdef dict from (guid, name, relativePath) tuples."""
    return {guid: {"name": name, "rootNamespace": name, "references": [], "relativePath": path} for guid, name, path in entries}


class TestApplyFiltersPath:
    """Tests for the filter_path parameter of apply_filters."""

    def _apply(self, asmdef_dict: dict, paths: list[str]) -> dict:
        return apply_filters(asmdef_dict, filter_root=[], filter_any=[], filter_path=paths)

    def test_prefix_match(self):
        d = _make_dict(("g1", "A", "Library/PackageCache/com.foo"), ("g2", "B", "Assets/Scripts"))
        result = self._apply(d, ["Library/PackageCache"])
        assert "g1" not in result
        assert "g2" in result

    def test_exact_match(self):
        d = _make_dict(("g1", "A", "Library/PackageCache"), ("g2", "B", "Assets/Scripts"))
        result = self._apply(d, ["Library/PackageCache"])
        assert "g1" not in result
        assert "g2" in result

    def test_mid_path_match(self):
        """Filter segment appearing in the middle of the path."""
        d = _make_dict(("g1", "A", "SomeRoot/Library/PackageCache/com.foo"), ("g2", "B", "Assets/Scripts"))
        result = self._apply(d, ["Library/PackageCache"])
        assert "g1" not in result
        assert "g2" in result

    def test_suffix_match(self):
        """Filter segment matching at the end of the path."""
        d = _make_dict(("g1", "A", "SomeRoot/Library/PackageCache"), ("g2", "B", "Assets/Scripts"))
        result = self._apply(d, ["Library/PackageCache"])
        assert "g1" not in result
        assert "g2" in result

    def test_no_partial_segment_match(self):
        """PackageCache2 must NOT be excluded by a filter for PackageCache."""
        d = _make_dict(("g1", "A", "Library/PackageCache2"), ("g2", "B", "Library/PackageCache"))
        result = self._apply(d, ["Library/PackageCache"])
        assert "g1" in result
        assert "g2" not in result

    def test_multiple_filters(self):
        d = _make_dict(
            ("g1", "A", "Library/PackageCache/com.foo"),
            ("g2", "B", "Assets/Plugins/Vendor"),
            ("g3", "C", "Assets/Scripts"),
        )
        result = self._apply(d, ["Library/PackageCache", "Assets/Plugins"])
        assert "g1" not in result
        assert "g2" not in result
        assert "g3" in result

    def test_empty_filter_passes_all(self):
        d = _make_dict(("g1", "A", "Library/PackageCache/com.foo"))
        result = self._apply(d, [])
        assert "g1" in result

    def test_metadata_preserved(self):
        d = _make_dict(("g1", "A", "Library/PackageCache/com.foo"))
        d["_metadata"] = {"generated": "2026-01-01"}
        result = self._apply(d, ["Library/PackageCache"])
        assert "_metadata" in result

    def test_windows_backslash_paths(self):
        d = _make_dict(("g1", "A", "Library\\PackageCache\\com.foo"))
        result = self._apply(d, ["Library/PackageCache"])
        assert "g1" not in result


class TestIsFilteredPath:
    """Tests for FileAnalyser._is_filtered_path."""

    def _analyser(self, filter_paths: list[str], tmp_path: Path) -> FileAnalyser:
        return FileAnalyser({}, tmp_path, filter_paths=filter_paths)

    def test_prefix_match(self, tmp_path):
        fa = self._analyser(["Library/PackageCache"], tmp_path)
        assert fa._is_filtered_path("Library/PackageCache/com.foo") is True

    def test_exact_match(self, tmp_path):
        fa = self._analyser(["Library/PackageCache"], tmp_path)
        assert fa._is_filtered_path("Library/PackageCache") is True

    def test_mid_path_match(self, tmp_path):
        fa = self._analyser(["Library/PackageCache"], tmp_path)
        assert fa._is_filtered_path("Outer/Library/PackageCache/Inner") is True

    def test_suffix_match(self, tmp_path):
        fa = self._analyser(["Library/PackageCache"], tmp_path)
        assert fa._is_filtered_path("Outer/Library/PackageCache") is True

    def test_no_partial_segment_match(self, tmp_path):
        fa = self._analyser(["PackageCache"], tmp_path)
        assert fa._is_filtered_path("Library/PackageCache2") is False

    def test_no_match(self, tmp_path):
        fa = self._analyser(["Library/PackageCache"], tmp_path)
        assert fa._is_filtered_path("Assets/Scripts") is False

    def test_empty_filters(self, tmp_path):
        fa = self._analyser([], tmp_path)
        assert fa._is_filtered_path("Library/PackageCache") is False
