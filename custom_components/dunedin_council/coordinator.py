"""Data coordinator for the Dunedin City Council integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from datetime import date
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import DunedinApiError, async_get_property
from .const import (
    CONF_ADDRESS,
    CONF_PROPERTY_ID,
    CONF_SWAP_WEEKS,
    CONF_TERTIARY,
    DOMAIN,
    SCAN_INTERVAL,
)
from .schedule import monday_of, parse_week_type

_LOGGER = logging.getLogger(__name__)

type DunedinConfigEntry = ConfigEntry["DunedinCouncilCoordinator"]


@dataclass
class PropertyData:
    """What we keep from the latest council lookup."""

    address: str
    collection_day_name: str | None
    collection_weekday: int | None  # ISO: 1 = Monday ... 7 = Sunday
    raw_week_code: str | None
    anchor_monday: date
    anchor_type: str | None  # "blue" / "yellow" / None if unrecognised
    tertiary: bool
    raw: dict[str, Any]


class DunedinCouncilCoordinator(DataUpdateCoordinator[PropertyData]):
    """Polls the council's GIS layer."""

    config_entry: DunedinConfigEntry

    def __init__(self, hass: HomeAssistant, entry: DunedinConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> PropertyData:
        entry = self.config_entry
        session = async_get_clientsession(self.hass)
        try:
            attrs = await async_get_property(session, entry.data[CONF_PROPERTY_ID])
        except DunedinApiError as err:
            raise UpdateFailed(str(err)) from err

        swap = entry.options.get(CONF_SWAP_WEEKS, False)
        tertiary = entry.options.get(CONF_TERTIARY, False)

        raw_code = attrs.get("CurrentWeek")
        anchor_type = parse_week_type(raw_code, swap)
        if anchor_type is None and not tertiary:
            _LOGGER.warning(
                "Unrecognised CurrentWeek value %r for %s; fortnightly bins will show "
                "as unknown. If you're in the Tertiary area, enable that option.",
                raw_code,
                entry.data.get(CONF_ADDRESS),
            )

        weekday = attrs.get("numberDay")
        try:
            weekday = int(weekday) if weekday is not None else None
        except (TypeError, ValueError):
            weekday = None

        return PropertyData(
            address=attrs.get("fmtaddress") or entry.data.get(CONF_ADDRESS, ""),
            collection_day_name=attrs.get("collectionDay"),
            collection_weekday=weekday,
            raw_week_code=raw_code,
            anchor_monday=monday_of(dt_util.now().date()),
            anchor_type=anchor_type,
            tertiary=tertiary,
            raw=attrs,
        )
