"""Unit tests for NetApp ONTAP integration."""
import sys
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import re

# Mock homeassistant and aiohttp for standalone testing
import types

class CoordinatorEntity:
    def __init__(self, coordinator=None, *args, **kwargs):
        self.coordinator = coordinator
    def __class_getitem__(cls, item):
        return cls

class BinarySensorEntity:
    pass

class SensorEntity:
    pass

class DataUpdateCoordinator:
    def __init__(self, hass=None, logger=None, *args, **kwargs):
        self.hass = hass
        self.logger = logger
        self.data = {}
    def __class_getitem__(cls, item):
        return cls

class UpdateFailed(Exception):
    pass

class MockModule(types.ModuleType):
    def __getattr__(self, name):
        if name == "CoordinatorEntity":
            return CoordinatorEntity
        if name == "BinarySensorEntity":
            return BinarySensorEntity
        if name == "SensorEntity":
            return SensorEntity
        if name == "DataUpdateCoordinator":
            return DataUpdateCoordinator
        if name == "UpdateFailed":
            return UpdateFailed
        return MagicMock()

for mod_name in [
    "aiohttp",
    "homeassistant",
    "homeassistant.core",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.helpers",
    "homeassistant.helpers.aiohttp_client",
    "homeassistant.helpers.entity",
    "homeassistant.helpers.entity_platform",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.components",
    "homeassistant.components.sensor",
    "homeassistant.components.binary_sensor",
    "homeassistant.components.switch",
    "homeassistant.components.button",
]:
    sys.modules[mod_name] = MockModule(mod_name)

from custom_components.netapp_ontap.api import NetAppOntapAPI, NetAppOntapAPIError
from custom_components.netapp_ontap.binary_sensor import NetAppOntapNodeHealthSensor
from custom_components.netapp_ontap.coordinator import NetAppOntapDataUpdateCoordinator


class TestNetAppOntapAPI(unittest.IsolatedAsyncioTestCase):
    """Test API client methods including pagination and URL validation."""

    async def test_get_disks_pagination(self):
        """Test get_disks follows _links.next pagination."""
        api = NetAppOntapAPI("127.0.0.1", 443, username="admin", password="password")

        page1 = {
            "records": [{"name": "1.0.0", "uid": "uid1"}],
            "_links": {"next": {"href": "/api/storage/disks?start=1"}},
        }
        page2 = {
            "records": [{"name": "1.0.1", "uid": "uid2"}],
            "_links": {},
        }

        with patch.object(api, "_request", side_effect=[page1, page2]) as mock_req:
            res = await api.get_disks()
            self.assertEqual(len(res["records"]), 2)
            self.assertEqual(res["records"][0]["name"], "1.0.0")
            self.assertEqual(res["records"][1]["name"], "1.0.1")
            self.assertEqual(mock_req.call_count, 2)

    async def test_get_ethernet_ports_pagination(self):
        """Test get_ethernet_ports follows _links.next pagination."""
        api = NetAppOntapAPI("127.0.0.1", 443, username="admin", password="password")

        page1 = {
            "records": [{"uuid": "eth1", "name": "e0a"}],
            "_links": {"next": {"href": "/api/network/ethernet/ports?start=1"}},
        }
        page2 = {
            "records": [{"uuid": "eth2", "name": "e0b"}],
            "_links": {},
        }

        with patch.object(api, "_request", side_effect=[page1, page2]) as mock_req:
            res = await api.get_ethernet_ports()
            self.assertEqual(len(res["records"]), 2)
            self.assertEqual(res["records"][0]["name"], "e0a")
            self.assertEqual(res["records"][1]["name"], "e0b")
            self.assertEqual(mock_req.call_count, 2)

    async def test_reject_untrusted_pagination_urls(self):
        """Test that external, non-HTTPS, or mismatched URLs are rejected and valid HTTPS default 443 URLs are accepted."""
        api = NetAppOntapAPI("192.168.1.50", 443, username="admin", password="password")

        # External host
        with self.assertRaises(NetAppOntapAPIError) as ctx1:
            await api._request("GET", "https://malicious-site.com/api/storage/disks")
        self.assertIn("Untrusted", str(ctx1.exception))

        # Plain HTTP
        with self.assertRaises(NetAppOntapAPIError) as ctx2:
            await api._request("GET", "http://192.168.1.50:443/api/storage/disks")
        self.assertIn("Untrusted", str(ctx2.exception))

        # Userinfo in URL
        with self.assertRaises(NetAppOntapAPIError) as ctx3:
            await api._request("GET", "https://user:pass@192.168.1.50:443/api/storage/disks")
        self.assertIn("Untrusted", str(ctx3.exception))

        # Port mismatch
        with self.assertRaises(NetAppOntapAPIError) as ctx4:
            await api._request("GET", "https://192.168.1.50:8443/api/storage/disks")
        self.assertIn("Untrusted", str(ctx4.exception))

        # Valid HTTPS with omitted default port 443 accepted
        with patch.object(api.session, "request") as mock_req:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value={"records": []})
            mock_req.return_value.__aenter__.return_value = mock_resp
            res = await api._request("GET", "https://192.168.1.50/api/storage/disks")
            self.assertEqual(res, {"records": []})


