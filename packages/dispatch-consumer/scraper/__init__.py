import logging

import httpx

from .richmond_active_calls import (
    RichmondActiveCallsError,
    fetch_active_calls,
    parse_time_received,  # pyright: ignore[reportUnusedImport]
)


logger = logging.getLogger("scraper")


def scrape_active_calls() -> list[ActiveCall] | None:
    try:
        calls, as_of = fetch_active_calls()
    except (httpx.HTTPError, RichmondActiveCallsError) as exc:
        logger.error("Failed to fetch active calls: %s", exc)
        return None

    logger.info("Fetched %s active call(s) as of %s", len(calls), as_of)
    return calls