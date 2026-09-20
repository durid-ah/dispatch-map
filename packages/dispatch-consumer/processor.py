import logging

from models import STATUS_ORDER, GroupedEvent, Event, GroupedResponder, Responder
from database import DB
from db.models import Location
from config import config
from geocoder import geocode_location

logger = logging.getLogger(__name__)

def process_grouped_events(grouped: dict[str, GroupedEvent]) -> None:
    with DB(config.db_url) as db:
        events = db.get_events(list(grouped.keys()))
        existing = group_existing_events(events)

        geocoded: dict[str, Location] = {}
        for grouped_event in grouped.values():
            if grouped_event.location not in geocoded:
                geocoded[grouped_event.location] = ensure_geocoded_location(
                    db, grouped_event.location
                )

        for external_id, grouped_event in grouped.items():
            event = existing.get(external_id)
            if event is None:
                event = handle_new_event(
                    db, grouped_event, geocoded[grouped_event.location]
                )
                for responder_group in grouped_event.responders:
                    handle_new_responder(db, event, responder_group)
            else:
                handle_existing_event(db, event, grouped_event)
        
        db.commit()


def group_existing_events(events: list[Event]) -> dict[str, Event]:
    grouped: dict[str, Event] = {}
    for event in events:
        grouped[event.external_id] = event

    return grouped

def ensure_geocoded_location(db: DB, raw_text: str) -> Location:
    location = db.get_or_create_location(raw_text)
    if location.latitude is not None and location.longitude is not None:
        return location

    coords = geocode_location(raw_text)
    if coords is None:
        return location

    return db.update_location_coordinates(location, coords[0], coords[1])


def handle_new_event(db: DB, grouped_event: GroupedEvent, location: Location) -> Event:
    return db.create_event(
        external_id=grouped_event.external_id,
        time_received=grouped_event.parsed_time,
        call_type=grouped_event.call_type,
        location=grouped_event.location,
        location_id=location.id,
    )

def handle_existing_event(db: DB, event: Event, grouped_event: GroupedEvent) -> None:
    by_key = group_responders(db.get_responders_for_event(event.id))
    for responder_group in grouped_event.responders:
        key = (
            responder_group.unit,
            responder_group.agency,
            responder_group.dispatch_area,
        )
        responder = by_key.get(key)
        if responder is None:
            handle_new_responder(db, event, responder_group)
        else:
            update_existing_responders(db, grouped_event, responder, responder_group)

def update_existing_responders(
    db: DB,
    grouped_event: GroupedEvent,
    responder: Responder,
    responder_group: GroupedResponder,
):
    for status in responder_group.statuses:
        status_order = STATUS_ORDER.get(status.upper(), 0)
        latest = db.latest_status(responder.id)
        if latest is None or latest.status_order < status_order:
            logger.info(
                "Create: call: %s; responder: %s; status: %s",
                grouped_event.call_type,
                responder_group.unit + " " + responder_group.agency,
                status,
            )
            db.create_status_event(responder.id, status)
        else:
            logger.info(
                "Responder %s has latest status %s",
                responder.id,
                latest.status,
            )

def handle_new_responder(db: DB, event: Event, responder_group: GroupedResponder) -> None:
    responder = db.create_responder(
        event_id=event.id,
        unit=responder_group.unit,
        dispatch_area=responder_group.dispatch_area,
        agency=responder_group.agency,
    )

    for status in responder_group.statuses:
        db.create_status_event(responder.id, status)

def group_responders(responders: list[Responder]) -> dict[tuple[str, str, str], Responder]:
    by_key = {
        (r.unit, r.agency, r.dispatch_area): r for r in responders
    }
    return by_key