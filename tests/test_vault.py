"""Tests for reading and changing the vault."""

import pytest

from custom_components.basaltnotes.api import BasaltConnectionError


async def test_prompt_has_fixed_instructions_and_only_matching_notes(vault, client):
    client.add("Anweisungen", "2 Regeln", "Antworte knapp.")
    client.add("Anweisungen", "1 Persona", "Du bist GLaDOS.")
    client.add("Anweisungen", "Aus", "Nicht verwenden.", enabled=False)
    client.add("Anweisungen/Gelernt", "Wenn ich gute Nacht sage", "Bett-Schaltung an")
    client.add("Anweisungen/Gelernt", "Stopp den Timer", "Timer abbrechen")
    client.add("Gedächtnis", "Auto", "Das Auto steht in Reihe 3.")
    await vault.async_refresh()

    prompt = vault.build_prompt("Gute Nacht!")

    assert prompt.index("Du bist GLaDOS.") < prompt.index("Antworte knapp.")
    assert "Nicht verwenden." not in prompt
    assert "- Wenn ich gute Nacht sage: Bett-Schaltung an" in prompt
    assert "Timer abbrechen" not in prompt
    assert "Reihe 3" not in prompt


async def test_prompt_does_not_grow_with_unrelated_notes(vault, client):
    client.add("Anweisungen", "Persona", "Du bist GLaDOS.")
    await vault.async_refresh()
    before = vault.build_prompt("Wie warm ist es im Bad?")

    for number in range(200):
        client.add("Gedächtnis", f"Fakt {number}", f"Der Schrank {number} enthält Werkzeug.")
    await vault.async_refresh()

    assert vault.build_prompt("Wie warm ist es im Bad?") == before


async def test_filler_words_alone_select_nothing(vault, client):
    client.add("Anweisungen/Gelernt", "Wenn ich sage, dass es kalt ist", "Heizung an")
    await vault.async_refresh()

    assert vault.select_for("Wenn ich das sage, was ist dann?") == []


async def test_rare_word_decides(vault, client):
    client.add("Anweisungen/Gelernt", "Licht im Bad", "Spiegelleuchte an")
    client.add("Anweisungen/Gelernt", "Licht im Flur", "Decke an")
    client.add("Anweisungen/Gelernt", "Licht im Labor", "Regal an")
    await vault.async_refresh()

    assert [n.title for n in vault.select_for("Mach das Licht im Bad an")] == ["Licht im Bad"]


async def test_selection_respects_the_budget(vault, client):
    client.add("Gedächtnis", "Auto 1", "Auto " + "x" * 30)
    client.add("Gedächtnis", "Auto 2", "Auto " + "y" * 30)
    await vault.async_refresh()

    assert len(vault.select_for("Auto")) == 1


async def test_only_changed_notes_are_fetched_again(vault, client):
    note_id = client.add("Gedächtnis", "Auto", "Reihe 3")
    client.add("Gedächtnis", "Rad", "Keller")
    await vault.async_refresh()
    assert client.text_requests == 2

    await vault.async_refresh()
    assert client.text_requests == 2

    await client.async_update_note("assist", note_id, "Auto", "Reihe 4")
    await vault.async_refresh()
    assert client.text_requests == 3
    assert vault.notes[note_id].text == "Reihe 4"


async def test_prompt_survives_an_offline_server(vault, client):
    client.add("Anweisungen", "Persona", "Du bist GLaDOS.")
    await vault.async_refresh()
    vault._fetched_at = 0.0
    client.offline = True

    assert "Du bist GLaDOS." in await vault.async_get_prompt(None)


async def test_copy_survives_a_restart(hass, vault, client):
    client.add("Anweisungen", "Persona", "Du bist GLaDOS.")
    await vault.async_refresh()
    await vault._store.async_save(vault._as_stored())
    vault.notes = {}

    await vault.async_load()

    assert "Du bist GLaDOS." in vault.build_prompt(None)


