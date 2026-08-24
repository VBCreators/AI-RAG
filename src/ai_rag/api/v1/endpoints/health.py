from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def health_live() -> dict[str, str]:
    """
    liveness check
    """
    return {"status": "ok"}


@router.get("/ready")
async def health_ready() -> dict[str, str]:
    """
    readiness check
    """
    return {"status": "ok"}
