from pydantic import BaseModel, ConfigDict, Field

from ai_rag.domains.chat.schemas import ChatStreamChunk, ErrorResponse


class ChatRequest(BaseModel):
    """Incoming user request for chat interaction."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
        description="The user chat input message",
    )


__all__ = ["ChatRequest", "ChatStreamChunk", "ErrorResponse"]
