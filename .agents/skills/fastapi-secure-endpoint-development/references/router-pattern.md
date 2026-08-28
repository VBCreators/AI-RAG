# Router Pattern — worked example

This is the canonical pattern for `src/ai_rag/api/v1/endpoints/<apiname>/`.
Copy it exactly; don't improvise a different wiring style.

## 1. `schemas.py`

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID


class ItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class ItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    created_at: datetime
    owner_id: UUID
```

Never return the SQLAlchemy model instance directly — always construct an
`ItemRead` (FastAPI does this automatically via `response_model` when
`from_attributes=True` is set).

## 2. `dependencies.py` (endpoint-specific, optional)

```python
from fastapi import Depends
from ai_rag.core.security import get_current_principal, Principal


def require_item_write(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    if "items:write" not in principal.scopes:
        from fastapi import HTTPException, status
        raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient scope")
    return principal
```

Reuse `ai_rag.core.security` (project-wide Keycloak/JWT dependency) —
never re-implement token parsing per endpoint.

## 3. `service.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from ai_rag.db.models import Item
from .schemas import ItemCreate


async def create_item(db: AsyncSession, data: ItemCreate, owner_id) -> Item:
    item = Item(**data.model_dump(), owner_id=owner_id)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item
```

All DB access goes through SQLAlchemy 2.0 async with bound parameters.
Never build SQL with string formatting/concatenation.

## 4. `router.py`

```python
from fastapi import APIRouter, Depends, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from ai_rag.core.db import get_db
from ai_rag.core.security import get_current_principal, Principal
from . import service
from .dependencies import require_item_write
from .schemas import ItemCreate, ItemRead

router = APIRouter(prefix="/items", tags=["items"])
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "",
    response_model=ItemRead,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def create_item(
    data: ItemCreate,
    principal: Principal = Depends(require_item_write),
    db: AsyncSession = Depends(get_db),
) -> ItemRead:
    item = await service.create_item(db, data, owner_id=principal.user_id)
    return ItemRead.model_validate(item)
```

Notes:

- Handler stays thin: validate (Pydantic did it), authorize (`Depends`),
  delegate to `service`, map to response schema.
- `response_model` is always set explicitly.
- Rate limiting via `slowapi` on write/expensive endpoints (see
  `recommended-libraries.md`).

## 5. `__init__.py`

```python
from .router import router

__all__ = ["router"]
```

## 6. Register on the parent router — `src/ai_rag/api/v1/api.py`

```python
from fastapi import APIRouter

from ai_rag.api.v1.endpoints.items import router as items_router
from ai_rag.api.v1.endpoints.users import router as users_router
# ... one import per endpoint module

api_router = APIRouter()

api_router.include_router(items_router)
api_router.include_router(users_router)
# ... one include_router call per endpoint module
```

Do **not** set `prefix=` again here — the resource prefix (`/items`) is
already defined on the router in `router.py`. `api.py` only aggregates.

## 7. Mount once in `src/ai_rag/main.py`

```python
from fastapi import FastAPI
from ai_rag.api.v1.api import api_router

app = FastAPI(title="ai-rag", docs_url="/docs" if settings.ENV != "production" else None)
app.include_router(api_router, prefix="/api/v1")
```

- Disable `/docs`, `/redoc`, `/openapi.json` in production
  (`docs_url=None, redoc_url=None, openapi_url=None`) unless the org
  explicitly wants them exposed; if they must stay on, put them behind auth.
- A new endpoint module is *never* included directly on `app` — always
  through `api_router` in `api.py`, so versioning (`/api/v1`, future
  `/api/v2`) stays centralized.
