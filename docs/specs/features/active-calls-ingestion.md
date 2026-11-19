---
feature: active-calls-ingestion
title: Active Calls Ingestion & Status Tracking
status: active
packages:
  - packages/db
  - packages/dispatch-consumer
  - packages/migrations
source_files:
  - packages/db/src/db/models.py
  - packages/dispatch-consumer/main.py
  - packages/dispatch-consumer/config.py
  - packages/dispatch-consumer/models.py
  - packages/dispatch-consumer/database.py
  - packages/dispatch-consumer/processor.py
  - packages/dispatch-consumer/parser/__init__.py
  - packages/dispatch-consumer/scraper/__init__.py
  - packages/dispatch-consumer/scraper/richmond_active_calls.py
tests:
  - packages/db/tests/test_models.py
  - packages/dispatch-consumer/tests/test_parser.py
---

# Active Calls Ingestion & Status Tracking

## 1. Overview

The dispatch consumer worker continuously polls Richmond's public Active Calls HTML feed, parses incident and unit rows, groups responders under deterministic incident identities, geocodes locations, and persists incremental responder status progressions into PostgreSQL.

## 2. Requirements & Behavior

### Polling Loop & HTML Scraping
- `packages/dispatch-consumer/main.py` runs `poll_once()` every `45` seconds (`POLL_INTERVAL_SECONDS = 45`) until interrupted.
- `fetch_active_calls()` fetches `ACTIVE_CALLS_URL` using `httpx.Client(timeout=30.0)` with the configured `USER_AGENT` header and raises for non-2xx HTTP status codes.
- `_parse_active_calls_html()` parses the response with BeautifulSoup (`html.parser`), extracting:
  - An optional feed timestamp from `<p class="fs-6">` matching `As of <timestamp> - This page will refresh every 45 seconds`.
  - Rows inside `<table id="tblActiveCallsListing"><tbody>`, expecting `7` columns per row in order: `time_received`, `agency`, `dispatch_area`, `unit`, `call_type`, `location`, `status`.
- `parse_time_received()` parses `time_received` using format `%m/%d/%Y %H:%M`.

### Event Identity, Deduplication & Grouping
- Each `ActiveCall` computes `external_id` via `compute_external_id(time_received, call_type, location)` (`sha256(f"{time_received}|{call_type}|{location}")`).
- `group_by_external_id()` deduplicates exact rows within a poll cycle by `(external_id, unit, agency, dispatch_area, status)`.
- `parse_active_calls()` aggregates rows into `GroupedEvent` records keyed by `external_id`, containing `GroupedResponder` entries keyed by `(unit, agency, dispatch_area)` with deduplicated statuses sorted ascending by `STATUS_ORDER` (`DISPATCHED=1`, `ENROUTE=2`, `ARRIVED=3`, unknown `0`).

### Transactional Persistence & Monotonic Status Updates
- `process_grouped_events()` runs inside a single `DB(config.db_url)` context manager session that commits once at the end of the poll cycle and rolls back on any exception:
  1. Batch-fetches existing `Event` rows for all `external_id` values in the current poll.
  2. Resolves and caches a `Location` row (and coordinates via [location-geocoding.md](location-geocoding.md)) for each unique location text.
  3. For a new `external_id`, creates the `Event`, each `Responder`, and all initial `ResponderStatusEvent` rows.
  4. For an existing `Event`, loads its responders keyed by `(unit, agency, dispatch_area)`:
     - Creates any newly seen responder and its initial status rows.
     - For an existing responder, compares each incoming status's `status_order` against `db.latest_status(responder.id)` (highest `status_order`) and appends a new `ResponderStatusEvent` only when `latest is None or latest.status_order < status_order`.

## 3. Interfaces & Contracts

- **Configuration (`packages/dispatch-consumer/config.py`)**:
  - `DB_URL`: SQLAlchemy PostgreSQL connection string.
  - `ACTIVE_CALLS_URL`: Target Richmond Active Calls endpoint.
  - `USER_AGENT`: HTTP `User-Agent` header sent to the feed.
- **Database & Domain Models**:
  - Uses `Location`, `Event`, `Responder`, `ResponderStatusEvent`, `ActiveCall`, `STATUS_ORDER`, and `compute_external_id` defined in `packages/db/src/db/models.py` (see [architecture.md](../architecture.md)).
  - In-memory grouping dataclasses `GroupedEvent` and `GroupedResponder` in `packages/dispatch-consumer/models.py`.

## 4. Edge Cases & Failure Modes

| Scenario | System Behavior | Expected Outcome / UX |
|---|---|---|
| HTTP timeout, non-2xx status, or missing `#tblActiveCallsListing` / `tbody` | `scrape_active_calls()` catches `httpx.HTTPError` and `RichmondActiveCallsError`, logs error, returns `None` | Poll cycle aborts safely; worker retries after `45s` |
| HTML table row has `!= 7` `<td>` cells | Row is skipped during `_parse_active_calls_html` | Partial/spacer rows do not break ingestion |
| `time_received` does not match `%m/%d/%Y %H:%M` | `parse_time_received()` logs error and returns `None` | Parsing failure surfaces to `poll_once()` exception handler without committing partial writes |
| Duplicate unit/status row appears in the same HTML snapshot | `group_by_external_id()` filters on `(external_id, unit, agency, dispatch_area, status)` | Duplicate row is ignored; no redundant status events created |
| Responder appears again with the same or lower `status_order` | `update_existing_responders()` skips insert when `latest.status_order >= status_order` | Status history remains strictly forward-progressing and duplicate-free |
| Unhandled exception during DB writes | `DB.__exit__` rolls back transaction and closes session/engine | Zero partial event or responder writes persisted; worker stays alive for next poll |

## 5. Verification

- **Automated Tests**:
  - `packages/db/tests/test_models.py`: verifies `compute_external_id` determinism, `STATUS_ORDER` values, `ActiveCall` derived properties, and relational foreign keys/relationships.
  - `packages/dispatch-consumer/tests/test_parser.py`: verifies `parse_time_received`, deduplication in `group_by_external_id`, and CSV fixture parsing via `parse_active_calls`.
  - Run via `./run-dev.sh spec:verify` (or `uv run python -m unittest discover packages/db/tests` and `packages/dispatch-consumer/tests`).
- **Known Test Coverage Notes**:
  - `scraper/richmond_active_calls.py` HTML parsing and `processor.py` DB persistence are verified through end-to-end consumer runs; unit tests currently target `models.py` and `parser/`.

