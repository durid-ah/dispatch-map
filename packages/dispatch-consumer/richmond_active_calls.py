from __future__ import annotations

import re
from datetime import datetime
import httpx
import logging

from bs4 import BeautifulSoup
from models import ActiveCall
from config import config

logger = logging.getLogger(__name__)

AS_OF_PATTERN = re.compile(
    r"As of\s+(.+?)\s+-\s+This page will refresh every 45 seconds"
)
EXPECTED_COLUMNS = 7


class RichmondActiveCallsError(Exception):
    pass

def fetch_active_calls() -> tuple[list[ActiveCall], str | None]:
    client = httpx.Client(timeout=30.0, headers={"User-Agent": config.user_agent})

    try:
        response = client.get(config.active_calls_url)
        response.raise_for_status() 
        return _parse_active_calls_html(response.text)
    finally:
        client.close()

def _parse_active_calls_html(html: str) -> tuple[list[ActiveCall], str | None]:
    soup = BeautifulSoup(html, "html.parser")
    as_of = _parse_as_of(soup)
    table = soup.find("table", id="tblActiveCallsListing")
    if table is None:
        raise RichmondActiveCallsError("Active calls table not found in response")

    tbody = table.find("tbody")
    if tbody is None:
        raise RichmondActiveCallsError("Active calls table body not found in response")

    calls: list[ActiveCall] = []
    for row in tbody.find_all("tr"):
        cells = [cell.get_text(strip=True) for cell in row.find_all("td")]
        if len(cells) != EXPECTED_COLUMNS:
            continue

        calls.append(
            ActiveCall(
                time_received=cells[0],
                agency=cells[1],
                dispatch_area=cells[2],
                unit=cells[3],
                call_type=cells[4],
                location=cells[5],
                status=cells[6],
            )
        )

    return calls, as_of

def _parse_as_of(soup: BeautifulSoup) -> str | None:
    header = soup.find("p", class_="fs-6")
    if header is None:
        return None

    match = AS_OF_PATTERN.search(header.get_text(" ", strip=True))
    if match is None:
        return None

    return match.group(1)

def parse_time_received(time_received: str) -> datetime | None:
    try:
        return datetime.strptime(time_received, "%m/%d/%Y %H:%M")
    except ValueError as e:
        logger.error("Failed to parse time_received '%s': %s", time_received, e)
        return None