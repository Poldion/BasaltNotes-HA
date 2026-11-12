"""Tests for the check against sentence triggers."""

from custom_components.basaltnotes.const import LLM_API_ID
from custom_components.basaltnotes.triggers import async_find_trigger, wordings
from homeassistant.helpers import llm
from homeassistant.setup import async_setup_component

from .test_setup import _context, _setup


def test_wordings_of_a_situation():
    assert wordings("Wenn ich „Gute Nacht“ sage") == ["Gute Nacht"]
    assert wordings("Wenn ich gute Nacht sage") == ["gute Nacht"]
    assert wordings("Wenn ich sage, dass ich den Müll rausgebracht habe") == [
        "ich den Müll rausgebracht habe"
    ]
    assert wordings("Schalte alle Lichter aus") == ["Schalte alle Lichter aus"]


async def _automation(hass):
    assert await async_setup_component(hass, "conversation", {})
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "triggers": {"trigger": "conversation", "command": ["Gute Nacht", "[Ich] geh[e] schlafen"]},
                "actions": {"action": "test.nothing"},
            }
        },
    )
    await hass.async_block_till_done()


async def test_trigger_found_without_running_it(hass):
    hass.config.language = "de"
    await _automation(hass)
    calls = []
    hass.services.async_register("test", "nothing", lambda call: calls.append(call))

    assert await async_find_trigger(hass, "Wenn ich „Gute Nacht“ sage", "de") == "Gute Nacht"
    assert await async_find_trigger(hass, "Wenn ich gute Nacht sage", "de") == "gute Nacht"
    assert await async_find_trigger(hass, "Wenn ich nach dem Wetter frage", "de") is None
    await hass.async_block_till_done()
    assert calls == []


async def test_learn_tool_warns(hass, client):
    await _automation(hass)
    await _setup(hass, client)
    instance = await llm.async_get_api(hass, LLM_API_ID, _context())

    result = await instance.async_call_tool(
        llm.ToolInput(
            tool_name="learn_instruction",
            tool_args={"when": "Wenn ich „Gute Nacht“ sage", "then": "Licht aus"},
        )
    )

    assert result.data["ok"] is True
    assert "Satz-Automation" in result.data["warning"]
    assert [n["title"] for n in client.notes.values()] == ["Wenn ich „Gute Nacht“ sage"]
