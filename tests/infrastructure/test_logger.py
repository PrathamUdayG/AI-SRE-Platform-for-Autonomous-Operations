# tests/infrastructure/test_logger.py
"""Unit tests for the structured logging configuration."""

import pytest
import structlog

from src.infrastructure.logging.logger import (
    configure_logger,
    get_logger,
    setup_logging,
)


def test_setup_logging():
    """Verify that logging setup executes correctly and configures loggers."""
    setup_logging()
    logger = get_logger("test_infra_logger")
    assert logger is not None


def test_configure_logger():
    """Verify that configure_logger executes correctly and configures loggers."""
    configure_logger()
    logger = get_logger("test_configure_logger")
    assert logger is not None


def test_contextvars_logging():
    """Verify context variable support in structured logging."""
    configure_logger()

    # Bind a context variable
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id="test-req-123", user_id="user-456"
    )

    # Retrieve and assert
    ctx = structlog.contextvars.get_contextvars()
    assert ctx.get("request_id") == "test-req-123"
    assert ctx.get("user_id") == "user-456"

    structlog.contextvars.clear_contextvars()
    assert not structlog.contextvars.get_contextvars()
