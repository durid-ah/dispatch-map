from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from db.models import Event, Location, Responder, ResponderStatusEvent
from schemas import (
    EventRespondersEnvelope,
    EventWithCoords,
    ResponderRead,
    ResponderStatusRead,
)


def get_recent_events_with_coords(
    session: Session,
    hours: int = 24,
) -> list[EventWithCoords]:
    """Fetch events received within the past `hours` with joined coordinates."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    statement = (
        select(Event, Location.latitude, Location.longitude)
        .outerjoin(Location, Event.location_id == Location.id)
        .where(Event.time_received >= cutoff)
        .order_by(Event.time_received.desc())
    )
    rows = session.exec(statement).all()
    return [
        EventWithCoords(
            id=event.id,
            external_id=event.external_id,
            time_received=event.time_received,
            call_type=event.call_type,
            location=event.location,
            location_id=event.location_id,
            latitude=latitude,
            longitude=longitude,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )
        for event, latitude, longitude in rows
    ]


def get_responders_by_external_id(
    session: Session,
    external_id: str,
) -> EventRespondersEnvelope | None:
    """Fetch all responders and their status timeline for a given event external_id."""
    statement = select(Event).where(Event.external_id == external_id)
    event = session.exec(statement).first()
    if event is None:
        return None

    # Fetch all responders and their status events in a single joined query to avoid N+1
    statement = (
        select(Responder, ResponderStatusEvent)
        .outerjoin(
            ResponderStatusEvent,
            Responder.id == ResponderStatusEvent.responder_id,
        )
        .where(Responder.event_id == event.id)
        .order_by(
            Responder.created_at.asc(),
            Responder.id.asc(),
            ResponderStatusEvent.created_at.asc(),
            ResponderStatusEvent.status_order.asc(),
        )
    )
    rows = session.exec(statement).all()

    responders_by_id: dict[int, ResponderRead] = {}
    for responder, status_event in rows:
        if responder.id not in responders_by_id:
            responders_by_id[responder.id] = ResponderRead(
                unit=responder.unit,
                dispatch_area=responder.dispatch_area,
                agency=responder.agency,
                created_at=responder.created_at,
                statuses=[],
            )
        if status_event is not None:
            responders_by_id[responder.id].statuses.append(
                ResponderStatusRead(
                    status=status_event.status,
                    status_order=status_event.status_order,
                    created_at=status_event.created_at,
                )
            )

    return EventRespondersEnvelope(
        external_id=event.external_id,
        responders=list(responders_by_id.values()),
    )


