"""Centralized logging configuration for the ScriptFlattener project.

This module provides a consistent logging setup across all modules with:
- Configurable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Console output with color-coded messages
- Optional file logging with rotation
- Structured log format with timestamps

Usage:
    from common.logging_config import get_logger

    logger = get_logger(__name__)
    logger.info("Processing asmdef files...")
    logger.warning("Missing namespace in file")
    logger.error("Failed to load file", exc_info=True)
"""

import logging
import sys
from pathlib import Path

# Default log format with timestamp, level, module, and message
DEFAULT_FORMAT = "%(asctime)s - %(levelname)-8s - %(name)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Global flag to track if logging has been configured
_logging_configured = False


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    file_level: str | None = None,
    console: bool = True,
) -> None:
    """Configure logging for the entire application.

    This should be called once at application startup. Subsequent calls
    will be ignored unless you explicitly reset the configuration.

    Args:
        level: Console log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file. If None, no file logging
        file_level: Log level for file output. If None, uses same as console
        console: Whether to enable console logging (default: True)

    Example:
        # Console only (default)
        setup_logging(level="INFO")

        # Console + file
        setup_logging(level="INFO", log_file="logs/analysis.log")

        # Debug to file, info to console
        setup_logging(level="INFO", log_file="logs/debug.log", file_level="DEBUG")
    """
    global _logging_configured

    if _logging_configured:
        return

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything, handlers will filter

    # Remove any existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(DEFAULT_FORMAT, datefmt=DATE_FORMAT)

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(getattr(logging, (file_level or level).upper()))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    _logging_configured = True


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    Args:
        name: Logger name, typically __name__ of the calling module

    Returns:
        Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Starting analysis...")
    """
    # Ensure logging is configured with defaults if not already done
    if not _logging_configured:
        setup_logging()

    return logging.getLogger(name)


def reset_logging() -> None:
    """Reset logging configuration.

    Useful for testing or when you need to reconfigure logging.
    """
    global _logging_configured
    _logging_configured = False

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.WARNING)
