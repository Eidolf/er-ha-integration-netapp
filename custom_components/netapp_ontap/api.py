"""NetApp ONTAP REST API Client."""
import logging
import asyncio
import aiohttp
from typing import Any, Dict, List, Optional
import time

_LOGGER = logging.getLogger(__name__)

class NetAppOntapAPIError(Exception):
    """Exception for NetApp ONTAP API errors carrying status code."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.message = message


class NetAppOntapAPI:
    """API Client for NetApp ONTAP."""

    def __init__(
        self,
        host: str,
        port: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_token: Optional[str] = None,
        verify_ssl: bool = False,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        """Initialize the API client."""
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.api_token = api_token
        self.verify_ssl = verify_ssl
        self.session = session or aiohttp.ClientSession()
        self._close_session = session is None

        # Build base URL
        protocol = "https"
        self.base_url = f"{protocol}://{self.host}:{self.port}"
        
        # Simple cache to avoid double polling within short intervals
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 5  # seconds

    async def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retries: int = 3,
    ) -> Any:
        """Make an async request to the ONTAP API."""
        url = f"{self.base_url}{path}" if not path.startswith("http") else path
        headers = {"Content-Type": "application/json"}

        # Set up Auth
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        elif self.username and self.password:
            auth = aiohttp.BasicAuth(self.username, self.password)
        else:
            auth = None

        # Handle cache for GET requests
        cache_key = f"{method}:{path}:{str(params)}"
        if method == "GET" and cache_key in self._cache:
            cache_val, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return cache_val

        # Setup SSL context
        connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
        
        for attempt in range(retries):
            try:
                async with self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    auth=auth if not self.api_token else None,
                    json=json,
                    params=params,
                    ssl=self.verify_ssl,
                ) as response:
                    if response.status in (401, 403):
                        error_text = await response.text()
                        raise NetAppOntapAPIError(response.status, f"Authentication failed: {error_text}")
                    
                    if response.status >= 400:
                        error_text = await response.text()
                        raise NetAppOntapAPIError(response.status, error_text)

                    if response.status == 204:
                        return True

                    result = await response.json()

                    if method == "GET":
                        self._cache[cache_key] = (result, time.time())

                    return result

            except aiohttp.ClientConnectorError as err:
                _LOGGER.warning("Connection failure to %s on attempt %d: %s", url, attempt + 1, err)
                if attempt == retries - 1:
                    raise Exception(f"Cannot connect to {self.host}") from err
                await asyncio.sleep(1 * (attempt + 1))
            except NetAppOntapAPIError:
                raise
            except Exception as err:
                _LOGGER.error("API error during %s request to %s: %s", method, url, err)
                raise err

    async def _request_all_pages(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fetch all records following _links.next pagination links."""
        res = await self._request("GET", path, params=params)
        if not isinstance(res, dict):
            return res

        all_records = list(res.get("records", []))
        next_link = res.get("_links", {}).get("next", {}).get("href")

        while next_link:
            next_res = await self._request("GET", next_link)
            if not isinstance(next_res, dict):
                break
            all_records.extend(next_res.get("records", []))
            next_link = next_res.get("_links", {}).get("next", {}).get("href")

        return {
            **res,
            "records": all_records,
            "num_records": len(all_records),
        }

    async def test_connection(self) -> bool:
        """Test authentication and connectivity."""
        try:
            res = await self._request("GET", "/api/cluster")
            return res is not None
        except Exception:
            return False

    async def get_cluster_info(self) -> Dict[str, Any]:
        """Fetch Cluster information."""
        return await self._request("GET", "/api/cluster")

    async def get_nodes(self) -> Dict[str, Any]:
        """Fetch storage nodes."""
        return await self._request("GET", "/api/cluster/nodes", params={"fields": "*"})

    async def get_volumes(self) -> Dict[str, Any]:
        """Fetch storage volumes."""
        return await self._request("GET", "/api/storage/volumes", params={"fields": "*"})

    async def get_aggregates(self) -> Dict[str, Any]:
        """Fetch storage aggregates."""
        return await self._request("GET", "/api/storage/aggregates", params={"fields": "*,space.*,space.block_storage.*,home_node.*,node.*,block_storage.*"})

    async def get_disks(self) -> Dict[str, Any]:
        """Fetch physical disks."""
        return await self._request_all_pages(
            "/api/storage/disks",
            params={"fields": "name,uid,serial_number,state,type,class,model,vendor,rpm,firmware_version,node.name"},
        )

    async def get_interfaces(self) -> Dict[str, Any]:
        """Fetch ethernet and SAN interfaces."""
        return await self._request("GET", "/api/network/ip/interfaces", params={"fields": "*"})

    async def get_events(self) -> Dict[str, Any]:
        """Fetch recent events or EMS messages."""
        return await self._request("GET", "/api/support/ems/events", params={"max_records": 20, "order_by": "time desc"})

    async def get_cloud_targets(self) -> Dict[str, Any]:
        """Fetch cloud (object storage) targets."""
        return await self._request("GET", "/api/cloud/targets", params={"fields": "*"})

    async def get_svms(self) -> Dict[str, Any]:
        """Fetch storage virtual machines (SVMs)."""
        return await self._request("GET", "/api/svm/svms", params={"fields": "*"})

    async def get_licenses(self) -> Dict[str, Any]:
        """Fetch licenses."""
        return await self._request("GET", "/api/cluster/licensing/licenses", params={"fields": "*"})

    async def get_fc_ports(self) -> Dict[str, Any]:
        """Fetch FC ports."""
        return await self._request("GET", "/api/network/fc/ports", params={"fields": "*"})

    async def get_ethernet_ports(self) -> Dict[str, Any]:
        """Fetch Ethernet ports."""
        return await self._request_all_pages(
            "/api/network/ethernet/ports",
            params={"fields": "uuid,name,node.name,state,enabled,type,speed,mac_address,mtu,broadcast_domain.name"},
        )

    async def get_cifs_shares(self) -> Dict[str, Any]:
        """Fetch CIFS shares."""
        return await self._request("GET", "/api/protocols/cifs/shares", params={"fields": "*"})

    async def set_volume_state(self, volume_uuid: str, state: str) -> bool:
        """Modify volume state (e.g. online, offline)."""
        # ONTAP REST API uses PATCH /api/storage/volumes/{uuid}
        # with state: "online" or "offline"
        path = f"/api/storage/volumes/{volume_uuid}"
        payload = {"state": state}
        await self._request("PATCH", path, json=payload)
        return True

    async def create_snapshot(self, volume_uuid: str, snapshot_name: str) -> bool:
        """Create a volume snapshot."""
        # ONTAP REST API uses POST /api/storage/volumes/{uuid}/snapshots
        path = f"/api/storage/volumes/{volume_uuid}/snapshots"
        payload = {"name": snapshot_name}
        await self._request("POST", path, json=payload)
        return True

    async def set_volume_qos(self, volume_uuid: str, max_iops: int) -> bool:
        """Set QoS policy maximum IOPS limit on a volume."""
        path = f"/api/storage/volumes/{volume_uuid}"
        payload = {
            "nas": {
                "security_style": "unix" # placeholder / verification
            },
            "qos": {
                "policy_group": {
                    "max_throughput_iops": max_iops
                }
            }
        }
        await self._request("PATCH", path, json=payload)
        return True

    async def close(self) -> None:
        """Close client session if owned."""
        if self._close_session and self.session:
            await self.session.close()
