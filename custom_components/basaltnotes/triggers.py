"""Find out whether a sentence trigger of an automation answers a wording before the assistant hears it."""

from __future__ import annotations

import logging
import re

from homeassistant.core import Context, HomeAssistant

_LOGGER = logging.getLogger(__name__)

_QUOTED = re.compile(r"[„“\"'«»‚‘]([^„“\"'«»‚‘”’]{2,})[“”\"'«»‘’]")
# "Wenn ich gute Nacht sage" -> "gute Nacht"
_FRAME = re.compile(
    r"^(?:wenn|falls|when|if)\s+(?:ich|jemand|man|du|i|someone|you)\s+"
    r"(?:(?:sage|sagt|frage|fragt|say|says|ask|asks)\b\s*,?\s*(?:dass\s+|that\s+)?)?(.*?)"
    r"(?:\s+(?:sage|sagt|frage|fragt|say|says|ask|asks))?$",
    re.IGNORECASE,
)


def wordings(when: str) -> list[str]:
    """Return the wordings a situation describes: quoted parts, otherwise the core of "Wenn ich … sage"."""
    if quoted := [part.strip() for part in _QUOTED.findall(when)]:
        return quoted
    if (match := _FRAME.match(when.strip(" ."))) and match.group(1).strip():
        return [match.group(1).strip()]
    return [when]


async def async_find_trigger(hass: HomeAssistant, when: str, language: str) -> str | None:
    """Return the wording that a sentence trigger answers, or None.

    Uses Home Assistant's recognition only, so no automation runs. It is not a public interface; if it changes,
    the check quietly finds nothing.
    """
    try:
        from homeassistant.components.conversation import (
            ConversationInput,
        )
        from homeassistant.components.conversation.const import (
            DATA_COMPONENT,
            HOME_ASSISTANT_AGENT,
        )

        agent = hass.data[DATA_COMPONENT].get_entity(HOME_ASSISTANT_AGENT)
        for wording in wordings(when):
            result = await agent.async_recognize_sentence_trigger(
                ConversationInput(
                    text=wording,
                    context=Context(),
                    conversation_id=None,
                    device_id=None,
                    satellite_id=None,
                    language=language,
                    agent_id=HOME_ASSISTANT_AGENT,
                )
            )
            if result is not None:
                return wording
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Could not check sentence triggers: %s", err)
    return None
