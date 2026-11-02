"""Tests for the config flow, the setup and the LLM APIs."""

from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.basaltnotes.api import BasaltAuthError
from custom_components.basaltnotes.const import (
    CONF_INSTRUCTIONS_FOLDER,
    CONF_LEARNED_FOLDER,
    CONF_MEMORY_FOLDER,
    CONF_VAULT_ID,
    CONF_VAULT_NAME,
    DOMAIN,
    LLM_API_ASSIST_ID,
    LLM_API_ID,
)
from homeassistant.components.conversation.chat_log import UserContent, async_get_chat_log
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.const import CONF_TOKEN, CONF_URL
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import chat_session, llm
from homeassistant.setup import async_setup_component

INPUT = {CONF_URL: "http://nas.local:4400", CONF_TOKEN: "bn_test", CONF_VAULT_NAME: "Assist"}


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="assist",
        title="Assist",
        data={
            CONF_URL: "http://nas.local:4400",
            CONF_TOKEN: "bn_test",
            CONF_VAULT_ID: "assist",
            CONF_VAULT_NAME: "Assist",
            CONF_INSTRUCTIONS_FOLDER: "Anweisungen",
            CONF_LEARNED_FOLDER: "Gelernt",
            CONF_MEMORY_FOLDER: "Gedächtnis",
        },
    )


async def _setup(hass, client) -> MockConfigEntry:
    hass.config.language = "de"
    entry = _entry()
    entry.add_to_hass(hass)
    with patch("custom_components.basaltnotes.BasaltClient", return_value=client):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def _context() -> llm.LLMContext:
    return llm.LLMContext(
        platform="test", context=None, language="de", assistant="conversation", device_id=None
    )


async def test_flow_creates_vault_and_first_instruction(hass, client):
    hass.config.language = "de"
    with (
        patch("custom_components.basaltnotes.config_flow.BasaltClient", return_value=client),
        patch("custom_components.basaltnotes.BasaltClient", return_value=client),
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], INPUT)
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_VAULT_ID] == "assist"
    assert result["data"][CONF_MEMORY_FOLDER] == "Gedächtnis"
    assert [v["name"] for v in client.vaults] == ["Assist"]
    assert [n["title"] for n in client.notes.values()] == ["Grundregeln"]


async def test_flow_uses_an_existing_vault_as_it_is(hass, client):
    client.vaults.append({"id": "assist", "name": "assist"})
    with (
        patch("custom_components.basaltnotes.config_flow.BasaltClient", return_value=client),
        patch("custom_components.basaltnotes.BasaltClient", return_value=client),
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], INPUT)
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert len(client.vaults) == 1
    assert client.notes == {}


async def test_flow_reports_a_bad_token(hass, client):
    async def denied():
        raise BasaltAuthError("no")

    client.async_get_vaults = denied
    with patch("custom_components.basaltnotes.config_flow.BasaltClient", return_value=client):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_setup_offers_apis_and_sensors(hass, client):
    client.add("Anweisungen", "Persona", "Du bist GLaDOS.")
    client.add("Gedächtnis", "Auto", "Das Auto steht in Reihe 3.")
    entry = await _setup(hass, client)

    assert entry.state is ConfigEntryState.LOADED
    assert {LLM_API_ID, LLM_API_ASSIST_ID} <= {api.id for api in llm.async_get_apis(hass)}
    states = {s.name: s.state for s in hass.states.async_all("sensor")}
    assert "1" in states.values()

    await hass.config_entries.async_unload(entry.entry_id)
    assert not {LLM_API_ID, LLM_API_ASSIST_ID} & {api.id for api in llm.async_get_apis(hass)}


async def test_setup_waits_without_server_and_without_copy(hass, client):
    client.offline = True
    entry = await _setup(hass, client)

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_api_brings_prompt_and_tools(hass, client):
    client.add("Anweisungen", "Persona", "Du bist GLaDOS.")
    await _setup(hass, client)

    instance = await llm.async_get_api(hass, LLM_API_ID, _context())

    assert "Du bist GLaDOS." in instance.api_prompt
    assert {t.name for t in instance.tools} == {
        "remember",
        "recall",
        "forget",
        "learn_instruction",
        "forget_instruction",
    }


async def test_combined_api_keeps_the_assist_tool_names(hass, client):
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, "intent", {})
    client.add("Anweisungen", "Persona", "Du bist GLaDOS.")
    await _setup(hass, client)

    instance = await llm.async_get_api(hass, LLM_API_ASSIST_ID, _context())
    assist = await llm.async_get_api(hass, llm.LLM_API_ASSIST, _context())
    names = {t.name for t in instance.tools}

    assert "remember" in names
    assert {t.name for t in assist.tools} <= names
    assert any(name.endswith("HassTurnOn") for name in names)
    assert "Du bist GLaDOS." in instance.api_prompt


async def test_tool_writes_to_the_vault_and_reports_offline(hass, client):
    await _setup(hass, client)
    instance = await llm.async_get_api(hass, LLM_API_ID, _context())

    result = await instance.async_call_tool(
        llm.ToolInput(tool_name="remember", tool_args={"text": "Das Auto steht in Reihe 3."})
    )
    assert result.data == {"ok": True}
    assert [n["text"] for n in client.notes.values()] == ["Das Auto steht in Reihe 3."]

    client.offline = True
    result = await instance.async_call_tool(
        llm.ToolInput(tool_name="remember", tool_args={"text": "Noch etwas."})
    )
    assert result.error
    assert result.data["ok"] is False


async def test_api_selects_by_the_current_question(hass, client):
    client.add("Gedächtnis", "Auto", "Das Auto steht in Reihe 3.")
    client.add("Gedächtnis", "Rad", "Das Fahrrad steht im Keller.")
    await _setup(hass, client)

    with chat_session.async_get_chat_session(hass) as session, async_get_chat_log(hass, session) as chat_log:
        chat_log.async_add_user_content(UserContent(content="Wo ist mein Auto?"))
        instance = await llm.async_get_api(hass, LLM_API_ID, _context())

    assert "Reihe 3" in instance.api_prompt
    assert "Keller" not in instance.api_prompt
