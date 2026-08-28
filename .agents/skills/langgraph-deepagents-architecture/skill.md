---
name: langgraph-deepagents-architecture
description: Architecture and implementation patterns for building agents and multi-agent systems with LangGraph and the Deep Agents framework — state schemas, prebuilt agent constructors, sub-agent composition, Postgres-backed checkpointing, Redis caching, streaming, human-in-the-loop interrupts, and structured output. Use this skill whenever designing or implementing an agent graph, a sub-agent, a planning/todo-list workflow, or persistence for agent state, and prefer the prebuilt components documented here over hand-written state machines.
---

# LangGraph & Deep Agents Architecture

Use this skill to decide *how* to structure agent code, after `langchain-security` has told you the safety constraints. Default to prebuilt, popular components — LangGraph and Deep Agents exist specifically so you don't hand-roll a state machine or an agent loop.

- `references/langgraph-patterns.md` — graph construction, state schemas, checkpointing, streaming, interrupts
- `references/deep-agents-patterns.md` — planning tool, sub-agents, virtual filesystem, when Deep Agents beats a bare LangGraph graph

## Decision: LangGraph alone vs. Deep Agents

- **Single agent, a handful of tools, no long-horizon planning needed** → `langgraph.prebuilt.create_react_agent`. Don't add Deep Agents' extra machinery for something this simple.
- **Long-horizon tasks that benefit from an explicit plan/todo list, delegation to specialized sub-agents, or a scratch/virtual filesystem for intermediate work** → `deepagents.create_deep_agent`. This is exactly the case it exists for — don't reimplement planning/sub-agent delegation by hand.
- **Multiple specialized agents that need to coordinate on a shared, evolving task** → Deep Agents sub-agents, or a LangGraph supervisor graph with agent nodes — pick whichever the specific workflow's control flow maps to more naturally, and say which you picked and why.

In both cases, the underlying execution is a LangGraph graph — everything about checkpointing, interrupts, and streaming below applies either way.

## Non-negotiable defaults

1. **State is a typed schema** (`TypedDict` or Pydantic model), never a bare `dict` with implicit keys.
2. **Persistence is Postgres**, via `langgraph-checkpoint-postgres`'s `PostgresSaver` / `AsyncPostgresSaver` — not the in-memory `MemorySaver` in anything that runs past a single process lifetime, and not a hand-rolled persistence layer.
3. **Redis** is for what it's good at here: short-TTL caching of tool results, rate-limit counters, pub/sub for streaming to multiple clients — not as a substitute for the Postgres checkpointer's durable state.
4. **Every graph has a `recursion_limit`** set at invoke time (see `langchain-security` skill) and, where relevant, a wall-clock timeout around the invoke call.
5. **Structured output everywhere an LLM's response drives control flow or a tool call**, via `with_structured_output(SomeModel)` — never regex/string-matching a raw completion to decide what happens next.
6. **Human-in-the-loop via `interrupt()`**, not a custom "ask the user" side-channel, for anything requiring approval — LangGraph's interrupt/resume mechanism already integrates with the checkpointer so state survives the pause.
7. **Streaming** uses LangGraph's built-in `.astream()` / `.astream_events()` rather than a hand-rolled generator wrapping `.invoke()`.

## Minimal example — prebuilt agent, Postgres checkpointing, bounded

```python
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_openai import ChatOpenAI

async def build_agent(db_conn_string: str, tools: list, system_prompt: str):
    checkpointer = AsyncPostgresSaver.from_conn_string(db_conn_string)
    await checkpointer.setup()  # idempotent; creates tables on first run

    model = ChatOpenAI(model="gpt-4.1-mini", timeout=30, max_retries=2)
    agent = create_react_agent(model, tools, checkpointer=checkpointer, prompt=system_prompt)
    return agent

# invocation, per request:
result = await agent.ainvoke(
    {"messages": [("user", user_message)]},
    config={"configurable": {"thread_id": conversation_id}, "recursion_limit": 25},
)
```

Notice what's *not* here: no custom loop, no custom state-diffing, no custom "save to DB" code — `create_react_agent` + `AsyncPostgresSaver` cover it.

## When you do need a custom graph

Reach for `StateGraph` directly when the control flow genuinely isn't a single ReAct loop — e.g. a multi-stage pipeline (classify → route → specialist node → review node) or a supervisor coordinating sub-agents. Even then, keep node functions small, typed, and unit-testable in isolation (see `testing-ai-agents` skill), and reuse `ToolNode` for tool execution rather than writing your own tool-dispatch code.

```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from typing import TypedDict

class SupportState(TypedDict):
    messages: list
    ticket_category: str | None

graph = StateGraph(SupportState)
graph.add_node("classify", classify_node)
graph.add_node("tools", ToolNode(tools))
graph.add_node("respond", respond_node)
graph.add_edge(START, "classify")
graph.add_conditional_edges("classify", route_by_category)
graph.add_edge("tools", "respond")
graph.add_edge("respond", END)
compiled = graph.compile(checkpointer=checkpointer)
```

Read `references/langgraph-patterns.md` before implementing checkpointing, interrupts, or streaming in detail, and `references/deep-agents-patterns.md` before implementing planning or sub-agent delegation.
