"""Config flow for NetApp ONTAP integration."""
import logging
from typing import Any, Dict, Optional
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_VERIFY_SSL,
    CONF_API_TOKEN,
    CONF_DETAIL_LEVEL,
    DEFAULT_PORT,
    DETAIL_LEVEL_STANDARD,
    DETAIL_LEVEL_ADVANCED,
    DETAIL_LEVEL_ALL,
)
from .api import NetAppOntapAPI

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required("host"): str,
        vol.Required("port", default=DEFAULT_PORT): int,
        vol.Optional("username"): str,
        vol.Optional("password"): str,
        vol.Optional(CONF_API_TOKEN): str,
        vol.Required(CONF_VERIFY_SSL, default=False): bool,
        vol.Required(CONF_DETAIL_LEVEL, default=DETAIL_LEVEL_STANDARD): vol.In(
            [DETAIL_LEVEL_STANDARD, DETAIL_LEVEL_ADVANCED, DETAIL_LEVEL_ALL]
        ),
    }
)

async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass)
    
    api = NetAppOntapAPI(
        host=data["host"],
        port=data["port"],
        username=data.get("username"),
        password=data.get("password"),
        api_token=data.get(CONF_API_TOKEN),
        verify_ssl=data.get(CONF_VERIFY_SSL, False),
        session=session,
    )

    if not await api.test_connection():
        raise CannotConnect

    cluster_info = await api.get_cluster_info()
    return {
        "title": cluster_info.get("name", "NetApp ONTAP Cluster"),
        "uuid": cluster_info.get("uuid"),
    }

class NetAppOntapConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NetApp ONTAP."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                
                await self.async_set_unique_id(info["uuid"])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=USER_SCHEMA,
            errors=errors,
        )

class CannotConnect(Exception):
    """Error to indicate we cannot connect."""
