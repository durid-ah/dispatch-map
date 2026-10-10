import csv
from datetime import datetime
from pathlib import Path
import sys
import unittest

CONSUMER_DIR = Path(__file__).resolve().parent.parent
if str(CONSUMER_DIR) not in sys.path:
    sys.path.insert(0, str(CONSUMER_DIR))

from models import ActiveCall, GroupedEvent, GroupedResponder
from parser import group_by_external_id, parse_active_calls
from scraper.richmond_active_calls import parse_time_received


class ConsumerParserTests(unittest.TestCase):
    def test_parse_time_received_valid_and_invalid(self):
        dt = parse_time_received("07/04/2026 14:50")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 7)
        self.assertEqual(dt.day, 4)
        self.assertEqual(dt.hour, 14)
        self.assertEqual(dt.minute, 50)

        invalid = parse_time_received("invalid-date-string")
        self.assertIsNone(invalid)

    def test_group_by_external_id_deduplicates_exact_calls(self):
        call1 = ActiveCall(
            time_received="07/04/2026 14:50",
            agency="RPD",
            dispatch_area="Precinct 2",
            unit="250",
            call_type="TEST CALL",
            location="100 MAIN ST",
            status="Enroute",
        )
        call2 = ActiveCall(
            time_received="07/04/2026 14:50",
            agency="RPD",
            dispatch_area="Precinct 2",
            unit="250",
            call_type="TEST CALL",
            location="100 MAIN ST",
            status="Enroute",
        )
        grouped = group_by_external_id([call1, call2])
        self.assertEqual(len(grouped[call1.external_id]), 1)

    def test_parse_active_calls_from_csv_fixture(self):
        repo_root = CONSUMER_DIR.parent.parent
        csv_path = repo_root / "test_data" / "active_calls_2026-07-04_21-58-29.csv"
        self.assertTrue(csv_path.exists(), f"Fixture file not found: {csv_path}")

        calls: list[ActiveCall] = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                calls.append(ActiveCall(**row))

        self.assertGreater(len(calls), 0)

        grouped_events = parse_active_calls(calls)
        self.assertIsInstance(grouped_events, dict)
        self.assertGreater(len(grouped_events), 0)

        for ext_id, event in grouped_events.items():
            self.assertEqual(ext_id, event.external_id)
            self.assertIsInstance(event, GroupedEvent)
            self.assertIsNotNone(event.parsed_time)
            self.assertTrue(len(event.responders) > 0)
            for resp in event.responders:
                self.assertIsInstance(resp, GroupedResponder)
                self.assertTrue(len(resp.statuses) > 0)


if __name__ == "__main__":
    unittest.main()