async def test_remember_ignores_duplicates(vault, client):
    await vault.async_remember("Das Auto steht in Reihe 3.")
    await vault.async_remember("das auto  steht in reihe 3.")

    assert [n.text for n in vault.memories] == ["Das Auto steht in Reihe 3."]


async def test_remember_reports_an_offline_server(vault, client):
    client.offline = True
    with pytest.raises(BasaltConnectionError):
        await vault.async_remember("Das Auto steht in Reihe 3.")


async def test_recall_ranks_by_words(vault, client):
    client.add("Gedächtnis", "Rad", "Das Fahrrad steht im Keller.")
    client.add("Gedächtnis", "Auto", "Das Auto steht in Reihe 3.")

    facts, total = await vault.async_recall("Wo steht mein Auto?")

    assert facts[0] == "Das Auto steht in Reihe 3."
    assert total == 2


async def test_recall_without_a_match_returns_the_newest(vault, client):
    client.add("Gedächtnis", "Auto", "Das Auto steht in Reihe 3.")

    facts, _ = await vault.async_recall("Schwiegermutter")

    assert facts == ["Das Auto steht in Reihe 3."]


async def test_forget_deletes_a_clear_match(vault, client):
    client.add("Gedächtnis", "Auto", "Das Auto steht in Reihe 3.")
    client.add("Gedächtnis", "Rad", "Das Fahrrad steht im Keller.")

    deleted, facts = await vault.async_forget("Auto Reihe")

    assert deleted
    assert facts == ["Das Auto steht in Reihe 3."]
    assert [n.text for n in vault.memories] == ["Das Fahrrad steht im Keller."]


async def test_forget_keeps_everything_if_ambiguous(vault, client):
    client.add("Gedächtnis", "Rad 1", "Das rote Fahrrad steht im Keller.")
    client.add("Gedächtnis", "Rad 2", "Das blaue Fahrrad steht im Hof.")

    deleted, facts = await vault.async_forget("Fahrrad")

    assert not deleted
    assert len(facts) == 2
    assert len(vault.memories) == 2


async def test_forget_keeps_everything_if_unrelated(vault, client):
    client.add("Gedächtnis", "Auto", "Das Auto steht in Reihe 3.")

    deleted, _ = await vault.async_forget("Schwiegermutter Geburtstag")

    assert not deleted
    assert len(vault.memories) == 1


async def test_learn_replaces_the_same_wording(vault, client):
    await vault.async_learn("Gute Nacht", "Licht aus")
    await vault.async_learn("gute  nacht", "Bett-Schaltung an")

    assert [(n.title, n.text) for n in vault.learned] == [("Gute Nacht", "Bett-Schaltung an.")]


async def test_tools_cannot_delete_handwritten_instructions(vault, client):
    client.add("Anweisungen", "Persona", "Du bist GLaDOS.")

    assert not await vault.async_forget_learned("Persona")
    assert [n.title for n in vault.instructions] == ["Persona"]


async def test_forget_learned(vault, client):
    await vault.async_learn("Gute Nacht", "Licht aus")

    assert await vault.async_forget_learned("gute nacht")
    assert vault.learned == []


async def test_learn_tidies_what_the_model_wrote(vault, client):
    await vault.async_learn("  wenn ich „Gute Nacht“ sage. ", "schalte die Bettbeleuchtung aus")

    assert [(n.title, n.text) for n in vault.learned] == [
        ("Wenn ich „Gute Nacht“ sage", "Schalte die Bettbeleuchtung aus.")
    ]


async def test_learn_removes_quotes_around_everything(vault, client):
    await vault.async_learn("'jemand fragt nach Kuchen'", "Sag, dass der Kuchen eine Lüge ist!")

    assert [(n.title, n.text) for n in vault.learned] == [
        ("Wenn jemand fragt nach Kuchen", "Sag, dass der Kuchen eine Lüge ist!")
    ]


async def test_learn_adds_the_missing_when(vault, client):
    await vault.async_learn("Ich sage „Zitronenkuchen“", "Nenne die Uhrzeit")
    await vault.async_learn("Gute Nacht", "Licht aus")

    assert sorted(n.title for n in vault.learned) == ["Gute Nacht", "Wenn ich sage „Zitronenkuchen“"]


