"""Sensors for the Dunedin City Council integration."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import DunedinConfigEntry, DunedinCouncilCoordinator
from .schedule import BINS, BinDef, next_collection, next_collection_summary


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DunedinConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [DunedinBinSensor(coordinator, entry, b) for b in BINS]
    entities.append(DunedinNextCollectionSensor(coordinator, entry))
    entities.append(DunedinCollectionDaySensor(coordinator, entry))
    async_add_entities(entities)


class DunedinBaseSensor(CoordinatorEntity[DunedinCouncilCoordinator], SensorEntity):
    """Shared device info and midnight refresh (so 'days until' never goes stale)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DunedinCouncilCoordinator, entry: DunedinConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Dunedin City Council",
            model="Kerbside collection",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_change(self.hass, self._handle_midnight, hour=0, minute=1, second=0)
        )

    @callback
    def _handle_midnight(self, _now: datetime) -> None:
        self.async_write_ha_state()

    @staticmethod
    def _today() -> date:
        return dt_util.now().date()


class DunedinBinSensor(DunedinBaseSensor):
    """Next collection date for a single bin."""

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(
        self, coordinator: DunedinCouncilCoordinator, entry: DunedinConfigEntry, bin_def: BinDef
    ) -> None:
        super().__init__(coordinator, entry)
        self._bin = bin_def
        self._attr_unique_id = f"{entry.unique_id}_{bin_def.key}"
        self._attr_name = bin_def.name
        self._attr_icon = bin_def.icon

    def _next(self) -> date | None:
        d = self.coordinator.data
        return next_collection(
            self._today(), d.collection_weekday, self._bin.cadence,
            d.anchor_monday, d.anchor_type, d.tertiary,
        )

    @property
    def native_value(self) -> date | None:
        return self._next()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        nxt = self._next()
        return {
            "bin_colour": self._bin.colour,
            "days_until": (nxt - self._today()).days if nxt else None,
        }


class DunedinNextCollectionSensor(DunedinBaseSensor):
    """Which bins go out next, e.g. 'Food scraps & garden, Mixed recycling'."""

    _attr_name = "Next collection"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: DunedinCouncilCoordinator, entry: DunedinConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.unique_id}_next_collection"

    def _summary(self):
        d = self.coordinator.data
        return next_collection_summary(
            self._today(), d.collection_weekday, d.anchor_monday, d.anchor_type, d.tertiary
        )

    @property
    def native_value(self) -> str | None:
        summary = self._summary()
        return ", ".join(b.name for b in summary[1]) if summary else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        summary = self._summary()
        if not summary:
            return {"date": None, "days_until": None, "bins": []}
        when, bins = summary
        return {
            "date": when.isoformat(),
            "days_until": (when - self._today()).days,
            "bins": [b.key for b in bins],
            "bin_colours": [b.colour for b in bins],
        }


class DunedinCollectionDaySensor(DunedinBaseSensor):
    """The property's collection weekday, plus raw council data for debugging."""

    _attr_name = "Collection day"
    _attr_icon = "mdi:calendar-today"

    def __init__(self, coordinator: DunedinCouncilCoordinator, entry: DunedinConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.unique_id}_collection_day"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.collection_day_name

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self.coordinator.data
        return {
            "this_week_fortnightly_bins": d.anchor_type,
            "council_current_week_code": d.raw_week_code,
            "tertiary_area": d.tertiary,
            "address": d.address,
        }
