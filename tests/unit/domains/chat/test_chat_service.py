import asyncio
import json
from collections.abc import AsyncIterator

import pytest
from langchain_core.messages import BaseMessage

from ai_rag.core.errors import EmptyMessageError
from ai_rag.domains.chat.services.chat_service import ChatService


class FakeLLM:
    def __init__(
        self,
        chunks: list[str] | None = None,
        raise_error: BaseException | None = None,
    ) -> None:
        self.chunks = chunks or ["Hello", " ", "world", "!"]
        self.raise_error = raise_error
        self.called_with_messages: list[BaseMessage] = []

    async def astream_response(self, messages: list[BaseMessage]) -> AsyncIterator[str]:
        self.called_with_messages = messages
        if self.raise_error:
            raise self.raise_error
        for chunk in self.chunks:
            yield chunk


@pytest.mark.asyncio
async def test_chat_service_stream_happy_path() -> None:
    fake_llm = FakeLLM(chunks=["Hi", " there"])
    service = ChatService(llm=fake_llm, system_prompt="System instructions")

    events = []
    async for event_name, data in service.stream_chat(
        user_message="Hello", request_id="req-123"
    ):
        events.append((event_name, json.loads(data)))

    assert len(events) == 2
    assert events[0][0] == "token"
    assert events[0][1]["content"] == "Hi"
    assert events[0][1]["chunk_index"] == 0

    assert events[1][0] == "token"
    assert events[1][1]["content"] == " there"
    assert events[1][1]["chunk_index"] == 1

    assert len(fake_llm.called_with_messages) == 2
    assert fake_llm.called_with_messages[0].content == "System instructions"
    assert fake_llm.called_with_messages[1].content == "Hello"


@pytest.mark.asyncio
async def test_chat_service_rejects_empty_message() -> None:
    fake_llm = FakeLLM()
    service = ChatService(llm=fake_llm, system_prompt="System instructions")

    with pytest.raises(EmptyMessageError):
        async for _ in service.stream_chat(user_message="   ", request_id="req-123"):
            pass


@pytest.mark.asyncio
async def test_chat_service_handles_llm_failure() -> None:
    fake_llm = FakeLLM(raise_error=RuntimeError("Google API quota exceeded"))
    service = ChatService(llm=fake_llm, system_prompt="System instructions")

    events = []
    async for event_name, data in service.stream_chat(
        user_message="Hello", request_id="req-123"
    ):
        events.append((event_name, json.loads(data)))

    assert len(events) == 1
    assert events[0][0] == "error"
    assert events[0][1]["error"] == "llm_error"
    assert events[0][1]["request_id"] == "req-123"


@pytest.mark.asyncio
async def test_chat_service_handles_cancellation() -> None:
    fake_llm = FakeLLM(raise_error=asyncio.CancelledError())
    service = ChatService(llm=fake_llm, system_prompt="System instructions")

    with pytest.raises(asyncio.CancelledError):
        async for _ in service.stream_chat(user_message="Hello", request_id="req-123"):
            pass
