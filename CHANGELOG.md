# Changelog

## [0.2.3] – 2026-11-12

### Changed

- The installation guide covers the Marketplace that is built into Home Assistant since 2026.11 and replaces HACS.

## [0.2.2] – 2026-11-12

### Fixed

- A learned situation that starts with “ich”, “du”, “jemand” or “man” (“I”, “you” …) gets the missing “Wenn”/“When” in front.

## [0.2.1] – 2026-11-12

### Fixed

- Learned corrections are written as complete sentences: the tool now describes both fields with examples, and the text is tidied before it is stored (capital first letter, full stop, no stray quotes).
- Corrections appear in the prompt as “situation: what to do” instead of repeating “When:” in front of a sentence that already starts with it.

## [0.2.0] – 2026-11-02

### Changed

- Corrections and facts are no longer all part of the prompt. They are searched for each question, and only the best matches are added, so the prompt no longer grows with the number of notes.
- The explanation of the tools in the prompt is shorter.
- The option for the prompt length now limits the matching notes per question; its default is 600 characters.

## [0.1.1] – 2026-11-02

### Fixed

- Translations no longer contain a URL, which Home Assistant's validation does not allow.
- The manifest now names its integration category.

## [0.1.0] – 2026-11-02

### Added

- Config flow that creates its own vault in BasaltNotes or uses an existing one of the same name.
- Two LLM APIs, “BasaltNotes” and “Assist + BasaltNotes”, that bring instructions, corrections and memory into the prompt.
- Tools `remember`, `recall`, `forget`, `learn_instruction` and `forget_instruction`.
- Local copy of the notes, used when the server does not answer in time.
- Sensors for the number of instructions and remembered facts.
- German and English texts.
