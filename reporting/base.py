"""Base reporter class for consistent reporting interface."""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseReporter(ABC):
    """Base class for all reporters.

    Provides common functionality for console and JSON reporting.
    """

    def __init__(self, verbose: bool = False):
        """Initialize reporter.

        Args:
            verbose: Enable verbose output
        """
        self.verbose = verbose

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
            print(f"Report saved to: {output_path}")
