from __future__ import annotations

import io

from app.core.db import SessionLocal
from app.db.models import PhonicsAttemptModel, PhonicsUnitModel
from app.services.shared.phonics_content import load_scope, load_sound_cards, load_units
from app.services.shared.phonics_progress import apply_attempt_to_progress, get_or_create_progress
from app.services.shared.phonics_scoring import decide_mastery, score_tap_items, score_word_match
from conftest import auth_headers
from scripts.seed_phonics import seed_sound_cards, seed_units

_CHILD_PAYLOAD = {
    "name": "小和",
    "age": 8,
    "level": "grade3",
    "learning_goal": "跟上三年级自然拼读",
    "preferred_review_duration_minutes": 10,
    "parent_notes": "二升三，学 PEP 三上",
}


# --------------------------- content + pure scoring --------------------------- #


def test_authored_content_loads_and_validates() -> None:
    scope = load_scope()
    assert scope.course.id == "course_pep_g3"
    cards = load_sound_cards()
    assert {"card_short_a", "card_b", "card_c", "card_d"} <= set(cards)
    units = load_units()
    unit = units[0]
    assert unit.unit_code == "L1-U1"
    assert unit.letters == ["a", "b", "c", "d"]
    # validator guarantees first-sound answers match the word's first segment
    answers = {i.answer for i in unit.first_sound_items}
    assert answers <= {"b", "c", "d"}


def test_full_course_covers_alphabet_and_short_vowels() -> None:
    units = load_units()
    assert [u.unit_code for u in units] == [
        "L1-U1", "L1-U2", "L1-U3", "L1-U4", "L1-U5", "L1-U6",
        "L2-U1", "L2-U2", "L2-U3", "L2-U4", "L2-U5", "L2-U6",
    ]
    # every unit is the standard Blevins 6-step lesson (read → build → spell)
    for unit in units:
        assert [s.key for s in unit.steps] == [
            "sound_intro", "first_sound", "blending", "tile_build", "dictation", "heart_word"
        ]
        # tile_build + dictation reuse authored decodable words
        word_ids = {w.id for w in unit.decodable_words}
        for step in unit.steps:
            if step.key in ("tile_build", "dictation"):
                assert step.word_ids and set(step.word_ids) <= word_ids
    cards = load_sound_cards()
    letters = {c.letter for c in cards.values()}
    # the whole alphabet is covered, plus the L2 digraphs and long-vowel spellings
    assert set("abcdefghijklmnopqrstuvwxyz") <= letters
    assert {"sh", "ch", "th", "wh"} <= letters
    assert {"a-e", "i-e", "o-e", "u-e", "ee", "ai", "ay"} <= letters
    # the five short vowels are authored as vowel cards
    vowels = {c.letter for c in cards.values() if c.card_type == "vowel"}
    assert set("aeiou") <= vowels
    # each unit's sound cards resolve and cover the letters it teaches
    for unit in units:
        card_letters = {cards[cid].letter for cid in unit.sound_card_ids}
        assert set(unit.letters) <= card_letters
    # L1 short-vowel focus follows PEP order a,e,i,o,u then a review unit
    assert [u.vowel_focus for u in units[:6]] == [
        "short_a", "short_e", "short_i", "short_o", "short_u", "review"
    ]
    # L2 progresses digraphs → magic-e long vowels → vowel teams
    assert [u.vowel_focus for u in units[6:]] == [
        "digraph_sh_ch", "digraph_th_wh", "long_a_magic_e",
        "long_i_o_magic_e", "long_u_e", "long_a_teams",
    ]


def test_l2_digraph_words_use_multichar_segments() -> None:
    units = {u.unit_code: u for u in load_units()}
    ship = next(w for w in units["L2-U1"].decodable_words if w.text == "ship")
    # digraphs are one blending tile, not two letters
    assert ship.segments == ["sh", "i", "p"]
    cake = next(w for w in units["L2-U3"].decodable_words if w.text == "cake")
    assert cake.segments == ["c", "a-e", "k"]
    # first-sound answers may be a digraph, and the validator already guarantees
    # answer == segments[0]; spot-check the sh/ch contrast item exists
    answers = {i.answer for i in units["L2-U1"].first_sound_items}
    assert "sh" in answers and "ch" in answers


