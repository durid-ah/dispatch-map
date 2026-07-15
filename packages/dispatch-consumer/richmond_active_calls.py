from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

from models import ActiveCall

ACTIVE_CALLS_URL = (
    "https://apps.richmondgov.com/applications/activecalls/Home/ActiveCalls"
)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0"
AS_OF_PATTERN = re.compile(
    r"As of\s+(.+?)\s+-\s+This page will refresh every 45 seconds"
)
EXPECTED_COLUMNS = 7


class RichmondActiveCallsError(Exception):
    pass

def fetch_active_calls() -> tuple[list[ActiveCall], str | None]:
    client = httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT})

    try:
        response = client.get(ACTIVE_CALLS_URL)
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
