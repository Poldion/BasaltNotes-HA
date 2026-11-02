"""Fixtures: a small in-memory BasaltNotes server behind the client interface."""

from itertools import count
from typing import Any

import pytest

from custom_components.basaltnotes.api import BasaltConnectionError, BasaltNotFoundError
from custom_components.basaltnotes.vault import AssistVault
from homeassistant.setup import async_setup_component


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load the integration from custom_components."""


@pytest.fixture(autouse=True)
async def core_components(hass):
    """Set up what the conversation integration expects to exist."""
    assert await async_setup_component(hass, "homeassistant", {})


class FakeClient:
    """Behaves like BasaltClient, without a network."""

    def __init__(self) -> None:
        self.notes: dict[str, dict[str, Any]] = {}
        self.vaults: list[dict[str, Any]] = []
        self.offline = False
        self.text_requests = 0
        self._ids = count(1)

    def _check(self) -> None:
        if self.offline:
            raise BasaltConnectionError("offline")

    def add(self, folder: str, title: str, text: str, **frontmatter: Any) -> str:
        number = next(self._ids)
        note_id = f"note{number}"
        self.notes[note_id] = {
            "id": note_id,
            "title": title,
            "path": f"{folder}/{title.replace('/', ' ')}.md",
            "version": f"v{number}",
            "updated": f"2026-11-02T10:{number:02d}:00+01:00",
            "frontmatter": frontmatter,
            "text": text,
        }
        return note_id

    async def async_get_vaults(self):
        self._check()
        return self.vaults

    async def async_create_vault(self, name, lang):
        self._check()
        vault = {"id": name.lower().replace(" ", "-"), "name": name}
        self.vaults.append(vault)
        return vault

    async def async_list_notes(self, vault, folder):
        self._check()
        return [
            {k: v for k, v in note.items() if k != "text"}
            for note in self.notes.values()
            if f"{folder}/" in note["path"]
        ]

    async def async_get_note_text(self, vault, note_id):
        self._check()
        self.text_requests += 1
        return self.notes[note_id]["text"]

    async def async_create_note(self, vault, folder, title, body):
        self._check()
        return self.notes[self.add(folder, title, body)]

    async def async_update_note(self, vault, note_id, title, body):
        self._check()
        note = self.notes[note_id]
        note["text"] = body
        note["version"] += "x"
        return note

    async def async_delete_note(self, vault, note_id):
        self._check()
        if note_id not in self.notes:
            raise BasaltNotFoundError(note_id)
        del self.notes[note_id]


@pytest.fixture
def client() -> FakeClient:
    """Return the fake server."""
    return FakeClient()


@pytest.fixture
def vault(hass, client) -> AssistVault:
    """Return a vault on the fake server."""
    return AssistVault(
        hass,
        client,
        "test",
        vault_id="assist",
        instructions_folder="Anweisungen",
        learned_folder="Gelernt",
        memory_folder="Gedächtnis",
        memory_budget=60,
        language="de",
    )
