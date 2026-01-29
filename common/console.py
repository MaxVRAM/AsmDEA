"""Rich console configuration for AsmDEA.

Provides a centralized Rich Console instance with configuration for
color output, terminal width, and plain text fallback mode.

Key functions:
    - get_console: Get the shared Console instance
    - configure_console: Configure console settings (call before using reporters)
    - reset_console: Reset console state (for testing)

Usage:
    from common import get_console, configure_console

    # Configure once at startup (optional)
    configure_console(plain=False)

    # Use throughout application
    console = get_console()
    console.print("[success]Operation completed![/]")

The console respects the NO_COLOR environment variable standard.
"""

from __future__ import annotations

import os

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.theme import Theme

# Custom theme for AsmDEA output
ASMDEF_THEME = Theme(
    {
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "info": "cyan",
        "highlight": "bold magenta",
        "muted": "dim",
        "assembly": "bold blue",
        "path": "italic cyan",
        "count": "bold white",
        "cycle": "bold red",
        "no_cycle": "dim",
        "step": "bold cyan",
        "section": "bold white",
    }
)

# Module-level console instance (singleton pattern)
_console: Console | None = None
_plain_mode: bool = False


def get_console() -> Console:
    """Get the shared Rich Console instance.

    Creates a new Console on first call, reuses it thereafter.
    Respects NO_COLOR environment variable and plain mode setting.

    Returns:
        Configured Console for rich output, or plain console if plain mode enabled.
    """
    global _console
    if _console is None:
        # Respect NO_COLOR environment variable (common convention)
        env_no_color = os.environ.get("NO_COLOR", "").lower() in ("1", "true", "yes")
        plain = _plain_mode or env_no_color
        _console = Console(
            theme=ASMDEF_THEME,
            no_color=plain,
            highlight=not plain,
        )
    return _console


def configure_console(plain: bool = False, width: int | None = None) -> Console:
    """Configure and return the Rich Console.

    Call this at application startup to configure console settings.
    If not called, get_console() will create a default console.

    Args:
        plain: Enable plain text mode (no colors, no formatting)
        width: Override terminal width (useful for testing)

    Returns:
        Configured Console instance
    """
    global _console, _plain_mode
    _plain_mode = plain

    # Respect NO_COLOR environment variable even if plain=False
    env_no_color = os.environ.get("NO_COLOR", "").lower() in ("1", "true", "yes")
    effective_plain = plain or env_no_color

    _console = Console(
        theme=ASMDEF_THEME,
        no_color=effective_plain,
        highlight=not effective_plain,
        width=width,
    )
    return _console


def reset_console() -> None:
    """Reset console configuration.

    Clears the singleton console instance. Primarily used for testing
    to ensure clean state between tests.
    """
    global _console, _plain_mode
    _console = None
    _plain_mode = False


def print_section_header(
    title: str,
    step: int | None = None,
    total_steps: int | None = None,
    style: str = "info",
) -> None:
    """Print a styled section header using Rich.

    Creates a visually distinct section header with optional step numbering.
    Use this to clearly separate different phases of analysis.

    Args:
        title: The section title text
        step: Current step number (optional)
        total_steps: Total number of steps (optional)
        style: Rich style to apply (default: 'info')

    Example:
        print_section_header("Building Assembly Dictionary", step=1, total_steps=4)
    """
    console = get_console()

    if step is not None and total_steps is not None:
        header_text = f"Step {step}/{total_steps}: {title}"
    else:
        header_text = title

    console.print()
    console.print(Rule(header_text, style=style, characters="─"))
    console.print()


def print_section_complete(
    message: str,
    success: bool = True,
) -> None:
    """Print a section completion message.

    Args:
        message: Completion message
        success: Whether the section completed successfully
    """
    console = get_console()
    style = "success" if success else "error"
    icon = "✓" if success else "✗"
    console.print(f"[{style}]{icon}[/] {message}")


def print_analysis_header(title: str = "AsmDEA Analysis") -> None:
    """Print the main analysis header panel.

    Args:
        title: Title for the analysis header
    """
    console = get_console()
    console.print()
    console.print(
        Panel(
            f"[bold]{title}[/]\n[muted]Assembly Dependency Enforcement Agency[/]",
            border_style="info",
            padding=(0, 2),
        )
    )
    console.print()


def print_analysis_complete(output_dir: str, success: bool = True) -> None:
    """Print the analysis completion panel.

    Args:
        output_dir: Directory where reports were saved
        success: Whether analysis completed successfully
    """
    console = get_console()
    style = "green" if success else "yellow"
    status = "Complete" if success else "Complete with Issues"

    console.print()
    console.print(
        Panel(
            f"[bold]Analysis {status}[/]\n\n[muted]Reports saved to:[/] [path]{output_dir}[/]",
            border_style=style,
            title="[bold]Summary[/]",
            padding=(1, 2),
        )
    )
    console.print()
