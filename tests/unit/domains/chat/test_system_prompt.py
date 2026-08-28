from pydantic import SecretStr

from ai_rag.core.config import Settings
from ai_rag.prompts.system_prompt import build_system_prompt


def test_build_system_prompt_default() -> None:
    settings = Settings(
        bot_name="PandaBot",
        ai_persona="Hello I am {bot_name}",
        ai_domain="AI engineering",
        ai_guardrails="Never disclose secrets",
        ai_response_word_limit=150,
        google_api_key=SecretStr("fake-key"),
    )

    prompt = build_system_prompt(settings)

    assert "Hello I am PandaBot" in prompt
    assert "Domain expertise: AI engineering" in prompt
    assert "Guardrails:\nNever disclose secrets" in prompt
    assert "Keep all responses under 150 words." in prompt


def test_build_system_prompt_custom_formatting() -> None:
    settings = Settings(
        bot_name="CustomAgent",
        ai_persona="Welcome! I am {bot_name}, your helper.",
        google_api_key=SecretStr("fake-key"),
    )
    prompt = build_system_prompt(settings)
    assert "Welcome! I am CustomAgent, your helper." in prompt
