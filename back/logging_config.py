"""Logging configuration helpers."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_CONFIGURED = False


def configure_logging() -> None:
    """Route logs to a file and avoid console output."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    default_log_path = Path(__file__).resolve().parent / "logs" / "app.log"
    log_path = Path(os.getenv("LOG_FILE", str(default_log_path)))
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)

    root.setLevel(log_level)
    root.addHandler(handler)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers = [handler]
        logger.setLevel(log_level)
        logger.propagate = False

    _CONFIGURED = True
