# src/infrastructure/logging/logger.py
"""Structured logging configuration module using structlog."""

import logging
import sys
from typing import Optional

import structlog
from structlog.types import Processor

from src.infrastructure.config.settings import settings


def configure_logger() -> None:
    """Configures structlog for structured logging across the application.

    Enables JSON logging for production environments and colorized console
    logging for local development. Includes support for context variables,
    log levels, timestamps, logger names, and exception/stack trace rendering.
    """
    # Determine log level from configuration
    log_level_str = settings.log_level.upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Determine if we should use JSON format or plain text
    # Default to JSON in production (when debug is False), unless explicitly overridden
    use_json = (
        settings.log_json if settings.log_json is not None else not settings.debug
    )

    # Base chain of processors to run for all logs
    processors: list[Processor] = [
        # Merge contextvars (context variable support for metadata and future correlation IDs)
        structlog.contextvars.merge_contextvars,
        # Add log level (e.g. info, debug, error)
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add timestamps in ISO format
        structlog.processors.TimeStamper(fmt="iso"),
        # Format exceptions and stack traces
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # Decode binary strings to unicode
        structlog.processors.UnicodeDecoder(),
    ]

    # Configure structlog
    structlog.configure(
        processors=processors
        + [
            # Wrap logs for standard library formatting
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to channel logs through structlog's formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # The ProcessorFormatter formats standard logging logs as well as structlog logs
    formatter = structlog.stdlib.ProcessorFormatter(
        # Processors to run on logs from standard logging library (foreign logs)
        foreign_pre_chain=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
        ],
        # Final renderer processor (either JSON or Console Renderer)
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            (
                structlog.processors.JSONRenderer()
                if use_json
                else structlog.dev.ConsoleRenderer(colors=True)
            ),
        ],
    )
    handler.setFormatter(formatter)

    # Setup the root logger
    root_logger = logging.getLogger()

    # Clear existing handlers to prevent duplicate output
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)


def setup_logging() -> None:
    """Configures structured logging. Backward-compatibility alias for configure_logger."""
    configure_logger()


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """Retrieves a structured logger instance.

    Args:
        name: Optional name for the logger. Typically __name__.

    Returns:
        A structlog BoundLogger instance.
    """
    return structlog.get_logger(name)
