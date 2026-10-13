from datetime import datetime

from sqlmodel import SQLModel


class EventWithCoords(SQLModel):
    id: int
    external_id: str
    time_received: datetime
    call_type: str
    location: str
    location_id: int | None
    latitude: float | None
    longitude: float | None
    created_at: datetime
    updated_at: datetime
