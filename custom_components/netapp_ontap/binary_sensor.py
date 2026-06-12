"""Binary sensor entities for NetApp ONTAP."""
from typing import Any, Dict, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NetAppOntapDataUpdateCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NetApp ONTAP binary sensor platform."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: NetAppOntapDataUpdateCoordinator = data["coordinator"]

    entities = []

    # Cluster health
    entities.append(NetAppOntapClusterHealthSensor(coordinator, entry))

    # Node health
    nodes = coordinator.data.get("nodes", [])
    for node in nodes:
        node_uuid = node.get("uuid")
        node_name = node.get("name")
        if node_uuid and node_name:
            entities.append(NetAppOntapNodeHealthSensor(coordinator, entry, node_uuid, node_name))

    # Volume status / health
    volumes = coordinator.data.get("volumes", [])
    for vol in volumes:
        vol_uuid = vol.get("uuid")
        vol_name = vol.get("name")
        if vol_uuid and vol_name:
            entities.append(NetAppOntapVolumeStatusSensor(coordinator, entry, vol_uuid, vol_name))

    async_add_entities(entities, update_before_add=True)


class NetAppOntapClusterHealthSensor(CoordinatorEntity[NetAppOntapDataUpdateCoordinator], BinarySensorEntity):
    """Cluster health binary sensor."""

    def __init__(
        self,
        coordinator: NetAppOntapDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize cluster health sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_name = f"{entry.title} Cluster Health"
        self._attr_unique_id = f"{entry.entry_id}_cluster_health"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info linking to the Cluster device."""
        cluster_info = self.coordinator.data.get("cluster", {})
        cluster_uuid = cluster_info.get("uuid", self.entry.entry_id)
        return DeviceInfo(
            identifiers={(DOMAIN, f"cluster_{cluster_uuid}")},
            name=f"Cluster: {cluster_info.get('name', self.entry.title)}",
            manufacturer="NetApp",
            model="ONTAP Cluster",
            sw_version=cluster_info.get("version"),
        )

    @property
    def is_on(self) -> bool:
        """Return true if there is a problem (cluster not healthy)."""
        healthy = self.coordinator.data.get("cluster", {}).get("healthy")
        if healthy is None:
            return False
        return not healthy


class NetAppOntapNodeHealthSensor(CoordinatorEntity[NetAppOntapDataUpdateCoordinator], BinarySensorEntity):
    """Node health binary sensor."""

    def __init__(
        self,
        coordinator: NetAppOntapDataUpdateCoordinator,
        entry: ConfigEntry,
        node_uuid: str,
        node_name: str,
    ) -> None:
        """Initialize node health sensor."""
        super().__init__(coordinator)
        self.node_uuid = node_uuid
        self.node_name = node_name
        self.entry = entry
        self._attr_name = f"NetApp Node {node_name} Health"
        self._attr_unique_id = f"{entry.entry_id}_node_health_{node_uuid}"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info linking to the Node device."""
        cluster_info = self.coordinator.data.get("cluster", {})
        cluster_uuid = cluster_info.get("uuid", self.entry.entry_id)
        
        # Find node model
        node_model = "ONTAP Node"
        node_version = None
        nodes = self.coordinator.data.get("nodes", [])
        for node in nodes:
            if node.get("uuid") == self.node_uuid:
                node_model = node.get("model", "ONTAP Node")
                node_version = node.get("version")
                
        return DeviceInfo(
            identifiers={(DOMAIN, f"node_{self.node_uuid}")},
            name=f"Node: {self.node_name}",
            manufacturer="NetApp",
            model=node_model,
            sw_version=node_version,
            via_device=(DOMAIN, f"cluster_{cluster_uuid}"),
        )

    @property
    def is_on(self) -> bool:
        """Return true if there is a node problem."""
        nodes = self.coordinator.data.get("nodes", [])
        for node in nodes:
            if node.get("uuid") == self.node_uuid:
                state = node.get("state")
                return state != "healthy"
        return True


class NetAppOntapVolumeStatusSensor(CoordinatorEntity[NetAppOntapDataUpdateCoordinator], BinarySensorEntity):
    """Volume state binary sensor (e.g. online vs offline)."""

    def __init__(
        self,
        coordinator: NetAppOntapDataUpdateCoordinator,
        entry: ConfigEntry,
        vol_uuid: str,
        vol_name: str,
    ) -> None:
        """Initialize volume status sensor."""
        super().__init__(coordinator)
        self.vol_uuid = vol_uuid
        self.vol_name = vol_name
        self.entry = entry
        self._attr_name = f"NetApp Volume {vol_name} Status"
        self._attr_unique_id = f"{entry.entry_id}_vol_status_{vol_uuid}"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info linking to the Volume device."""
        cluster_info = self.coordinator.data.get("cluster", {})
        cluster_uuid = cluster_info.get("uuid", self.entry.entry_id)
        return DeviceInfo(
            identifiers={(DOMAIN, f"volume_{self.vol_uuid}")},
            name=f"Volume: {self.vol_name}",
            manufacturer="NetApp",
            model="ONTAP Volume",
            via_device=(DOMAIN, f"cluster_{cluster_uuid}"),
        )

    @property
    def is_on(self) -> bool:
        """Return true if volume is offline / degraded."""
        volumes = self.coordinator.data.get("volumes", [])
        for vol in volumes:
            if vol.get("uuid") == self.vol_uuid:
                state = vol.get("state")
                return state != "online"
        return True
