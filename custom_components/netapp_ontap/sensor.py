"""Sensor entities for NetApp ONTAP."""
from typing import Any, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DETAIL_LEVEL_ADVANCED, DETAIL_LEVEL_ALL
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

    # Cluster/Topology master sensor
    entities.append(NetAppOntapTopologySensor(coordinator, entry))

    # Add performance and capacity sensors for each volume
    volumes = coordinator.data.get("volumes", [])
    for vol in volumes:
        vol_uuid = vol.get("uuid")
        vol_name = vol.get("name")
        if vol_uuid and vol_name:
            entities.append(NetAppOntapVolumeUsageSensor(coordinator, entry, vol_uuid, vol_name))
            
            # Performance metrics only for Advanced or All monitoring levels
            if coordinator.detail_level in (DETAIL_LEVEL_ADVANCED, DETAIL_LEVEL_ALL):
                entities.append(NetAppVolumePerformanceSensor(coordinator, entry, vol_uuid, vol_name, "iops"))
                entities.append(NetAppVolumePerformanceSensor(coordinator, entry, vol_uuid, vol_name, "latency"))
                entities.append(NetAppVolumePerformanceSensor(coordinator, entry, vol_uuid, vol_name, "throughput"))

    # Add capacity sensors for each aggregate
    aggrs = coordinator.data.get("aggregates", [])
    for aggr in aggrs:
        aggr_uuid = aggr.get("uuid")
        aggr_name = aggr.get("name")
        if aggr_uuid and aggr_name:
            entities.append(NetAppOntapAggregateUsageSensor(coordinator, entry, aggr_uuid, aggr_name))

    # All level sensors: SVMs, Cloud targets, and Licenses
    if coordinator.detail_level == DETAIL_LEVEL_ALL:
        svms = coordinator.data.get("svms", [])
        for svm in svms:
            svm_uuid = svm.get("uuid")
            svm_name = svm.get("name")
            if svm_uuid and svm_name:
                entities.append(NetAppOntapSvmSensor(coordinator, entry, svm_uuid, svm_name))

        cloud_targets = coordinator.data.get("cloud_targets", [])
        for ct in cloud_targets:
            ct_uuid = ct.get("uuid")
            ct_name = ct.get("name")
            if ct_uuid and ct_name:
                entities.append(NetAppOntapCloudTargetSensor(coordinator, entry, ct_uuid, ct_name))

        licenses = coordinator.data.get("licenses", [])
        for lic in licenses:
            lic_name = lic.get("name")
            if lic_name:
                entities.append(NetAppOntapLicenseSensor(coordinator, entry, lic_name))

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
        self.entry = entry
        self._attr_name = f"NetApp Volume {vol_name} Storage Used"
        self._attr_unique_id = f"{entry.entry_id}_vol_used_{vol_uuid}"
        self._attr_unit_of_measurement = "%"
        self._attr_icon = "mdi:database"

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
        self.entry = entry
        self._attr_name = f"NetApp Aggregate {aggr_name} Storage Used"
        self._attr_unique_id = f"{entry.entry_id}_aggr_used_{aggr_uuid}"
        self._attr_unit_of_measurement = "%"
        self._attr_icon = "mdi:server"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info linking to the Aggregate device."""
        cluster_info = self.coordinator.data.get("cluster", {})
        cluster_uuid = cluster_info.get("uuid", self.entry.entry_id)
        return DeviceInfo(
            identifiers={(DOMAIN, f"aggregate_{self.aggr_uuid}")},
            name=f"Aggregate: {self.aggr_name}",
            manufacturer="NetApp",
            model="ONTAP Aggregate",
            via_device=(DOMAIN, f"cluster_{cluster_uuid}"),
        )

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
        self.entry = entry
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
    def state(self) -> Optional[float]:
        """Return metric state."""
        volumes = self.coordinator.data.get("volumes", [])
        for vol in volumes:
            if vol.get("uuid") == self.vol_uuid:
                metric = vol.get("metric", {})
                if self.metric_type == "iops":
                    return metric.get("iops", {}).get("total", 0)
                elif self.metric_type == "latency":
                    latency = metric.get("latency", {}).get("total", 0)
                    return round(latency / 1000, 2)
                elif self.metric_type == "throughput":
                    throughput = metric.get("throughput", {}).get("total", 0)
                    return round(throughput / (1024 * 1024), 2)
        return None


class NetAppOntapSvmSensor(CoordinatorEntity[NetAppOntapDataUpdateCoordinator]):
    """SVM sensor representing its operational state."""

    def __init__(
        self,
        coordinator: NetAppOntapDataUpdateCoordinator,
        entry: ConfigEntry,
        svm_uuid: str,
        svm_name: str,
    ) -> None:
        """Initialize SVM sensor."""
        super().__init__(coordinator)
        self.svm_uuid = svm_uuid
        self.svm_name = svm_name
        self.entry = entry
        self._attr_name = f"NetApp SVM {svm_name} State"
        self._attr_unique_id = f"{entry.entry_id}_svm_{svm_uuid}"
        self._attr_icon = "mdi:shield-check"

    @property
    def device_info(self) -> DeviceInfo:
        """Link to Cluster."""
        cluster_info = self.coordinator.data.get("cluster", {})
        cluster_uuid = cluster_info.get("uuid", self.entry.entry_id)
        return DeviceInfo(
            identifiers={(DOMAIN, f"cluster_{cluster_uuid}")},
            name=f"Cluster: {cluster_info.get('name', self.entry.title)}",
        )

    @property
    def state(self) -> Optional[str]:
        """Return SVM state (e.g. running)."""
        svms = self.coordinator.data.get("svms", [])
        for svm in svms:
            if svm.get("uuid") == self.svm_uuid:
                return svm.get("state")
        return None


class NetAppOntapCloudTargetSensor(CoordinatorEntity[NetAppOntapDataUpdateCoordinator]):
    """Cloud Target sensor representing storage target health."""

    def __init__(
        self,
        coordinator: NetAppOntapDataUpdateCoordinator,
        entry: ConfigEntry,
        ct_uuid: str,
        ct_name: str,
    ) -> None:
        """Initialize Cloud Target sensor."""
        super().__init__(coordinator)
        self.ct_uuid = ct_uuid
        self.ct_name = ct_name
        self.entry = entry
        self._attr_name = f"NetApp Cloud Target {ct_name} State"
        self._attr_unique_id = f"{entry.entry_id}_cloud_{ct_uuid}"
        self._attr_icon = "mdi:cloud"

    @property
    def device_info(self) -> DeviceInfo:
        """Link to Cluster."""
        cluster_info = self.coordinator.data.get("cluster", {})
        cluster_uuid = cluster_info.get("uuid", self.entry.entry_id)
        return DeviceInfo(
            identifiers={(DOMAIN, f"cluster_{cluster_uuid}")},
            name=f"Cluster: {cluster_info.get('name', self.entry.title)}",
        )

    @property
    def state(self) -> Optional[str]:
        """Return target state."""
        cts = self.coordinator.data.get("cloud_targets", [])
        for ct in cts:
            if ct.get("uuid") == self.ct_uuid:
                return ct.get("state", "unknown")
        return None


class NetAppOntapLicenseSensor(CoordinatorEntity[NetAppOntapDataUpdateCoordinator]):
    """License sensor representing license status."""

    def __init__(
        self,
        coordinator: NetAppOntapDataUpdateCoordinator,
        entry: ConfigEntry,
        lic_name: str,
    ) -> None:
        """Initialize license sensor."""
        super().__init__(coordinator)
        self.lic_name = lic_name
        self.entry = entry
        self._attr_name = f"NetApp License {lic_name} Active"
        self._attr_unique_id = f"{entry.entry_id}_license_{lic_name}"
        self._attr_icon = "mdi:key"

    @property
    def device_info(self) -> DeviceInfo:
        """Link to Cluster."""
        cluster_info = self.coordinator.data.get("cluster", {})
        cluster_uuid = cluster_info.get("uuid", self.entry.entry_id)
        return DeviceInfo(
            identifiers={(DOMAIN, f"cluster_{cluster_uuid}")},
            name=f"Cluster: {cluster_info.get('name', self.entry.title)}",
        )

    @property
    def state(self) -> Optional[str]:
        """Return license state."""
        licenses = self.coordinator.data.get("licenses", [])
        for lic in licenses:
            if lic.get("name") == self.lic_name:
                return "Active" if lic.get("active", True) else "Inactive"
        return "Active"
