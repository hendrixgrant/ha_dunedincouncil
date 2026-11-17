"""Tiny client for DCC's public ArcGIS refuse collection layer."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import API_URL, REQUEST_TIMEOUT, USER_AGENT

_LOGGER = logging.getLogger(__name__)

SEARCH_FIELDS = "OBJECTID,fmtaddress,tpklpaprop,collectionDay,numberDay,CurrentWeek"


class DunedinApiError(Exception):
    """Raised when the council service can't be reached or returns an error."""


async def _query(session: aiohttp.ClientSession, params: dict[str, Any]) -> list[dict]:
    full = {"returnGeometry": "false", "f": "json", **params}
    try:
        async with asyncio.timeout(REQUEST_TIMEOUT):
            async with session.get(
                API_URL, params=full, headers={"User-Agent": USER_AGENT}
            ) as resp:
                resp.raise_for_status()
                # ArcGIS often labels JSON as text/plain
                data = await resp.json(content_type=None)
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        raise DunedinApiError(f"Error talking to Dunedin City Council: {err}") from err

    if not isinstance(data, dict) or "error" in data:
        raise DunedinApiError(f"Unexpected response from council service: {data!r}"[:300])

    return [f.get("attributes", {}) for f in data.get("features", [])]


async def async_search_addresses(
    session: aiohttp.ClientSession, text: str, limit: int = 15
) -> list[dict]:
    """Find properties whose formatted address contains ``text``."""
    cleaned = " ".join(text.split()).upper().replace("'", "''")
    return await _query(
        session,
        {
            "where": f"UPPER(fmtaddress) LIKE '%{cleaned}%'",
            "outFields": SEARCH_FIELDS,
            "orderByFields": "fmtaddress",
            "resultRecordCount": limit,
        },
    )


async def async_get_property(session: aiohttp.ClientSession, property_id: str | int) -> dict:
    """Fetch the collection attributes for one property."""
    rows = await _query(
        session,
        {"where": f"tpklpaprop = {int(property_id)}", "outFields": "*", "resultRecordCount": 1},
    )
    if not rows:
        raise DunedinApiError(f"Property {property_id} not found in council data")
    return rows[0]
