# Recommended Libraries (all free / open source)

Prefer these over custom code. Only add something not on this list if none
of these fit, and say so explicitly when you do.

| Concern                                     | Library                                                                               | Notes                                                          |
| ------------------------------------------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| Web framework                               | `fastapi`                                                                             | already in stack                                               |
| Validation/schemas                          | `pydantic` v2                                                                         | `extra="forbid"`, constrained types                            |
| Settings/secrets                            | `pydantic-settings`                                                                   | reads env vars / `.env` / Docker secrets                       |
| Async ORM                                   | `sqlalchemy[asyncio]` 2.0 + `asyncpg`                                                 | parameterized queries only                                     |
| Migrations                                  | `alembic`                                                                             | never hand-edit schema in prod                                 |
| AuthN/AuthZ (Keycloak)                      | `python-keycloak` or `fastapi-keycloak-middleware`                                    | JWKS validation, token introspection                           |
| JWT handling                                | `python-jose[cryptography]` or `PyJWT[crypto]`                                        | if not fully covered by the Keycloak wrapper above             |
| Password hashing (if any local creds exist) | `passlib[argon2]` (argon2id)                                                          | prefer delegating all auth to Keycloak instead                 |
| Rate limiting                               | `slowapi`                                                                             | Redis-backed via `redis.asyncio`                               |
| Caching                                     | `fastapi-cache2`                                                                      | Redis backend                                                  |
| Pagination                                  | `fastapi-pagination`                                                                  | cursor or limit/offset                                         |
| Retries/backoff                             | `tenacity`                                                                            | outbound HTTP/LLM calls                                        |
| Outbound HTTP                               | `httpx` (async)                                                                       | explicit timeouts always                                       |
| Security headers                            | `secure`                                                                              | one-line middleware for common headers                         |
| Structured logging                          | `structlog`                                                                           | redact secrets/PII in processors                               |
| Background/long jobs                        | FastAPI `BackgroundTasks` for lightweight, `arq` (Redis-based) for heavier async jobs | avoid Celery unless already justified in this stack            |
| LLM orchestration                           | `langchain`, `langgraph`, deep agents tooling                                         | already in stack — reuse existing chains/graphs, don't rebuild |
| Testing                                     | `pytest`, `pytest-asyncio`, `httpx.AsyncClient`, `pytest-cov`                         | AI-generated tests per `testing-template.md`                   |
| Test data factories                         | `polyfactory` (Pydantic/SQLAlchemy-aware)                                             | instead of hand-written fixtures for every model               |
| Static analysis (security)                  | `bandit`                                                                              | run in pre-commit + CI                                         |
| Dependency vuln scanning                    | `pip-audit` (or `safety`)                                                             | run in CI                                                      |
| Secret scanning                             | `gitleaks` (or `detect-secrets`)                                                      | pre-commit + CI                                                |
| Linting/formatting                          | `ruff`                                                                                | replaces flake8/isort/black/pyupgrade                          |
| Type checking                               | `mypy`                                                                                | strict mode where practical                                    |
| Container scanning                          | `trivy`                                                                               | CI, scan built image before push                               |
| SAST (broader)                              | `semgrep` (optional, free CE ruleset)                                                 | catches more than bandit alone                                 |

## Explicitly avoid writing yourself

- Custom JWT parsing/verification → use the Keycloak/JWT libraries above.
- Custom rate limiter → `slowapi`.
- Custom pagination math → `fastapi-pagination`.
- Custom retry/backoff loops → `tenacity`.
- Custom CORS/security-header middleware → `CORSMiddleware` + `secure`.
- Custom password hashing → `passlib[argon2]` (or better: delegate to Keycloak entirely).
