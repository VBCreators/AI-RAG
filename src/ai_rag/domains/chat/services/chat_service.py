import asyncio
from collections.abc import AsyncIterator

import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from ai_rag.core.errors import EmptyMessageError
from ai_rag.domains.chat.ports.llm_port import LLMPort
from ai_rag.domains.chat.schemas import ChatStreamChunk, ErrorResponse

logger = structlog.get_logger()


class ChatService:
    """Orchestrates chat message processing and response streaming."""

    def __init__(self, llm: LLMPort, system_prompt: str) -> None:
        self._llm = llm
        self._system_prompt = system_prompt

    async def stream_chat(
        self, user_message: str, request_id: str
    ) -> AsyncIterator[tuple[str, str]]:
        """Yield (event_name, json_payload) tuples for each streamed response chunk."""
        if not user_message or not user_message.strip():
            raise EmptyMessageError("Message cannot be empty or whitespace only")

        log = logger.bind(request_id=request_id)
        log.info(
            "chat_stream.start",
            message_length=len(user_message),
        )

        messages = [
            SystemMessage(content=self._system_prompt),
            HumanMessage(content=user_message),
        ]

        chunk_index = 0
        try:
            async for token in self._llm.astream_response(messages):
                chunk = ChatStreamChunk(content=token, chunk_index=chunk_index)
                yield ("token", chunk.model_dump_json())
                chunk_index += 1
        except asyncio.CancelledError:
            log.info(
                "chat_stream.client_disconnected",
                chunks_sent=chunk_index,
            )
            raise
        except Exception as exc:
            log.exception(
                "chat_stream.llm_error",
                chunks_sent=chunk_index,
                error=str(exc),
            )
            error_payload = ErrorResponse(
                error="llm_error",
                message="An error occurred while generating response",
                request_id=request_id,
            )
            yield ("error", error_payload.model_dump_json())
            return

        log.info("chat_stream.complete", total_chunks=chunk_index)
