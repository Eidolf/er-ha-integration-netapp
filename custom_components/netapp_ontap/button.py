"""Button entities for NetApp ONTAP."""
from datetime import datetime
import logging

from homeassistant.components.button import ButtonEntity
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
    """Set up NetApp ONTAP button platform."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: NetAppOntapDataUpdateCoordinator = data["coordinator"]

    entities = []

    # Button to trigger snapshot for each volume
    volumes = coordinator.data.get("volumes", [])
    for vol in volumes:
        vol_uuid = vol.get("uuid")
        vol_name = vol.get("name")
        if vol_uuid and vol_name:
            entities.append(NetAppOntapSnapshotButton(coordinator, entry, vol_uuid, vol_name))

    async_add_entities(entities, update_before_add=True)


class NetAppOntapSnapshotButton(CoordinatorEntity[NetAppOntapDataUpdateCoordinator], ButtonEntity):
    """Button to trigger a manual snapshot of a NetApp volume."""

    def __init__(
        self,
        coordinator: NetAppOntapDataUpdateCoordinator,
        entry: ConfigEntry,
        vol_uuid: str,
        vol_name: str,
    ) -> None:
        """Initialize snapshot button."""
        super().__init__(coordinator)
        self.vol_uuid = vol_uuid
        self.vol_name = vol_name
        self.entry = entry
        self._attr_name = f"NetApp Volume {vol_name} Create Snapshot"
        self._attr_unique_id = f"{entry.entry_id}_snapshot_btn_{vol_uuid}"
        self._attr_icon = "mdi:camera"

    async def async_press(self) -> None:
        """Handle button press."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_name = f"ha_manual_{timestamp}"
        _LOGGER.info("Triggering snapshot creation '%s' for volume %s", snapshot_name, self.vol_name)
        api = self.coordinator.api
        await api.create_snapshot(self.vol_uuid, snapshot_name)
        await self.coordinator.async_request_refresh()