def test_unit_detail_for_a_later_unit(api_client) -> None:
    headers, _ = auth_headers(api_client)
    _seed()
    child_id = _create_child(api_client, headers)
    detail = api_client.get(
        f"/v1/phonics/units/phonics_l1_u2?child_id={child_id}", headers=headers
    )
    assert detail.status_code == 200
    d = detail.json()
    assert d["unit"]["vowel_focus"] == "short_e"
    assert any(c["id"] == "card_short_e" for c in d["sound_cards"])
    # first-sound task isolates the new consonants f, g, h
    assert {i["answer"] for i in d["first_sound_items"]} == {"f", "g", "h"}


def test_unit_lock_progression_unlocks_next_on_mastery(api_client) -> None:
    headers, _ = auth_headers(api_client)
    _seed()
    child_id = _create_child(api_client, headers)

    body = api_client.get(f"/v1/phonics/units?child_id={child_id}", headers=headers).json()
    codes = [u["unit_code"] for u in body["units"]]
    assert codes == [
        "L1-U1", "L1-U2", "L1-U3", "L1-U4", "L1-U5", "L1-U6",
        "L2-U1", "L2-U2", "L2-U3", "L2-U4", "L2-U5", "L2-U6",
    ]
    statuses = {u["unit_code"]: u["status"] for u in body["units"]}
    assert statuses["L1-U1"] == "unlocked"
    assert statuses["L1-U2"] == "locked"
    assert statuses["L1-U6"] == "locked"
    assert statuses["L2-U1"] == "locked"
    assert body["next_unit_id"] == "phonics_l1_u1"

    # Master U1 (first-sound + three blended words) → U2 should unlock.
    db = SessionLocal()
    try:
        unit = db.get(PhonicsUnitModel, "phonics_l1_u1")
        fs = PhonicsAttemptModel(
            child_id=child_id, unit_id=unit.id, practice_type="first_sound_tap",
            accuracy_score=1.0, passed=True, status="scored",
        )
        db.add(fs)
        db.flush()
        apply_attempt_to_progress(db, unit=unit, attempt=fs)
        for word in ("dad", "bad", "cab"):
            attempt = PhonicsAttemptModel(
                child_id=child_id, unit_id=unit.id, practice_type="blend_word_asr",
                target_text=word, accuracy_score=1.0, passed=True, status="scored",
            )
            db.add(attempt)
            db.flush()
            apply_attempt_to_progress(db, unit=unit, attempt=attempt)
        db.commit()
    finally:
        db.close()

    body2 = api_client.get(f"/v1/phonics/units?child_id={child_id}", headers=headers).json()
    st2 = {u["unit_code"]: u["status"] for u in body2["units"]}
    assert st2["L1-U1"] == "mastered"
    assert st2["L1-U2"] == "unlocked"
    assert st2["L1-U3"] == "locked"
    assert body2["next_unit_id"] == "phonics_l1_u2"

    # Mastering the last L1 unit unlocks the first L2 unit (cross-level chain).
    db = SessionLocal()
    try:
        unit6 = db.get(PhonicsUnitModel, "phonics_l1_u6")
        fs6 = PhonicsAttemptModel(
            child_id=child_id, unit_id=unit6.id, practice_type="first_sound_tap",
            accuracy_score=1.0, passed=True, status="scored",
        )
        db.add(fs6)
        db.flush()
        apply_attempt_to_progress(db, unit=unit6, attempt=fs6)
        for word in ("van", "zip", "box"):
            attempt = PhonicsAttemptModel(
                child_id=child_id, unit_id=unit6.id, practice_type="blend_word_asr",
                target_text=word, accuracy_score=1.0, passed=True, status="scored",
            )
            db.add(attempt)
            db.flush()
            apply_attempt_to_progress(db, unit=unit6, attempt=attempt)
        db.commit()
    finally:
        db.close()

    body3 = api_client.get(f"/v1/phonics/units?child_id={child_id}", headers=headers).json()
    st3 = {u["unit_code"]: u["status"] for u in body3["units"]}
    assert st3["L1-U6"] == "mastered"
    assert st3["L2-U1"] == "unlocked"
    assert st3["L2-U2"] == "locked"


