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


class ResponderStatusRead(SQLModel):
    status: str
    status_order: int
    created_at: datetime


class ResponderRead(SQLModel):
    unit: str
    dispatch_area: str
    agency: str
    created_at: datetime
    statuses: list[ResponderStatusRead] = []


class EventRespondersEnvelope(SQLModel):
    external_id: str
    responders: list[ResponderRead] = []

