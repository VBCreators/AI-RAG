from pydantic import BaseModel, Field


class EchoRequest(BaseModel):
    message: str = Field(
        ..., min_length=1, max_length=500, description="Message to be echoed"
    )

    model_config = {"json_schema_extra": {"example": {"message": "Hello World"}}}


class EchoResponse(BaseModel):
    original: str = Field(..., description="Original message")
    reversed: str = Field(..., description="Reversed message")

    model_config = {
        "json_schema_extra": {
            "example": {"original": "Hello World", "reversed": "dlroW olleH"}
        }
    }
