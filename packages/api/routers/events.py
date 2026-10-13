from fastapi import APIRouter, HTTPException, Query

from database import SessionDep
from schemas import EventRespondersEnvelope, EventWithCoords
from services.event_service import (
    get_recent_events_with_coords,
    get_responders_by_external_id,
)

router = APIRouter(tags=["events"])


@router.get("/events", response_model=list[EventWithCoords])
def get_recent_events(
    session: SessionDep,
    hours: int = Query(default=24, ge=1, le=168),
) -> list[EventWithCoords]:
    return get_recent_events_with_coords(session=session, hours=hours)


@router.get(
    "/events/{external_id}/responders",
    response_model=EventRespondersEnvelope,
    responses={404: {"description": "Event not found"}},
)
def get_event_responders(
    external_id: str,
    session: SessionDep,
) -> EventRespondersEnvelope:
    envelope = get_responders_by_external_id(session=session, external_id=external_id)
    if envelope is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return envelope

