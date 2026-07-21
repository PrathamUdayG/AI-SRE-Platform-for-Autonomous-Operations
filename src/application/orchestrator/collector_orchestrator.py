"""
-------------------------------------------------------
File:
collector_orchestrator.py

Purpose:
Orchestrates execution cycles for registered collectors.

Why this file exists:
Acts as the central engine managing telemetry collection runs. It coordinates commands, manages execution modes (sequential vs parallel), and isolates collector failures so one failing collector does not halt the entire cycle.

Responsibilities:
- Run a single named collector with error isolation.
- Run all registered collectors sequentially.
- Run all registered collectors in parallel using asyncio.gather.
- Collect and return lists of CollectorResults.

Used By:
- Agent Run loop / scheduler

Depends On:
- src.application.orchestrator.collector_registry.CollectorRegistry
- src.domain.collectors.collector_result.CollectorResult
- src.domain.collectors.collector_status.CollectorStatus
- src.domain.interfaces.connectors.ICommandExecutor
-------------------------------------------------------
"""

import asyncio
from datetime import datetime, timezone
import time
from typing import List
import structlog

from src.application.orchestrator.collector_registry import CollectorRegistry
from src.domain.collectors.collector_result import CollectorResult
from src.domain.collectors.collector_status import CollectorStatus
from src.domain.collectors.metric_type import MetricType
from src.domain.interfaces.connectors import ICommandExecutor

logger = structlog.get_logger(__name__)


class CollectorOrchestrator:
    """
    Why this class exists:
    Executes and coordinates telemetry collection routines in the Application layer.

    Responsibility:
    Safeguards run cycles by trapping collector crashes, measuring run times,
    and managing parallel/sequential scheduling.

    Who uses it:
    Agent scheduling daemon or ad-hoc diagnostic runner.
    """

    def __init__(self, registry: CollectorRegistry) -> None:
        """
        Initialize CollectorOrchestrator with a collector registry.

        Args:
            registry (CollectorRegistry): Dynamic registry storing active collectors.
        """
        self._registry = registry

    async def run_collector(self, name: str, executor: ICommandExecutor) -> CollectorResult:
        """
        Execute a single collector by name, capturing any unhandled exceptions safely.

        Args:
            name (str): Name of collector to run.
            executor (ICommandExecutor): System command executor to pass to the collector.

        Returns:
            CollectorResult: Structured result of execution or crash metadata.
        """
        start_time = time.perf_counter()
        timestamp = datetime.now(timezone.utc)

        try:
            collector = self._registry.get(name)
        except Exception as err:
            logger.error("Failed to fetch collector for run", collector=name, error=str(err))
            execution_time_ms = int((time.perf_counter() - start_time) * 1000)
            return CollectorResult(
                timestamp=timestamp,
                hostname="unknown",
                collector_name=name,
                metric_type=MetricType.LOG,
                payload={},
                status=CollectorStatus.FAILED,
                errors=[f"Failed to retrieve collector: {str(err)}"],
                execution_time_ms=execution_time_ms,
            )

        try:
            logger.info("Executing collector", collector=name)
            return await collector.collect(executor)
        except Exception as e:
            logger.error("Collector raised unhandled exception during execute", collector=name, error=str(e))
            execution_time_ms = int((time.perf_counter() - start_time) * 1000)
            return CollectorResult(
                timestamp=timestamp,
                hostname="unknown",
                collector_name=name,
                metric_type=collector.metric_type,
                payload={},
                status=CollectorStatus.FAILED,
                errors=[f"Unhandled exception during collection: {str(e)}"],
                execution_time_ms=execution_time_ms,
            )

    async def run_all(self, executor: ICommandExecutor) -> List[CollectorResult]:
        """
        Execute all registered collectors sequentially.

        Args:
            executor (ICommandExecutor): Executor passed to collectors.

        Returns:
            List[CollectorResult]: Collected results of all executions.
        """
        results: List[CollectorResult] = []
        for collector in self._registry.list():
            result = await self.run_collector(collector.name, executor)
            results.append(result)
        return results

    async def run_parallel(self, executor: ICommandExecutor) -> List[CollectorResult]:
        """
        Execute all registered collectors concurrently using asyncio.gather.

        Args:
            executor (ICommandExecutor): Executor passed to collectors.

        Returns:
            List[CollectorResult]: Collected results of all executions.
        """
        collectors = self._registry.list()
        if not collectors:
            return []

        tasks = [self.run_collector(c.name, executor) for c in collectors]
        logger.info("Starting parallel telemetry collection", count=len(tasks))
        results = await asyncio.gather(*tasks)
        return list(results)
