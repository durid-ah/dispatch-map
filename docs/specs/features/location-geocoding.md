---
feature: location-geocoding
title: Location Normalization & Nominatim Geocoding
status: active
packages:
  - packages/db
  - packages/dispatch-consumer
source_files:
  - packages/dispatch-consumer/geocoder.py
  - packages/dispatch-consumer/processor.py
  - packages/dispatch-consumer/database.py
  - packages/dispatch-consumer/config.py
  - packages/db/src/db/models.py
tests: []
---

# Location Normalization & Nominatim Geocoding

## 1. Overview

The location geocoding pipeline converts Richmond CAD street and intersection strings into WGS84 latitude/longitude coordinates via a Nominatim search service and caches resolved results in PostgreSQL so incidents can be plotted on the map without redundant lookups.

## 2. Requirements & Behavior

### CAD Location Text Normalization
`normalize_location_query(raw_text)` transforms raw CAD location text before querying Nominatim:
1. Trims surrounding whitespace.
2. Removes a trailing `RICH` jurisdiction suffix (case-insensitive).
3. Strips CAD block markers such as `2600-BLK` or `2600 BLK` down to the street number (`2600`).
4. Replaces intersection slashes `/` with ` and `.
5. Lowercases numeric ordinal suffixes (`1ST`, `2ND`, `3RD`, `4TH` -> `1st`, `2nd`, `3rd`, `4th`).
6. Expands directional abbreviations (`N`, `S`, `E`, `W`, `NE`, `NW`, `SE`, `SW`) and street suffixes (`ST`, `AVE`, `RD`, `BLVD`, `DR`, `LN`, `CT`, `PL`, `CIR`, `TER`, `PKWY`, `HWY`, `TPKE`, `TP`, `EXPY`, `ALY`).
7. Appends `config.geocode_city` (default `"Richmond, VA"`) when not already present in the normalized string.

### Bounded Nominatim Search
`geocode_location(raw_text)` sends an HTTP `GET` request to `config.nominatim_url` (default `http://localhost:8091/search`) with:
- Query parameters: `q=<normalized_query>`, `format=json`, `limit=1`, `countrycodes=us`, `viewbox=-77.65,37.65,-77.25,37.40`, `bounded=1`.
- Headers: `User-Agent` (configured value or fallback `"dispatch-map/0.1"`) and `Accept-Language: en`.
- Timeout: `15.0` seconds.

### Three-Tier Caching Strategy
During `process_grouped_events()` (see [active-calls-ingestion.md](active-calls-ingestion.md)), `ensure_geocoded_location()` avoids duplicate Nominatim calls across three layers:
1. **Per-poll batch map**: `geocoded[grouped_event.location]` deduplicates repeated locations within the same poll cycle.
2. **PostgreSQL `locations` table**: `db.get_or_create_location(raw_text)` looks up or inserts a row keyed by unique `raw_text`. If `latitude` and `longitude` are already non-null, Nominatim is skipped; otherwise `db.update_location_coordinates()` persists resolved coordinates and refreshes `updated_at`.
3. **In-memory negative cache**: Process-lifetime `_unmatched_queries` set records normalized queries that returned empty results (`[]`) from Nominatim so unresolved addresses are not re-queried on every 45s poll.

## 3. Interfaces & Contracts

- **Configuration (`packages/dispatch-consumer/config.py`)**:
  - `NOMINATIM_URL`: Search endpoint URL (default `http://localhost:8091/search`; Docker Compose defaults to `http://host.docker.internal:8091/search`).
  - `GEOCODE_CITY`: City/state suffix appended when absent (default `"Richmond, VA"`).
  - `USER_AGENT`: HTTP `User-Agent` sent to Nominatim.
- **Database Model**:
  - `Location` table (`locations`) in `packages/db/src/db/models.py` storing `raw_text` (`UNIQUE`), nullable `latitude`/`longitude` (`double precision`), `created_at`, and `updated_at` (see [architecture.md](../architecture.md)).

## 4. Edge Cases & Failure Modes

| Scenario | System Behavior | Expected Outcome / UX |
|---|---|---|
| Empty or whitespace-only normalized query | `geocode_location()` returns `None` immediately | Event is saved with `location_id` pointing to `Location(latitude=None, longitude=None)`; UI displays `⏳ Pending` |
| Nominatim returns `[]` (no match) | Query is added to `_unmatched_queries`; returns `None` | Subsequent polls skip querying that address until worker restart; event persists without coordinates |
| Nominatim HTTP error, timeout, or invalid JSON | Logged as error; query is **not** added to `_unmatched_queries`; returns `None` | Transient Nominatim outages are retried on future poll cycles |
| Nominatim result has missing or non-numeric `lat`/`lon` | Caught `(KeyError, TypeError, ValueError)`, logged, returns `None` | Location remains ungeocoded without crashing the poll cycle |

## 5. Verification

- **Automated Tests**:
  - Dedicated unit tests for `normalize_location_query()` and `geocode_location()` are not yet present (`tests: []`); adding mocked `httpx` and CAD string normalization tests is recommended before modifying normalization rules.
- **Manual Checks**:
  - Run consumer against a local Nominatim instance and inspect `locations` rows for populated `latitude`/`longitude` values and expected `⏳ Pending` vs `📍 Mapped` state in the UI.

