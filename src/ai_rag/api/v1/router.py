from fastapi import APIRouter

from ai_rag.api.v1.endpoints.chat.router import router as chat_router

router = APIRouter(prefix="/v1")
router.include_router(chat_router)

__all__ = ["router"]
