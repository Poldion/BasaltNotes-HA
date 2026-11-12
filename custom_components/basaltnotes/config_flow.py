"""Config flow: connect to BasaltNotes and find or create the vault."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import probatio

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_TOKEN, CONF_URL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import BasaltAuthError, BasaltClient, BasaltConnectionError, BasaltError
from .const import (
    CONF_EMBEDDING_KEY,
    CONF_EMBEDDING_MODEL,
    CONF_EMBEDDING_URL,
    CONF_INSTRUCTIONS_FOLDER,
    CONF_LEARNED_FOLDER,
    CONF_MEMORY_BUDGET,
    CONF_MEMORY_FOLDER,
    CONF_VAULT_ID,
    CONF_VAULT_NAME,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_MEMORY_BUDGET,
    DEFAULT_VAULT_NAME,
    DOMAIN,
)
from .vault import AssistVault, texts_for

_LOGGER = logging.getLogger(__name__)

_TOKEN_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


class BasaltConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the setup."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the server, the token and the name of the vault."""
        errors: dict[str, str] = {}
        if user_input is not None:
            client = BasaltClient(
                async_get_clientsession(self.hass), user_input[CONF_URL], user_input[CONF_TOKEN]
            )
            try:
                return await self._async_create(client, user_input)
            except BasaltConnectionError:
                errors["base"] = "cannot_connect"
            except BasaltAuthError:
                errors["base"] = "invalid_auth"
            except BasaltError:
                _LOGGER.exception("Unexpected answer from BasaltNotes")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                probatio.Schema(
                    {
                        probatio.Required(CONF_URL): TextSelector(
                            TextSelectorConfig(type=TextSelectorType.URL)
                        ),
                        probatio.Required(CONF_TOKEN): _TOKEN_SELECTOR,
                        probatio.Required(CONF_VAULT_NAME, default=DEFAULT_VAULT_NAME): TextSelector(),
                    }
                ),
                user_input,
            ),
            errors=errors,
        )

    async def _async_create(self, client: BasaltClient, user_input: dict[str, Any]) -> ConfigFlowResult:
        """Use the vault of that name, or create it if there is none."""
        name = user_input[CONF_VAULT_NAME].strip()
        language = self.hass.config.language
        texts = texts_for(language)
        vaults = await client.async_get_vaults()
        vault = next((v for v in vaults if v["name"].casefold() == name.casefold()), None)
        created = vault is None
        if vault is None:
            vault = await client.async_create_vault(name, "de" if language.startswith("de") else "en")

        await self.async_set_unique_id(vault["id"])
        self._abort_if_unique_id_configured()

        data = {
            CONF_URL: user_input[CONF_URL],
            CONF_TOKEN: user_input[CONF_TOKEN],
            CONF_VAULT_ID: vault["id"],
            CONF_VAULT_NAME: vault["name"],
            CONF_INSTRUCTIONS_FOLDER: texts["instructions_folder"],
            CONF_LEARNED_FOLDER: texts["learned_folder"],
            CONF_MEMORY_FOLDER: texts["memory_folder"],
        }
        if created:
            helper = AssistVault(
                self.hass,
                client,
                "setup",
                vault_id=vault["id"],
                instructions_folder=data[CONF_INSTRUCTIONS_FOLDER],
                learned_folder=data[CONF_LEARNED_FOLDER],
                memory_folder=data[CONF_MEMORY_FOLDER],
                memory_budget=DEFAULT_MEMORY_BUDGET,
                language=language,
            )
            await helper.async_seed()
        return self.async_create_entry(title=vault["name"], data=data)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Ask for a new token after the old one stopped working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Check the new token against the vault."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            client = BasaltClient(
                async_get_clientsession(self.hass), entry.data[CONF_URL], user_input[CONF_TOKEN]
            )
            try:
                vaults = await client.async_get_vaults()
            except BasaltConnectionError:
                errors["base"] = "cannot_connect"
            except BasaltAuthError:
                errors["base"] = "invalid_auth"
            except BasaltError:
                _LOGGER.exception("Unexpected answer from BasaltNotes")
                errors["base"] = "unknown"
            else:
                if any(v["id"] == entry.data[CONF_VAULT_ID] for v in vaults):
                    return self.async_update_reload_and_abort(
                        entry, data_updates={CONF_TOKEN: user_input[CONF_TOKEN]}
                    )
                errors["base"] = "invalid_auth"
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=probatio.Schema({probatio.Required(CONF_TOKEN): _TOKEN_SELECTOR}),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> BasaltOptionsFlow:
        """Return the options flow."""
        return BasaltOptionsFlow()


class BasaltOptionsFlow(OptionsFlow):
    """Change how notes are chosen for the prompt."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the budget and the optional embedding server."""
        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_MEMORY_BUDGET: int(user_input[CONF_MEMORY_BUDGET]),
                    CONF_EMBEDDING_URL: (user_input.get(CONF_EMBEDDING_URL) or "").strip(),
                    CONF_EMBEDDING_MODEL: (
                        user_input.get(CONF_EMBEDDING_MODEL) or DEFAULT_EMBEDDING_MODEL
                    ).strip(),
                    CONF_EMBEDDING_KEY: user_input.get(CONF_EMBEDDING_KEY) or "",
                }
            )
        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                probatio.Schema(
                    {
                        probatio.Required(CONF_MEMORY_BUDGET): NumberSelector(
                            NumberSelectorConfig(min=0, max=20000, step=100, mode=NumberSelectorMode.BOX)
                        ),
                        probatio.Optional(CONF_EMBEDDING_URL): TextSelector(
                            TextSelectorConfig(type=TextSelectorType.URL)
                        ),
                        probatio.Optional(CONF_EMBEDDING_MODEL): TextSelector(),
                        probatio.Optional(CONF_EMBEDDING_KEY): _TOKEN_SELECTOR,
                    }
                ),
                {
                    CONF_MEMORY_BUDGET: options.get(CONF_MEMORY_BUDGET, DEFAULT_MEMORY_BUDGET),
                    CONF_EMBEDDING_URL: options.get(CONF_EMBEDDING_URL, ""),
                    CONF_EMBEDDING_MODEL: options.get(CONF_EMBEDDING_MODEL, DEFAULT_EMBEDDING_MODEL),
                    CONF_EMBEDDING_KEY: options.get(CONF_EMBEDDING_KEY, ""),
                },
            ),
        )
