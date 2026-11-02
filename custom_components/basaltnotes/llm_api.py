"""LLM APIs: bring the vault into the prompt and give the assistant its memory tools."""

from __future__ import annotations

from typing import Any

import probatio

from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm

from .api import BasaltError
from .const import DOMAIN, LLM_API_ASSIST_ID, LLM_API_ID
from .vault import AssistVault


class _VaultTool(llm.Tool):
    """A tool that works on the vault."""

    integration = DOMAIN

    def __init__(self, vault: AssistVault) -> None:
        """Initialize the tool."""
        self.vault = vault

    async def async_call(
        self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext
    ) -> llm.ToolResult | dict[str, Any]:
        """Run the tool; a server problem is reported to the model, so it can tell the user."""
        try:
            return await self._async_run(tool_input.tool_args)
        except BasaltError as err:
            return llm.ToolResult(data={"ok": False, "error": str(err)}, error=True)

    async def _async_run(self, args: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class RememberTool(_VaultTool):
    """Store a fact."""

    name = "remember"
    annotations = llm.ToolAnnotations(destructive=False, idempotent=True)

    def __init__(self, vault: AssistVault) -> None:
        """Initialize the tool."""
        super().__init__(vault)
        self.description = vault.texts["remember"]
        self.parameters = probatio.Schema(
            {probatio.Required("text", description=vault.texts["remember_text"]): str}
        )

    async def _async_run(self, args: dict[str, Any]) -> dict[str, Any]:
        await self.vault.async_remember(args["text"])
        return {"ok": True}


class RecallTool(_VaultTool):
    """Search the facts."""

    name = "recall"
    annotations = llm.ToolAnnotations(read_only=True, destructive=False, idempotent=True)

    def __init__(self, vault: AssistVault) -> None:
        """Initialize the tool."""
        super().__init__(vault)
        self.description = vault.texts["recall"]
        self.parameters = probatio.Schema(
            {probatio.Optional("query", description=vault.texts["recall_query"]): str}
        )

    async def _async_run(self, args: dict[str, Any]) -> dict[str, Any]:
        facts, total = await self.vault.async_recall(args.get("query"))
        return {"facts": facts, "total": total}


class ForgetTool(_VaultTool):
    """Delete a fact."""

    name = "forget"

    def __init__(self, vault: AssistVault) -> None:
        """Initialize the tool."""
        super().__init__(vault)
        self.description = vault.texts["forget"]
        self.parameters = probatio.Schema(
            {probatio.Required("text", description=vault.texts["forget_text"]): str}
        )

    async def _async_run(self, args: dict[str, Any]) -> dict[str, Any]:
        deleted, facts = await self.vault.async_forget(args["text"])
        return {"ok": deleted, "deleted" if deleted else "candidates": facts}


class LearnInstructionTool(_VaultTool):
    """Store a correction."""

    name = "learn_instruction"
    annotations = llm.ToolAnnotations(idempotent=True)

    def __init__(self, vault: AssistVault) -> None:
        """Initialize the tool."""
        super().__init__(vault)
        self.description = vault.texts["learn"]
        self.parameters = probatio.Schema(
            {
                probatio.Required("when", description=vault.texts["learn_when"]): str,
                probatio.Required("then", description=vault.texts["learn_then"]): str,
            }
        )

    async def _async_run(self, args: dict[str, Any]) -> dict[str, Any]:
        await self.vault.async_learn(args["when"], args["then"])
        return {"ok": True}


class ForgetInstructionTool(_VaultTool):
    """Delete a correction."""

    name = "forget_instruction"

    def __init__(self, vault: AssistVault) -> None:
        """Initialize the tool."""
        super().__init__(vault)
        self.description = vault.texts["forget_learned"]
        self.parameters = probatio.Schema(
            {probatio.Required("when", description=vault.texts["forget_learned_when"]): str}
        )

    async def _async_run(self, args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": await self.vault.async_forget_learned(args["when"])}


class BasaltLLMAPI(llm.API):
    """The vault as an LLM API, optionally together with the Assist tools."""

    def __init__(
        self, hass: HomeAssistant, vault: AssistVault, *, api_id: str, name: str, with_assist: bool
    ) -> None:
        """Initialize the API."""
        super().__init__(hass=hass, id=api_id, name=name)
        self.vault = vault
        self.with_assist = with_assist

    async def async_get_api_instance(self, llm_context: llm.LLMContext) -> llm.APIInstance:
        """Return the prompt and the tools for one conversation."""
        prompt = await self.vault.async_get_prompt()
        tools: list[llm.Tool] = [
            tool(self.vault)
            for tool in (
                RememberTool,
                RecallTool,
                ForgetTool,
                LearnInstructionTool,
                ForgetInstructionTool,
            )
        ]
        serializer = None
        if self.with_assist:
            assist = await llm.async_get_api(self.hass, llm.LLM_API_ASSIST, llm_context)
            prompt = f"{assist.api_prompt}\n\n{prompt}"
            tools = [*assist.tools, *tools]
            serializer = assist.custom_serializer
        return llm.APIInstance(
            api=self,
            api_prompt=prompt,
            llm_context=llm_context,
            tools=tools,
            custom_serializer=serializer,
        )


def async_register_apis(hass: HomeAssistant, vault: AssistVault) -> list:
    """Register both APIs and return the functions that remove them again."""
    return [
        llm.async_register_api(
            hass,
            BasaltLLMAPI(hass, vault, api_id=LLM_API_ID, name="BasaltNotes", with_assist=False),
        ),
        llm.async_register_api(
            hass,
            BasaltLLMAPI(
                hass, vault, api_id=LLM_API_ASSIST_ID, name="Assist + BasaltNotes", with_assist=True
            ),
        ),
    ]
