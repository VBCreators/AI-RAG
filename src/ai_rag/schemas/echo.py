from pydantic import BaseModel, ConfigDict, Field


class EchoRequest(BaseModel):
    """Request schema for echo service."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., min_length=1, description="Message to echo")


class EchoResponse(BaseModel):
    """Response schema for echo service."""

    model_config = ConfigDict(extra="forbid")

    original: str
    reversed: str
