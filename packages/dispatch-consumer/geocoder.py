from __future__ import annotations

import logging
import re

import httpx

from config import config

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "dispatch-map/0.1"

# Richmond, VA metro bounding box: west, north, east, south
RICHMOND_VIEWBOX = "-77.65,37.65,-77.25,37.40"

# Captures the street number and removes CAD block markers such as "2600-BLK".
_BLK_PATTERN = re.compile(r"(\d+)-?\s*BLK\b", re.IGNORECASE)
# Removes the trailing Richmond jurisdiction code from intersection locations.
_TRAILING_CITY_CODE = re.compile(r"\s+RICH\s*$", re.IGNORECASE)
# Captures numeric ordinals so their suffix can be normalized to lowercase.
_ORDINAL_PATTERN = re.compile(r"\b(\d+)(ST|ND|RD|TH)\b", re.IGNORECASE)
# Matches runs of whitespace so they can be collapsed to single spaces.
_WHITESPACE = re.compile(r"\s+")

_DIRECTIONALS = {
    "N": "North",
    "S": "South",
    "E": "East",
    "W": "West",
    "NE": "Northeast",
    "NW": "Northwest",
    "SE": "Southeast",
    "SW": "Southwest",
}

_STREET_SUFFIXES = {
    "ST": "Street",
    "AVE": "Avenue",
    "RD": "Road",
    "BLVD": "Boulevard",
    "DR": "Drive",
    "LN": "Lane",
    "CT": "Court",
    "PL": "Place",
    "CIR": "Circle",
    "TER": "Terrace",
    "PKWY": "Parkway",
    "HWY": "Highway",
    "TPKE": "Turnpike",
    "TP": "Turnpike",
    "EXPY": "Expressway",
    "ALY": "Alley",
}

_unmatched_queries: set[str] = set()


def normalize_location_query(raw_text: str) -> str:
    # Convert Richmond CAD notation into an address Nominatim can search.
    text = raw_text.strip()
    text = _TRAILING_CITY_CODE.sub("", text)
    text = _BLK_PATTERN.sub(r"\1", text)
    text = text.replace("/", " and ")
    text = _ORDINAL_PATTERN.sub(lambda match: match.group(1) + match.group(2).lower(), text)
    text = " ".join(_expand_token(token) for token in _WHITESPACE.split(text) if token)
    city = config.geocode_city
    if city and city.lower() not in text.lower():
        text = f"{text}, {city}"
    return text


def geocode_location(raw_text: str) -> tuple[float, float] | None:
    query = normalize_location_query(raw_text)
    # Avoid repeatedly searching unresolved locations during every poll.
    if not query or query in _unmatched_queries:
        return None

    try:
        response = httpx.get(
            config.nominatim_url,
            params={
                "q": query,
                "format": "json",
                "limit": 1,
                "countrycodes": "us",
                # Prefer results within the Richmond metro area.
                "viewbox": RICHMOND_VIEWBOX,
                "bounded": 1,
            },
            headers={
                "User-Agent": config.user_agent or DEFAULT_USER_AGENT,
                "Accept-Language": "en",
            },
            timeout=15.0,
        )
        response.raise_for_status()
        results = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Nominatim request failed for %r: %s", query, exc)
        return None

    if not results:
        _unmatched_queries.add(query)
        logger.warning("No Nominatim match for %r (query %r)", raw_text, query)
        return None

    try:
        latitude = float(results[0]["lat"])
        longitude = float(results[0]["lon"])
    except (KeyError, TypeError, ValueError) as exc:
        logger.error("Invalid Nominatim response for %r: %s", query, exc)
        return None

    logger.info("Geocoded %r -> %s, %s", raw_text, latitude, longitude)
    return latitude, longitude


def _expand_token(token: str) -> str:
    # Expand common CAD abbreviations to improve address matching.
    key = token.upper().rstrip(".")
    if key in _DIRECTIONALS:
        return _DIRECTIONALS[key]
    if key in _STREET_SUFFIXES:
        return _STREET_SUFFIXES[key]
    return token
