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
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        """Initialize."""
        self.api = api
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from NetApp ONTAP REST API."""
        try:
            # Gather all system parameters concurrently
            # cluster info, nodes, volumes, aggregates, interfaces, and events
            _LOGGER.debug("Fetching latest metrics from NetApp ONTAP cluster")
            
            cluster_info = await self.api.get_cluster_info()
            nodes_data = await self.api.get_nodes()
            volumes_data = await self.api.get_volumes()
            aggregates_data = await self.api.get_aggregates()
            interfaces_data = await self.api.get_interfaces()
            events_data = await self.api.get_events()

            return {
                "cluster": cluster_info,
                "nodes": nodes_data.get("records", []),
                "volumes": volumes_data.get("records", []),
                "aggregates": aggregates_data.get("records", []),
                "interfaces": interfaces_data.get("records", []),
                "events": events_data.get("records", []),
            }

        except Exception as err:
            _LOGGER.error("Error communicating with NetApp ONTAP REST API: %s", err)
            raise UpdateFailed(f"Error communicating with NetApp API: {err}") from err
