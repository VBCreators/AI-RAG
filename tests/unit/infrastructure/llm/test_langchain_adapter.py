from collections.abc import AsyncIterator

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessageChunk, BaseMessage, HumanMessage
from pydantic import SecretStr

from ai_rag.core.config import Settings
from ai_rag.infrastructure.llm import create_chat_model
from ai_rag.infrastructure.llm.langchain_llm_adapter import LangChainLLMAdapter


class StreamingMockChatModel(BaseChatModel):
    """Simple mock chat model that streams preconfigured chunks."""

    def _generate(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    async def _agenerate(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    @property
    def _llm_type(self) -> str:
        return "mock-chat-model"

    async def astream(  # type: ignore[override]
        self,
        input: list[BaseMessage],
        config: dict | None = None,
        **kwargs,
    ) -> AsyncIterator[AIMessageChunk]:
        yield AIMessageChunk(content="Hello")
        yield AIMessageChunk(content=" from")
        yield AIMessageChunk(content=" LangChain")


@pytest.mark.asyncio
async def test_langchain_adapter_astream_response() -> None:
    mock_model = StreamingMockChatModel()
    adapter = LangChainLLMAdapter(model=mock_model)

    chunks = []
    async for chunk in adapter.astream_response([HumanMessage(content="test")]):
        chunks.append(chunk)

    assert chunks == ["Hello", " from", " LangChain"]


def test_create_chat_model_unsupported_provider() -> None:
    settings = Settings(
        llm_provider="unsupported-provider",
        google_api_key=SecretStr("fake"),
    )
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        create_chat_model(settings)


def test_create_chat_model_missing_api_key() -> None:
    settings = Settings(
        llm_provider="google-genai",
        google_api_key=SecretStr(""),
    )
    with pytest.raises(
        ValueError, match="GOOGLE_API_KEY environment variable is required"
    ):
        create_chat_model(settings)


def test_create_chat_model_google_genai_success() -> None:
    settings = Settings(
        llm_provider="google-genai",
        llm_model_name="gemini-2.5-flash-lite",
        google_api_key=SecretStr("fake-key-for-init"),
    )
    model = create_chat_model(settings)
    assert model is not None
