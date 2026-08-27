from typing import Annotated

from fastapi import Depends

from ai_rag.core.config import Settings, get_settings
from ai_rag.domains.chat.services.chat_service import ChatService
from ai_rag.infrastructure.llm import create_chat_model
from ai_rag.infrastructure.llm.langchain_llm_adapter import LangChainLLMAdapter
from ai_rag.prompts.system_prompt import build_system_prompt


def get_chat_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatService:
    """Dependency provider for ChatService."""
    model = create_chat_model(settings)
    adapter = LangChainLLMAdapter(model)
    system_prompt = build_system_prompt(settings)
    return ChatService(llm=adapter, system_prompt=system_prompt)
