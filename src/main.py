# src/main.py
# Why: Main entrypoint of the FastAPI application. Sets up routes,
# metadata, and global handlers including centralized exception handling
# to map domain exceptions to proper HTTP responses.

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.domain.exceptions import (
    ConflictError,
    DomainError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from src.presentation.api.v1 import router as v1_router
from src.presentation.api.v1.health import router as health_router

app = FastAPI(
    title="AI_SRE Platform",
    description="Autonomous SRE with AI",
    version="0.1.0",
)


# Centralized exception handler for DomainError
@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(exc, NotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ValidationError):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, ConflictError):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, UnauthorizedError):
        status_code = status.HTTP_401_UNAUTHORIZED

    return JSONResponse(status_code=status_code, content=exc.to_dict())


# Mount routes
app.include_router(health_router)  # /health and /health/readiness
app.include_router(v1_router)  # /api/v1/...


@app.get("/")
async def root():
    return {"message": "Welcome to AI_SRE Platform", "docs": "/docs"}