ROOMS = {"labor": {"labor", "hobbyraum"}, "kueche": {"küche"}, "bad": {"bad", "badezimmer"}}


async def test_meaning_finds_what_words_miss(smart_vault, client):
    client.add("Anweisungen/Gelernt", "Wenn ich nach der Uhrzeit frage", "Rufe GetDateTime auf.")
    client.add("Anweisungen/Gelernt", "Schalte alle Lichter aus", "Jedes Licht ausschalten.")
    await smart_vault.async_refresh()
    question = "Wie spät ist es?"

    assert smart_vault.select_for(question) == []
    vector = await smart_vault._async_question_vector(question)
    assert [n.title for n in smart_vault.select_for(question, question_vector=vector)] == [
        "Wenn ich nach der Uhrzeit frage"
    ]


async def test_words_decide_when_the_embedder_is_down(smart_vault, client, embedder):
    client.add("Anweisungen/Gelernt", "Stopp den Timer", "Timer abbrechen.")
    await smart_vault.async_refresh()
    embedder.offline = True

    prompt = await smart_vault.async_get_prompt("Stopp den Timer")

    assert "Timer abbrechen." in prompt


async def test_vectors_are_kept_until_a_note_changes(smart_vault, client, embedder):
    note_id = client.add("Gedächtnis", "Auto", "Das Auto steht in Reihe 3.")
    await smart_vault.async_refresh()
    await smart_vault.async_refresh()
    assert embedder.calls == 1

    await client.async_update_note("assist", note_id, "Auto", "Das Auto steht in Reihe 4.")
    await smart_vault.async_refresh()
    assert embedder.calls == 2


async def test_recall_by_meaning(smart_vault, client):
    client.add("Gedächtnis", "Auto", "Das Auto steht in Reihe 3.")
    client.add("Gedächtnis", "Lisa", "Lisa mag keinen Koriander.")

    facts, total = await smart_vault.async_recall("Wo habe ich geparkt?")

    assert facts == ["Das Auto steht in Reihe 3."]
    assert total == 2


async def test_notes_about_another_room_stay_out(vault, client):
    client.add("Anweisungen/Gelernt", "Licht im Labor", "Laborlicht an, Druckerlicht aus.")
    client.add("Anweisungen/Gelernt", "Licht in der Küche", "Nur die Deckenlampe.")
    await vault.async_refresh()
    vault.memory_budget = 600

    in_kitchen = vault.select_for("Mach das Licht an", here="kueche", rooms=ROOMS)
    asked_for_lab = vault.select_for("Mach das Licht im Hobbyraum an", here="kueche", rooms=ROOMS)
    no_room_known = vault.select_for("Mach das Licht an", rooms=ROOMS)

    assert [n.title for n in in_kitchen] == ["Licht in der Küche"]
    assert [n.title for n in asked_for_lab] == ["Licht im Labor"]
    assert len(no_room_known) == 2


async def test_room_names_in_compounds(vault, client):
    client.add("Anweisungen/Gelernt", "Laborlicht", "Nur das Regal.")
    await vault.async_refresh()

    assert vault.select_for("Mach das Licht an", here="kueche", rooms=ROOMS) == []


async def test_same_situation_in_other_words_replaces(vault, client):
    await vault.async_learn("Wenn ich gute Nacht sage", "Licht aus")
    replaced = await vault.async_learn("ich sage gute Nacht", "Bett-Schaltung an und Licht aus")

    assert replaced == "Wenn ich gute Nacht sage"
    assert [(n.title, n.text) for n in vault.learned] == [
        ("Wenn ich sage gute Nacht", "Bett-Schaltung an und Licht aus.")
    ]


async def test_different_situations_stay_apart(vault, client):
    await vault.async_learn("Licht im Bad", "Spiegelleuchte an")
    replaced = await vault.async_learn("Licht im Flur", "Decke an")

    assert replaced is None
    assert len(vault.learned) == 2
