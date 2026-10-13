# Feature Specification: Event Responders & Status History Endpoint

- **Status**: Approved
- **Author**: AI Assistant & Pair
- **Date**: 2026-10-13
- **Related Issues / PRs**: N/A
- **Spec ID**: `002-event-responders-endpoint`

---

## 1. Summary & Problem Statement

### Problem
Today, the Dispatch Map frontend and consumers can query recent events (`GET /events`), which returns basic incident metadata (call type, location, timestamps, coordinates). However, emergency response operations involve multiple responding units (police, fire, EMS) transitioning through operational phases (`DISPATCHED` -> `ENROUTE` -> `ARRIVED`). 

While the data ingestion pipeline in `packages/dispatch-consumer` actively parses and records responders and their sequential status events into PostgreSQL (`responders` and `responder_status_events` tables), there is currently no API endpoint exposing this information. Consequently, clients cannot view which units were dispatched to an incident or track when responder statuses were updated.

### Proposed Solution
Introduce a dedicated RESTful API endpoint:
`GET /events/{external_id}/responders`

This endpoint accepts an event's SHA-256 `external_id` and returns an envelope payload containing all responders assigned to that event, along with each responder's chronological status event timeline (`status`, `status_order`, and `created_at` timestamp). Database surrogate keys (`id`) and intermediate foreign keys are stripped from the payload for a clean, domain-centric representation.

### User Stories / Use Cases
- **As a** dispatch operator or public viewer,
- **I want to** inspect an incident and see which units responded and how quickly they progressed through dispatch phases,
- **So that** I have full visibility into the timeline and operational response of the incident.

- **As an** API consumer or frontend engineer,
- **I want to** query responder details using the incident's stable `external_id`,
- **So that** I can retrieve responder timelines without needing internal database surrogate IDs.

---

## 2. Scope Boundaries

### In Scope
- **Backend API (`packages/api`)**:
  - Define response schemas in `packages/api/schemas.py`: `ResponderStatusRead`, `ResponderRead`, and `EventRespondersEnvelope`.
  - Implement query and aggregation logic in `packages/api/services/event_service.py` to fetch responders and their status events ordered chronologically.
  - Expose the route in `packages/api/routers/events.py` via `get_event_responders(external_id, session)`.
  - Add unit tests in `packages/api/tests/test_api.py` covering success (with responders/statuses), empty state (event with zero responders), and 404 (non-existent `external_id`).
- **Contracts & Code Generation**:
  - Re-export `packages/api/openapi.json` via `./run-dev.sh spec:export`.
  - Regenerate TypeScript types in `packages/web/src/types/api.generated.ts` via `./run-dev.sh spec:types`.
  - Validate the entire Spec-Driven Development pipeline via `./run-dev.sh spec:verify`.

### Out of Scope (Deferred)
- **Frontend UI Display**: Wiring up responder detail drawer/modal cards in `packages/web` will be addressed in a subsequent feature spec.
- **Database Schema Changes**: No new tables, columns, or Alembic migrations are required; `events`, `responders`, and `responder_status_events` already exist in `packages/db/src/db/models.py`.
- **Real-time Push / SSE**: Streaming responder status updates in real-time will be handled under a separate live-stream spec.

---

## 3. Data Models & Interface Contracts

### 3.1 Database Schema (SQLModel / PostgreSQL)
The endpoint leverages the existing relational schema in `packages/db/src/db/models.py`:
- `Event` (`__tablename__ = "events"`):
  - `id`: `BigInteger` (Surrogate Primary Key)
  - `external_id`: `CHAR(64)` (Unique natural key)
- `Responder` (`__tablename__ = "responders"`):
  - `id`: `BigInteger` (Surrogate Primary Key)
  - `event_id`: `BigInteger` (Foreign Key to `events.id`)
  - `unit`: `str`
  - `dispatch_area`: `str`
  - `agency`: `str`
  - `created_at`: `DateTime(timezone=True)`
- `ResponderStatusEvent` (`__tablename__ = "responder_status_events"`):
  - `id`: `BigInteger` (Surrogate Primary Key)
  - `responder_id`: `BigInteger` (Foreign Key to `responders.id`)
  - `status`: `str`
  - `status_order`: `int`
  - `created_at`: `DateTime(timezone=True)`

No schema migrations or model modifications are required.

### 3.2 API Endpoint & Schemas (FastAPI / OpenAPI)

#### Endpoint Definition
- **Route**: `GET /events/{external_id}/responders`
- **Path Parameter**: `external_id: str` (the 64-character SHA-256 identifier)
- **Handler Name**: `get_event_responders`
- **Tags**: `["events"]`