def test_tile_build_and_dictation_count_toward_mastery(api_client) -> None:
    headers, _ = auth_headers(api_client)
    _seed()
    child_id = _create_child(api_client, headers)
    unit_id = "phonics_l1_u1"

    def submit(step: str, practice_type: str, words: list[tuple[str, str, bool]]):
        return api_client.post(
            "/v1/phonics/attempts",
            json={
                "child_id": child_id,
                "unit_id": unit_id,
                "step": step,
                "practice_type": practice_type,
                "item_results": [
                    {"prompt": w, "expected": exp, "given": given, "correct": exp == given}
                    for (w, exp, given) in words
                ],
            },
            headers=headers,
        )

    # First-sound mastery (tap).
    fs = api_client.post(
        "/v1/phonics/attempts",
        json={
            "child_id": child_id, "unit_id": unit_id, "step": "first_sound",
            "practice_type": "first_sound_tap",
            "item_results": [
                {"prompt": "bad", "expected": "b", "given": "b", "correct": True},
                {"prompt": "cab", "expected": "c", "given": "c", "correct": True},
                {"prompt": "dad", "expected": "d", "given": "d", "correct": True},
            ],
        },
        headers=headers,
    )
    assert fs.status_code == 201

    # Tile-build two words correctly (assembled == expected spelling).
    tb = submit("tile_build", "tile_build", [("bad", "bad", "bad"), ("cab", "cab", "cab")])
    assert tb.status_code == 201
    assert tb.json()["attempt"]["accuracy_score"] == 1.0

    # Dictation one more word correctly → 3 distinct decoded words total → mastery.
    dct = submit("dictation", "dictation", [("dab", "dab", "dab")])
    assert dct.status_code == 201
    prog = dct.json()["progress"]
    assert set(prog["blended_words"]) == {"bad", "cab", "dab"}
    assert prog["status"] == "mastered"
    assert prog["mastered"] is True

    # A wrong tile-build item is not credited.
    child2 = _create_child(api_client, headers)
    wrong = api_client.post(
        "/v1/phonics/attempts",
        json={
            "child_id": child2, "unit_id": unit_id, "step": "tile_build",
            "practice_type": "tile_build",
            "item_results": [{"prompt": "bad", "expected": "bad", "given": "bda", "correct": False}],
        },
        headers=headers,
    )
    assert wrong.status_code == 201
    assert wrong.json()["progress"]["blended_words"] == []


def test_score_word_match_is_honest() -> None:
    assert score_word_match("dad", "dad").passed
    assert score_word_match("the dad ran", "dad").passed  # token contained
    empty = score_word_match("", "dad")
    assert not empty.passed and empty.status == "no_match"
    fuzzy = score_word_match("bad", "dad")
    assert not fuzzy.passed and fuzzy.status == "scored" and fuzzy.accuracy < 0.8


def test_l2_word_scoring_is_whole_word_so_digraphs_pass() -> None:
    # score_word_match compares the ASR transcript to the target *word*, so L2
    # digraph / magic-e / vowel-team words score exactly like L1 CVC words — no
    # special-casing of multi-letter graphemes is needed on the scoring side.
    for word in ("ship", "chip", "fish", "thin", "when", "cake", "bike", "home", "bee", "play"):
        assert score_word_match(word, word).passed, word
        # ASR often returns the word inside a short phrase / with punctuation.
        assert score_word_match(f"{word.capitalize()}.", word).passed, word
    # a genuinely different word must not pass (sh vs ch contrast stays honest)
    wrong = score_word_match("chip", "ship")
    assert not wrong.passed and wrong.status == "scored"
    # empty transcript is a retry, not a crash
    empty = score_word_match("", "ship")
    assert not empty.passed and empty.status == "no_match"