class TestNetAppCoordinatorFailurePolicy(unittest.IsolatedAsyncioTestCase):
    """Test coordinator optional endpoint status handling."""

    async def test_coordinator_suppresses_unsupported_status(self):
        api = MagicMock()
        api.get_cluster_info = AsyncMock(return_value={"name": "cluster1"})
        api.get_nodes = AsyncMock(return_value={"records": []})
        api.get_volumes = AsyncMock(return_value={"records": []})
        api.get_aggregates = AsyncMock(return_value={"records": []})
        api.get_interfaces = AsyncMock(return_value={"records": []})
        api.get_events = AsyncMock(return_value={"records": []})
        # 404 Not Found on disks
        api.get_disks = AsyncMock(side_effect=NetAppOntapAPIError(404, "Endpoint not found"))

        hass = MagicMock()
        coord = NetAppOntapDataUpdateCoordinator(hass, api, detail_level="advanced")
        data = await coord._async_update_data()
        self.assertEqual(data["disks"], [])

    async def test_coordinator_propagates_auth_and_server_error(self):
        api = MagicMock()
        api.get_cluster_info = AsyncMock(return_value={"name": "cluster1"})
        api.get_nodes = AsyncMock(return_value={"records": []})
        api.get_volumes = AsyncMock(return_value={"records": []})
        api.get_aggregates = AsyncMock(return_value={"records": []})
        api.get_interfaces = AsyncMock(return_value={"records": []})
        api.get_events = AsyncMock(return_value={"records": []})
        # 401 Unauthorized
        api.get_disks = AsyncMock(side_effect=NetAppOntapAPIError(401, "Auth failed"))

        hass = MagicMock()
        coord = NetAppOntapDataUpdateCoordinator(hass, api, detail_level="advanced")
        with self.assertRaises(Exception) as ctx:
            await coord._async_update_data()
        self.assertIn("Auth failed", str(ctx.exception))


class TestNetAppNodeHealthSensorProductionPath(unittest.TestCase):
    """Test NetAppOntapNodeHealthSensor using production extra_state_attributes."""

    def create_sensor_with_events(self, node_uuid: str, node_name: str, events: list):
        coordinator = MagicMock()
        coordinator.data = {
            "cluster": {"name": "cluster1", "uuid": "c-uuid"},
            "nodes": [{"uuid": node_uuid, "name": node_name, "state": "healthy"}],
            "events": events,
        }
        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.title = "NetApp Test"
        return NetAppOntapNodeHealthSensor(coordinator, entry, node_uuid, node_name)

    def test_exact_ev_node_match(self):
        sensor_node1 = self.create_sensor_with_events("n1", "node1", [
            {"node": {"name": "node1"}, "message": "Disk failed"}
        ])
        sensor_node2 = self.create_sensor_with_events("n2", "node2", [
            {"node": {"name": "node1"}, "message": "Disk failed"}
        ])

        self.assertIn("Disk failed", sensor_node1.extra_state_attributes["recent_alerts"][0])
        self.assertEqual(sensor_node2.extra_state_attributes["recent_alerts"], ["No active alerts detected"])

    def test_prefix_node_name_isolation(self):
        """Ensure node1 does not match node10 in message text."""
        sensor_node1 = self.create_sensor_with_events("n1", "node1", [
            {"message": "Alert on node10: Power supply degraded"}
        ])
        sensor_node10 = self.create_sensor_with_events("n10", "node10", [
            {"message": "Alert on node10: Power supply degraded"}
        ])

        self.assertEqual(sensor_node1.extra_state_attributes["recent_alerts"], ["No active alerts detected"])
        self.assertIn("Power supply degraded", sensor_node10.extra_state_attributes["recent_alerts"][0])

    def test_log_message_preferred_over_message(self):
        sensor = self.create_sensor_with_events("n1", "node1", [
            {
                "log_message": "Node node1 CPU over temperature",
                "message": {"text": "Generic cluster alert"},
            }
        ])
        self.assertIn("Node node1 CPU over temperature", sensor.extra_state_attributes["recent_alerts"][0])


if __name__ == "__main__":
    unittest.main()
