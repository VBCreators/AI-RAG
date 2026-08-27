from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── App ──
    app_name: str = "AI RAG"
    app_version: str = "0.1.0"
    debug: bool = False
    env: str = "dev"
    log_level: str = "INFO"

    # ── Server ──
    # 0.0.0.0 is standard for containerized deployments
    host: str = "0.0.0.0"  # nosec: B104
    port: int = 8000

    # ── CORS ──
    cors_allowed_origins: list[str] = ["http://localhost:3000"]

    # ── Bot Identity ──
    bot_name: str = "Panda"

    # ── System Prompt Components ──
    ai_persona: str = "You are {bot_name}, a friendly and knowledgeable AI assistant."
    ai_domain: str = (
        "You specialize in answering questions about technology, programming, "
        "and software engineering."
    )
    ai_guardrails: str = (
        "Do not provide medical, legal, or financial advice. "
        "Do not generate harmful, offensive, or misleading content. "
        "If you are unsure, say so honestly."
    )
    ai_response_word_limit: int = 300

    # ── LLM Settings ──
    llm_provider: str = "google-genai"
    llm_model_name: str = "gemini-2.5-flash-lite"
    llm_temperature: float = 0.7
    llm_max_output_tokens: int = 2048
    llm_top_p: float = 0.95
    llm_timeout: int = 30
    llm_max_retries: int = 2
    google_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="Google AI API key for Gemini",
    )

    # ── SSE ──
    sse_ping_interval: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
