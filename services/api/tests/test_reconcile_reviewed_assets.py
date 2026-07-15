from __future__ import annotations

from app.models.contracts import LearningAsset, MediaGenerationStatus
from app.services.shared.pipeline import reconcile_reviewed_learning_assets


def _asset(asset_id: str, text: str, kind: str = "word", *, image_ready: bool = False) -> LearningAsset:
    return LearningAsset.model_validate(
        {
            "id": asset_id,
            "text": text,
            "kind": kind,
            "translation": "",
            "source_page_index": 1,
            "pronunciation_text": text,
            "image_prompt": "",
            "primary_accent": "us",
            "generated_image_status": "ready" if image_ready else "pending",
            "generated_image_url": "https://cdn/x.png" if image_ready else "",
        }
    )


def test_drops_asset_whose_word_was_removed() -> None:
    assets = [_asset("a", "cat"), _asset("b", "dog"), _asset("c", "bird")]
    kept = reconcile_reviewed_learning_assets(assets, ["cat", "bird"], [])
    assert [asset.text for asset in kept] == ["cat", "bird"]


def test_keeps_sentence_assets_by_reviewed_sentences() -> None:
    assets = [
        _asset("a", "cat"),
        _asset("s", "It is a cat.", kind="sentence"),
    ]
    kept = reconcile_reviewed_learning_assets(assets, ["cat"], ["It is a cat."])
    assert [asset.text for asset in kept] == ["cat", "It is a cat."]


def test_reused_asset_keeps_its_generated_media() -> None:
    ready = _asset("a", "cat", image_ready=True)
    kept = reconcile_reviewed_learning_assets([ready], ["cat"], [])
    assert len(kept) == 1
    assert kept[0].id == "a"
    assert kept[0].generated_image_status == MediaGenerationStatus.ready
    assert kept[0].generated_image_url == "https://cdn/x.png"


def test_corrected_word_becomes_fresh_media_pending_asset() -> None:
    # Parent fixes 'cet' -> 'cat': the stale asset is dropped and the corrected
    # word gets a fresh asset the media pipeline will fill in (not the old one).
    stale = _asset("a", "cet", image_ready=True)
    result = reconcile_reviewed_learning_assets([stale], ["cat"], [])
    assert [asset.text for asset in result] == ["cat"]
    fresh = result[0]
    assert fresh.id != "a"
    assert fresh.generated_image_status == MediaGenerationStatus.pending
    assert fresh.tts_us_status == MediaGenerationStatus.pending


def test_added_word_becomes_fresh_media_pending_asset() -> None:
    existing = _asset("a", "cat", image_ready=True)
    result = reconcile_reviewed_learning_assets([existing], ["cat", "dog"], [])
    assert [asset.text for asset in result] == ["cat", "dog"]
    assert result[0].id == "a"  # reused
    assert result[1].id != "a"  # added -> fresh
    assert result[1].kind == "word"
    assert result[1].generated_image_status == MediaGenerationStatus.pending


def test_empty_reviewed_lists_drop_all_assets() -> None:
    # Parent deleted everything -> honour it (no resurrecting the original OCR).
    assets = [_asset("a", "cat")]
    assert reconcile_reviewed_learning_assets(assets, [], []) == []


def test_matching_is_case_and_whitespace_insensitive() -> None:
    assets = [_asset("s", "A queen can sing.", kind="sentence")]
    kept = reconcile_reviewed_learning_assets(assets, [], ["  a QUEEN can SING.  "])
    assert [asset.text for asset in kept] == ["A queen can sing."]
    assert kept[0].id == "s"  # reused, not re-created


def test_reviewed_order_is_preserved_vocab_then_sentences() -> None:
    assets = [_asset("s", "It is a cat.", kind="sentence"), _asset("a", "cat")]
    result = reconcile_reviewed_learning_assets(assets, ["cat"], ["It is a cat."])
    assert [asset.text for asset in result] == ["cat", "It is a cat."]
