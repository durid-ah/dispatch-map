---
feature: interactive-map
title: Interactive Leaflet Dispatch Map & Markers
status: active
packages:
  - packages/web
source_files:
  - packages/web/src/features/map/components/dispatch-map.tsx
  - packages/web/src/features/map/components/event-marker.tsx
  - packages/web/src/pages/dispatch-page.tsx
tests: []
---

# Interactive Leaflet Dispatch Map & Markers

## 1. Overview

The interactive map renders geocoded emergency dispatch incidents on a Leaflet map centered on Richmond, Virginia, using color-coded pulsing markers that stay synchronized with event selection in the sidebar.

## 2. Requirements & Behavior

### Map Viewport & Responsive Layout
- `DispatchPage` arranges `EventList` and `DispatchMap` in a responsive split container (`flex-col-reverse md:flex-row`), placing the map above the feed on mobile viewports and to the right of the sidebar on desktop (`md` and above).
- `DispatchMap` initializes a `react-leaflet` `MapContainer` with:
  - Default center `[37.5407, -77.436]` (Richmond, VA) and default zoom `12`.
  - Scroll-wheel zoom enabled (`scrollWheelZoom={true}`).
  - OpenStreetMap `TileLayer` (`https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`).

### Coordinate Filtering & Category Markers
- `DispatchMap` filters `events` down to `mappedEvents` where both `latitude` and `longitude` are finite numbers (`typeof === 'number'` and `!Number.isNaN(...)`).
- Each mapped incident renders an `EventMarker` with a custom `24x24` `L.divIcon` (`iconAnchor: [12, 12]`, `popupAnchor: [0, -14]`) containing a pulsing ring and solid center dot colored by `call_type`:
  - `fire` (`fire`, `alarm`, `smoke`): `#ef4444`
  - `medical` (`med`, `ems`, `cardiac`, `injury`): `#10b981`
  - `traffic` (`traffic`, `accident`, `crash`): `#f59e0b`
  - `police` (all other call types): `#3b82f6`

### Selection Synchronization & Camera Control
- Clicking an `EventMarker` invokes `onSelectEvent(event)`, updating `selectedEventId` in `DispatchPage` and opening the incident detail view ([event-details-and-responders.md](event-details-and-responders.md)).
- When `isSelected` is true on a marker, its icon receives the `marker-selected` wrapper CSS class.
- `MapController` watches `selectedEvent` (derived from `mappedEvents` matching `selectedEventId`) and smoothly animates the map camera via `map.flyTo([latitude, longitude], 15, { duration: 1.2 })`.

## 3. Interfaces & Contracts

- **Component Props**:
  - `DispatchMapProps`: `events?: EventWithCoords[]`, `selectedEventId?: number | null`, `onSelectEvent?: (event: EventWithCoords) => void`, `center?: [number, number]`, `zoom?: number`, `className?: string`.
  - `EventMarkerProps`: `event: EventWithCoords & { latitude: number; longitude: number }`, `isSelected?: boolean`, `onSelect?: (event: EventWithCoords) => void`.
- **Types**:
  - Consumes `EventWithCoords` from `packages/web/src/features/events/types/index.ts`.

## 4. Edge Cases & Failure Modes

| Scenario | System Behavior | Expected Outcome / UX |
|---|---|---|
| Event has `null` or `NaN` coordinates | Excluded by `mappedEvents` filter in `DispatchMap` | Omitted from map without runtime Leaflet errors; remains visible in `EventList` |
| User selects an ungeocoded event from `EventList` | `selectedEvent` in `DispatchMap` resolves to `null` | Map viewport remains unchanged while sidebar shows detail view with `⏳ Pending Geocoding` |
| Empty `events` array | `mappedEvents` is `[]` | Map renders base OpenStreetMap tiles centered on Richmond, VA |

## 5. Verification

- **Automated Tests**:
  - TypeScript compilation and linting of map components are verified via `./run-dev.sh spec:verify` (`tsc -b && vite build` and `oxlint`).
  - No component unit/DOM tests currently exist (`tests: []`).
- **Manual Checks**:
  - Run `./run-dev.sh web` and confirm category colors, marker click selection, and `flyTo` zoom behavior when selecting events from either the map or sidebar.

