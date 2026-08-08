from collections import defaultdict
from datetime import datetime

from models import ActiveCall, STATUS_ORDER, GroupedResponder, GroupedEvent
from scraper import parse_time_received
def parse_active_calls(
    calls: list[tuple[ActiveCall, datetime]],
) -> dict[str, GroupedEvent]:
    by_event = group_by_external_id(calls)

    grouped: dict[str, GroupedEvent] = {}
    for external_id, event_calls in by_event.items():
        first_call = event_calls[0]
        responders_map: dict[tuple[str, str, str], list[str]] = defaultdict(list)
        seen_statuses: dict[tuple[str, str, str], set[str]] = defaultdict(set)

        for call in event_calls:
            key = (call.unit, call.agency, call.dispatch_area)
            if call.status not in seen_statuses[key]:
                responders_map[key].append(call.status)
                seen_statuses[key].add(call.status)

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
            time_received=first_call.time_received,
            parsed_time= parse_time_received(first_call.time_received),
            call_type=first_call.call_type,
            location=first_call.location,
            responders=responders,
        )

    return grouped


def group_by_external_id(
    calls: list[ActiveCall],
) -> dict[str, list[ActiveCall]]:
    grouped: dict[str, list[ActiveCall]] = defaultdict(list)
    # Use a set to track seen (external_id, unit, agency) keys to avoid duplicates
    seen = set()
    for call in calls:
        key = (call.external_id, call.unit, call.agency, call.dispatch_area, call.status)
        if key not in seen:
            grouped[call.external_id].append(call)
            seen.add(key)

    return grouped