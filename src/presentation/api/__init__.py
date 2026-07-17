from fastapi import APIRouter
from src.presentation.api.v1 import metrics

# This router will be mounted under /api/v1
router = APIRouter(prefix="/api/v1")
router.include_router(metrics.router)