from sqlmodel import create_engine, Session, select
from models import Event

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
        return self.session \
            .exec(select(Event).where(Event.external_id.in_(external_ids))) \
            .all()

    def __exit__(self, exc_type, exc_value, traceback):
        self.session.close()
        self.engine.dispose()
