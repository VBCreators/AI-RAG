from fastapi import APIRouter

from ai_rag.api.v1.endpoints.echo import router as echo_router
from ai_rag.api.v1.endpoints.health import router as health_router

router = APIRouter(prefix="/v1", tags=["v1"])

router.include_router(health_router)
router.include_router(echo_router)
