# tests/infrastructure/test_logger.py
import logging
import pytest
from src.infrastructure.logging.logger import get_logger, setup_logging, set_correlation_id, get_correlation_id

def test_setup_logging():
    """Verify that logging setup executes correctly and configures loggers."""
    setup_logging()
    logger = get_logger("test_infra_logger")
    assert logger is not None

def test_correlation_id():
    """Verify context-based correlation ID propagation."""
    set_correlation_id("test-correlation-123")
    assert get_correlation_id() == "test-correlation-123"
    
    set_correlation_id(None)
    assert get_correlation_id() is None
