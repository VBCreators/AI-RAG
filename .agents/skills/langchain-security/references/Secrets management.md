# Secrets Management

## Rule

All secrets (LLM provider API keys, DB URL, Redis URL, Keycloak client secret, signing keys) are loaded **only** from environment variables or mounted secret files, via one central `pydantic-settings` object. Nothing else in the codebase reads `os.environ` directly for a secret.

## Pattern — central settings object

```python
# app/core/config.py
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM providers
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None

    # Data stores
    database_url: SecretStr
    redis_url: SecretStr

    # Keycloak
    keycloak_server_url: str
    keycloak_realm: str
    keycloak_client_id: str
    keycloak_client_secret: SecretStr
    keycloak_audience: str = "account"

    # App
    environment: str = Field(default="development")
    log_level: str = "INFO"

settings = Settings()  # raises at startup if a required var is missing — fail fast
```

- Use `SecretStr` for anything sensitive so it never accidentally ends up in a `repr()`, log line, or traceback.
- `Settings()` is instantiated once at import time so misconfiguration fails at container startup, not mid-request.
- `.env` is for **local dev only**, is `.gitignore`d, and is never baked into a Docker image.

## Docker / Docker Compose

- In `docker-compose.yml`, pass secrets via `environment:` referencing the host `.env`, or better, Compose `secrets:` (file-based, not baked into the image layer) for anything long-lived in a shared/staging environment.
- Never `COPY .env` into a Dockerfile. Never put a real secret in a Dockerfile `ENV` instruction — that value is permanently baked into the image layer history.
- In CI/CD (GitHub Actions), secrets come from **GitHub Actions Secrets**, injected as env vars only for the step that needs them.

## Logging

```python
def safe_settings_view(s: Settings) -> dict:
    return {
        "environment": s.environment,
        "keycloak_realm": s.keycloak_realm,
        "database_configured": bool(s.database_url),
        # never include the SecretStr values themselves
    }
```

Never do `logger.info(settings)` or `logger.info(str(settings))` — even with `SecretStr` fields, prefer an explicit redacted view for anything written to shared logs, since library/version changes can otherwise change what gets rendered.

## What NOT to do

- ❌ `api_key = "sk-..."` hardcoded anywhere, including tests (use a fake/test key + mocked client).
- ❌ Reading secrets ad-hoc with `os.getenv(...)` scattered across the codebase — one settings module, one source of truth.
- ❌ Committing `.env`, `*.pem`, `*.key`, or Keycloak client-secret files to git — add them to `.gitignore` and let CI's secret scanner (`gitleaks`, see `container-cicd-security` skill) catch accidental commits.
- ❌ Passing secrets as CLI arguments (visible in `ps`/process list) — use env vars or files instead.
