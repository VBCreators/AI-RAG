# Deep Agents Patterns

Deep Agents (`deepagents` package, built on LangGraph) exists for long-horizon, planning-heavy agent tasks. It bundles four things you'd otherwise have to build by hand — use them instead of reinventing them:

1. **A planning tool** — the agent maintains an explicit todo list it writes to and updates as it works, instead of trying to hold a multi-step plan implicitly in context.
2. **Sub-agent delegation** — the main ("orchestrator") agent can hand off a well-scoped piece of work to a specialized sub-agent with its own tools/system prompt, then absorb the result.
3. **A virtual filesystem** — scratch space for intermediate artifacts (draft documents, research notes, partial results) that doesn't pollute the main message history/context window.
4. **A default, extensible system prompt** tuned for planning-and-delegating behavior.

## Minimal setup

```python
from deepagents import create_deep_agent

def research_subagent_config() -> dict:
    return {
        "name": "researcher",
        "description": "Searches and summarizes information from approved sources only.",
        "tools": [search_docs_tool],       # narrow, least-privilege toolset for this sub-agent
        "prompt": "You research topics using only the search_docs tool. Cite sources.",
    }

agent = create_deep_agent(
    tools=[search_docs_tool, write_report_tool],
    instructions="You are a research assistant that plans, delegates research to the "
                 "researcher sub-agent, and writes a final report.",
    subagents=[research_subagent_config()],
)
```

## Security implications specific to Deep Agents

- **Sub-agents get their own least-privilege toolset**, defined explicitly per sub-agent (as above) — don't give every sub-agent the full parent toolset "for convenience". A research sub-agent should not have the refund/delete tools even if the orchestrator does.
- **The virtual filesystem is not a substitute for real access control.** Don't write secrets, PII, or anything a user shouldn't later retrieve into virtual-FS scratch files unless you've deliberately decided that's acceptable — treat it as part of the same trust boundary as the rest of agent state, and apply the same "never write secrets to agent-visible storage" rule from the `langchain-security` skill.
- **The planning/todo list is agent-writable state** — validate/sanity-check it the same way you would any other structured output if your application logic branches on its contents (e.g. don't let a todo-list item's free text be used to construct a shell command or file path).
- **Bound sub-agent recursion too.** A sub-agent delegating further can still blow the same `recursion_limit`; keep the limit set at the top-level `invoke`/`ainvoke` call so it caps the whole tree, not just the orchestrator's own steps.

## When Deep Agents is overkill

If the task is a single tool-calling loop with no multi-step planning or delegation benefit (e.g. "answer this question using a search tool"), use `langgraph.prebuilt.create_react_agent` instead — Deep Agents' planning/sub-agent/virtual-FS machinery adds real complexity (more state, more context overhead, more surface area to secure) that only pays for itself on genuinely long-horizon tasks. Say explicitly which one you chose and why when implementing.

## Testing

- Test sub-agent toolsets are actually scoped as intended: assert a given sub-agent's tool list does not include tools it shouldn't have, as a straightforward regression test — this is cheap to test and catches accidental over-privileging early.
- Test the orchestrator's delegation logic with a fake/scripted model so you can assert it calls the expected sub-agent for a given input without depending on real model behavior.
- Integration-test one full plan → delegate → synthesize run against fake tools to confirm the wiring works end-to-end, separate from unit tests of individual nodes/tools.
