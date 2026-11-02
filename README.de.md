# BasaltNotes für Home Assistant

🇬🇧 [English](README.md) · 🇩🇪 Deutsch

> Anweisungen und Gedächtnis deines Home-Assistant-Sprachassistenten als einfache Markdown-Notizen in
> [BasaltNotes](https://github.com/Poldion/BasaltNotes).

**Lizenz:** MIT · **Sprache:** Python · **Installation:** HACS (benutzerdefiniertes Repository) · **Voraussetzung:** Home
Assistant 2026.10, BasaltNotes 0.24 · **Teil von:** [Poldion Self-Hosted](https://github.com/Poldion/BasaltNotes/blob/main/README.de.md)

## Überblick

Die Integration legt bei der Einrichtung einen eigenen Vault an und verbindet ihn mit jedem Assist-Agenten, der ein
Sprachmodell nutzt (Ollama, OpenAI, Google …). Alles, was dem Assistenten gesagt wurde oder was er gelernt hat, ist eine
Notiz, die du in BasaltNotes oder Obsidian lesen und ändern kannst, mit Git-Verlauf und Papierkorb.

## Funktionen

| Bereich | Was es tut |
|---|---|
| **Eigener Vault** | Wird bei der Einrichtung automatisch angelegt; ein vorhandener Vault gleichen Namens wird unverändert genutzt |
| **Anweisungen** | Notizen direkt in `Anweisungen/` stehen immer im Systemprompt, sortiert nach Pfad, halte sie also kurz. `enabled: false` in den Eigenschaften schaltet eine Notiz ab |
| **Korrekturen** | „Das war falsch, ich meinte …“ wird als Notiz in `Anweisungen/Gelernt/` gespeichert: Titel = Wenn, Text = Dann |
| **Kleine Prompts** | Korrekturen und Fakten werden zu jeder Frage durchsucht. Nur die besten Treffer kommen in den Prompt, er wächst also nicht mit der Zahl der Notizen |
| **Gedächtnis** | Fakten sind Notizen in `Gedächtnis/`. Der Assistent bekommt die passenden mit der Frage und kann sie auch per Werkzeug suchen |
| **Werkzeuge** | `remember`, `recall`, `forget`, `learn_instruction`, `forget_instruction` |
| **Geschützte Regeln** | Die Werkzeuge ändern nur `Gedächtnis/` und `Anweisungen/Gelernt/`. Deine eigenen Anweisungen lassen sich nicht per Sprache ändern |
| **Offline** | Home Assistant behält eine Kopie. Antwortet der Server nicht innerhalb von 2 Sekunden, arbeitet der Assistent mit dieser Kopie |
| **Sensoren** | Anzahl der Anweisungen und gemerkten Fakten |

Die Ordner heißen so wie die Sprache deines Home Assistant beim Verbinden (Englisch: `Instructions/`,
`Instructions/Learned/`, `Memory/`).

## Schnellstart

1. In BasaltNotes: *Einstellungen → API-Tokens → neues Token* mit dem Recht, Vaults anzulegen (`create_vault`). Das Token
   sieht dann nur den Vault, den es selbst anlegt.
2. In HACS: *Benutzerdefinierte Repositories* → `https://github.com/Poldion/BasaltNotes-HA`, Kategorie *Integration*.
   Installieren und Home Assistant neu starten.
3. *Einstellungen → Geräte & Dienste → Integration hinzufügen → BasaltNotes*: Adresse (z. B. `http://nas.local:4400`),
   Token und Name des Vaults eintragen.
4. In den Einstellungen des Gesprächsagenten unter *Home Assistant steuern* **Assist + BasaltNotes** wählen.
5. Deine Anweisungen nach `Anweisungen/` verschieben und das Anweisungsfeld des Agenten auf eine Zeile kürzen, z. B.
   „Deine Anweisungen folgen weiter unten.“ Ist das Feld leer, nimmt Home Assistant seinen allgemeinen Standardprompt.

## Die zwei APIs

| API | Wofür |
|---|---|
| **Assist + BasaltNotes** | Der Agent soll Geräte steuern. Enthält die Assist-Werkzeuge unter ihren gewohnten Namen |
| **BasaltNotes** | Der Agent braucht nur Anweisungen und Gedächtnis, oder du kombinierst APIs selbst. Bei mehreren gewählten APIs setzt Home Assistant vor alle Werkzeugnamen einen Präfix, womit kleine lokale Modelle schlechter zurechtkommen |

## Konfiguration

*Konfigurieren* an der Integration:

| Option | Standard | Bedeutung |
|---|---|---|
| Zeichen passender Notizen je Frage | `600` | Obergrenze für Korrekturen und Fakten im Prompt, höchstens 5 Notizen. `0` = Fakten nur über das Suchwerkzeug |

Änderungen im Vault gelten ab dem nächsten Gespräch, spätestens nach 60 Sekunden.

## Sicherheit

Anweisungen sind Teil des Systemprompts: Wer im Vault schreiben darf, kann deinen Assistenten steuern. Beschränke das
Token auf diesen Vault. Gemerkte Fakten sind im Prompt als Daten gekennzeichnet, aber ein Sprachmodell hält sich nicht
zuverlässig daran; speichere keine Texte aus unsicheren Quellen als Fakten.

## Entwicklung

Voraussetzung: Python 3.14 unter Linux oder im Container (Home Assistant läuft nicht unter Windows).

```bash
pip install -r requirements_test.txt ruff
python scripts/install_ha_test_requirements.py
ruff check custom_components tests scripts
pytest -q
```

## Lizenz

Der Code steht unter der [MIT-Lizenz](LICENSE). „Obsidian“ ist eine Marke von Dynalist Inc.; dieses Projekt ist
unabhängig und nicht damit verbunden.

## Unterstützung

Rückmeldungen, Fehlerberichte und Pull Requests sind willkommen. Du kannst mir auch
[einen Kaffee spendieren](https://buymeacoffee.com/poldion).
