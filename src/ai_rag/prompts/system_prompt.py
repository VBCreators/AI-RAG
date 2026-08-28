from ai_rag.core.config import Settings


def build_system_prompt(settings: Settings) -> str:
    """Assemble modular system prompt pieces from settings."""
    persona = settings.ai_persona.format(bot_name=settings.bot_name)
    return (
        f"{persona}\n\n"
        f"Domain expertise: {settings.ai_domain}\n\n"
        f"Guardrails:\n{settings.ai_guardrails}\n\n"
        f"Response constraint: Keep all responses under {settings.ai_response_word_limit} words."
    )


__all__ = ["build_system_prompt"]
