---
feature: event-details-and-responders
title: Event Details View & Responders Timeline
status: active
packages:
  - packages/api
  - packages/web
  - packages/db
source_files:
  - packages/api/routers/events.py
  - packages/api/services/event_service.py
  - packages/api/schemas.py
  - packages/web/src/features/events/api/get-event-responders.ts
  - packages/web/src/features/events/api/use-event-responders-query.ts
  - packages/web/src/features/events/api/query-keys.ts
  - packages/web/src/features/events/types/index.ts
  - packages/web/src/features/events/components/event-detail-card.tsx
  - packages/web/src/features/events/components/responder-card.tsx
  - packages/web/src/features/events/components/event-list.tsx
  - packages/web/src/pages/dispatch-page.tsx
  - packages/web/src/lib/formatters.ts
tests:
  - packages/api/tests/test_api.py
---

# Event Details View & Responders Timeline

## 1. Overview

Selecting an incident from either the event feed or the map transitions the sidebar into a full-height `EventDetailCard` displaying incident metadata alongside each assigned responder unit's chronological status timeline fetched from `GET /events/{external_id}/responders`.

## 2. Requirements & Behavior

### Backend Responders Endpoint (`GET /events/{external_id}/responders`)
- Accepts the incident's 64-character SHA-256 `external_id` path parameter (not surrogate `events.id`).
- `get_responders_by_external_id()` looks up the `Event` by `external_id`, returning `None` (mapped to HTTP `404` `{"detail": "Event not found"}`) when missing.
- Fetches responders and their status history in a single `outerjoin(ResponderStatusEvent, Responder.id == ResponderStatusEvent.responder_id)` query ordered deterministically by `Responder.created_at ASC`, `Responder.id ASC`, `ResponderStatusEvent.created_at ASC`, `ResponderStatusEvent.status_order ASC`.
- Returns `EventRespondersEnvelope` containing `external_id` and `responders`. Surrogate database keys (`id`, `event_id`, `responder_id`) and computed `current_status` fields are excluded from the API payload.

### Frontend Querying & View Transitions
- `EventList` renders `EventDetailCard` in place of the incident list whenever `activeEvent` is non-null, while retaining `searchQuery` state across transitions.
- Top action bar provides a sole `"All calls"` back button (`aria-label="Back to all calls"`) with a left arrow icon and the relative incident timestamp on the right (no secondary `'✕'` close button or external ID copy action).
- `DispatchPage` attaches a global `Escape` key listener that clears `selectedEventId` whenever an event is selected; changing the `hours` window in `AppHeader` also clears `selectedEventId`.
- `useEventRespondersQuery(event.external_id)` fetches responders when `externalId` is truthy, configured with `staleTime: 15_000` (15s) and `refetchInterval: 30_000` (30s).

### Incident Overview & Responder Timeline Cards
- **Incident Overview Card**: Displays the uppercase category-colored call-type badge, full street `location`, formatted full date/time (`formatFullDateTime`), and a coordinate badge (`📍 <lat.toFixed(4)>, <lng.toFixed(4)>` or `⏳ Pending Geocoding`).
- **Assigned Units Header**: Shows unit count (`"{count} Unit"` / `"{count} Units"`) once loaded.
- **`ResponderCard`**:
  - Displays `unit`, `agency`, and optional `dispatch_area` badges.
  - Sorts `responder.statuses` by `status_order ASC`, then `created_at ASC`, and derives the current status badge from the final entry (defaulting to `ASSIGNED` when empty): `ARRIVED` (emerald), `ENROUTE` (amber), `DISPATCHED` (sky), fallback muted style.
  - Renders a vertical status timeline stepper with each status label, exact local timestamp (`formatExactTime`), and step-to-step elapsed duration badge (`formatElapsedDuration`: `+Xs` or `+Xm Ys`).

## 3. Interfaces & Contracts

- **API Endpoint (`packages/api/routers/events.py`)**:
  - `GET /events/{external_id}/responders` -> `200 OK` (`EventRespondersEnvelope`), `404 Not Found` (`Event not found`), or `422 Unprocessable Entity`.
- **Backend Schemas (`packages/api/schemas.py`)**:
  - `ResponderStatusRead`: `status`, `status_order`, `created_at`.
  - `ResponderRead`: `unit`, `dispatch_area`, `agency`, `created_at`, `statuses: list[ResponderStatusRead]`.
  - `EventRespondersEnvelope`: `external_id`, `responders: list[ResponderRead]`.
- **Database Models**:
  - Reads `Event`, `Responder`, and `ResponderStatusEvent` from `packages/db/src/db/models.py` (see [architecture.md](../architecture.md)).
- **Frontend Contracts & Modules**:
  - Generated schema aliases `EventRespondersEnvelope`, `ResponderRead`, and `ResponderStatusRead` in `packages/web/src/features/events/types/index.ts`.
  - Query key `eventKeys.responders(externalId)` (`['events', 'responders', externalId]`) in `packages/web/src/features/events/api/query-keys.ts`.
  - Fetcher `getEventResponders()` in `packages/web/src/features/events/api/get-event-responders.ts` (throws `"Event not found: <externalId>"` on 404).
  - Hook `useEventRespondersQuery()` in `packages/web/src/features/events/api/use-event-responders-query.ts`.

## 4. Edge Cases & Failure Modes

| Scenario | System Behavior | Expected Outcome / UX |
|---|---|---|
| Unknown `external_id` requested | Service returns `None`; router raises HTTP `404` | Returns `{"detail": "Event not found"}`; fetcher surfaces `"Event not found: <externalId>"` |
| Event has zero responders | Service returns empty `responders: []` with `200 OK` | Renders `"No units dispatched"` empty state card |
| Responder has zero `status_events` | Outer join returns `(responder, None)`; `statuses` stays `[]` | Header status badge shows `ASSIGNED`; body renders `"No status progression recorded"` |
| Responders query loading | `useEventRespondersQuery` `isLoading: true` | Renders loading spinner and `"Fetching responding units…"` |
| Responders query error | `useEventRespondersQuery` `isError: true` | Renders error panel with error message and `"Retry"` button calling `refetch()` |
| User presses `Escape` or clicks `"All calls"` | `selectedEventId` resets to `null` | Returns to `EventList` with previous `searchQuery` intact |

## 5. Verification

- **Automated Tests**:
  - `packages/api/tests/test_api.py`:
    - `test_get_event_responders_success`: verifies envelope, chronological responder/status order, responder with empty `statuses`, and exclusion of `id`, `event_id`, `responder_id`, and `current_status`.
    - `test_get_event_responders_empty`: verifies `200 OK` with `responders: []`.
    - `test_get_event_responders_not_found`: verifies `404` with `{"detail": "Event not found"}`.
  - Contract sync (`openapi-typescript --check`), web build, and lint verified via `./run-dev.sh spec:verify`.
- **Manual Checks**:
  - Verify clicking list cards and map pins opens `EventDetailCard`, responder timeline durations render accurately, `"All calls"` and `Escape` restore the filtered feed, and `404`/network error states display cleanly.

