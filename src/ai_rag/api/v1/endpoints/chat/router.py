from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from ai_rag.api.dependencies import get_chat_service
from ai_rag.api.v1.endpoints.chat.schemas import ChatRequest, ChatStreamChunk
from ai_rag.core.config import Settings, get_settings
from ai_rag.domains.chat.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/stream",
    summary="Stream chat completion via SSE",
    response_description="Server-Sent Events stream containing token chunks",
)
async def stream_chat(
    body: ChatRequest,
    request: Request,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EventSourceResponse:
    """Accept chat input and stream LLM responses via Server-Sent Events."""
    request_id = getattr(request.state, "request_id", "") or ""

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        has_error = False
        async for event_name, json_data in chat_service.stream_chat(
            user_message=body.message,
            request_id=request_id,
        ):
            if event_name == "error":
                has_error = True
            yield {"event": event_name, "data": json_data}

        if not has_error:
            done_chunk = ChatStreamChunk(content="[DONE]")
            yield {"event": "done", "data": done_chunk.model_dump_json()}

    return EventSourceResponse(
        event_generator(),
        ping=settings.sse_ping_interval,
    )
