import asyncio

from ai_rag.schemas.echo import EchoRequest, EchoResponse


class EchoService:
    async def echo_message(self, request: EchoRequest) -> EchoResponse:
        """Echo the given message."""
        return EchoResponse(original=request.message, reversed=request.message[::-1])

    async def echo_with_delay(
        self, request: EchoRequest, delay: float = 1.0
    ) -> EchoResponse:
        """Echo the given message with a delay."""
        await asyncio.sleep(delay)
        return EchoResponse(original=request.message, reversed=request.message[::-1])
