# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Centralized logging configuration for FDO use cases package.

This module provides a unified logging setup with:
- Colored console output (DEBUG=blue, INFO=green, WARNING=yellow, ERROR=red)
- File logging to fdo_usecases.log
- Simple format with module name and log level
- Configurable via parameter or LOG_LEVEL environment variable
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

from colorama import Fore, Style
from colorama import init as colorama_init


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels for console output.

    Attributes:
        COLORS: Mapping of log levels to colorama foreground colors

    """

    COLORS = {
        logging.DEBUG: Fore.BLUE,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    def __init__(self, fmt: str, datefmt: Optional[str] = None):  # noqa: D107
        super().__init__(fmt, datefmt)
        colorama_init(autoreset=True)

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with color based on log level."""
        color = self.COLORS.get(record.levelno, "")
        reset = Style.RESET_ALL
        record.levelname = f"{color}{record.levelname}{reset}"
        return super().format(record)


def setup_logging(
    level: Optional[int] = None,
    log_file: Optional[str] = None,
    log_dir: Optional[Path] = None,
) -> None:
    """Configure package-wide logging with colored console output and file logging.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               If None, uses LOG_LEVEL env var or defaults to INFO.
        log_file: Optional filename for log file. Defaults to "fdo_usecases.log".
        log_dir: Optional directory for log file. Defaults to current working directory.

    Example:
        ```python
        from fdo_usecases.utils.logging_config import setup_logging
        import logging

        setup_logging(level=logging.DEBUG)
        logger = logging.getLogger(__name__)
        logger.info("Logging configured")
        ```

    """
    # Determine log level from parameter or environment variable
    if level is None:
        level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)

    # Get root logger for fdo_usecases package
    root_logger = logging.getLogger("fdo_usecases")
    root_logger.setLevel(level)

    # Avoid duplicate handlers on re-initialization
    if root_logger.handlers:
        return

    # Simple format with module name
    format_string = "[%(name)s] %(levelname)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = ColoredFormatter(format_string, date_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file is None:
        log_file = "fdo_usecases.log"

    if log_dir is None:
        log_dir = Path.cwd()
    else:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

    log_path = log_dir / log_file
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(format_string, date_format)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Log initialization message
    root_logger.info(f"Logging initialized at level {logging.getLevelName(level)}")
    root_logger.debug(f"Log file: {log_path}")


__all__ = ["setup_logging", "ColoredFormatter"]
