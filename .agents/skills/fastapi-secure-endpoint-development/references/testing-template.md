# Testing Template

Every endpoint module gets `tests/test_<apiname>.py`. Use
`pytest` + `pytest-asyncio` + `httpx.AsyncClient` against the app via
`ASGITransport` (no real network). Auth is overridden with
`app.dependency_overrides`, never by minting a real Keycloak token in tests.

```python
import pytest
from httpx import AsyncClient, ASGITransport

from ai_rag.main import app
from ai_rag.core.security import get_current_principal, Principal
from ai_rag.api.v1.endpoints.items.dependencies import require_item_write


@pytest.fixture
def authed_principal() -> Principal:
    return Principal(user_id="00000000-0000-0000-0000-000000000001",
                      scopes=["items:write"])


@pytest.fixture(autouse=True)
def override_auth(authed_principal):
    app.dependency_overrides[get_current_principal] = lambda: authed_principal
    app.dependency_overrides[require_item_write] = lambda: authed_principal
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_create_item_happy_path(client):
    resp = await client.post("/api/v1/items", json={"name": "widget"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "widget"


@pytest.mark.asyncio
async def test_create_item_requires_auth(client):
    app.dependency_overrides.clear()  # remove the auth override for this test
    resp = await client.post("/api/v1/items", json={"name": "widget"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_item_requires_scope(client, authed_principal):
    authed_principal.scopes = []  # valid principal, wrong scope
    resp = await client.post("/api/v1/items", json={"name": "widget"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_item_validation_error(client):
    resp = await client.post("/api/v1/items", json={"name": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_item_rejects_unknown_fields(client):
    # extra="forbid" on the schema should reject unexpected fields
    resp = await client.post(
        "/api/v1/items", json={"name": "widget", "owner_id": "attacker-id"}
    )
    assert resp.status_code == 422
```

## Minimum required coverage per endpoint
1. Happy path (2xx, correct response shape).
2. Missing/invalid auth → 401.
3. Valid auth, insufficient scope/role → 403.
4. Invalid input → 422 (including a mass-assignment attempt, per
   `security-checklist.md` API3).
5. One domain-specific edge case (not-found, conflict, rate-limit, etc.).

Use `polyfactory` to generate valid request payloads for larger schemas
instead of hand-writing every field in every test. Run `pytest --cov` and
keep new endpoint code at or above the project's coverage threshold (see CI
workflow, default gate: 85%).
