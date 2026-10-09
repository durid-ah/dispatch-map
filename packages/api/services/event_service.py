from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from db.models import Event, Location
from schemas import EventWithCoords


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
