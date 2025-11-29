"""
logger.py
------------

This logger:
- Prints clear logs to both the console and a file
- Automatically rotates old log files to prevent huge files
- Creates the log directory automatically
- Has consistent, timestamped output
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Final

# Basic config settings
LOG_DIR: Final[Path] = Path('logs')
LOG_FILE: Final[Path] = LOG_DIR / 'general.log'
LOG_LEVEL: Final[int] = logging.DEBUG  # Set the minimum severity level to handle
MAX_BYTES: Final[int] = 5 * 1024 * 1024 # 5 MB maximum file size
BACKUP_COUNT: Final[int] = 5          # Keep up to 5 rotated backup files

def setup_logger(name: str = "app_logger") -> logging.Logger:
    """
    Creates and returns a configured logger instance that handles both console and file output.

    Uses a RotatingFileHandler to manage log file size and an explicit
    formatter to ensure consistent, timestamped output.

    Args:
        name: The name of the logger, typically __name__ from the calling module.
              Defaults to "app_logger".

    Returns:
        A fully configured logging.Logger instance.
    """
    # 1. Ensure the log directory exists
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # 2. Create the Logger object
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    # Setting propagate=False prevents log records from being sent to the
    # root logger, which avoids duplicate log entries if the root logger is also configured.
    logger.propagate = False

    # 3. Prevent duplicate handlers if called multiple times (e.g., in different modules)
    if logger.handlers:
        return logger

    # 4. Define the format for log lines
    # Example format: 2025-11-12 19:30:55 | app_logger | INFO | Starting email fetch process
    log_format = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

    # 5. Console handler (prints logs to the terminal)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 6. File handler (writes logs to log/general.log with rotation)
    file_handler = RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8"
    )
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger