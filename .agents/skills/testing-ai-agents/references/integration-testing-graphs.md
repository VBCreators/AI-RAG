# Integration Testing: Graphs, Testcontainers, and FastAPI Routes

Goal: prove the compiled graph, its Postgres checkpointer, Redis-backed caching/rate-limiting, and the FastAPI route wiring it all together actually work — against **real** (but ephemeral, disposable) infrastructure, never shared dev infra.

## Why testcontainers, never shared/dev infra

- Shared dev Postgres/Redis means tests are order-dependent, leak state between runs, and can't run in parallel in CI.
- `testcontainers` (the `testcontainers-python` package, with `testcontainers[postgres]` / a Redis module) spins up a throwaway container per test session or module and tears it down automatically — this is what `container-cicd-security`'s CI pipeline expects to run in an isolated job, with no external network dependency beyond pulling the image.
- If Docker isn't available in the environment (e.g. some sandboxed CI runners), skip integration tests explicitly with a marker rather than silently degrading them to no-ops — a skipped test is visible in the report; a silently-passing fake isn't.

## Postgres-backed checkpointer, end-to-end

```python
import pytest
from testcontainers.postgres import PostgresContainer
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

@pytest.fixture(scope="module")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg

@pytest.fixture
async def checkpointer(postgres_container):
    conn_string = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2", "postgresql"
    )
    saver = AsyncPostgresSaver.from_conn_string(conn_string)
    await saver.setup()  # idempotent — creates checkpoint tables
    yield saver

@pytest.mark.asyncio
async def test_graph_resumes_from_checkpoint(checkpointer, fake_model):
    agent = create_react_agent(fake_model, tools=[], checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-thread-1"}, "recursion_limit": 10}

    await agent.ainvoke({"messages": [("user", "hi")]}, config=config)
    state = await agent.aget_state(config)

    assert state.values["messages"], "checkpoint should persist message history"
    # a second invoke with the same thread_id should see the prior turn
    result2 = await agent.ainvoke({"messages": [("user", "and then?")]}, config=config)
    assert len(result2["messages"]) >= 3
```

This is the test that actually validates rule 2 in `langgraph-deepagents-architecture` ("persistence is Postgres... not a hand-rolled persistence layer") — a unit test with a mocked saver can't catch a broken SQL schema or a serialization bug in real checkpoint rows.

## Redis: caching and rate-limit counters

```python
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="module")
def redis_container():
    with RedisContainer("redis:7-alpine") as r:
        yield r

@pytest.mark.asyncio
async def test_tool_result_cache_hits_redis(redis_container):
    client = redis.asyncio.from_url(redis_container.get_connection_url())
    cached_tool = with_redis_cache(expensive_tool, client, ttl_seconds=60)

    result1 = await cached_tool.ainvoke({"query": "x"})
    result2 = await cached_tool.ainvoke({"query": "x"})  # should hit cache, not recompute

    assert result1 == result2
    assert await client.get("expensive_tool:x") is not None
```

Also test the rate-limiter's *failure* mode: assert requests beyond the configured limit are actually rejected (429), not silently allowed through — this is what proves `langchain-security` rule 7 ("rate limit and cap cost") is real, not aspirational.

## FastAPI routes: httpx.AsyncClient + fake auth

Never hit a real Keycloak instance in these tests. Override the auth dependency with a fixture that returns a fake, already-validated principal (or issue a JWT signed with a test-only key that your dependency is configured to trust in the `testing` environment).

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.auth import get_current_principal

def override_principal():
    return {"sub": "test-user", "roles": ["agent:invoke"]}

@pytest.fixture
def client():
    app.dependency_overrides[get_current_principal] = override_principal
    transport = ASGITransport(app=app)
    yield AsyncClient(transport=transport, base_url="http://test")
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_agent_route_requires_role(client):
    app.dependency_overrides[get_current_principal] = lambda: {"sub": "u", "roles": []}
    resp = await client.post("/agents/support/invoke", json={"message": "hi"})
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_agent_route_happy_path(client, checkpointer_override):
    resp = await client.post("/agents/support/invoke", json={"message": "hi"})
    assert resp.status_code == 200
    assert "response" in resp.json()
```

Always include a test for the **missing/insufficient role** case (403) and the **missing/invalid token** case (401), not just the happy path — that's what proves `langchain-security` rule 2 ("enforces the specific role/scope it needs") is enforced, not just present as a decorator.

## Session-scoping containers for speed

Scope `PostgresContainer`/`RedisContainer` fixtures at `module` or `session` level and truncate/reset data between tests (e.g. a per-test transaction rollback, or a `TRUNCATE` in an autouse fixture) rather than starting a fresh container per test — container startup dominates test runtime otherwise.
