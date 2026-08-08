from __future__ import annotations

import logging
import time
from datetime import datetime

import httpx

from richmond_active_calls import (
    RichmondActiveCallsError,
    fetch_active_calls,
    parse_time_received,
)
from db.models import STATUS_ORDER, ActiveCall
from config import config
from database import DB
from util import group_active_calls, group_existing_events

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

    grouped = group_active_calls(valid_calls)

    new_events = 0
    new_responders = 0
    new_status = 0
    status_updates = 0

    with DB(config.db_url) as db:
        events = db.get_events(list(grouped.keys()))
        existing = group_existing_events(events)

        for external_id, grouped_event in grouped.items():
            event = existing.get(external_id)
            if event is None:
                location = db.get_or_create_location(grouped_event.location)
                event = db.create_event(
                    external_id=external_id,
                    time_received=grouped_event.parsed_time,
                    call_type=grouped_event.call_type,
                    location=grouped_event.location,
                    location_id=location.id,
                )
                new_events += 1

                for responder_group in grouped_event.responders:
                    responder = db.create_responder(
                        event_id=event.id,
                        unit=responder_group.unit,
                        dispatch_area=responder_group.dispatch_area,
                        agency=responder_group.agency,
                    )
                    new_responders += 1
                    for status in responder_group.statuses:
                        db.create_status_event(responder.id, status)
                        new_status += 1
                continue

            responders = db.get_responders_for_event(event.id)
            by_key = {
                (r.unit, r.agency, r.dispatch_area): r for r in responders
            }

            for responder_group in grouped_event.responders:
                key = (
                    responder_group.unit,
                    responder_group.agency,
                    responder_group.dispatch_area,
                )
                responder = by_key.get(key)
                if responder is None:
                    responder = db.create_responder(
                        event_id=event.id,
                        unit=responder_group.unit,
                        dispatch_area=responder_group.dispatch_area,
                        agency=responder_group.agency,
                    )
                    by_key[key] = responder
                    new_responders += 1
                    for status in responder_group.statuses:
                        db.create_status_event(responder.id, status)
                        new_status += 1
                    continue

                for status in responder_group.statuses:
                    status_order = STATUS_ORDER.get(status.upper(), 0)
                    latest = db.latest_status(responder.id)
                    if latest is None or latest.status_order < status_order:
                        logger.info(
                            "Create: call: %s; responder: %s; status: %s",
                            grouped_event.call_type,
                            responder_group.unit + " " + responder_group.agency,
                            status,
                        )
                        db.create_status_event(responder.id, status)
                        status_updates += 1
                    else:
                        logger.info(
                            "Responder %s has latest status %s",
                            responder.id,
                            latest.status,
                        )

        db.commit()

    logger.info(
        "Persist complete: %s new event(s), %s new responder(s), %s status update(s)",
        new_events,
        new_responders,
        status_updates,
    )


if __name__ == "__main__":
    main()
