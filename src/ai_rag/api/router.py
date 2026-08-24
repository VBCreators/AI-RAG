from fastapi import APIRouter

from ai_rag.api.v1.router import router as v1_router

router = APIRouter(prefix="/api", tags=["api"])

router.include_router(v1_router)
