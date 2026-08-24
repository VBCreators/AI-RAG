from typing import Annotated

from fastapi import APIRouter, Depends

from ai_rag.core.config import Settings
from ai_rag.dependencies.common import settings_dependency
from ai_rag.schemas.echo import EchoRequest, EchoResponse
from ai_rag.services.echo_service import EchoService

router = APIRouter(prefix="/echo", tags=["echo"])

echo_service = EchoService()

# Reusable dependency type – no function call in the default
SettingsDep = Annotated[Settings, Depends(settings_dependency)]


@router.get("/echo_normal", response_model=EchoResponse)
async def echo_normal(request: EchoRequest, settings: SettingsDep):
    """Echo the given message."""
    return await echo_service.echo_message(request)


@router.post("/echo_with_delay", response_model=EchoResponse)
async def echo_with_delay(request: EchoRequest, settings: SettingsDep):
    """Echo the given message with a delay."""
    return await echo_service.echo_with_delay(request)
