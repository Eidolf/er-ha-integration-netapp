"""Switch entities for NetApp ONTAP."""
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NetAppOntapDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NetApp ONTAP switch platform."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: NetAppOntapDataUpdateCoordinator = data["coordinator"]

    entities = []

    # Switches for each volume to enable/disable (online/offline)
    volumes = coordinator.data.get("volumes", [])
    for vol in volumes:
        vol_uuid = vol.get("uuid")
        vol_name = vol.get("name")
        if vol_uuid and vol_name:
            entities.append(NetAppOntapVolumeSwitch(coordinator, entry, vol_uuid, vol_name))

    async_add_entities(entities, update_before_add=True)


class NetAppOntapVolumeSwitch(CoordinatorEntity[NetAppOntapDataUpdateCoordinator], SwitchEntity):
    """Switch to online/offline a NetApp volume."""

    def __init__(
        self,
        coordinator: NetAppOntapDataUpdateCoordinator,
        entry: ConfigEntry,
        vol_uuid: str,
        vol_name: str,
    ) -> None:
        """Initialize volume switch."""
        super().__init__(coordinator)
        self.vol_uuid = vol_uuid
        self.vol_name = vol_name
        self.entry = entry
        self._attr_name = f"NetApp Volume {vol_name} Enabled"
        self._attr_unique_id = f"{entry.entry_id}_vol_switch_{vol_uuid}"
        self._attr_icon = "mdi:power"

    @property
    def is_on(self) -> bool:
        """Return true if the volume is online."""
        volumes = self.coordinator.data.get("volumes", [])
        for vol in volumes:
            if vol.get("uuid") == self.vol_uuid:
                return vol.get("state") == "online"
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the volume online."""
        _LOGGER.info("Turning volume %s ON (online)", self.vol_name)
        api = self.coordinator.api
        await api.set_volume_state(self.vol_uuid, "online")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the volume offline."""
        _LOGGER.info("Turning volume %s OFF (offline)", self.vol_name)
        api = self.coordinator.api
        await api.set_volume_state(self.vol_uuid, "offline")
        await self.coordinator.async_request_refresh()
