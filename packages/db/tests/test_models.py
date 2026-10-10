from datetime import datetime, timezone
import hashlib
import unittest

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from db.models import (
    ActiveCall,
    Event,
    Location,
    Responder,
    ResponderStatusEvent,
    STATUS_ORDER,
    compute_external_id,
)


class ModelContractTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

    def test_compute_external_id_determinism(self):
        time_rcv = "2026-10-10 12:00:00"
        call_type = "STRUCTURE FIRE"
        location = "500 E BROAD ST"

        expected_hash = hashlib.sha256(
            f"{time_rcv}|{call_type}|{location}".encode()
        ).hexdigest()

        computed = compute_external_id(time_rcv, call_type, location)
        self.assertEqual(computed, expected_hash)
        self.assertEqual(len(computed), 64)

    def test_status_order_values(self):
        self.assertEqual(STATUS_ORDER["DISPATCHED"], 1)
        self.assertEqual(STATUS_ORDER["ENROUTE"], 2)
        self.assertEqual(STATUS_ORDER["ARRIVED"], 3)

    def test_active_call_derived_properties(self):
        call = ActiveCall(
            time_received="2026-10-10 12:00:00",
            agency="RFD",
            dispatch_area="FIRE",
            unit="E1",
            call_type="STRUCTURE FIRE",
            location="500 E BROAD ST",
            status="ARRIVED",
        )
        self.assertEqual(call.call_id, call.external_id)
        self.assertEqual(call.status_order, 3)

    def test_relational_hierarchy_and_foreign_keys(self):
        now = datetime.now(timezone.utc)
        with Session(self.engine) as session:
            loc = Location(
                id=1,
                raw_text="123 MAIN ST",
                latitude=37.54,
                longitude=-77.43,
                created_at=now,
                updated_at=now,
            )
            session.add(loc)
            session.commit()

            evt = Event(
                id=1,
                external_id=compute_external_id("2026-10-10 12:00:00", "FIRE", "123 MAIN ST"),
                time_received=now,
                call_type="FIRE",
                location="123 MAIN ST",
                location_id=loc.id,
                created_at=now,
                updated_at=now,
            )
            session.add(evt)
            session.commit()

            resp = Responder(
                id=1,
                event_id=evt.id,
                unit="E10",
                dispatch_area="FIRE",
                agency="RFD",
                created_at=now,
            )
            session.add(resp)
            session.commit()

            status = ResponderStatusEvent(
                id=1,
                responder_id=resp.id,
                status="ENROUTE",
                status_order=2,
                created_at=now,
            )
            session.add(status)
            session.commit()

            # Query back to test relationships
            queried_event = session.exec(select(Event).where(Event.id == evt.id)).one()
            self.assertEqual(queried_event.location_row.raw_text, "123 MAIN ST")
            self.assertEqual(len(queried_event.responders), 1)
            self.assertEqual(queried_event.responders[0].unit, "E10")
            self.assertEqual(len(queried_event.responders[0].status_events), 1)
            self.assertEqual(queried_event.responders[0].status_events[0].status, "ENROUTE")


if __name__ == "__main__":
    unittest.main()
