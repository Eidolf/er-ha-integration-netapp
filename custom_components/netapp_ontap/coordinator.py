"""DataUpdateCoordinator for NetApp ONTAP."""
from datetime import timedelta
import logging
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL
from .api import NetAppOntapAPI

_LOGGER = logging.getLogger(__name__)

class NetAppOntapDataUpdateCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Class to manage fetching NetApp ONTAP data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: NetAppOntapAPI,
        detail_level: str,
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        """Initialize."""
        self.api = api
        self.detail_level = detail_level
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from NetApp ONTAP REST API."""
        try:
            _LOGGER.debug("Fetching latest metrics from NetApp ONTAP cluster (Level: %s)", self.detail_level)
            
            cluster_info = await self.api.get_cluster_info()
            nodes_data = await self.api.get_nodes()
            volumes_data = await self.api.get_volumes()
            aggregates_data = await self.api.get_aggregates()

            interfaces = []
            events = []
            disks = []
            cloud_targets = []
            svms = []
            licenses = []

            # Advanced or All Detail Level polls more endpoints
            if self.detail_level in ("advanced", "all"):
                interfaces_data = await self.api.get_interfaces()
                interfaces = interfaces_data.get("records", [])
                events_data = await self.api.get_events()
                events = events_data.get("records", [])
                try:
                    disks_data = await self.api.get_disks()
                    disks = disks_data.get("records", [])
                except Exception as disk_err:
                    _LOGGER.debug("Disks endpoint query failed or not supported: %s", disk_err)

            # All Detail Level also polls cloud, svm, licenses, fc ports, ethernet ports, cifs shares
            fc_ports = []
            ethernet_ports = []
            cifs_shares = []
            if self.detail_level == "all":
                cloud_data = await self.api.get_cloud_targets()
                cloud_targets = cloud_data.get("records", [])
                svm_data = await self.api.get_svms()
                svms = svm_data.get("records", [])
                license_data = await self.api.get_licenses()
                licenses = license_data.get("records", [])
                fc_data = await self.api.get_fc_ports()
                fc_ports = fc_data.get("records", [])
                eth_data = await self.api.get_ethernet_ports()
                ethernet_ports = eth_data.get("records", [])
                cifs_data = await self.api.get_cifs_shares()
                cifs_shares = cifs_data.get("records", [])

            return {
                "cluster": cluster_info,
                "nodes": nodes_data.get("records", []),
                "volumes": volumes_data.get("records", []),
                "aggregates": aggregates_data.get("records", []),
                "interfaces": interfaces,
                "events": events,
                "disks": disks,
                "cloud_targets": cloud_targets,
                "svms": svms,
                "licenses": licenses,
                "fc_ports": fc_ports,
                "ethernet_ports": ethernet_ports,
                "cifs_shares": cifs_shares,
            }

        except Exception as err:
            _LOGGER.error("Error communicating with NetApp ONTAP REST API: %s", err)
            raise UpdateFailed(f"Error communicating with NetApp API: {err}") from err
