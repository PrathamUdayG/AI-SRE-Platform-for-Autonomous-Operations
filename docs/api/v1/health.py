# src/presentation/api/v1/health.py
from fastapi import APIRouter, status

from src.infrastructure.config import settings

# Create a router for health endpoints
router = APIRouter()


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check endpoint",
    description="Returns the status of the application.",
)
async def health_check() -> dict:
    """
    Health check endpoint.
    Returns basic information about the application.
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "environment": settings.app_env,
        "debug_mode": settings.debug,
    }


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness check endpoint",
    description="Returns whether the application is ready to serve traffic.",
)
async def readiness_check() -> dict:
    """
    Readiness check endpoint.
    Used by orchestrators (like Kubernetes) to know when the app is ready.
    """
    # For now, we're always ready
    # Later we'll check database connections, etc.
    return {
        "status": "ready",
        "app": settings.app_name,
    }


"""
What this file does (in simple words):
/health – A simple endpoint that returns {"status": "healthy"}. You'll use this to check if the app is running.

/ready – A readiness endpoint. In the future, this will check if the database is connected before saying "I'm ready".

"""
