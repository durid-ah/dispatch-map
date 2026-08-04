from collections import defaultdict
from datetime import datetime
from db.models import ActiveCall, Event

def group_by_external_id(calls: list[tuple[ActiveCall, datetime]]) -> dict[str, list[tuple[ActiveCall, datetime]]]:
    grouped: dict[str, list[tuple[ActiveCall, datetime]]] = defaultdict(list)
    # Use a set to track seen (external_id, unit, agency) keys to avoid duplicates
    seen = set()
    for call, parsed_time in calls:
        key = (call.external_id, call.unit, call.agency, call.dispatch_area, call.status)
        if key not in seen:
            grouped[call.external_id].append((call, parsed_time))
            seen.add(key)
  
    return grouped

def group_existing_events(events: list[Event]) -> dict[str, Event]:
    grouped: dict[str, Event] = {}
    for event in events:
        grouped[event.external_id] = event

    return grouped