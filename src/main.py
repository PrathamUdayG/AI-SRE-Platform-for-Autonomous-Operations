# src/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infrastructure.config import settings
from src.infrastructure.logging.logger import setup_logging, get_logger
from src.presentation.api.v1 import health

# Setup logging first
setup_logging()
logger = get_logger(__name__)

# Create the FastAPI application
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI SRE Platform for Autonomous Operations",
    debug=settings.debug,
)

# Add CORS middleware (allows other domains to call our API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "environment": settings.app_env,
        "docs": "/docs",
    }

# Log startup
logger.info(
    "Application starting",
    app_name=settings.app_name,
    environment=settings.app_env,
    debug=settings.debug,
)

"""
What this file does (in simple words):
Creates the main FastAPI application.

Sets up logging.

Connects the health check endpoints we created.

Adds a root endpoint (/) that gives a welcome message.

The app will automatically generate API documentation at /docs.
"""