"""BasaltNotes: instructions and memory of Assist, kept in a vault."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN, CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BasaltAuthError, BasaltClient, BasaltError
from .const import (
    CONF_EMBEDDING_KEY,
    CONF_EMBEDDING_MODEL,
    CONF_EMBEDDING_URL,
    CONF_INSTRUCTIONS_FOLDER,
    CONF_LEARNED_FOLDER,
    CONF_MEMORY_BUDGET,
    CONF_MEMORY_FOLDER,
    CONF_VAULT_ID,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_MEMORY_BUDGET,
    DOMAIN,
)
from .embeddings import Embedder
from .llm_api import async_register_apis
from .vault import AssistVault

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]
UPDATE_INTERVAL = timedelta(minutes=5)

type BasaltConfigEntry = ConfigEntry[DataUpdateCoordinator[None]]


async def async_setup_entry(hass: HomeAssistant, entry: BasaltConfigEntry) -> bool:
    """Connect to the vault and offer the LLM APIs."""
    session = async_get_clientsession(hass)
    client = BasaltClient(session, entry.data[CONF_URL], entry.data[CONF_TOKEN])
    embedder = None
    if url := entry.options.get(CONF_EMBEDDING_URL):
        embedder = Embedder(
            session,
            url,
            entry.options.get(CONF_EMBEDDING_MODEL) or DEFAULT_EMBEDDING_MODEL,
            entry.options.get(CONF_EMBEDDING_KEY) or None,
        )
    vault = AssistVault(
        hass,
        client,
        entry.entry_id,
        vault_id=entry.data[CONF_VAULT_ID],
        instructions_folder=entry.data[CONF_INSTRUCTIONS_FOLDER],
        learned_folder=entry.data[CONF_LEARNED_FOLDER],
        memory_folder=entry.data[CONF_MEMORY_FOLDER],
        memory_budget=entry.options.get(CONF_MEMORY_BUDGET, DEFAULT_MEMORY_BUDGET),
        language=hass.config.language,
        embedder=embedder,
    )
    await vault.async_load()

    # With a copy from the last run the assistant keeps working while the server is down
    try:
        await vault.async_refresh()
    except BasaltAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except BasaltError as err:
        if not vault.notes:
            raise ConfigEntryNotReady(str(err)) from err
        _LOGGER.warning("BasaltNotes not reachable, using the last known copy: %s", err)

    async def _async_update() -> None:
        try:
            await vault.async_refresh()
        except BasaltAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except BasaltError as err:
            raise UpdateFailed(str(err)) from err

    coordinator: DataUpdateCoordinator[None] = DataUpdateCoordinator(
        hass,
        _LOGGER,
        config_entry=entry,
        name=DOMAIN,
        update_method=_async_update,
        update_interval=UPDATE_INTERVAL,
    )
    coordinator.vault = vault
    await coordinator.async_refresh()
    entry.runtime_data = coordinator

    for unregister in async_register_apis(hass, vault):
        entry.async_on_unload(unregister)
    entry.async_on_unload(entry.add_update_listener(_async_options_changed))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_options_changed(hass: HomeAssistant, entry: BasaltConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: BasaltConfigEntry) -> bool:
    """Unload the integration."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
