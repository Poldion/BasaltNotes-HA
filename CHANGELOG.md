# Changelog

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
