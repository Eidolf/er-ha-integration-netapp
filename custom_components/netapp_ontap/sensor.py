"""Sensor entities for NetApp ONTAP."""
from typing import Any, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NetAppOntapDataUpdateCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NetApp ONTAP sensor platform."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: NetAppOntapDataUpdateCoordinator = data["coordinator"]

    entities = []

    # Topology master sensor
    entities.append(NetAppOntapTopologySensor(coordinator, entry))

    # Add performance and capacity sensors for each volume
    volumes = coordinator.data.get("volumes", [])
    for vol in volumes:
        vol_uuid = vol.get("uuid")
        vol_name = vol.get("name")
        if vol_uuid and vol_name:
            entities.append(NetAppOntapVolumeUsageSensor(coordinator, entry, vol_uuid, vol_name))
            entities.append(NetAppOntapVolumePerformanceSensor(coordinator, entry, vol_uuid, vol_name, "iops"))
            entities.append(NetAppOntapVolumePerformanceSensor(coordinator, entry, vol_uuid, vol_name, "latency"))
            entities.append(NetAppOntapVolumePerformanceSensor(coordinator, entry, vol_uuid, vol_name, "throughput"))

    # Add capacity sensors for each aggregate
    aggrs = coordinator.data.get("aggregates", [])
    for aggr in aggrs:
        aggr_uuid = aggr.get("uuid")
        aggr_name = aggr.get("name")
        if aggr_uuid and aggr_name:
            entities.append(NetAppOntapAggregateUsageSensor(coordinator, entry, aggr_uuid, aggr_name))

    async_add_entities(entities, update_before_add=True)


class NetAppOntapTopologySensor(CoordinatorEntity[NetAppOntapDataUpdateCoordinator]):
    """Master topology sensor containing the complete schematic tree representation."""

    def __init__(
        self,
        coordinator: NetAppOntapDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize topology sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_name = f"{entry.title} Topology"
        self._attr_unique_id = f"{entry.entry_id}_topology"
        self._attr_icon = "mdi:sitemap"

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        return self.coordinator.data.get("cluster", {}).get("name", "Unknown Cluster")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes containing full topology."""
        return {
            "cluster": self.coordinator.data.get("cluster", {}),
            "nodes": self.coordinator.data.get("nodes", []),
            "aggregates": self.coordinator.data.get("aggregates", []),
            "volumes": self.coordinator.data.get("volumes", []),
            "interfaces": self.coordinator.data.get("interfaces", []),
            "events": self.coordinator.data.get("events", []),
        }


class NetAppOntapVolumeUsageSensor(CoordinatorEntity[NetAppOntapDataUpdateCoordinator]):
    """Volume usage percentage sensor."""

    def __init__(
        self,
        coordinator: NetAppOntapDataUpdateCoordinator,
        entry: ConfigEntry,
        vol_uuid: str,
        vol_name: str,
    ) -> None:
        """Initialize usage sensor."""
        super().__init__(coordinator)
        self.vol_uuid = vol_uuid
        self.vol_name = vol_name
        self._attr_name = f"NetApp Volume {vol_name} Storage Used"
        self._attr_unique_id = f"{entry.entry_id}_vol_used_{vol_uuid}"
        self._attr_unit_of_measurement = "%"
        self._attr_icon = "mdi:database"

    @property
    def state(self) -> Optional[float]:
        """Return percentage of volume used."""
        volumes = self.coordinator.data.get("volumes", [])
        for vol in volumes:
            if vol.get("uuid") == self.vol_uuid:
                space = vol.get("space", {})
                size = space.get("size", 1)
                used = space.get("used", 0)
                if size > 0:
                    return round((used / size) * 100, 2)
        return None


class NetAppOntapAggregateUsageSensor(CoordinatorEntity[NetAppOntapDataUpdateCoordinator]):
    """Aggregate usage percentage sensor."""

    def __init__(
        self,
        coordinator: NetAppOntapDataUpdateCoordinator,
        entry: ConfigEntry,
        aggr_uuid: str,
        aggr_name: str,
    ) -> None:
        """Initialize aggregate usage sensor."""
        super().__init__(coordinator)
        self.aggr_uuid = aggr_uuid
        self.aggr_name = aggr_name
        self._attr_name = f"NetApp Aggregate {aggr_name} Storage Used"
        self._attr_unique_id = f"{entry.entry_id}_aggr_used_{aggr_uuid}"
        self._attr_unit_of_measurement = "%"
        self._attr_icon = "mdi:server"

    @property
    def state(self) -> Optional[float]:
        """Return percentage of aggregate used."""
        aggrs = self.coordinator.data.get("aggregates", [])
        for aggr in aggrs:
            if aggr.get("uuid") == self.aggr_uuid:
                space = aggr.get("space", {})
                size = space.get("size", 1)
                used = space.get("used", 0)
                if size > 0:
                    return round((used / size) * 100, 2)
        return None


class NetAppVolumePerformanceSensor(CoordinatorEntity[NetAppOntapDataUpdateCoordinator]):
    """Volume performance metrics sensor."""

    def __init__(
        self,
        coordinator: NetAppOntapDataUpdateCoordinator,
        entry: ConfigEntry,
        vol_uuid: str,
        vol_name: str,
        metric_type: str,  # "iops", "latency", "throughput"
    ) -> None:
        """Initialize performance sensor."""
        super().__init__(coordinator)
        self.vol_uuid = vol_uuid
        self.vol_name = vol_name
        self.metric_type = metric_type
        
        self._attr_name = f"NetApp Volume {vol_name} {metric_type.capitalize()}"
        self._attr_unique_id = f"{entry.entry_id}_vol_{metric_type}_{vol_uuid}"
        
        if metric_type == "iops":
            self._attr_unit_of_measurement = "IOPS"
            self._attr_icon = "mdi:speedometer"
        elif metric_type == "latency":
            self._attr_unit_of_measurement = "ms"
            self._attr_icon = "mdi:clock-fast"
        else:
            self._attr_unit_of_measurement = "MB/s"
            self._attr_icon = "mdi:download"

    @property
    def state(self) -> Optional[float]:
        """Return metric state."""
        volumes = self.coordinator.data.get("volumes", [])
        for vol in volumes:
            if vol.get("uuid") == self.vol_uuid:
                metric = vol.get("metric", {})
                if self.metric_type == "iops":
                    return metric.get("iops", {}).get("total", 0)
                elif self.metric_type == "latency":
                    # convert microsecond latency to ms
                    latency = metric.get("latency", {}).get("total", 0)
                    return round(latency / 1000, 2)
                elif self.metric_type == "throughput":
                    # convert byte throughput to MB/s
                    throughput = metric.get("throughput", {}).get("total", 0)
                    return round(throughput / (1024 * 1024), 2)
        return None
