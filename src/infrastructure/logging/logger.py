# src/infrastructure/logging/logger.py
import logging
import sys
from typing import Optional

import structlog
from structlog.types import EventDict, Processor

from src.infrastructure.config.settings import settings


def add_correlation_id(logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add correlation ID to every log entry if available.
    This helps trace requests across the system.
    """
    # We'll add correlation ID later via middleware
    # For now, we just set a default
    if "correlation_id" not in event_dict:
        event_dict["correlation_id"] = "no-correlation-id"
    return event_dict


def setup_logging() -> None:
    """
    Configure structlog for the entire application.
    """
    # Determine if we should use JSON format or plain text
    use_json = settings.logging.json_format

    # List of processors (steps that modify/enrich log entries)
    processors: list[Processor] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        add_correlation_id,
    ]

    # If JSON is enabled, add the JSON renderer at the end
    if use_json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Otherwise use a nice colorized console output
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Also configure standard logging for third-party libraries
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.logging.level.upper()),
        stream=sys.stdout,
    )

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.
    
    Example:
        logger = get_logger(__name__)
        logger.info("Hello world", extra_field="value")
    """
    return structlog.get_logger(name)


    """
What this file does (in simple words):

It sets up logging so that all your log messages are formatted nicely.

If you're in production, it outputs logs as JSON (easier for computers to read).

If you're in development, it outputs colorful text (easier for humans to read).

It adds a correlation_id to each log so you can trace a single request across the system.
    """