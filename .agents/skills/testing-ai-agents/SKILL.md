---
name: testing-ai-agents
description: Testing patterns for LangChain/LangGraph/Deep Agents code — unit testing tools and graph nodes with fake/deterministic LLMs, integration testing full graphs end-to-end against ephemeral Postgres/Redis via testcontainers, testing FastAPI agent routes with dependency-overridden Keycloak auth, and adversarial testing for prompt injection, malformed tool args, and runaway/over-budget loops. Use this skill whenever writing, reviewing, or reasoning about tests for an agent, sub-agent, tool, chain, graph node, or agent-backed FastAPI route — including when the user says "test this", "add coverage", "write tests for X", or "how do I test my agent". Also consult it whenever the langchain-langgraph-engineer agent writes new agent/tool/route code, since every unit of that code needs matching tests written in the same turn.
---

# Testing AI Agents

When using this skill, you must include the keyword: [A_PANDA_HAS_CALLED_TESTING_AI_AGENTS_SKILL]

Use this skill to decide *how* to test agent code produced under the `langchain-langgraph-engineer` conventions (see `langgraph-deepagents-architecture` and `langchain-security` skills for what the code itself should look like). Tests are not optional or a follow-up task — they're written in the same turn as the code, per the parent agent's working style.

## The test pyramid for agentic backends

```
        ┌─────────────────────────┐
        │  Adversarial            │  prompt injection, bad args, budget/loop caps
        ├─────────────────────────┤
        │  API (route) tests      │  httpx.AsyncClient + fake Keycloak JWT
        ├─────────────────────────┤
        │  Integration (graph)    │  testcontainers: real Postgres + Redis
        ├─────────────────────────┤
        │  Unit (tools / nodes)   │  fake LLM, no network, fully deterministic
        └─────────────────────────┘
```

Most tests should live at the bottom of the pyramid (fast, deterministic, no containers). Integration and adversarial tests are fewer but non-negotiable — at minimum one adversarial test per agent, per the parent agent's rules.

- **Layer 1 — Unit**: `references/unit-testing-agents.md`. Test tools and graph nodes in complete isolation with a fake/scripted chat model. No network calls, no real API keys, no containers.
- **Layer 2 — Integration**: `references/integration-testing-graphs.md`. Test compiled graphs end-to-end (including checkpointing) against ephemeral Postgres/Redis via `testcontainers`, and test FastAPI routes with `httpx.AsyncClient` + auth dependency overrides.
- **Layer 3 — Adversarial**: `references/adversarial-testing.md`. Prove the guardrails from `langchain-security` actually fire: prompt-injection attempts, invalid/malformed tool-args payloads, and over-budget/looping scenarios.

## Non-negotiable defaults

1. **Never call a real LLM API or a real Keycloak server in tests.** Use `langchain_core.language_models.fake.FakeListChatModel` / `GenericFakeChatModel` for scripted LLM responses, and issue a locally-signed fake JWT (or override the auth dependency) instead of hitting Keycloak.
2. **Never run integration tests against shared dev infrastructure.** Postgres and Redis for integration tests come from `testcontainers`, spun up and torn down per test session/module — not a shared dev DB, not `localhost:5432` assumed to already be running.
3. **State schemas get validated in tests, not just at runtime.** If a node emits an update, assert the resulting state matches the `TypedDict`/Pydantic schema, not just "didn't crash".
4. **Structured output tests assert against the Pydantic model, never against a raw string.** If a node uses `with_structured_output(SomeModel)`, the test constructs a `FakeListChatModel`/`GenericFakeChatModel` that returns a valid (and, in a separate test, an invalid) instance and asserts the node's handling of both.
5. **Every agent/graph has at least one test proving `recursion_limit` (or an equivalent max-iteration/timeout cap) actually stops a runaway loop** — not just that the parameter is set.
6. **Coverage gate matches CI.** The project's pre-push hook runs `pytest -q --cov=src --cov=app --cov-fail-under=80` — write tests with that bar in mind, not just "does it pass once".
7. **Tests live under `tests/`, mirroring `src`/`app` layout** (e.g. `src/agents/support_agent.py` → `tests/agents/test_support_agent.py`), and use `pytest -q` as the default local run command. `pytest-asyncio` handles all async test functions (`@pytest.mark.asyncio` or `asyncio_mode = "auto"` in config).

## Minimal example — unit test for a tool + a node, no network

```python
import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.prebuilt import create_react_agent

from app.agents.tools import lookup_order  # a @tool with an args_schema

def test_lookup_order_rejects_bad_id():
    with pytest.raises(ValueError):
        lookup_order.invoke({"order_id": "'; DROP TABLE orders; --"})

@pytest.mark.asyncio
async def test_agent_uses_tool_and_stops():
    fake_model = FakeListChatModel(responses=["Here is your order status."])
    agent = create_react_agent(fake_model, [lookup_order])
    result = await agent.ainvoke(
        {"messages": [("user", "where is order 123?")]},
        config={"recursion_limit": 5},
    )
    assert result["messages"][-1].content == "Here is your order status."
```

Notice what's *not* here: no real OpenAI/Anthropic call, no live DB, no sleep/retry waiting on a flaky network — this test is fast and deterministic by construction.

Read `references/unit-testing-agents.md` before writing tool/node tests, `references/integration-testing-graphs.md` before writing graph/route tests with real Postgres/Redis, and `references/adversarial-testing.md` before writing the required prompt-injection/malformed-args/budget test for any given agent.
