from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import BaseMessage

from ai_rag.api.dependencies import get_chat_service
from ai_rag.domains.chat.ports.llm_port import LLMPort
from ai_rag.domains.chat.services.chat_service import ChatService
from ai_rag.main import create_app


class FakeTestLLM(LLMPort):
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    async def astream_response(self, messages: list[BaseMessage]) -> AsyncIterator[str]:
        if self.should_fail:
            raise RuntimeError("Test simulated LLM failure")
        for chunk in ["Hello", " world", "!"]:
            yield chunk


@pytest.fixture
def app():
    test_app = create_app()
    fake_service = ChatService(
        llm=FakeTestLLM(should_fail=False),
        system_prompt="Test System Prompt",
    )
    test_app.dependency_overrides[get_chat_service] = lambda: fake_service
    return test_app


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_chat_stream_endpoint_happy_path(client) -> None:
    response = await client.post(
        "/api/v1/chat/stream",
        json={"message": "Tell me a joke"},
        headers={"X-Request-ID": "custom-req-id-123"},
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert response.headers["x-request-id"] == "custom-req-id-123"

    body = response.text
    assert "event: token" in body
    assert "event: done" in body
    assert "[DONE]" in body
    assert "Hello" in body


@pytest.mark.asyncio
async def test_chat_stream_endpoint_empty_message(client) -> None:
    response = await client.post(
        "/api/v1/chat/stream",
        json={"message": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_stream_endpoint_rejects_extra_fields(client) -> None:
    response = await client.post(
        "/api/v1/chat/stream",
        json={"message": "hello", "unexpected_field": 123},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_stream_endpoint_mid_stream_error(app) -> None:
    failing_service = ChatService(
        llm=FakeTestLLM(should_fail=True),
        system_prompt="Test System Prompt",
    )
    app.dependency_overrides[get_chat_service] = lambda: failing_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/chat/stream",
            json={"message": "Trigger failure"},
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    body = response.text
    assert "event: error" in body
    assert "llm_error" in body
    assert "event: done" not in body  # Should not emit [DONE] on error
