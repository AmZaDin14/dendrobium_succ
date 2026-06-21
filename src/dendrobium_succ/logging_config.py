"""Logging configuration for dendrobium_succ.

Hybrid logging: pretty console output (rich) + structured JSON file (machine-parseable).

Usage:
    from .logging_config import setup_logging, get_logger

    setup_logging(level="INFO", log_file="data/processed/run.log")
    logger = get_logger(__name__)
    logger.info("Pipeline started", extra={"input": "proteins.faa"})

JSON log format (one entry per line):
    {"timestamp": "2026-06-21T10:30:45.123456", "level": "INFO", "message": "...", ...}
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from rich.logging import RichHandler


class JSONFormatter(logging.Formatter):
    """Format log records as JSON lines for machine parsing."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, "duration"):
            log_entry["duration"] = record.duration
        if hasattr(record, "url"):
            log_entry["url"] = record.url
        if hasattr(record, "status_code"):
            log_entry["status_code"] = record.status_code
        if hasattr(record, "input_path"):
            log_entry["input_path"] = str(record.input_path)
        if hasattr(record, "output_path"):
            log_entry["output_path"] = str(record.output_path)
        if hasattr(record, "count"):
            log_entry["count"] = record.count
        if hasattr(record, "size_mb"):
            log_entry["size_mb"] = record.size_mb

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(
    level: str = "INFO",
    log_file: str | Path | None = "data/processed/run.log",
) -> None:
    """Configure hybrid logging: rich console + JSON file.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Path to JSON log file. If None, no file logging.
            Default: data/processed/run.log
    """
    # Get root logger
    root_logger = logging.getLogger("dendrobium_succ")
    root_logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler (rich, pretty output)
    console_handler = RichHandler(
        level=level.upper(),
        show_time=True,
        show_level=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(console_handler)

    # File handler (JSON, structured)
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setLevel(level.upper())
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)

        # Log initial metadata
        root_logger.info(
            "Logging initialized",
            extra={
                "log_level": level,
                "log_file": str(log_file),
                "python_version": sys.version,
            },
        )


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a module.

    Args:
        name: Module name (typically __name__).

    Returns:
        Logger instance.
    """
    return logging.getLogger(f"dendrobium_succ.{name}")
