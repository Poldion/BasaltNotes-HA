# BasaltNotes for Home Assistant

🇬🇧 English · 🇩🇪 [Deutsch](README.de.md)

> Keep the instructions and the memory of your Home Assistant voice assistant as plain Markdown notes in
> [BasaltNotes](https://github.com/Poldion/BasaltNotes).

**License:** MIT · **Language:** Python · **Install:** Marketplace or HACS (custom repository) · **Requires:** Home Assistant 2026.10,
BasaltNotes 0.24 · **Part of:** [Poldion Self-Hosted](https://github.com/Poldion/BasaltNotes#the-poldion-family)

## Overview

The integration creates its own vault during setup and connects it to any Assist agent that uses a language model
(Ollama, OpenAI, Google …). Everything the assistant is told or has learned is a note you can read and edit in
BasaltNotes or Obsidian, with git history and a trash.

## Features

| Area | What it does |
|---|---|
| **Own vault** | Created automatically during setup; an existing vault of the same name is used as it is |
| **Instructions** | Notes directly in `Instructions/` are always part of the system prompt, sorted by path, so keep them short. `enabled: false` in the frontmatter switches a note off |
| **Corrections** | “That was wrong, I meant …” is stored as a note in `Instructions/Learned/`: title = when, text = then |
| **Small prompts** | Corrections and facts are searched for each question. Only the best matches go into the prompt, so it does not grow with the number of notes |
| **By meaning** | Optional: with an embedding model (e.g. EmbeddingGemma on Ollama) notes are chosen by meaning, so “What time is it?” finds a correction about “the clock”. Without the server the words decide |
| **Rooms** | A note that names a room only comes up in that room: asked there, or said to the satellite standing there |
| **No duplicates** | A correction for the same situation in other words replaces the old one instead of adding a second |
| **Sentence automations** | If an automation with a sentence trigger answers the wording before the assistant hears it, the assistant says so when learning the correction |
| **Memory** | Facts are notes in `Memory/`. The assistant gets the matching ones with the question and can also look them up with a tool |
| **Tools** | `remember`, `recall`, `forget`, `learn_instruction`, `forget_instruction` |
| **Protected rules** | The tools only touch `Memory/` and `Instructions/Learned/`. Your own instructions cannot be changed by voice |
| **Offline** | A copy is kept in Home Assistant. If the server does not answer within 2 seconds, the assistant works with that copy |
| **Sensors** | Number of instructions and remembered facts |

The folders are named in the language of your Home Assistant when the vault is connected (German: `Anweisungen/`,
`Anweisungen/Gelernt/`, `Gedächtnis/`).

## Quick start

1. In BasaltNotes: *Settings → API tokens → new token* with the permission to create vaults (`create_vault`). The token
   then only sees the vault it creates.
2. Add `https://github.com/Poldion/BasaltNotes-HA` as a custom repository, category *Integration*, install it and restart
   Home Assistant:
   - **Home Assistant 2026.11 and later:** in the built-in *Marketplace*, which replaces HACS. Custom repositories need a
     GitHub account connected to the Marketplace.
   - **Older versions:** in HACS under *Custom repositories*.
3. *Settings → Devices & services → Add integration → BasaltNotes*: enter the address (e.g. `http://nas.local:4400`), the
   token and the name of the vault.
4. In the settings of your conversation agent, under *Control Home Assistant*, select **Assist + BasaltNotes**.
5. Move your instructions into `Instructions/` and reduce the agent's own instructions field to one line, e.g. “Your
   instructions follow below.” Home Assistant uses its generic default prompt if the field is empty.

## The two APIs

| API | Use it when |
|---|---|
| **Assist + BasaltNotes** | The agent should control devices. Contains the Assist tools under their usual names |
| **BasaltNotes** | The agent only needs instructions and memory, or you combine APIs yourself. When several APIs are selected, Home Assistant prefixes all tool names, which small local models handle worse |

## Configuration

*Configure* on the integration:

| Option | Default | Meaning |
|---|---|---|
| Characters of matching notes per question | `600` | Upper limit for corrections and facts in the prompt, at most 5 notes. `0` = facts only through the search tool |
| Embedding server | – | OpenAI-compatible address ending in `/v1`, e.g. `http://nas.local:11434/v1` for Ollama. Empty = words only |
| Embedding model | `embeddinggemma` | Install it on Ollama with `ollama pull embeddinggemma` |
| API key of the embedding server | – | Only if the server needs one |

Changes in the vault apply to the next conversation, at most 60 seconds later.

## Security

Instructions are part of the system prompt, so anyone who can write in the vault can steer your assistant. Keep the token
limited to this vault. Remembered facts are marked as data in the prompt, but a language model does not reliably keep to
such marks; do not store text from untrusted sources as facts.

## Development

Requirements: Python 3.14 on Linux or in a container (Home Assistant does not run on Windows).

```bash
pip install -r requirements_test.txt ruff
python scripts/install_ha_test_requirements.py
ruff check custom_components tests scripts
pytest -q
```

## License

The code is licensed under the [MIT license](LICENSE). “Obsidian” is a trademark of Dynalist Inc.; this project is
independent and not affiliated with it.

## Support

Feedback, bug reports and pull requests are welcome. You can also [buy me a coffee](https://buymeacoffee.com/poldion).
