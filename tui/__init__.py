"""TUI module for AsmDEA - Textual-based user interface.

This module provides an interactive terminal UI for analyzing Unity Assembly
Definitions, viewing cycle reports, namespace compliance, and file mappings.

Main entry point:
    from tui import AsmDEAApp
    app = AsmDEAApp()
    app.run()
"""

from .app import AsmDEAApp

__all__ = ["AsmDEAApp"]
