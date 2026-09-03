from __future__ import annotations

import logging
import time

from scraper import scrape_active_calls
from parser import parse_active_calls
from config import config
from processor import process_grouped_events

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
        active_calls = scrape_active_calls()
        if active_calls is None:
            logger.error("Failed to scrape active calls")
            return

        parsed_calls = parse_active_calls(active_calls)
        process_grouped_events(parsed_calls)
    except Exception as exc:
        logger.error("Failed to scrape active calls: %s", exc)


if __name__ == "__main__":
    main()
