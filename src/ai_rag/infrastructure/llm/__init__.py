from langchain_core.language_models import BaseChatModel

from ai_rag.core.config import Settings


def create_chat_model(settings: Settings) -> BaseChatModel:
    """Factory creating the configured LangChain BaseChatModel instance."""
    if settings.llm_provider == "google-genai":
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = settings.google_api_key.get_secret_value()
        if not api_key:
            msg = "GOOGLE_API_KEY environment variable is required to initialize Google GenAI model"
            raise ValueError(msg)

        return ChatGoogleGenerativeAI(
            model=settings.llm_model_name,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_max_output_tokens,
            top_p=settings.llm_top_p,
            timeout=settings.llm_timeout,
            max_retries=settings.llm_max_retries,
            api_key=api_key,
        )

    msg = f"Unsupported LLM provider: {settings.llm_provider}"
    raise ValueError(msg)


__all__ = ["create_chat_model"]
