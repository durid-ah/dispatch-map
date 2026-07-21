from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime

import httpx

from richmond_active_calls import (
    RichmondActiveCallsError,
    fetch_active_calls,
    parse_time_received,
)
from db.models import ActiveCall
from config import config
from database import DB

POLL_INTERVAL_SECONDS = 45

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Starting Richmond active calls consumer")
    logger.info("Source URL: %s", config.active_calls_url)
    logger.info("Poll interval: %ss", POLL_INTERVAL_SECONDS)

    try:
        while True:
            poll_once()
            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logger.info("Shutting down")


def poll_once() -> None:
    try:
        calls, as_of = fetch_active_calls()
    except (httpx.HTTPError, RichmondActiveCallsError) as exc:
        logger.error("Failed to fetch active calls: %s", exc)
        return

    logger.info("Fetched %s active call(s) as of %s", len(calls), as_of)
    persist(calls)


def persist(calls: list[ActiveCall]) -> None:
    valid_calls: list[tuple[ActiveCall, datetime]] = []
    for call in calls:
        parsed_time = parse_time_received(call.time_received)
        if parsed_time is None:
            continue
        valid_calls.append((call, parsed_time))

    if not valid_calls:
        logger.info("No valid calls to persist")
        return

    grouped: dict[str, list[tuple[ActiveCall, datetime]]] = defaultdict(list)
    for call, parsed_time in valid_calls:
        grouped[call.external_id].append((call, parsed_time))

    new_events = 0
    new_responders = 0
    status_updates = 0

    with DB(config.db_url) as db:
        existing = {
            event.external_id: event
            for event in db.get_events(list(grouped.keys()))
        }

        for external_id, group in grouped.items():
            event = existing.get(external_id)
            if event is None:
                call, parsed_time = group[0]
                location = db.get_or_create_location(call.location)
                event = db.create_event(
                    external_id=external_id,
                    time_received=parsed_time,
                    call_type=call.call_type,
                    location=call.location,
                    location_id=location.id,
                )
                new_events += 1

                for call, _ in group:
                    responder = db.create_responder(
                        event_id=event.id,
                        unit=call.unit,
                        dispatch_area=call.dispatch_area,
                        agency=call.agency,
                    )
                    db.create_status_event(responder.id, call.status)
                    new_responders += 1
                continue

            responders = db.get_responders_for_event(event.id)
            by_key = {(r.unit, r.agency): r for r in responders}

            for call, _ in group:
                key = (call.unit, call.agency)
                responder = by_key.get(key)
                if responder is None:
                    responder = db.create_responder(
                        event_id=event.id,
                        unit=call.unit,
                        dispatch_area=call.dispatch_area,
                        agency=call.agency,
                    )
                    db.create_status_event(responder.id, call.status)
                    by_key[key] = responder
                    new_responders += 1
                    continue

                latest = db.latest_status(responder.id)
                if latest != call.status:
                    db.create_status_event(responder.id, call.status)
                    status_updates += 1

        db.commit()

    logger.info(
        "Persist complete: %s new event(s), %s new responder(s), %s status update(s)",
        new_events,
        new_responders,
        status_updates,
    )


if __name__ == "__main__":
    main()
