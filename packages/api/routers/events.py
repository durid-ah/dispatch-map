from fastapi import APIRouter, Query

from database import SessionDep
from schemas import EventWithCoords
from services.event_service import get_recent_events_with_coords

router = APIRouter(tags=["events"])


@router.get("/events", response_model=list[EventWithCoords])
def get_recent_events(
    session: SessionDep,
    hours: int = Query(default=24, ge=1, le=168),
) -> list[EventWithCoords]:
    return get_recent_events_with_coords(session=session, hours=hours)
