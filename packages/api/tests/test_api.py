from datetime import datetime, timezone
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
from db.models import Event, Location
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

        def override_get_session():
            with Session(cls.engine) as s:
                yield s

        app.dependency_overrides[get_session] = override_get_session
        cls.client = TestClient(app)

    def test_item_detail(self):
        res = self.client.get("/items/1?q=test")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"item_id": 1, "q": "test"})

    def test_item_stream(self):
        res = self.client.get("/items/stream")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/event-stream", res.headers["content-type"])

    def test_events_endpoint(self):
        res = self.client.get("/events?hours=24")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
        self.assertEqual(data[0]["call_type"], "MEDICAL EMERGENCY")
        self.assertEqual(data[0]["latitude"], 37.54)
        self.assertEqual(data[0]["longitude"], -77.43)

    def test_static_stream_file(self):
        res = self.client.get("/static/stream.html")
        self.assertEqual(res.status_code, 200)
        self.assertIn("<!DOCTYPE html>", res.text)


if __name__ == "__main__":
    unittest.main()
