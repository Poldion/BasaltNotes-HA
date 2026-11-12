"""Constants of the BasaltNotes integration."""

from typing import Final

DOMAIN: Final = "basaltnotes"

CONF_VAULT_ID: Final = "vault_id"
CONF_VAULT_NAME: Final = "vault_name"
CONF_INSTRUCTIONS_FOLDER: Final = "instructions_folder"
CONF_LEARNED_FOLDER: Final = "learned_folder"
CONF_MEMORY_FOLDER: Final = "memory_folder"
CONF_MEMORY_BUDGET: Final = "memory_budget"
CONF_EMBEDDING_URL: Final = "embedding_url"
CONF_EMBEDDING_MODEL: Final = "embedding_model"
CONF_EMBEDDING_KEY: Final = "embedding_api_key"

DEFAULT_VAULT_NAME: Final = "Home Assistant Assist"
DEFAULT_MEMORY_BUDGET: Final = 600
DEFAULT_EMBEDDING_MODEL: Final = "embeddinggemma"

# The two LLM APIs. "basaltnotes" can be combined with others in the agent settings, but Home Assistant
# then prefixes every tool name. "basaltnotes_assist" contains the Assist tools under their usual names,
# which small local models cope with better.
LLM_API_ID: Final = "basaltnotes"
LLM_API_ASSIST_ID: Final = "basaltnotes_assist"
