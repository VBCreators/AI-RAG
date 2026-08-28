# LangGraph Implementation Patterns

## State schema

Always type the state explicitly. Use `Annotated[list, add_messages]` for message history so LangGraph merges updates correctly instead of overwriting:

```python
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_id: str
    remaining_budget_cents: int
```

For non-message fields that should be replaced (not merged) on each node's return, plain typed keys are fine — LangGraph replaces by default unless you supply a reducer.

## Postgres checkpointing (persistence)

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async with AsyncPostgresSaver.from_conn_string(settings.database_url.get_secret_value()) as checkpointer:
    await checkpointer.setup()  # creates checkpoint tables if absent; safe to call on every startup
    graph = builder.compile(checkpointer=checkpointer)
```

- Use one `thread_id` per logical conversation/task; it's your durable key for resuming state.
- Don't build your own "save state to a JSON column" mechanism — the checkpointer already versions state per step and supports time-travel/replay, which a hand-rolled column doesn't give you for free.
- Reuse the app's existing async SQLAlchemy engine's connection string/pool settings (same Postgres instance, same connection limits) rather than opening an unrelated second pool with different settings.

## Redis's role alongside Postgres

- **Cache** expensive/idempotent tool results with a short TTL (`redis.asyncio`, `EX=...`) — e.g. a search API call keyed by query hash.
- **Rate limiting** — token-bucket or fixed-window counters per user/IP, via `fastapi-limiter` (which itself uses Redis) rather than hand-writing counter logic.
- **Pub/sub for multi-instance streaming** — if the API runs multiple replicas, use Redis pub/sub (or a managed equivalent) so a `.astream_events()` consumer connected to one replica can receive events published by the replica actually running the graph.
- Don't use Redis as the checkpointer — it's not what `langgraph-checkpoint-postgres` and the ecosystem's persistence guarantees are built around here; Postgres is the durable source of truth.

## Human-in-the-loop interrupts

```python
from langgraph.types import interrupt, Command

def approval_node(state: AgentState):
    decision = interrupt({"action": "refund", "amount_cents": state["amount_cents"]})
    return {"approved": decision["approved"]}

# resuming after a human responds, from your FastAPI route:
result = await graph.ainvoke(Command(resume={"approved": True}), config={"configurable": {"thread_id": tid}})
```

The graph pauses at `interrupt()`, persists state via the checkpointer, and returns control to your API layer — you don't need a custom "pending approval" table; the checkpointer already holds the paused state keyed by `thread_id`.

## Streaming

```python
async for event in graph.astream_events(inputs, config=config, version="v2"):
    if event["event"] == "on_chat_model_stream":
        yield event["data"]["chunk"].content
```

Use `.astream_events()` (token-level + node-level events) for chat UIs, and FastAPI's `StreamingResponse`/`EventSourceResponse` (via `sse-starlette`, a popular maintained package) to relay it — don't hand-roll SSE framing.

## Bounding execution

```python
config = {
    "configurable": {"thread_id": thread_id},
    "recursion_limit": 25,       # hard cap on graph steps
}
```

Combine with a per-request wall-clock timeout at the API layer (`asyncio.wait_for` around `ainvoke`) and per-model timeouts (`ChatOpenAI(timeout=30, max_retries=2)`) so a stuck node can't hang a request indefinitely.

## Testing graphs

- Unit test individual node functions as plain functions — pass a hand-built `AgentState` dict, assert the returned partial state.
- For full-graph tests, swap in a fake chat model (`langchain_core.language_models.fake_chat_models.FakeListChatModel` or a scripted `GenericFakeChatModel`) so tests are deterministic and don't hit real providers.
- For checkpointer-dependent tests, use `testcontainers`' Postgres module for a real, ephemeral instance rather than mocking the checkpointer itself — persistence bugs are exactly the kind of thing a mock hides.
