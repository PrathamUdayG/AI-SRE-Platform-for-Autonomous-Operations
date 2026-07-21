"""
-------------------------------------------------------
File:
test_collector_registry.py

Purpose:
Unit tests for the CollectorRegistry in the Application Layer.

Why this file exists:
Verifies that the registry safely controls collector lifecycle, prevents name collisions, returns exact collector instances, and reports clean errors when lookups fail.

Responsibilities:
- Verify successful collector registration and exists check.
- Verify duplicate registration raises ConflictError.
- Verify unregistering removes target collector.
- Verify unregistering non-existent name raises NotFoundError.
- Verify retrieval of specific collectors.
- Verify listing of active registry contents.

Used By:
- pytest runner

Depends On:
- src.application.orchestrator.collector_registry.CollectorRegistry
- src.domain.collectors.collector.Collector
-------------------------------------------------------
"""

from unittest.mock import MagicMock
import pytest

from src.application.orchestrator.collector_registry import CollectorRegistry
from src.domain.collectors.collector import Collector
from src.domain.exceptions import ConflictError, NotFoundError


@pytest.fixture
def registry():
    return CollectorRegistry()


@pytest.fixture
def mock_collector():
    col = MagicMock(spec=Collector)
    col.name = "MockCollector"
    col.metric_type = "MOCK"
    return col


def test_register_and_exists(registry, mock_collector):
    """Verify standard registration and exists query."""
    assert not registry.exists("MockCollector")
    registry.register(mock_collector)
    assert registry.exists("MockCollector")
    assert registry.get("MockCollector") is mock_collector


def test_register_duplicate_raises_conflict(registry, mock_collector):
    """Verify duplicate registrations raise ConflictError."""
    registry.register(mock_collector)
    with pytest.raises(ConflictError) as excinfo:
        registry.register(mock_collector)
    assert "already registered" in str(excinfo.value)


def test_unregister(registry, mock_collector):
    """Verify removing a collector deletes it from lookup tables."""
    registry.register(mock_collector)
    assert registry.exists("MockCollector")
    
    registry.unregister("MockCollector")
    assert not registry.exists("MockCollector")


def test_unregister_missing_raises_not_found(registry):
    """Verify unregistering missing items raises NotFoundError."""
    with pytest.raises(NotFoundError) as excinfo:
        registry.unregister("MissingCollector")
    assert "not registered" in str(excinfo.value)


def test_get_missing_raises_not_found(registry):
    """Verify retrieval of missing items raises NotFoundError."""
    with pytest.raises(NotFoundError) as excinfo:
        registry.get("MissingCollector")
    assert "not registered" in str(excinfo.value)


def test_list_collectors(registry):
    """Verify listing all active collectors."""
    assert len(registry.list()) == 0

    col1 = MagicMock(spec=Collector)
    col1.name = "Col1"
    
    col2 = MagicMock(spec=Collector)
    col2.name = "Col2"

    registry.register(col1)
    registry.register(col2)

    lst = registry.list()
    assert len(lst) == 2
    assert col1 in lst
    assert col2 in lst
