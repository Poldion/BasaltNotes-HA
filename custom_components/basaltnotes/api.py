"""Small client for the REST API of BasaltNotes."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import aiohttp

REQUEST_TIMEOUT = 10
PAGE_SIZE = 500


class BasaltError(Exception):
    """A request to BasaltNotes failed."""


class BasaltConnectionError(BasaltError):
    """BasaltNotes cannot be reached."""


class BasaltAuthError(BasaltError):
    """The token is invalid or lacks a permission."""


class BasaltNotFoundError(BasaltError):
    """The vault or note does not exist."""


class BasaltClient:
    """Access to one BasaltNotes server."""

    def __init__(self, session: aiohttp.ClientSession, url: str, token: str) -> None:
        """Initialize the client."""
        self._session = session
        self._base = f"{url.rstrip('/')}/api/v1"
        self._token = token

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Send a request and return the decoded answer."""
        all_headers = {
            "Authorization": f"Bearer {self._token}",
            "X-Basalt-Lang": "en",
            **(headers or {}),
        }
        try:
            async with self._session.request(
                method,
                f"{self._base}{path}",
                json=body,
                params=params,
                headers=all_headers,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as response:
                if response.status in (401, 403):
                    raise BasaltAuthError(await response.text())
                if response.status == 404:
                    raise BasaltNotFoundError(path)
                if response.status >= 400:
                    raise BasaltError(f"HTTP {response.status}: {await response.text()}")
                if response.status == 204:
                    return None
                return await response.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError) as err:
            raise BasaltConnectionError(str(err)) from err

    async def async_get_health(self) -> dict[str, Any]:
        """Return the server status; needs no sign-in."""
        return await self._request("GET", "/health")

    async def async_get_vaults(self) -> list[dict[str, Any]]:
        """Return the vaults this token can access."""
        return (await self._request("GET", "/vaults"))["items"]

    async def async_create_vault(self, name: str, lang: str) -> dict[str, Any]:
        """Create a free vault without a template."""
        return await self._request("POST", "/vaults", body={"name": name, "preset": "empty", "lang": lang})

    async def async_list_notes(self, vault: str, folder: str) -> list[dict[str, Any]]:
        """Return the summaries of all notes in a folder, subfolders included."""
        notes: list[dict[str, Any]] = []
        params: dict[str, Any] = {"folder": folder, "limit": PAGE_SIZE}
        while True:
            page = await self._request("GET", f"/vaults/{quote(vault)}/notes", params=params)
            notes.extend(page["items"])
            if not page.get("next_cursor"):
                return notes
            params["cursor"] = page["next_cursor"]

    async def async_get_note_text(self, vault: str, note_id: str) -> str:
        """Return a note's text without frontmatter, section markers and link brackets."""
        note = await self._request(
            "GET",
            f"/vaults/{quote(vault)}/notes/{quote(note_id)}",
            params={"clean": 1},
        )
        return note["body"]

    async def async_create_note(self, vault: str, folder: str, title: str, body: str) -> dict[str, Any]:
        """Create a note."""
        return await self._request(
            "POST",
            f"/vaults/{quote(vault)}/notes",
            body={"title": title, "body": body, "folder": folder},
        )

    async def async_update_note(self, vault: str, note_id: str, title: str, body: str) -> dict[str, Any]:
        """Replace a note's text."""
        return await self._request(
            "PUT",
            f"/vaults/{quote(vault)}/notes/{quote(note_id)}",
            body={"frontmatter": {"title": title, "type": "note"}, "body": body},
            headers={"If-Match": "*"},
        )

    async def async_delete_note(self, vault: str, note_id: str) -> None:
        """Move a note to the trash of the vault."""
        await self._request("DELETE", f"/vaults/{quote(vault)}/notes/{quote(note_id)}")
