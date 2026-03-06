"""
Structured JSON logging configuration with tenant context.

Usage:
    from app.logging_config import setup_logging
    setup_logging()  # Call once at startup (main.py)

All loggers then output JSON lines with tenant_id when available.
"""

import json
import logging
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Produce one JSON object per log line with structured fields."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add tenant_id from Flask g if available
        try:
            from flask import g
            tenant = getattr(g, "tenant_id", None)
            if tenant:
                log_entry["tenant_id"] = tenant
            user = getattr(g, "user", None)
            if user and isinstance(user, dict):
                log_entry["user_id"] = user.get("id")
        except (RuntimeError, ImportError):
            pass  # Outside request context or Flask not installed

        # Add extra fields
        if hasattr(record, "extra_data") and record.extra_data:
            log_entry.update(record.extra_data)

        # Add exception info
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add source location for warnings and above
        if record.levelno >= logging.WARNING:
            log_entry["source"] = f"{record.pathname}:{record.lineno}"

        return json.dumps(log_entry, default=str)


def setup_logging(level: str = "INFO"):
    """Configure root logger with JSON output.

    Call once at app startup. In DEBUG mode, uses a simpler format
    for readability; in production, uses JSON.
    """
    from app.config import settings

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if settings.DEBUG:
        # Human-readable format for development
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
            datefmt="%H:%M:%S",
        ))
    else:
        # JSON format for production (structured logging)
        handler.setFormatter(JSONFormatter())

    root.addHandler(handler)

    # Quiet down noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
