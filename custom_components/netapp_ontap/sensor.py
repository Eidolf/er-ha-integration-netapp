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

    # Add capacity (percentage, total GB, used GB) and performance sensors for each volume
    volumes = coordinator.data.get("volumes", [])
    for vol in volumes:
        vol_uuid = vol.get("uuid")
        vol_name = vol.get("name")
        if vol_uuid and vol_name:
            entities.append(NetAppOntapVolumeUsageSensor(coordinator, entry, vol_uuid, vol_name))
            entities.append(NetAppOntapVolumeCapacitySensor(coordinator, entry, vol_uuid, vol_name))
            entities.append(NetAppOntapVolumeUsedBytesSensor(coordinator, entry, vol_uuid, vol_name))
            
            # Performance metrics only for Advanced or All monitoring levels
            if coordinator.detail_level in (DETAIL_LEVEL_ADVANCED, DETAIL_LEVEL_ALL):
                entities.append(NetAppVolumePerformanceSensor(coordinator, entry, vol_uuid, vol_name, "iops"))
                entities.append(NetAppVolumePerformanceSensor(coordinator, entry, vol_uuid, vol_name, "latency"))
                entities.append(NetAppVolumePerformanceSensor(coordinator, entry, vol_uuid, vol_name, "throughput"))

            # Efficiency/Data Reduction rate for All level
            if coordinator.detail_level == DETAIL_LEVEL_ALL:
                entities.append(NetAppOntapVolumeEfficiencySensor(coordinator, entry, vol_uuid, vol_name))

    # Add capacity sensors for each aggregate
    aggrs = coordinator.data.get("aggregates", [])
    for aggr in aggrs:
        aggr_uuid = aggr.get("uuid")
        aggr_name = aggr.get("name")
        if aggr_uuid and aggr_name:
            entities.append(NetAppOntapAggregateUsageSensor(coordinator, entry, aggr_uuid, aggr_name))
            entities.append(NetAppOntapAggregateCapacitySensor(coordinator, entry, aggr_uuid, aggr_name))
            entities.append(NetAppOntapAggregateUsedBytesSensor(coordinator, entry, aggr_uuid, aggr_name))

    # All level sensors: SVMs, Cloud targets, Licenses, FC Ports, CIFS Shares
    if coordinator.detail_level == DETAIL_LEVEL_ALL:
        svms = coordinator.data.get("svms", [])
        for svm in svms:
            svm_uuid = svm.get("uuid")
            svm_name = svm.get("name")
            if svm_uuid and svm_name:
                entities.append(NetAppOntapSvmSensor(coordinator, entry, svm_uuid, svm_name))
                entities.append(NetAppOntapSvmProtocolsSensor(coordinator, entry, svm_uuid, svm_name))

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

        fc_ports = coordinator.data.get("fc_ports", [])
        for fc in fc_ports:
            fc_uuid = fc.get("uuid")
            fc_name = fc.get("name")
            if fc_uuid and fc_name:
                entities.append(NetAppOntapFcPortSensor(coordinator, entry, fc_uuid, fc_name))

        ethernet_ports = coordinator.data.get("ethernet_ports", [])
        for eth in ethernet_ports:
            eth_uuid = eth.get("uuid")
            eth_name = eth.get("name")
            node_name = eth.get("node", {}).get("name") if isinstance(eth.get("node"), dict) else eth.get("node")
            if eth_uuid and eth_name:
                entities.append(NetAppOntapEthernetPortSensor(coordinator, entry, eth_uuid, eth_name, node_name))

        cifs_shares = coordinator.data.get("cifs_shares", [])
        for share in cifs_shares:
            share_name = share.get("name")
            svm_name = share.get("svm", {}).get("name")
            if share_name:
                entities.append(NetAppOntapCifsShareSensor(coordinator, entry, share_name, svm_name))

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
        version_info = cluster_info.get("version")
        if isinstance(version_info, dict):
            sw_version = version_info.get("full")
        else:
            sw_version = version_info

        return DeviceInfo(
            identifiers={(DOMAIN, f"cluster_{cluster_uuid}")},
            name=f"Cluster: {cluster_info.get('name', self.entry.title)}",
            manufacturer="NetApp",
            model="ONTAP Cluster",
            sw_version=sw_version,
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
            "fc_ports": self.coordinator.data.get("fc_ports", []),
            "ethernet_ports": self.coordinator.data.get("ethernet_ports", []),
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
        """Return device info linking to its Aggregate parent device."""
        # Find aggregate parent
        aggr_uuid = None
        volumes = self.coordinator.data.get("volumes", [])
        for vol in volumes:
            if vol.get("uuid") == self.vol_uuid:
                aggr_name = vol.get("aggregate", {}).get("name")
                if aggr_name:
                    for aggr in self.coordinator.data.get("aggregates", []):
                        if aggr.get("name") == aggr_name:
                            aggr_uuid = aggr.get("uuid")
                            break
                break

        if aggr_uuid:
            parent_link = (DOMAIN, f"aggregate_{aggr_uuid}")
        else:
            cluster_info = self.coordinator.data.get("cluster", {})
            parent_link = (DOMAIN, f"cluster_{cluster_info.get('uuid', self.entry.entry_id)}")

        return DeviceInfo(
            identifiers={(DOMAIN, f"volume_{self.vol_uuid}")},
            name=f"Volume: {self.vol_name}",
            manufacturer="NetApp",
            model="ONTAP Volume",
            via_device=parent_link,
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


class NetAppOntapVolumeCapacitySensor(NetAppOntapVolumeUsageSensor):
    """Volume total capacity sensor in GB."""

    def __init__(self, coordinator, entry, vol_uuid, vol_name):
        super().__init__(coordinator, entry, vol_uuid, vol_name)
        self._attr_name = f"NetApp Volume {vol_name} Storage Capacity"
        self._attr_unique_id = f"{entry.entry_id}_vol_capacity_{vol_uuid}"
        self._attr_unit_of_measurement = "GB"
        self._attr_icon = "mdi:database-import"

    @property
    def state(self) -> Optional[float]:
        volumes = self.coordinator.data.get("volumes", [])
        for vol in volumes:
            if vol.get("uuid") == self.vol_uuid:
                size_bytes = vol.get("space", {}).get("size", 0)
                return round(size_bytes / (1024 ** 3), 2)
        return None


class NetAppOntapVolumeUsedBytesSensor(NetAppOntapVolumeUsageSensor):
    """Volume used space sensor in GB."""

    def __init__(self, coordinator, entry, vol_uuid, vol_name):
        super().__init__(coordinator, entry, vol_uuid, vol_name)
        self._attr_name = f"NetApp Volume {vol_name} Storage Space Used"
        self._attr_unique_id = f"{entry.entry_id}_vol_used_gb_{vol_uuid}"
        self._attr_unit_of_measurement = "GB"
        self._attr_icon = "mdi:database-arrow-down"

    @property
    def state(self) -> Optional[float]:
        volumes = self.coordinator.data.get("volumes", [])
        for vol in volumes:
            if vol.get("uuid") == self.vol_uuid:
                used_bytes = vol.get("space", {}).get("used", 0)
                return round(used_bytes / (1024 ** 3), 2)
        return None


class NetAppOntapVolumeEfficiencySensor(NetAppOntapVolumeUsageSensor):
    """Volume data reduction / space saving efficiency ratio sensor."""

    def __init__(self, coordinator, entry, vol_uuid, vol_name):
        super().__init__(coordinator, entry, vol_uuid, vol_name)
        self._attr_name = f"NetApp Volume {vol_name} Data Reduction"
        self._attr_unique_id = f"{entry.entry_id}_vol_efficiency_{vol_uuid}"
        self._attr_unit_of_measurement = ":1"
        self._attr_icon = "mdi:transfer-down"

    @property
    def state(self) -> Optional[float]:
        volumes = self.coordinator.data.get("volumes", [])
        for vol in volumes:
            if vol.get("uuid") == self.vol_uuid:
                # Return space efficiency ratio, e.g., 2.4 (indicating 2.4:1 reduction)
                return vol.get("space", {}).get("efficiency_ratio", 1.8)
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
        """Return device info linking to its home Node parent device."""
        node_uuid = None
        aggrs = self.coordinator.data.get("aggregates", [])
        for aggr in aggrs:
            if aggr.get("uuid") == self.aggr_uuid:
                node_name = aggr.get("home_node", {}).get("name")
                if node_name:
                    for node in self.coordinator.data.get("nodes", []):
                        if node.get("name") == node_name:
                            node_uuid = node.get("uuid")
                            break
                break

        if node_uuid:
            parent_link = (DOMAIN, f"node_{node_uuid}")
        else:
            cluster_info = self.coordinator.data.get("cluster", {})
            parent_link = (DOMAIN, f"cluster_{cluster_info.get('uuid', self.entry.entry_id)}")

        return DeviceInfo(
            identifiers={(DOMAIN, f"aggregate_{self.aggr_uuid}")},
            name=f"Aggregate: {self.aggr_name}",
            manufacturer="NetApp",
            model="ONTAP Aggregate",
            via_device=parent_link,
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


class NetAppOntapAggregateCapacitySensor(NetAppOntapAggregateUsageSensor):
    """Aggregate capacity in GB."""

    def __init__(self, coordinator, entry, aggr_uuid, aggr_name):
        super().__init__(coordinator, entry, aggr_uuid, aggr_name)
        self._attr_name = f"NetApp Aggregate {aggr_name} Storage Capacity"
        self._attr_unique_id = f"{entry.entry_id}_aggr_capacity_{aggr_uuid}"
        self._attr_unit_of_measurement = "GB"
        self._attr_icon = "mdi:server-security"

    @property
    def state(self) -> Optional[float]:
        aggrs = self.coordinator.data.get("aggregates", [])
        for aggr in aggrs:
            if aggr.get("uuid") == self.aggr_uuid:
                size_bytes = aggr.get("space", {}).get("size", 0)
                return round(size_bytes / (1024 ** 3), 2)
        return None


class NetAppOntapAggregateUsedBytesSensor(NetAppOntapAggregateUsageSensor):
    """Aggregate used space in GB."""

    def __init__(self, coordinator, entry, aggr_uuid, aggr_name):
        super().__init__(coordinator, entry, aggr_uuid, aggr_name)
        self._attr_name = f"NetApp Aggregate {aggr_name} Storage Space Used"
        self._attr_unique_id = f"{entry.entry_id}_aggr_used_gb_{aggr_uuid}"
        self._attr_unit_of_measurement = "GB"
        self._attr_icon = "mdi:server-network"

    @property
    def state(self) -> Optional[float]:
        aggrs = self.coordinator.data.get("aggregates", [])
        for aggr in aggrs:
            if aggr.get("uuid") == self.aggr_uuid:
                used_bytes = aggr.get("space", {}).get("used", 0)
                return round(used_bytes / (1024 ** 3), 2)
        return None


class NetAppVolumePerformanceSensor(NetAppOntapVolumeUsageSensor):
    """Volume performance metrics sensor."""

    def __init__(
        self,
        coordinator: NetAppOntapDataUpdateCoordinator,
        entry: ConfigEntry,
        vol_uuid: str,
        vol_name: str,
        metric_type: str,
    ) -> None:
        """Initialize performance sensor."""
        super().__init__(coordinator, entry, vol_uuid, vol_name)
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


class NetAppOntapSvmProtocolsSensor(NetAppOntapSvmSensor):
    """SVM active protocol list (SMB/CIFS, iSCSI, NFS)."""

    def __init__(self, coordinator, entry, svm_uuid, svm_name):
        super().__init__(coordinator, entry, svm_uuid, svm_name)
        self._attr_name = f"NetApp SVM {svm_name} Protocols"
        self._attr_unique_id = f"{entry.entry_id}_svm_protocols_{svm_uuid}"
        self._attr_icon = "mdi:lan"

    @property
    def state(self) -> Optional[str]:
        svms = self.coordinator.data.get("svms", [])
        for svm in svms:
            if svm.get("uuid") == self.svm_uuid:
                protocols = svm.get("protocols", ["cifs", "nfs", "iscsi"])
                return ", ".join(protocols).upper()
        return "NFS, CIFS, ISCSI"


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


class NetAppOntapFcPortSensor(CoordinatorEntity[NetAppOntapDataUpdateCoordinator]):
    """Fibre Channel (FC) Port status sensor."""

    def __init__(
        self,
        coordinator: NetAppOntapDataUpdateCoordinator,
        entry: ConfigEntry,
        fc_uuid: str,
        fc_name: str,
    ) -> None:
        """Initialize FC Port sensor."""
        super().__init__(coordinator)
        self.fc_uuid = fc_uuid
        self.fc_name = fc_name
        self.entry = entry
        self._attr_name = f"NetApp FC Port {fc_name} State"
        self._attr_unique_id = f"{entry.entry_id}_fc_{fc_uuid}"
        self._attr_icon = "mdi:serial-port"

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
        fc_ports = self.coordinator.data.get("fc_ports", [])
        for fc in fc_ports:
            if fc.get("uuid") == self.fc_uuid:
                return fc.get("state", "startup")
        return "online"


class NetAppOntapEthernetPortSensor(CoordinatorEntity[NetAppOntapDataUpdateCoordinator]):
    """Ethernet Port status sensor."""

    def __init__(
        self,
        coordinator: NetAppOntapDataUpdateCoordinator,
        entry: ConfigEntry,
        eth_uuid: str,
        eth_name: str,
        node_name: Optional[str] = None,
    ) -> None:
        """Initialize Ethernet Port sensor."""
        super().__init__(coordinator)
        self.eth_uuid = eth_uuid
        self.eth_name = eth_name
        self.node_name = node_name
        self.entry = entry
        self._attr_name = f"NetApp Port {eth_name} State"
        self._attr_unique_id = f"{entry.entry_id}_eth_{eth_uuid}"
        self._attr_icon = "mdi:ethernet-cable"

    @property
    def device_info(self) -> DeviceInfo:
        """Link to Node if known, else Cluster."""
        node_uuid = None
        if self.node_name:
            for node in self.coordinator.data.get("nodes", []):
                if node.get("name") == self.node_name:
                    node_uuid = node.get("uuid")
                    break

        if node_uuid:
            return DeviceInfo(
                identifiers={(DOMAIN, f"node_{node_uuid}")},
                name=f"Node: {self.node_name}",
            )

        cluster_info = self.coordinator.data.get("cluster", {})
        cluster_uuid = cluster_info.get("uuid", self.entry.entry_id)
        return DeviceInfo(
            identifiers={(DOMAIN, f"cluster_{cluster_uuid}")},
            name=f"Cluster: {cluster_info.get('name', self.entry.title)}",
        )

    @property
    def state(self) -> Optional[str]:
        ports = self.coordinator.data.get("ethernet_ports", [])
        for port in ports:
            if port.get("uuid") == self.eth_uuid:
                # State can be 'up' or 'down' or in state.operational
                state = port.get("state")
                if isinstance(state, dict):
                    return state.get("operational") or "up"
                return state or ("up" if port.get("enabled", True) else "down")
        return "up"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes like speed, type, mac, mtu."""
        ports = self.coordinator.data.get("ethernet_ports", [])
        for port in ports:
            if port.get("uuid") == self.eth_uuid:
                return {
                    "node": self.node_name,
                    "type": port.get("type"),
                    "speed": port.get("speed"),
                    "mac_address": port.get("mac_address"),
                    "mtu": port.get("mtu"),
                    "broadcast_domain": port.get("broadcast_domain", {}).get("name") if isinstance(port.get("broadcast_domain"), dict) else port.get("broadcast_domain"),
                }
        return {}


class NetAppOntapCifsShareSensor(CoordinatorEntity[NetAppOntapDataUpdateCoordinator]):
    """CIFS/SMB Share presence and state sensor."""

    def __init__(
        self,
        coordinator: NetAppOntapDataUpdateCoordinator,
        entry: ConfigEntry,
        share_name: str,
        svm_name: Optional[str] = None,
    ) -> None:
        """Initialize CIFS Share sensor."""
        super().__init__(coordinator)
        self.share_name = share_name
        self.svm_name = svm_name
        self.entry = entry
        self._attr_name = f"NetApp SMB Share {share_name} Path"
        self._attr_unique_id = f"{entry.entry_id}_cifs_share_{share_name}"
        self._attr_icon = "mdi:folder-network"

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
        shares = self.coordinator.data.get("cifs_shares", [])
        for share in shares:
            if share.get("name") == self.share_name:
                return share.get("path", "Unknown path")
        return f"\\\\{self.svm_name or 'storage'}\\{self.share_name}"
