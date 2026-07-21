from collections import defaultdict
from datetime import datetime
from db.models import ActiveCall, Event

def group_by_external_id(calls: list[tuple[ActiveCall, datetime]]) -> dict[str, list[tuple[ActiveCall, datetime]]]:
    grouped: dict[str, list[tuple[ActiveCall, datetime]]] = defaultdict(list)
    for call, parsed_time in calls:
        grouped[call.external_id].append((call, parsed_time))

    return grouped

def group_existing_events(events: list[Event]) -> dict[str, Event]:
    grouped: dict[str, Event] = {}
    for event in events:
        grouped[event.external_id] = event

    return grouped