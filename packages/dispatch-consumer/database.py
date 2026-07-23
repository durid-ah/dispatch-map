from datetime import datetime

from sqlmodel import Session, create_engine, select

from db.models import Event, Location, Responder, ResponderStatusEvent


class DB:
    url: str
    session: Session

    def __init__(self, url: str):
        self.url = url

    def __enter__(self):
        self.engine = create_engine(self.url)
        self.session = Session(self.engine)
        return self

    def get_events(self, external_ids: list[str]) -> list[Event]:
        if not external_ids:
            return []
        return list(
            self.session.exec(
                select(Event).where(Event.external_id.in_(external_ids))
            ).all()
        )

    def get_or_create_location(self, raw_text: str) -> Location:
        location = self.session.exec(
            select(Location).where(Location.raw_text == raw_text)
        ).first()
        if location is not None:
            return location

        location = Location(raw_text=raw_text)
        self.session.add(location)
        self.session.flush()
        return location

    def create_event(
        self,
        *,
        external_id: str,
        time_received: datetime,
        call_type: str,
        location: str,
        location_id: int | None,
    ) -> Event:
        event = Event(
            external_id=external_id,
            time_received=time_received,
            call_type=call_type,
            location=location,
            location_id=location_id,
        )
        self.session.add(event)
        self.session.flush()
        return event

    def get_responders_for_event(self, event_id: int) -> list[Responder]:
        return list(
            self.session.exec(
                select(Responder).where(Responder.event_id == event_id)
            ).all()
        )

    def create_responder(
        self,
        *,
        event_id: int,
        unit: str,
        dispatch_area: str,
        agency: str,
    ) -> Responder:
        responder = Responder(
            event_id=event_id,
            unit=unit,
            dispatch_area=dispatch_area,
            agency=agency,
        )
        self.session.add(responder)
        self.session.flush()
        return responder

    def create_status_event(
        self,
        responder_id: int,
        status: str,
    ) -> ResponderStatusEvent:
        status_event = ResponderStatusEvent(
            responder_id=responder_id,
            status=status,
        )
        self.session.add(status_event)
        self.session.flush()
        return status_event

    def latest_status(self, responder_id: int) -> str | None:
        status_event = self.session.exec(
            select(ResponderStatusEvent)
            .where(ResponderStatusEvent.responder_id == responder_id)
            .order_by(ResponderStatusEvent.created_at.desc())
            .limit(1)
        ).first()
        
        if status_event is None:
            return None
        return status_event.status

    def commit(self) -> None:
        self.session.commit()

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            self.session.rollback()
        self.session.close()
        self.engine.dispose()
