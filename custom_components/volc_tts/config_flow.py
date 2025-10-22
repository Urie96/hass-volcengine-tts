import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from typing import Any, Dict
import logging

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: Dict[str, str] = {}
        if user_input:
            return self.async_create_entry(title="Volc TTS", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("app_id"): str,
                    vol.Required("access_token"): str,
                    vol.Optional(
                        "model", default="zh_female_wanwanxiaohe_moon_bigtts"
                    ): str,
                },
            ),
            errors=errors,
        )