#### Pydantic / SQLModel Schemas (`packages/api/schemas.py`)
```python
class ResponderStatusRead(SQLModel):
    status: str
    status_order: int
    created_at: datetime


class ResponderRead(SQLModel):
    unit: str
    dispatch_area: str
    agency: str
    created_at: datetime
    statuses: list[ResponderStatusRead] = []


class EventRespondersEnvelope(SQLModel):
    external_id: str
    responders: list[ResponderRead] = []
```

#### Responses

##### `200 OK`
```json
{
  "external_id": "4cf5153fbfe8dbb70ea01d752aa47bcbc0e271ebc347d4e3cb4877e8a9f39002",
  "responders": [
    {
      "unit": "E10",
      "dispatch_area": "FIRE",
      "agency": "RFD",
      "created_at": "2026-10-13T17:45:00Z",
      "statuses": [
        {
          "status": "DISPATCHED",
          "status_order": 1,
          "created_at": "2026-10-13T17:45:00Z"
        },
        {
          "status": "ENROUTE",
          "status_order": 2,
          "created_at": "2026-10-13T17:49:12Z"
        },
        {
          "status": "ARRIVED",
          "status_order": 3,
          "created_at": "2026-10-13T17:55:30Z"
        }
      ]
    }
  ]
}
```

##### `404 Not Found`
When the requested `external_id` does not match an existing event:
```json
{
  "detail": "Event not found"
}
```

### 3.3 Frontend Contracts & Types (TypeScript)
Re-running `./run-dev.sh spec:types` will update `packages/web/src/types/api.generated.ts` with:
```typescript
export interface paths {
  "/events/{external_id}/responders": {
    get: operations["get_event_responders_events__external_id__responders_get"];
  };
}

export interface components {
  schemas: {
    EventRespondersEnvelope: {
      external_id: string;
      responders: components["schemas"]["ResponderRead"][];
    };
    ResponderRead: {
      unit: string;
      dispatch_area: string;
      agency: string;
      created_at: string;
      statuses: components["schemas"]["ResponderStatusRead"][];
    };
    ResponderStatusRead: {
      status: string;
      status_order: number;
      created_at: string;
    };
  };
}
```

---

## 4. Edge Cases, Failure Modes & Resilience

| Scenario | System Behavior | Expected Result |
|---|---|---|
| Event does not exist in database | Service returns `None`; router raises `HTTPException(status_code=404, detail="Event not found")` | Returns 404 with standard error body |
| Event exists but has zero responders | Query returns empty list | Returns 200 OK with `{"external_id": "...", "responders": []}` |
| Responder has multiple status updates | Statuses ordered chronologically by `created_at ASC`, `status_order ASC` | Status history array represents sequential timeline |
| Responder has no status events logged | `statuses` defaults to empty array `[]` | Returns responder with `"statuses": []` |
| Multiple responders for a single event | Responders ordered by `created_at ASC`, `id ASC` | Deterministic array ordering of units |

---

## 5. Executable Acceptance Criteria

### Verification Commands
- [ ] Backend test suite passes: `uv run python -m unittest discover packages/api/tests`
- [ ] Contract exported & TypeScript types synchronized: `./run-dev.sh spec:types`
- [ ] Web package builds with clean TypeScript check: `npm run build --prefix packages/web`
- [ ] Full SDD verification pipeline passes: `./run-dev.sh spec:verify`

### Behavior Checklist
- [ ] `packages/api/schemas.py` defines `ResponderStatusRead`, `ResponderRead`, and `EventRespondersEnvelope`.
- [ ] `packages/api/services/event_service.py` provides `get_responders_by_external_id(session, external_id)`.
- [ ] `packages/api/routers/events.py` registers `GET /events/{external_id}/responders` using handler function `get_event_responders`.
- [ ] Path parameter uses `external_id` (string), not integer database surrogate ID.
- [ ] Non-existent `external_id` returns HTTP 404 with `{"detail": "Event not found"}`.
- [ ] Existing event with no responders returns HTTP 200 with empty `responders` array in envelope.
- [ ] Existing event with responders returns HTTP 200 with responders and their status progression list.
- [ ] No database surrogate IDs (`id`, `responder_id`, `event_id`) are included in responder or status payloads.
- [ ] `current_status` is not present in responder payloads.
- [ ] `packages/api/openapi.json` includes `paths["/events/{external_id}/responders"]`.
- [ ] `packages/web/src/types/api.generated.ts` contains the generated types matching the new endpoint contract.