def test_asr_accent_maps_child_accent() -> None:
    from app.services.shared.phonics_scoring import asr_accent_for

    assert asr_accent_for("uk") == "br"
    assert asr_accent_for("US") == "am"  # us / unknown -> default American
    assert asr_accent_for("") == "am"
    # a British child keeps British even when the server default changes
    assert asr_accent_for("uk", default="en-US") == "br"
    assert asr_accent_for("us", default="en-US") == "en-US"


def test_tap_and_mastery_decisions() -> None:
    tap = score_tap_items([{"correct": True}, {"correct": True}, {"correct": False}])
    assert tap.correct == 2 and tap.total == 3 and not tap.passed
    mastered = decide_mastery(
        first_sound_accuracy=1.0, blended_words=["dad", "bad", "cab"], total_blend_targets=3, attempts_count=4
    )
    assert mastered.mastered and mastered.status == "mastered"
    partial = decide_mastery(first_sound_accuracy=0.5, blended_words=[], total_blend_targets=3, attempts_count=1)
    assert not partial.mastered and partial.status == "in_progress"


# --------------------------- end-to-end API --------------------------- #


def _seed() -> None:
    db = SessionLocal()
    try:
        seed_sound_cards(db)
        seed_units(db)
    finally:
        db.close()


def _create_child(api_client, headers) -> str:
    resp = api_client.post("/v1/children", json=_CHILD_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


def test_units_list_and_unit_detail(api_client) -> None:
    headers, _ = auth_headers(api_client)
    _seed()
    child_id = _create_child(api_client, headers)

    units = api_client.get(f"/v1/phonics/units?child_id={child_id}", headers=headers)
    assert units.status_code == 200
    body = units.json()
    assert body["course"]["id"] == "course_pep_g3"
    assert body["units"][0]["unit_code"] == "L1-U1"
    assert body["units"][0]["status"] == "unlocked"
    unit_id = body["units"][0]["id"]
    assert body["next_unit_id"] == unit_id

    detail = api_client.get(f"/v1/phonics/units/{unit_id}?child_id={child_id}", headers=headers)
    assert detail.status_code == 200
    d = detail.json()
    assert len(d["sound_cards"]) == 4
    assert any(c["id"] == "card_short_a" for c in d["sound_cards"])
    # sound card feeds a speakable string, never IPA
    card = next(c for c in d["sound_cards"] if c["id"] == "card_short_a")
    assert not card["speakable_sound"].startswith("/")
    assert len(d["decodable_words"]) >= 4
    assert len(d["first_sound_items"]) == 3
    assert d["progress"]["status"] == "unlocked"
    assert [s["key"] for s in d["steps"]] == [
        "sound_intro", "first_sound", "blending", "tile_build", "dictation", "heart_word"
    ]


def test_unknown_unit_returns_404(api_client) -> None:
    headers, _ = auth_headers(api_client)
    _seed()
    child_id = _create_child(api_client, headers)
    resp = api_client.get(f"/v1/phonics/units/nope?child_id={child_id}", headers=headers)
    assert resp.status_code == 404


def test_child_accent_create_and_patch(api_client) -> None:
    headers, _ = auth_headers(api_client)
    uk = api_client.post("/v1/children", json={**_CHILD_PAYLOAD, "accent": "uk"}, headers=headers)
    assert uk.status_code == 201 and uk.json()["accent"] == "uk"
    us = api_client.post("/v1/children", json=_CHILD_PAYLOAD, headers=headers)
    assert us.json()["accent"] == "us"  # default
    patched = api_client.patch(f"/v1/children/{us.json()['id']}", json={"accent": "uk"}, headers=headers)
    assert patched.status_code == 200 and patched.json()["accent"] == "uk"
    bad = api_client.patch(f"/v1/children/{uk.json()['id']}", json={"accent": "fr"}, headers=headers)
    assert bad.status_code == 422
    assert api_client.patch("/v1/children/nope", json={"accent": "us"}, headers=headers).status_code == 404


def test_phonics_audio_follows_child_accent(api_client) -> None:
    from app.services.shared.phonics_media import generate_phonics_unit_media

    headers, _ = auth_headers(api_client)
    _seed()
    db = SessionLocal()
    try:
        assert generate_phonics_unit_media(db, "phonics_l1_u1")["status"] in {"ready", "partial"}
    finally:
        db.close()

    us_child = _create_child(api_client, headers)
    uk_child = api_client.post(
        "/v1/children", json={**_CHILD_PAYLOAD, "name": "英音娃", "accent": "uk"}, headers=headers
    ).json()["id"]

    def sound_url(child_id: str) -> str:
        d = api_client.get(f"/v1/phonics/units/phonics_l1_u1?child_id={child_id}", headers=headers).json()
        return next(c for c in d["sound_cards"] if c["id"] == "card_short_a")["sound_audio_url"]

    us_url, uk_url = sound_url(us_child), sound_url(uk_child)
    assert "/sound-us" in us_url and "/sound-uk" in uk_url and us_url != uk_url
    # flipping a child's accent flips which audio the API serves
    api_client.patch(f"/v1/children/{us_child}", json={"accent": "uk"}, headers=headers)
    assert "/sound-uk" in sound_url(us_child)


def test_tap_attempt_scores_and_updates_progress(api_client) -> None:
    headers, _ = auth_headers(api_client)
    _seed()
    child_id = _create_child(api_client, headers)
    unit_id = "phonics_l1_u1"

    tap = api_client.post(
        "/v1/phonics/attempts",
        json={
            "child_id": child_id,
            "unit_id": unit_id,
            "step": "first_sound",
            "practice_type": "first_sound_tap",
            "item_results": [
                {"prompt": "bad", "expected": "b", "given": "b", "correct": True},
                {"prompt": "cab", "expected": "c", "given": "c", "correct": True},
                {"prompt": "dad", "expected": "d", "given": "d", "correct": True},
            ],
        },
        headers=headers,
    )
    assert tap.status_code == 201
    payload = tap.json()
    assert payload["attempt"]["accuracy_score"] == 1.0
    assert payload["attempt"]["passed"] is True
    assert payload["progress"]["first_sound_accuracy"] == 1.0
    assert payload["progress"]["status"] == "in_progress"
    assert payload["progress"]["attempts_count"] == 1


def test_audio_attempt_endpoint_accepts_recording(api_client) -> None:
    headers, _ = auth_headers(api_client)
    _seed()
    child_id = _create_child(api_client, headers)
    resp = api_client.post(
        "/v1/phonics/attempts/audio",
        data={
            "child_id": child_id,
            "unit_id": "phonics_l1_u1",
            "target_text": "dad",
            "step": "blending",
            "audio_duration_ms": "900",
        },
        files={"audio": ("dad.m4a", io.BytesIO(b"fake-audio-bytes"), "audio/mp4")},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["target_text"] == "dad"
    assert body["practice_type"] == "blend_word_asr"
    assert body["status"] == "recording_uploaded"
    fetched = api_client.get(f"/v1/phonics/attempts/{body['id']}", headers=headers)
    assert fetched.status_code == 200


def test_blend_passes_drive_mastery_and_unlock(api_client) -> None:
    headers, _ = auth_headers(api_client)
    _seed()
    child_id = _create_child(api_client, headers)

    db = SessionLocal()
    try:
        unit = db.get(PhonicsUnitModel, "phonics_l1_u1")
        # first-sound mastery
        fs = PhonicsAttemptModel(
            child_id=child_id, unit_id=unit.id, practice_type="first_sound_tap",
            accuracy_score=1.0, passed=True, status="scored",
        )
        db.add(fs)
        db.flush()
        apply_attempt_to_progress(db, unit=unit, attempt=fs)
        # three blended words
        for word in ("dad", "bad", "cab"):
            attempt = PhonicsAttemptModel(
                child_id=child_id, unit_id=unit.id, practice_type="blend_word_asr",
                target_text=word, accuracy_score=1.0, passed=True, status="scored",
            )
            db.add(attempt)
            db.flush()
            apply_attempt_to_progress(db, unit=unit, attempt=attempt)
        db.commit()
        progress = get_or_create_progress(db, child_id, unit.id)
        assert progress.status == "mastered"
        assert progress.mastered_at is not None
    finally:
        db.close()

    prog = api_client.get(f"/v1/phonics/progress?child_id={child_id}", headers=headers).json()
    assert prog["mastered_count"] == 1
