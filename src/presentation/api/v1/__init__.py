from fastapi import APIRouter

from .chat import router as chat_router
from .health import router as health_router
from .incidents import router as incidents_router
from .infrastructure import router as infrastructure_router
from .inventory import router as inventory_router
from .metrics import router as metrics_router
from .monitoring import router as monitoring_router
from .servers import router as servers_router
from .telemetry import router as telemetry_router

router = APIRouter(prefix="/api/v1")
router.include_router(health_router)
router.include_router(incidents_router)
router.include_router(infrastructure_router)
router.include_router(inventory_router)
router.include_router(telemetry_router)
router.include_router(monitoring_router)
router.include_router(chat_router)
router.include_router(metrics_router)
router.include_router(servers_router)
