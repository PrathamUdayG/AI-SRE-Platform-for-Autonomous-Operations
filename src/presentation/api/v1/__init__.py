from fastapi import APIRouter
from .health import router as health_router
from .incidents import router as incidents_router
from .infrastructure import router as infrastructure_router
from .chat import router as chat_router
from .metrics import router as metrics_router
from .servers import router as servers_router

router = APIRouter(prefix="/api/v1")
router.include_router(health_router)
router.include_router(incidents_router)
router.include_router(infrastructure_router)
router.include_router(chat_router)
router.include_router(metrics_router)
router.include_router(servers_router)
