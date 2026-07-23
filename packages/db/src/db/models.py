import hashlib
from datetime import datetime

from sqlalchemy import BigInteger, CHAR, Column, DateTime, Double, text
from sqlmodel import Field, Relationship, SQLModel


STATUS_ORDER = {
    "DISPATCHED": 1,
    "ENROUTE": 2,
    "ARRIVED": 3,
}


def compute_external_id(
    time_received: str,
    call_type: str,
    location: str,
) -> str:
    key = "|".join((time_received, call_type, location))
    return hashlib.sha256(key.encode()).hexdigest()


class Location(SQLModel, table=True):
    __tablename__ = "locations"

    id: int | None = Field(default=None, sa_type=BigInteger, primary_key=True)
    raw_text: str = Field(unique=True)
    latitude: float | None = Field(default=None, sa_type=Double)
    longitude: float | None = Field(default=None, sa_type=Double)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
    )

    events: list[Event] = Relationship(back_populates="location_row")


class Event(SQLModel, table=True):
    __tablename__ = "events"

    id: int | None = Field(default=None, sa_type=BigInteger, primary_key=True)
    external_id: str = Field(sa_column=Column(CHAR(64), nullable=False, unique=True))
    time_received: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    call_type: str
    location: str
    location_id: int | None = Field(
        default=None,
        foreign_key="locations.id",
        sa_type=BigInteger,
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
    )

    location_row: Location | None = Relationship(back_populates="events")
    responders: list[Responder] = Relationship(back_populates="event")


class Responder(SQLModel, table=True):
    __tablename__ = "responders"

    id: int | None = Field(default=None, sa_type=BigInteger, primary_key=True)
    event_id: int = Field(foreign_key="events.id", sa_type=BigInteger)
    unit: str
    dispatch_area: str
    agency: str
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
    )

    event: Event = Relationship(back_populates="responders")
    status_events: list[ResponderStatusEvent] = Relationship(back_populates="responder")


class ResponderStatusEvent(SQLModel, table=True):
    __tablename__ = "responder_status_events"

    id: int | None = Field(default=None, sa_type=BigInteger, primary_key=True)
    responder_id: int = Field(foreign_key="responders.id", sa_type=BigInteger)
    status: str
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
    )

    responder: Responder = Relationship(back_populates="status_events")


class ActiveCall(SQLModel):
    """Flat record parsed from Richmond active calls HTML."""

    time_received: str
    agency: str
    dispatch_area: str
    unit: str
    call_type: str
    location: str
    status: str

    @property
    def external_id(self) -> str:
        return compute_external_id(
            self.time_received,
            self.call_type,
            self.location,
        )

    @property
    def call_id(self) -> str:
        return self.external_id

    @property
    def status_order(self) -> int:
        return STATUS_ORDER.get(self.status, 0)
