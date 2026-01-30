"""Base reporter class for consistent reporting interface.

Provides an abstract base class that all reporters inherit from, ensuring
consistent console output, JSON serialization, and file saving across
different analysis types.

Key classes:
    - BaseReporter: Abstract base for all reporter implementations

Subclasses must implement:
    - print_console_report: Format and display results
    - generate_json_report: Convert results to JSON-serializable dict

Usage:
    from reporting import BaseReporter

    class MyReporter(BaseReporter):
        def print_console_report(self, data):
            logger.info("Results: %s", data)

        def generate_json_report(self, data):
            return {"results": data}

    reporter = MyReporter(verbose=True)
    reporter.save_json_report(data, "output.json")
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

from common import get_console, get_logger

if TYPE_CHECKING:
    from rich.console import Console

logger = get_logger(__name__)


class BaseReporter(ABC):
    """Base class for all reporters.

    Provides common functionality for console and JSON reporting.
    """

    def __init__(self, verbose: bool = False, detailed: bool = False, depth: int = 3, console: Console | None = None):
        """Initialize reporter.

        Args:
            verbose: Enable verbose output
            detailed: Enable detailed output (e.g., dependency trees)
            depth: Maximum depth for dependency tree visualization
            console: Rich Console instance (uses shared instance if not provided)
        """
        self.verbose = verbose
        self.detailed = detailed
        self.depth = depth
        self._console = console

    @property
    def console(self) -> Console:
        """Get the Rich Console for output."""
        if self._console is None:
            self._console = get_console()
        return self._console

    @abstractmethod
    def print_console_report(self, data: Any) -> None:
        """Print formatted report to console.

        Args:
            data: Analysis results to report
        """
        pass

    @abstractmethod
    def generate_json_report(self, data: Any) -> dict[str, Any]:
        """Generate JSON-serializable report structure.

        Args:
            data: Analysis results to convert

        Returns:
            Dictionary ready for JSON serialization
        """
        pass

    def save_json_report(self, data: Any, output_path: Path) -> None:
        """Save JSON report to file.

        Args:
            data: Analysis results
            output_path: Path to output JSON file
        """
        report = self.generate_json_report(data)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        if self.verbose:
            logger.info("Report saved to: %s", output_path)
