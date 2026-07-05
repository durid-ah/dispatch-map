from __future__ import annotations

import logging
import time

import httpx
import pandas as pd

from models import ActiveCall
from richmond_active_calls import ACTIVE_CALLS_URL, fetch_active_calls
from richmond_active_calls import RichmondActiveCallsError

POLL_INTERVAL_SECONDS = 45

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Starting Richmond active calls consumer")
    logger.info("Source URL: %s", ACTIVE_CALLS_URL)
    logger.info("Poll interval: %ss", POLL_INTERVAL_SECONDS)

    known_calls: dict[str, ActiveCall] = {}

    try:
        while True:
            poll_once(known_calls)
            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logger.info("Shutting down")


def poll_once(known_calls: dict[str, ActiveCall]) -> None:
    try:
        calls, as_of = fetch_active_calls()
    except (httpx.HTTPError, RichmondActiveCallsError) as exc:
        logger.error("Failed to fetch active calls: %s", exc)
        return

    if as_of:
        logger.info("Fetched %s active call(s) as of %s", len(calls), as_of)
    else:
        logger.info("Fetched %s active call(s)", len(calls))

    df = pd.DataFrame(calls)
    print(df)



if __name__ == "__main__":
    main()
