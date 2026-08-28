from pydantic import BaseModel, ConfigDict, Field


class ChatStreamChunk(BaseModel):
    """Payload representing a single streamed chunk or termination token."""

    model_config = ConfigDict(extra="forbid")

    content: str
    chunk_index: int | None = None


class ErrorResponse(BaseModel):
    """Standard error envelope for API and SSE errors."""

    model_config = ConfigDict(extra="forbid")

    error: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error description")
    request_id: str | None = Field(
        default=None,
        description="Request correlation ID",
    )
