from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

# Ensure packages/api is on sys.path
API_DIR = Path(__file__).resolve().parent.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from database import get_session
from db.models import Event, Location, Responder, ResponderStatusEvent
from main import app


class ApiEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(cls.engine)

        now = datetime.now(timezone.utc)
        with Session(cls.engine) as s:
            loc = Location(
                id=1,
                raw_text="100 MAIN ST",
                latitude=37.54,
                longitude=-77.43,
                created_at=now,
                updated_at=now,
            )
            s.add(loc)
            s.commit()

            evt = Event(
                id=1,
                external_id="test_external_id_123",
                time_received=now,
                call_type="MEDICAL EMERGENCY",
                location="100 MAIN ST",
                location_id=loc.id,
                created_at=now,
                updated_at=now,
            )
            s.add(evt)
            s.commit()

            evt_empty = Event(
                id=2,
                external_id="test_external_id_empty",
                time_received=now,
                call_type="TRAFFIC ACCIDENT",
                location="100 MAIN ST",
                location_id=loc.id,
                created_at=now,
                updated_at=now,
            )
            s.add(evt_empty)
            s.commit()

            resp1 = Responder(
                id=1,
                event_id=evt.id,
                unit="E10",
                dispatch_area="FIRE",
                agency="RFD",
                created_at=now,
            )
            s.add(resp1)
            s.commit()

            se1 = ResponderStatusEvent(
                id=1,
                responder_id=resp1.id,
                status="DISPATCHED",
                status_order=1,
                created_at=now,
            )
            se2 = ResponderStatusEvent(
                id=2,
                responder_id=resp1.id,
                status="ENROUTE",
                status_order=2,
                created_at=now + timedelta(minutes=2),
            )
            se3 = ResponderStatusEvent(
                id=3,
                responder_id=resp1.id,
                status="ARRIVED",
                status_order=3,
                created_at=now + timedelta(minutes=5),
            )
            s.add_all([se1, se2, se3])
            s.commit()

            resp2 = Responder(
                id=2,
                event_id=evt.id,
                unit="MED1",
                dispatch_area="EMS",
                agency="RFD",
                created_at=now + timedelta(minutes=1),
            )
            s.add(resp2)
            s.commit()

            se4 = ResponderStatusEvent(
                id=4,
                responder_id=resp2.id,
                status="DISPATCHED",
                status_order=1,
                created_at=now + timedelta(minutes=1),
            )
            s.add(se4)
            s.commit()

            resp3 = Responder(
                id=3,
                event_id=evt.id,
                unit="BAT1",
                dispatch_area="FIRE",
                agency="RFD",
                created_at=now + timedelta(minutes=2),
            )
            s.add(resp3)
            s.commit()

        def override_get_session():
            with Session(cls.engine) as s:
                yield s

        app.dependency_overrides[get_session] = override_get_session
        cls.client = TestClient(app)

    def test_events_endpoint(self):
        res = self.client.get("/events?hours=24")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
        self.assertEqual(data[0]["call_type"], "MEDICAL EMERGENCY")
        self.assertEqual(data[0]["latitude"], 37.54)
        self.assertEqual(data[0]["longitude"], -77.43)

    def test_get_event_responders_success(self):
        res = self.client.get("/events/test_external_id_123/responders")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["external_id"], "test_external_id_123")
        responders = data["responders"]
        self.assertEqual(len(responders), 3)

        # Check first responder
        first_resp = responders[0]
        self.assertEqual(first_resp["unit"], "E10")
        self.assertEqual(first_resp["dispatch_area"], "FIRE")
        self.assertEqual(first_resp["agency"], "RFD")
        self.assertIn("created_at", first_resp)
        self.assertNotIn("id", first_resp)
        self.assertNotIn("event_id", first_resp)
        self.assertNotIn("current_status", first_resp)

        # Check status progression
        statuses = first_resp["statuses"]
        self.assertEqual(len(statuses), 3)
        self.assertEqual(statuses[0]["status"], "DISPATCHED")
        self.assertEqual(statuses[0]["status_order"], 1)
        self.assertEqual(statuses[1]["status"], "ENROUTE")
        self.assertEqual(statuses[1]["status_order"], 2)
        self.assertEqual(statuses[2]["status"], "ARRIVED")
        self.assertEqual(statuses[2]["status_order"], 3)
        self.assertNotIn("id", statuses[0])
        self.assertNotIn("responder_id", statuses[0])

        # Check third responder with no status events
        third_resp = responders[2]
        self.assertEqual(third_resp["unit"], "BAT1")
        self.assertEqual(third_resp["statuses"], [])


    def test_get_event_responders_empty(self):
        res = self.client.get("/events/test_external_id_empty/responders")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data, {"external_id": "test_external_id_empty", "responders": []})

    def test_get_event_responders_not_found(self):
        res = self.client.get("/events/non_existent_external_id/responders")
        self.assertEqual(res.status_code, 404)
        data = res.json()
        self.assertEqual(data, {"detail": "Event not found"})


if __name__ == "__main__":
    unittest.main()

