"""Subprocess execution utilities for running analysis scripts."""

import sys
import subprocess
from pathlib import Path
from typing import List


class ScriptRunner:
    """Executes Python scripts as subprocesses with consistent error handling."""

    def __init__(self, script_dir: Path):
        """
        Initialize script runner.

        Args:
            script_dir: Directory containing scripts to run
        """
        self.script_dir = Path(script_dir)

    def run(
        self, script_name: str, args: List[str], step_description: str, check: bool = True
    ) -> subprocess.CompletedProcess:
        """
        Execute a Python script as subprocess.

        Args:
            script_name: Name of script file (e.g., "asmdef_dictionary.py")
            args: Command-line arguments to pass
            step_description: Human-readable action description for errors
            check: Raise exception on non-zero exit code

        Returns:
            CompletedProcess instance

        Raises:
            FileNotFoundError: If script doesn't exist
            RuntimeError: If script execution fails and check=True
        """
        script_path = self.script_dir / script_name
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")

        try:
            return subprocess.run(
                [sys.executable, str(script_path)] + args, check=check, capture_output=False, text=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to {step_description} (exit code {e.returncode})") from e
