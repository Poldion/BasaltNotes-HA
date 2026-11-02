"""Sensors: how many instructions and facts the assistant currently knows."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BasaltConfigEntry
from .const import CONF_VAULT_NAME, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BasaltConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    async_add_entities(BasaltCountSensor(entry, key) for key in ("instructions", "memories"))


class BasaltCountSensor(CoordinatorEntity, SensorEntity):
    """Number of notes of one kind."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry: BasaltConfigEntry, key: str) -> None:
        """Initialize the sensor."""
        super().__init__(entry.runtime_data)
        self._key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data[CONF_VAULT_NAME],
            manufacturer="BasaltNotes",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=entry.data[CONF_URL],
        )

    @property
    def native_value(self) -> int:
        """Return the number of notes; corrections count as instructions."""
        vault = self.coordinator.vault
        if self._key == "memories":
            return len(vault.memories)
        return len(vault.instructions) + len(vault.learned)
