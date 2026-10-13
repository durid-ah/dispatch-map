# Feature Specification: Retire Items Endpoints and Legacy Frontend Demo

- **Status**: Implemented
- **Author**: AI Assistant & Pair
- **Date**: 2026-10-11
- **Related Issues / PRs**: N/A
- **Spec ID**: `001-retire-items-endpoints`

---

## 1. Summary & Problem Statement

### Problem
During the early bootstrap phase of the project, sample `/items` endpoints (`GET /items/{item_id}` and `GET /items/stream`), an in-memory mock `Item` Pydantic model, and a standalone HTML demo page (`packages/api/static/stream.html`) were introduced to validate FastAPI SSE streaming and static serving.

Now that the core emergency dispatch domain is implemented (`GET /events` backed by PostgreSQL/SQLModel, TanStack Query polling, and Leaflet map rendering in `packages/web`), the legacy `items` code is obsolete. Retaining it introduces technical debt:
1. It bloats `packages/api/openapi.json` and the auto-generated TypeScript contracts in `packages/web/src/types/api.generated.ts`.
2. `packages/web/vite.config.ts` still proxies `/items` to FastAPI.
3. Test suites in `packages/api/tests/test_api.py` continue to test mock item endpoints instead of production domain behavior.
4. Developers and agents may be confused about whether SSE streaming for items is part of the application domain.

### Proposed Solution
Formally decommission and remove the items endpoints, schemas, static demo frontend, Vite proxy rules, and associated unit tests. Synchronize the OpenAPI contract and frontend TypeScript types using the project's Spec-Driven Development (SDD) tooling (`./run-dev.sh spec:types`), and ensure full contract verification passes (`./run-dev.sh spec:verify`).

### User Stories / Use Cases
- **As a** developer or agent working on `packages/api` and `packages/web`,
- **I want to** have a clean API contract and codebase focused exclusively on the emergency dispatch domain,
- **So that** generated types, documentation, and routes accurately reflect production capabilities without confusing legacy scaffolding.

---

## 2. Scope Boundaries

### In Scope
- **Backend API (`packages/api`)**:
  - Delete `packages/api/routers/items.py`.
  - Remove `items_router` import and registration from `packages/api/routers/__init__.py` and `packages/api/main.py`.
  - Remove the `Item` Pydantic model from `packages/api/schemas.py`.
  - Delete the legacy SSE demo frontend `packages/api/static/stream.html`.
  - Remove item-related unit tests (`test_item_detail`, `test_item_stream`, `test_static_stream_file`) from `packages/api/tests/test_api.py`.
  - Update `packages/api/README.md` to remove references to `static/stream.html`.
- **Frontend Web (`packages/web`)**:
  - Remove the `/items` proxy configuration in `packages/web/vite.config.ts`.
  - Update `packages/web/README.md` to reflect that the development proxy targets `/events`.
- **Contracts & Code Generation**:
  - Re-export `packages/api/openapi.json` via `packages/api/export_openapi.py`.
  - Regenerate `packages/web/src/types/api.generated.ts` via `npm run typegen --prefix packages/web`.
  - Verify complete system integrity via `./run-dev.sh spec:verify`.

### Out of Scope (Deferred)
- **Real-time SSE for Dispatch Events**: Implementing a live streaming endpoint for real-time dispatch calls (`GET /events/stream`) will be designed under a separate, dedicated feature spec.
- **Database Schema Changes**: No database tables or migrations are affected; `Item` was purely an in-memory Pydantic model with no SQLModel/PostgreSQL representation.

---

## 3. Data Models & Interface Contracts

### 3.1 Database Schema (SQLModel / PostgreSQL)
No changes. The database schema in `packages/db/src/db/models.py` and Alembic migrations in `packages/migrations` have no references to `items`.

### 3.2 API Endpoint & Schemas (FastAPI / OpenAPI)

#### Decommissioned Endpoints
The following routes will be removed from the FastAPI application router:
- `GET /items/{item_id}`
- `GET /items/stream`
- Static route serving `GET /static/stream.html`

#### Schema Removal (`packages/api/schemas.py`)
Remove the following model:
```python
# REMOVE FROM packages/api/schemas.py
class Item(BaseModel):
    name: str
    description: str | None
```

#### Retained Active API Contract
Following retirement, the active API contract consists solely of:
- `GET /events` (`hours: int = 24`) -> `list[EventWithCoords]`
- `GET /{full_path:path}` -> React SPA fallback router

### 3.3 Frontend Contracts & Types (TypeScript)
Regenerating `packages/web/src/types/api.generated.ts` via `openapi-typescript` will eliminate:
- `paths["/items/stream"]`
- `paths["/items/{item_id}"]`
- `operations["sse_items_items_stream_get"]`
- `operations["read_item_items__item_id__get"]`

The frontend build will continue to compile cleanly as no React components or hooks consume these types.

---

## 4. Edge Cases, Failure Modes & Resilience

| Scenario | System Behavior | Expected UX / Feedback |
|---|---|---|
| Client requests `GET /items/1` or `GET /items/stream` | FastAPI route matcher does not find `/items/*`; falls through to SPA catch-all router (`GET /{full_path:path}`) | Non-existent client asset returns `404 Not Found` (or serves `index.html` fallback if requested with `Accept: text/html`) |
| Client requests `GET /static/stream.html` | File no longer exists in `packages/api/static/` | Returns standard FastAPI `404 Not Found` |
| Vite dev server proxy for `/items` | Proxy rule removed from `vite.config.ts` | Vite dev server returns `404` directly without proxy forwarding |
| Contract verification check | `npm run typegen:check --prefix packages/web` | Passes with exit code 0 because `openapi.json` and `api.generated.ts` are re-synced in lockstep |

---

## 5. Executable Acceptance Criteria

### Verification Commands
- [x] Backend test suite passes: `uv run python -m unittest discover packages/api/tests`
- [x] Contract types cleanly generated: `./run-dev.sh spec:types`
- [x] Web package compiles with zero TypeScript errors: `npm run build --prefix packages/web`
- [x] Linter checks pass: `npm run lint --prefix packages/web`
- [x] Full SDD verification pipeline passes: `./run-dev.sh spec:verify`

### Behavior Checklist
- [x] `packages/api/routers/items.py` is deleted.
- [x] `packages/api/static/stream.html` is deleted.
- [x] `packages/api/schemas.py` no longer contains the `Item` class.
- [x] `packages/api/main.py` does not import or mount `items_router`.
- [x] `packages/api/routers/__init__.py` exports only `events_router` and `spa_router`.
- [x] `packages/web/vite.config.ts` proxies only `/events` (no `/items` entry).
- [x] `packages/api/tests/test_api.py` contains only tests for `/events` and SPA handling.
- [x] `packages/api/openapi.json` has zero occurrences of `items`.
- [x] `packages/web/src/types/api.generated.ts` has zero occurrences of `items` or `Item` (excluding native UI select items).
