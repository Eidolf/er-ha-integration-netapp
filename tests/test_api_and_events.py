"""Unit tests for NetApp ONTAP integration."""
import sys
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import re

# Mock homeassistant and aiohttp for standalone testing
import types

class MockModule(types.ModuleType):
    def __getattr__(self, name):
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


class TestNetAppOntapAPI(unittest.IsolatedAsyncioTestCase):
    """Test API client methods including pagination."""

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


class TestNetAppNodeEventMatching(unittest.TestCase):
    """Test EMS event text extraction and node token matching."""

    def match_event(self, node_name: str, ev: dict) -> bool:
        node_name_lower = (node_name or "").lower()
        node_token_pattern = rf"\b{re.escape(node_name_lower)}\b" if node_name_lower else None

        msg_obj = ev.get("log_message") if ev.get("log_message") is not None else ev.get("message")
        msg_text = ""
        if isinstance(msg_obj, str):
            msg_text = msg_obj
        elif isinstance(msg_obj, dict):
            msg_text = msg_obj.get("text") or msg_obj.get("name") or msg_obj.get("message") or ""
        elif msg_obj is not None:
            msg_text = str(msg_obj)

        ev_node = ev.get("node", {})
        ev_node_name = ev_node.get("name", "") if isinstance(ev_node, dict) else str(ev_node)

        if ev_node_name and node_name_lower == ev_node_name.lower():
            return True
        if node_token_pattern and re.search(node_token_pattern, msg_text, re.IGNORECASE):
            return True
        return False

    def test_exact_ev_node_match(self):
        ev = {"node": {"name": "node1"}, "message": "Disk failed"}
        self.assertTrue(self.match_event("node1", ev))
        self.assertFalse(self.match_event("node2", ev))

    def test_prefix_node_name_isolation(self):
        """Ensure node1 does not match node10 in message text."""
        ev = {"message": "Alert on node10: Power supply degraded"}
        self.assertFalse(self.match_event("node1", ev))
        self.assertTrue(self.match_event("node10", ev))

    def test_log_message_preferred_over_message(self):
        ev = {
            "log_message": "Node node1 CPU over temperature",
            "message": {"text": "Generic cluster alert"},
        }
        self.assertTrue(self.match_event("node1", ev))


if __name__ == "__main__":
    unittest.main()
