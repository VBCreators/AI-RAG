---
name: langchain-security
description: Production security patterns for LangChain/LangGraph/Deep Agents code — secrets management, prompt-injection defense, least-privilege tool design, input/output validation, Keycloak-based authN/authZ, SQL injection prevention, rate limiting, and safe logging. Use this skill whenever writing or reviewing ANY agent, tool, chain, graph node, or FastAPI route that touches an LLM, a database, Redis, or an external API — even if the user didn't explicitly ask about security. Also use it when the user asks to "harden", "review for security", or "productionize" agent code.
---

# LangChain / LangGraph Production Security

  When using this skill, you must include the keyword: [A_PANDA_HAS_CALLED_LANGCHAIN_SECURITY_SKILL]

This skill is the top-priority checklist for the `langchain-langgraph-engineer` subagent. Read the relevant reference file before implementing the corresponding piece.

- `references/secrets-management.md` — env vars, `pydantic-settings`, Docker/Compose secrets, never-log rules
- `references/prompt-injection-defense.md` — untrusted input, tool allow-lists, output validation, human-in-the-loop
- `references/authn-authz-keycloak.md` — OIDC/JWT verification, FastAPI dependencies, role/scope enforcement

## Core rules (always apply)

1. **Secrets** live only in environment variables / a secret manager, loaded once via a `pydantic-settings` `BaseSettings` subclass. Never hardcode API keys, DB URLs, or Keycloak client secrets. Never log a settings object directly — log a redacted view.
2. **Every FastAPI route that isn't explicitly public** depends on a Keycloak-verified-JWT dependency, and enforces the specific role/scope it needs — not just "is authenticated".
3. **Every DB call** goes through SQLAlchemy's ORM or parameterized `text()` with bound params. Never f-string or `%`-format user input, tool arguments, or LLM output into SQL.
4. **Every LangChain tool** declares a typed Pydantic `args_schema`. Tool functions validate/re-check inputs even though LangChain validates against the schema — treat the schema as a first filter, not a guarantee, because models can still produce malformed or adversarial values within a valid type.
5. **Treat all LLM output as untrusted.** Before executing, storing, or returning it: validate structured output against a Pydantic model (`with_structured_output`), never `eval`/`exec` it, never pass it to a shell (`subprocess` with `shell=True` is banned outright), and never use it to build file paths without `pathlib` + allow-listed base directories.
6. **Treat all user input that reaches the LLM as a prompt-injection vector.** Untrusted content (user messages, retrieved documents, tool outputs, uploaded files) must be clearly delimited from system/developer instructions in the prompt template, and the agent's tool-calling permissions must not expand based on instructions found inside that untrusted content.
7. **Rate limit and cap cost.** Every LLM-calling endpoint sits behind a Redis-backed rate limiter (`fastapi-limiter`) and every agent run has an explicit max-iteration / max-token / wall-clock timeout, enforced by LangGraph's recursion limit and `tenacity`-based retry caps — not by hoping the loop terminates.
8. **Least privilege per tool.** A tool that only needs to read one table gets a DB role/connection that can only read that table. A tool that calls an external API gets only the scopes it needs. Don't give an agent's toolset broader access than the specific tools require, even if it's "more convenient".
9. **Human-in-the-loop for irreversible actions.** Payments, deletions, external communications (email/SMS/webhooks to third parties), and privilege changes go through a LangGraph `interrupt()` checkpoint for explicit approval, unless the user has explicitly said the workflow must be fully autonomous — and even then, flag the risk.
10. **Never log secrets, full prompts containing PII, or raw LLM completions containing PII at INFO level.** Use structured logging with an explicit redaction step for known-sensitive fields; log at DEBUG (disabled in prod) if you need full payloads for debugging.
11. **Pin and scan dependencies.** `requirements.txt`/`pyproject.toml` pins exact versions (or via `uv`/`pip-tools` lockfiles); CI runs a vulnerability scan (`pip-audit`) and secret scan (`gitleaks`) — see the `container-cicd-security` skill for the pipeline itself.
12. **Fail closed.** If a security check (auth, rate limit, schema validation) can't complete — e.g. Keycloak/JWKS endpoint unreachable — the request is rejected, not allowed through.

## Quick self-check before finishing any agent/tool/route

- [ ] No secret, credential, or connection string is hardcoded or logged in plaintext
- [ ] Route requires Keycloak auth + correct role/scope (or is deliberately, explicitly public)
- [ ] All DB access is parameterized/ORM-based
- [ ] Tool has a Pydantic `args_schema` and re-validates inputs in the function body
- [ ] LLM output that drives an action is parsed via a structured-output schema, not string-matched
- [ ] User/retrieved content is delimited from instructions in the prompt template
- [ ] Rate limiting + iteration/token/timeout caps are present
- [ ] Irreversible tool calls require human approval or are explicitly justified as autonomous
- [ ] Logging redacts secrets/PII
- [ ] New/changed dependencies are pinned and popular/maintained
