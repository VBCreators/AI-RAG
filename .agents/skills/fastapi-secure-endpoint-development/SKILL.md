---
name: fastapi-secure-endpoint-development
description: >
  How to write, wire, secure, and test FastAPI endpoints in this project.
  Use this skill whenever creating or modifying anything under
  src/ai_rag/api/v1/endpoints/, wiring a new router into the parent
  api_router, adding Pydantic request/response schemas, adding auth/authz
  (Keycloak/OAuth2/JWT), rate limiting, file uploads, pagination, or when
  writing pytest tests for API endpoints. Make sure to use this skill
  even for "small" endpoint changes — router wiring mistakes and skipped
  security checks are the most common source of production incidents in
  this codebase, so always check this skill before touching API code,
  even if the change looks trivial.
---

# FastAPI Secure Endpoint Development

This skill packages the project's conventions for API code so every
endpoint is structured, wired, and secured the same way, using
well-established open-source libraries instead of custom code.

## Core principle

If a popular, maintained, open-source library already solves a problem
(auth, validation, rate limiting, retries, pagination, caching, hashing),
**use it**. Do not write custom security-relevant code from scratch. See
`references/recommended-libraries.md` for the approved list and what each
one replaces.

## Directory & router convention

```
src/ai_rag/api/v1/
├── api.py                     # parent api_router — includes every endpoint router
└── endpoints/
    └── <apiname>/
        ├── __init__.py
        ├── router.py           # APIRouter for this resource
        ├── schemas.py          # Pydantic v2 request/response models
        ├── service.py          # business logic, called by router.py
        ├── dependencies.py     # endpoint-specific Depends() (optional)
        └── tests/
            └── test_<apiname>.py
```

Every `<apiname>` router is included into `api.py`'s `api_router`, which is
mounted once in `src/ai_rag/main.py`. See
`references/router-pattern.md` for the exact, copy-pasteable pattern —
follow it verbatim so router prefixes, tags, and dependency layering stay
consistent project-wide.

## Workflow for a new endpoint

1. **Check for reuse first.** Grep `src/ai_rag/api/v1/endpoints/` for a
   similar resource — copy its structure rather than inventing a new one.
2. **Define schemas** in `schemas.py` (Pydantic v2, `extra="forbid"`,
   explicit types/constraints — no bare `dict`/`Any` on the wire).
3. **Write the router** in `router.py` per `references/router-pattern.md`,
   thin handlers only — no business logic inline.
4. **Put logic in `service.py`**, called from the route.
5. **Add auth/authz** via `Security(...)` dependencies (Keycloak JWT/JWKS —
   see `references/security-checklist.md` §AuthN/AuthZ).
6. **Register the router** on the parent `api_router` in `api.py`.
7. **Write tests** in `tests/test_<apiname>.py` per
   `references/testing-template.md`.
8. **Run the security self-check**: walk through
   `references/security-checklist.md` and confirm each applicable item.

## Reference files

Read these as needed — don't load all of them if the task only needs one:

- `references/router-pattern.md` — exact router creation + parent
  registration pattern, with a full worked example.
- `references/security-checklist.md` — OWASP API Security Top 10 mapped to
  concrete mitigations and the library that implements each one.
- `references/recommended-libraries.md` — approved, popular, open-source
  libraries for auth, validation, rate limiting, caching, DB access,
  testing, and security scanning, with what each replaces.
- `references/testing-template.md` — pytest + httpx.AsyncClient test
  skeleton, including how to override auth dependencies in tests.
