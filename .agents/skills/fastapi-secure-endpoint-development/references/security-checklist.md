# FastAPI Security Checklist (OWASP API Security Top 10 mapping)

Walk through this for every new/changed endpoint. Each item names the
open-source library/feature to use — do not hand-roll these.

## API1: Broken Object Level Authorization
- Every fetch/update/delete by ID must check the authenticated principal
  owns/has-scope-for that specific object — not just "is authenticated".
  Enforce in `service.py`, not just the route.
- Never trust an ID from the request path/body as sufficient authorization.

## API2: Broken Authentication
- All authentication is via Keycloak-issued OAuth2/OIDC tokens.
- Validate JWTs against Keycloak's JWKS endpoint using `python-jose[cryptography]`
  or `PyJWT[crypto]` with a JWKS client (cache keys, handle rotation) —
  or use `fastapi-keycloak-middleware` / `python-keycloak` which wraps this.
- Never accept unsigned tokens, never trust a client-supplied `sub`/role
  claim without verifying the signature and issuer/audience.
- Token expiry and `iss`/`aud` are always validated.

## API3: Broken Object Property Level Authorization
- Response schemas (`ItemRead`, etc.) are explicit allowlists of fields —
  never `dict(model.__dict__)` or a schema built from `**kwargs`.
- Mass-assignment protection: `ItemCreate`/`ItemUpdate` schemas only expose
  fields the client is allowed to set (e.g., never `owner_id`, `is_admin`
  directly from client input).

## API4: Unrestricted Resource Consumption
- Rate limit with `slowapi` (Redis-backed storage in this stack) on all
  public, auth, and expensive (LLM/agent) endpoints.
- Pagination (`limit`/`offset` or cursor) with a hard max page size on all
  list endpoints — use `fastapi-pagination` rather than custom logic.
- Request body size limits via ASGI/reverse-proxy config; file upload size
  caps enforced explicitly in the handler.
- Bound any LLM/agent call's token/time budget — don't let a client trigger
  unbounded LangGraph/Deep Agents runs.

## API5: Broken Function Level Authorization
- Admin-only / privileged routes use a distinct `Security` dependency
  (e.g., `require_admin`) — never a boolean check buried in handler logic.
- Prefer scope/role-based `Security(...)` dependencies over per-line `if`
  checks so authorization is visible and testable.

## API6: Unrestricted Access to Sensitive Business Flows
- Sensitive flows (password reset, payment, bulk export) get rate limiting
  + additional verification (e.g., re-auth, CAPTCHA if user-facing) — flag
  this explicitly if you're implementing one.

## API7: Server-Side Request Forgery (SSRF)
- Any endpoint that fetches a user-supplied URL (webhooks, RAG ingestion
  from URL, etc.) must validate/allowlist the target and use `httpx` with
  redirects disabled or carefully validated, never fetch internal/
  metadata IPs. Consider a dedicated egress proxy/allowlist for this.

## API8: Security Misconfiguration
- CORS: explicit origin allowlist via `CORSMiddleware`, never `allow_origins=["*"]`
  combined with `allow_credentials=True` in production.
- Security headers via the `secure` (PyPI: `secure`) library or an ASGI
  middleware: `Strict-Transport-Security`, `X-Content-Type-Options`,
  `X-Frame-Options`, `Content-Security-Policy` as appropriate.
- `/docs`, `/redoc`, `/openapi.json` disabled or auth-gated in production.
- Debug mode / verbose tracebacks off in production (`DEBUG=false`), custom
  exception handlers return generic error bodies.
- All config/secrets via `pydantic-settings` reading from environment
  variables / Docker/K8s secrets — never committed to the repo.

## API9: Improper Inventory Management
- Every endpoint is versioned under `/api/v1/...` and tagged (`tags=[...]`)
  so OpenAPI stays an accurate inventory. Deprecate old versions explicitly
  with FastAPI's `deprecated=True` rather than leaving undocumented routes.

## API10: Unsafe Consumption of APIs
- Any outbound call to a third-party or internal service uses `httpx`
  (async) with explicit timeouts and `tenacity` for retries with backoff —
  never trust an unbounded/unvalidated response schema; validate it with a
  Pydantic model before use.

## Cross-cutting, every endpoint
- [ ] Input fully validated by a Pydantic v2 model (`extra="forbid"`,
      bounded lengths/ranges).
- [ ] Output goes through an explicit response schema.
- [ ] AuthN required unless the endpoint is intentionally public (state why).
- [ ] AuthZ (object- and function-level) enforced, not just AuthN.
- [ ] Rate limit applied if public, auth-related, or expensive.
- [ ] No secrets, stack traces, or internal identifiers in responses/logs.
- [ ] DB access parameterized via SQLAlchemy — no raw string SQL.
- [ ] Tests cover happy path, 401, 403, 422, and a domain-specific edge case.
