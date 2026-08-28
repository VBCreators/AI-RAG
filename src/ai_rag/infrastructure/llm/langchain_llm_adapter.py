from collections.abc import AsyncIterator

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

from ai_rag.domains.chat.ports.llm_port import LLMPort


class LangChainLLMAdapter(LLMPort):
    """Adapter that wraps any LangChain BaseChatModel to satisfy LLMPort."""

    def __init__(self, model: BaseChatModel) -> None:
        self._model = model

    async def astream_response(self, messages: list[BaseMessage]) -> AsyncIterator[str]:
        """Stream chunks from the underlying LangChain model."""
        async for chunk in self._model.astream(messages):
            if not chunk.content:
                continue

            if isinstance(chunk.content, str):
                yield chunk.content
            elif isinstance(chunk.content, list):
                for part in chunk.content:
                    if isinstance(part, str):
                        yield part
                    elif isinstance(part, dict) and "text" in part:
                        yield str(part["text"])
