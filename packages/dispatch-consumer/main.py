from __future__ import annotations

import logging
import time

import httpx

from dotenv import load_dotenv
from richmond_active_calls import fetch_active_calls, parse_time_received, RichmondActiveCallsError
from models import ActiveCall
from config import config
from db import DB

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
    # df = pd.DataFrame(calls)
    # as_of_str = dt.strptime(as_of, '%m/%d/%Y %I:%M:%S %p').strftime("%Y-%m-%d_%H-%M-%S")
    # df.to_csv(f"./test_data/active_calls_{as_of_str}.csv", index=False)


def persist(calls: list[ActiveCall]) -> None:
    for call in calls:
        parsed_time = parse_time_received(call.time_received)
        if parsed_time is None:
            continue

        logger.info("Persisting call: %s", call)

    external_ids = [call.external_id for call in calls]
    with DB(config.db_url) as db:
        events = db.get_events(external_ids)
        logger.info("Events: %s", events)

    # check if the events are new
    # old events:
    # ├── update old responders
    # └── create new responders
    # new events:
    # ├── create new event
    # └── create new responders
    # └── create new responder status events
    # └── create new location

if __name__ == "__main__":
    main()