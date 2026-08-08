from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from db.models import STATUS_ORDER, ActiveCall, Event


def dataclass_encoder(obj):
    if hasattr(obj, "__dataclass_fields__"):
        return {k: dataclass_encoder(v) for k, v in obj.__dict__.items()}
    elif isinstance(obj, list):
        return [dataclass_encoder(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: dataclass_encoder(v) for k, v in obj.items()}
    else:
        return obj


@dataclass
class GroupedResponder:
    unit: str
    agency: str
    dispatch_area: str
    statuses: list[str] = field(default_factory=list)


@dataclass
class GroupedEvent:
    external_id: str
    time_received: str
    call_type: str
    location: str
    responders: list[GroupedResponder] = field(default_factory=list)


def group_active_calls(calls: list[ActiveCall]) -> dict[str, GroupedEvent]:
    by_event = group_by_external_id(calls)

    grouped: dict[str, GroupedEvent] = {}
    for external_id, event_calls in by_event.items():
        first = event_calls[0][0]
        responders_map: dict[tuple[str, str, str], list[str]] = defaultdict(list)
        seen_statuses: dict[tuple[str, str, str], set[str]] = defaultdict(set)

        for call in event_calls:
            key = (call[0].unit, call[0].agency, call[0].dispatch_area)
            if call[0].status not in seen_statuses[key]:
                responders_map[key].append(call[0].status)
                seen_statuses[key].add(call[0].status)

        responders = [
            GroupedResponder(
                unit=unit,
                agency=agency,
                dispatch_area=dispatch_area,
                statuses=sorted(
                    statuses,
                    key=lambda s: STATUS_ORDER.get(s.upper(), 0),
                ),
            )
            for (unit, agency, dispatch_area), statuses in responders_map.items()
        ]

        grouped[external_id] = GroupedEvent(
            external_id=external_id,
            time_received=first.time_received,
            call_type=first.call_type,
            location=first.location,
            responders=responders,
        )

    return grouped


def group_by_external_id(
    calls: list[tuple[ActiveCall, datetime]],
) -> dict[str, list[tuple[ActiveCall, datetime]]]:
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
