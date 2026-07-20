# tests/application/test_metric_service.py
"""Unit tests for the MetricService class."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.services.metric_service import MetricService
from src.domain.entities.metric import Metric
from src.domain.exceptions import ValidationError


@pytest.mark.asyncio
async def test_create_metric_success():
    """Verify that a valid metric is created successfully."""
    repo = MagicMock()

    def mock_save(m):
        m.id = 123
        return m

    repo.save = AsyncMock(side_effect=mock_save)

    service = MetricService(repo)
    metric = await service.create_metric(
        name="memory.usage",
        value=64.8,
        service="web-service",
        tags={"env": "staging"},
    )

    assert metric.id == 123
    assert metric.name == "memory.usage"
    assert metric.value == 64.8
    assert metric.service == "web-service"
    assert metric.tags == {"env": "staging"}
    repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_create_metric_validation_failures():
    """Verify validation triggers error on missing fields."""
    repo = MagicMock()
    service = MetricService(repo)

    # Empty name
    with pytest.raises(ValidationError) as exc:
        await service.create_metric(
            name=" ",
            value=10.0,
            service="some-service",
        )
    assert "Metric name cannot be empty" in str(exc.value)

    # Empty service
    with pytest.raises(ValidationError) as exc:
        await service.create_metric(
            name="cpu",
            value=10.0,
            service="",
        )
    assert "Service name cannot be empty" in str(exc.value)
