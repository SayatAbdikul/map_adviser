"""Environment-aware logging configuration."""

from __future__ import annotations

import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Iterable

_CONFIGURED = False


def _clear_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)


def _build_stream_handler(level: str) -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    handler.setLevel(level)
    return handler


def _build_file_handler(path: Path, level: str, json_format: bool) -> logging.Handler:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    if json_format:
        fmt = (
            '{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s",'
            '"msg":"%(message)s","module":"%(module)s","line":%(lineno)d}'
        )
    else:
        fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    handler.setLevel(level)
    return handler


def _wire_library_loggers(handler: logging.Handler, level: str, names: Iterable[str]) -> None:
    for name in names:
        logger = logging.getLogger(name)
        _clear_handlers(logger)
        logger.setLevel(level)
        logger.addHandler(handler)
        logger.propagate = False


def configure_logging() -> None:
    """
    Configure logging with dev/prod presets.

    Env vars:
    - APP_ENV=dev|prod (default: dev)
    - LOG_LEVEL (default: INFO)
    - LOG_FILE (prod only, default: back/logs/app.log)
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    env = os.getenv("APP_ENV", "dev").lower()
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    root = logging.getLogger()
    _clear_handlers(root)
    root.setLevel(log_level)

    default_log_path = Path(__file__).resolve().parent / "logs" / "app.log"
    log_path = Path(os.getenv("LOG_FILE", str(default_log_path)))
    file_handler = _build_file_handler(log_path, log_level, json_format=True)
    root.addHandler(file_handler)
    _wire_library_loggers(file_handler, log_level, ("uvicorn", "uvicorn.error", "uvicorn.access"))

    _CONFIGURED = True
