"""The NetApp ONTAP integration."""
import logging
from typing import Dict, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, PLATFORMS, CONF_VERIFY_SSL, CONF_API_TOKEN, CONF_DETAIL_LEVEL
from .api import NetAppOntapAPI
from .coordinator import NetAppOntapDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up NetApp ONTAP from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host = entry.data["host"]
    port = entry.data["port"]
    username = entry.data.get("username")
    password = entry.data.get("password")
    api_token = entry.data.get(CONF_API_TOKEN)
    verify_ssl = entry.data.get(CONF_VERIFY_SSL, False)
    detail_level = entry.data.get(CONF_DETAIL_LEVEL, "standard")

    session = async_get_clientsession(hass)
    
    api = NetAppOntapAPI(
        host=host,
        port=port,
        username=username,
        password=password,
        api_token=api_token,
        verify_ssl=verify_ssl,
        session=session,
    )

    coordinator = NetAppOntapDataUpdateCoordinator(hass, api, detail_level=detail_level)

    # Perform initial update
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        api = data["api"]
        await api.close()

    return unload_ok
