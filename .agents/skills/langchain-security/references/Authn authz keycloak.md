# AuthN / AuthZ with Keycloak in FastAPI

## Prefer a maintained library over hand-rolled JWT parsing

Use `python-keycloak` (or `fastapi-keycloak-middleware`, both open source) to handle token verification and JWKS caching instead of writing your own JWT/JWKS-fetching code. Only fall back to manual `python-jose`/`authlib` verification if the project has a specific reason not to use a Keycloak-specific library.

## Pattern — verify JWT, extract roles, enforce per-route

```python
# app/core/security.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from keycloak import KeycloakOpenID
from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=True)

keycloak_openid = KeycloakOpenID(
    server_url=settings.keycloak_server_url,
    realm_name=settings.keycloak_realm,
    client_id=settings.keycloak_client_id,
    client_secret_key=settings.keycloak_client_secret.get_secret_value(),
)

class AuthenticatedUser(BaseModel):
    sub: str
    username: str
    roles: list[str]

async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthenticatedUser:
    try:
        # verifies signature against Keycloak's JWKS, checks exp/aud/iss
        token_info = keycloak_openid.decode_token(
            creds.credentials,
            validate=True,
        )
    except Exception:
        # fail closed: any verification error -> 401, never let a bad/expired
        # token fall through
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    roles = token_info.get("realm_access", {}).get("roles", [])
    return AuthenticatedUser(sub=token_info["sub"], username=token_info.get("preferred_username", ""), roles=roles)

def require_role(role: str):
    async def _check(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if role not in user.roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role: {role}")
        return user
    return _check
```

```python
# app/api/routes/agent.py
from fastapi import APIRouter, Depends
from app.core.security import get_current_user, require_role, AuthenticatedUser

router = APIRouter()

@router.post("/agent/chat")
async def chat(payload: ChatRequest, user: AuthenticatedUser = Depends(get_current_user)):
    tools = build_tools_for_user(user)  # least-privilege tool binding, see prompt-injection-defense.md
    ...

@router.post("/agent/admin/refund")
async def admin_refund(payload: RefundRequest, user: AuthenticatedUser = Depends(require_role("support-agent"))):
    ...
```

## Rules

1. **Every non-public route** depends on `get_current_user` at minimum, and on `require_role(...)` for anything privileged. Don't rely on frontend hiding a button as the security boundary.
2. **Verify signature + expiry + audience + issuer** on every request — this is what `decode_token(validate=True)` / an equivalent library call does; never manually decode a JWT without verification (`jwt.decode(..., options={"verify_signature": False})` is banned outright, including "just for local dev" — use a real test realm/token instead).
3. **Cache the JWKS**, don't fetch it on every request — the Keycloak client libraries do this by default; don't disable that caching.
4. **Fail closed** — any exception during verification is a 401, never a silent pass-through.
5. **Map Keycloak roles → FastAPI dependency checks**, not string comparisons scattered through business logic. Centralize `require_role`/`require_any_role` helpers.
6. **Service-to-service calls** (e.g. a background worker calling the API) use the OAuth2 client-credentials grant with their own confidential Keycloak client — never share a user's token or use a static shared secret in place of real auth.
7. **Tests** use a locally-issued fake JWT (e.g. signed with a test key, with `get_current_user` overridden via FastAPI's `dependency_overrides`) — don't spin up a real Keycloak just to unit-test a route's business logic; do use a real (ephemeral, `testcontainers`) Keycloak for integration tests that specifically verify the auth wiring itself.
