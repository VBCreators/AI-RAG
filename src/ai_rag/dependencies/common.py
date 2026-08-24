from ai_rag.core.config import Settings, get_settings


def settings_dependency() -> Settings:
    return get_settings()
