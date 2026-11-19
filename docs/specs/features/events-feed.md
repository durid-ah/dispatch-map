---
feature: events-feed
title: Dispatch Events API & Searchable Live Feed
status: active
packages:
  - packages/api
  - packages/web
  - packages/db
source_files:
  - packages/api/routers/events.py
  - packages/api/services/event_service.py
  - packages/api/schemas.py
  - packages/web/src/pages/dispatch-page.tsx
  - packages/web/src/components/layout/app-header.tsx
  - packages/web/src/components/layout/app-layout.tsx
  - packages/web/src/features/events/api/get-events.ts
  - packages/web/src/features/events/api/use-events-query.ts
  - packages/web/src/features/events/api/query-keys.ts
  - packages/web/src/features/events/types/index.ts
  - packages/web/src/features/events/components/event-list.tsx
  - packages/web/src/features/events/components/event-card.tsx
  - packages/web/src/lib/formatters.ts
  - packages/web/src/lib/query-client.ts
tests:
  - packages/api/tests/test_api.py
---

# Dispatch Events API & Searchable Live Feed

## 1. Overview

The events feed exposes recent emergency dispatch incidents over REST (`GET /events`) and renders a live-polling, time-windowed, client-searchable sidebar list (`EventList` and `EventCard`) paired with the header controls (`AppHeader`) in `DispatchPage`.

## 2. Requirements & Behavior

### Backend Query & Ordering (`GET /events`)
- Accepts optional query parameter `hours` (integer, default `24`, constrained `1 <= hours <= 168`).
- `get_recent_events_with_coords()` computes `cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)`, left-outer-joins `Event` with `Location` on `Event.location_id == Location.id`, filters `Event.time_received >= cutoff`, and orders results newest-first (`Event.time_received DESC`).
- Returns `list[EventWithCoords]` combining event columns with joined `latitude` and `longitude` (nullable when unmapped).

### Header Controls & Live Polling
- `DispatchPage` defaults `hours` to `24` and queries via `useEventsQuery({ hours })`, which polls every `30` seconds (`refetchInterval: 30_000`) using `QueryClient` defaults (`staleTime: 30_000`, `refetchOnWindowFocus: false`, `retry: 2`).
- `AppHeader` displays:
  - Brand title (`911 Dispatch` / `Active Emergency CAD Calls`) and pulsing `LIVE` badge.
  - Total loaded call count badge (`<count> Calls`) when data is available.
  - Time range `<Select>` offering `Past 6 Hours` (`6`), `Past 12 Hours` (`12`), `Past 24 Hours` (`24`), `Past 48 Hours` (`48`), and `Past 7 Days` (`168`); changing the window updates `hours` and clears `selectedEventId`.
  - Manual refresh button invoking `refetch()`, disabled with a spinning icon while `isFetching` is true.

### Searchable Event Sidebar & Cards
- `EventList` renders a responsive left sidebar (`w-full md:w-[390px]`, `min-w-[320px]`, `max-w-[440px]`) containing:
  - Search input (`aria-label="Search dispatch events"`) filtering client-side (case-insensitive substring match) on `ev.call_type` and `ev.location`, with a clear (`X`) button when non-empty.
  - Result count label (`"{filtered} of {total} calls"` when searching, `"{total} calls recorded"` otherwise).
  - Scrollable list of `EventCard` items; `searchQuery` state is preserved inside `EventList` when transitioning to and back from [event-details-and-responders.md](event-details-and-responders.md).
- Each `EventCard` renders:
  - Keyboard-accessible clickable card (`role="button"`, `tabIndex={0}`, `Enter`/`Space` activation, `aria-pressed={isSelected}`, `data-event-id={event.id}`).
  - Call category badge styled by `getCallCategoryVariant(call_type)` (`fire`, `medical`, `traffic`, `police`), safely truncated (`max-w-[210px]`, `truncate`) with full `call_type` exposed in a native `title` tooltip.
  - Relative timestamp (`formatRelativeTime`) with localized `toLocaleString()` tooltip.
  - Incident street/intersection `location`.
  - Geocoding status pill (`📍 Mapped` when both `latitude` and `longitude` are non-null, otherwise `⏳ Pending`).

## 3. Interfaces & Contracts

- **API Endpoint (`packages/api/routers/events.py`)**:
  - `GET /events?hours=24` -> `200 OK` (`list[EventWithCoords]`) or `422 Unprocessable Entity` if `hours` violates `1..168`.
- **Backend Schema (`packages/api/schemas.py`)**:
  - `EventWithCoords`: `id`, `external_id`, `time_received`, `call_type`, `location`, `location_id`, `latitude`, `longitude`, `created_at`, `updated_at`.
- **Database Models**:
  - Reads `Event` and `Location` from `packages/db/src/db/models.py` (see [architecture.md](../architecture.md)).
- **Frontend Contracts & Modules**:
  - Generated schema alias `EventWithCoords` in `packages/web/src/features/events/types/index.ts` (derived from `packages/web/src/types/api.generated.ts`).
  - Query key `eventKeys.list({ hours })` (`['events', 'list', { hours }]`) in `packages/web/src/features/events/api/query-keys.ts`.
  - Fetcher `getEvents()` in `packages/web/src/features/events/api/get-events.ts` and hook `useEventsQuery()` in `packages/web/src/features/events/api/use-events-query.ts`.

## 4. Edge Cases & Failure Modes

| Scenario | System Behavior | Expected Outcome / UX |
|---|---|---|
| `hours` query param `< 1` or `> 168` | FastAPI `Query(ge=1, le=168)` rejects request | Returns `422 Unprocessable Entity` |
| Initial load in progress | `useEventsQuery` reports `isLoading: true` | `EventList` renders spinner and `"Fetching dispatch events..."` |
| API error or network offline | TanStack Query retries twice, then sets `isError: true` | `EventList` renders error message with `"Retry"` button calling `refetch()` |
| No events in timeframe | Backend returns `[]` | `EventList` renders `"No incidents recorded in this timeframe"` |
| Search query matches zero events | Client filter yields `[]` | `EventList` renders `No calls matching "<query>"` |
| Event lacks coordinates (`latitude` or `longitude` is `null`) | Outer join preserves row with null coords | Rendered in sidebar with `⏳ Pending` badge |

## 5. Verification

- **Automated Tests**:
  - `packages/api/tests/test_api.py` (`test_events_endpoint`): verifies `GET /events?hours=24` status `200`, list payload, `call_type`, and joined coordinates using in-memory SQLite.
  - Contract sync (`openapi-typescript --check`), TypeScript build (`tsc -b && vite build`), and linter (`oxlint`) run via `./run-dev.sh spec:verify`.
- **Manual Checks**:
  - Verify time-range switching (`6h`–`7d`), manual refresh spinner, long call-type badge truncation + hover tooltip, and search filtering in `packages/web`.

