from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from langchain_core.messages import BaseMessage


@runtime_checkable
class LLMPort(Protocol):
    """Port interface for streaming LLM responses."""

    def astream_response(self, messages: list[BaseMessage]) -> AsyncIterator[str]:
        """Yield text token chunks asynchronously for the given messages."""
        ...
