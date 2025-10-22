"""The speech service."""

import logging

from homeassistant.components.tts import (
    TextToSpeechEntity,
    TTSAudioResponse,
)
from homeassistant.components.tts.entity import TTSAudioRequest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from propcache.api import cached_property

from .const import DEFAULT_LANG
from .volc import VolcTTSClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([VolcTTSEntity(hass, config_entry)])


class VolcTTSEntity(TextToSpeechEntity):
    _attr_name = "Volcengine TTS"

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        voice_type = config_entry.data["voice_type"]
        self._attr_name = f"Volc TTS({voice_type})"
        self._attr_unique_id = f"{config_entry.entry_id[:7]}-volc-tts"
        self.tts_client = VolcTTSClient(
            appid=config_entry.data["app_id"],
            access_token=config_entry.data["access_token"],
            voice_type=voice_type,
        )

    @cached_property
    def default_language(self) -> str:
        return DEFAULT_LANG

    @cached_property
    def supported_languages(self) -> list[str]:
        return list([DEFAULT_LANG])

    async def async_stream_tts_audio(
        self, request: TTSAudioRequest
    ) -> TTSAudioResponse:
        data_gen = self.tts_client.tts(request.message_gen)
        return TTSAudioResponse(extension="mp3", data_gen=data_gen)
