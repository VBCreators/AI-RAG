# Unit Testing Tools and Graph Nodes

Goal: test the smallest unit of agent logic (a `@tool`, a graph node function, a Pydantic schema) with zero network calls, zero real credentials, and full determinism.

## Faking the LLM

Two built-ins from `langchain_core` cover almost every case:

- **`FakeListChatModel(responses=[...])`** — returns each string in `responses` in order, one per call. Use when you just need the model to "say" a fixed sequence of things.
- **`GenericFakeChatModel`** — subclass or parametrize when you need tool-calling behavior (i.e. the fake model must return `AIMessage` objects with `tool_calls` set, not just plain text), since a real agent loop inspects `tool_calls` to decide whether to call a tool or finish.

```python
from langchain_core.messages import AIMessage
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

def make_tool_calling_fake(tool_name: str, args: dict, then_text: str):
    """Fake model: first call emits a tool call, second call finishes with text."""
    messages = [
        AIMessage(content="", tool_calls=[{"name": tool_name, "args": args, "id": "call_1"}]),
        AIMessage(content=then_text),
    ]
    return GenericFakeChatModel(messages=iter(messages))
```

Never instantiate a real provider class (`ChatOpenAI`, `ChatAnthropic`, etc.) in a unit test, even "just to see if it compiles" — that's a network call and a real API key waiting to happen in CI.

## Testing a `@tool` directly

Every tool has a Pydantic `args_schema` (per `langchain-security`). Test three things per tool:

1. **Happy path** — valid args in, expected result out.
2. **Schema rejection** — invalid *type* (e.g. string where int expected) raises a validation error before your function body even runs.
3. **In-body re-validation** — a value that's the *right type* but semantically hostile/invalid (SQL-meta-characters in an ID, a path-traversal string in a filename, an out-of-range value) is still rejected by the function body's own check, not just trusted because it passed the schema. This is the test that proves rule 4 in `langchain-security` ("treat the schema as a first filter, not a guarantee") is actually implemented.

```python
def test_tool_rejects_type_mismatch():
    with pytest.raises((ValueError, TypeError)):
        lookup_order.invoke({"order_id": {"nested": "object"}})

def test_tool_rejects_semantically_invalid_value():
    # right type (str), but the tool's own body must still reject it
    with pytest.raises(ValueError):
        lookup_order.invoke({"order_id": "../../etc/passwd"})
```

## Testing a graph node function

Graph nodes are plain functions (or async functions) that take state and return a partial state update — test them exactly like any other typed function, independent of the graph they'll be wired into.

```python
@pytest.mark.asyncio
async def test_classify_node_sets_category():
    state = {"messages": [("user", "I want a refund")], "ticket_category": None}
    result = await classify_node(state, fake_config_with_structured_output_model)
    assert result["ticket_category"] == "refund"
```

Key points:

- Pass in a **minimal, explicit state dict** matching the `TypedDict`/Pydantic schema — don't rely on defaults you haven't declared.
- If the node calls `with_structured_output(SomeModel)`, inject a fake model that returns a `SomeModel` instance (via `.with_structured_output` on a fake, or by mocking the method) so the test never touches a real provider.
- Assert on the **returned partial state**, not on side effects you didn't declare — a node that mutates a global or writes to a DB directly (instead of returning a state update) is itself a design smell to flag back to the `langchain-langgraph-engineer` agent.

## Mocking non-LLM HTTP calls

For tools that call external APIs, mock at the HTTP layer (`httpx` transport mock, `respx`, or `pytest-mock` patching the client method) rather than mocking your own wrapper function — this catches serialization bugs (bad JSON body, wrong headers) that a higher-level mock would hide.

```python
import respx
from httpx import Response

@respx.mock
def test_external_lookup_tool_parses_response():
    respx.get("https://api.example.com/orders/123").mock(
        return_value=Response(200, json={"status": "shipped"})
    )
    result = lookup_order.invoke({"order_id": "123"})
    assert result.status == "shipped"
```

## What NOT to unit test here

- Checkpointing/persistence correctness — that's an integration-test concern (`references/integration-testing-graphs.md`), since it needs a real Postgres to be meaningful.
- Auth/JWT verification — that's an API-layer test concern, not a tool/node concern.
- Anything requiring two or more real infrastructure pieces talking to each other — if the test needs both Postgres and Redis to make sense, it's integration, not unit.
