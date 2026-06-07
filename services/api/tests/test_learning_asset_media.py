from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app
from app.models.contracts import LearningAsset, MediaGenerationStatus, SourceBoundingBox
from app.services.shared.learning_asset_media import HN014MockMediaProvider


def test_hn014_mock_media_provider_fills_urls_for_known_asset() -> None:
    provider = HN014MockMediaProvider(public_base_url="http://testserver")
    assets = [
        LearningAsset(
            id="asset_1",
            text="queen",
            kind="",
            source_page_index=1,
            pronunciation_text="queen",
            image_prompt="参考讲义女王线稿生成彩色图。",
        )
    ]

    updated = provider.apply(assets)

    assert updated[0].translation == "女王"
    assert updated[0].kind == "word"
    assert updated[0].source_bbox == SourceBoundingBox(x=0.05, y=0.14, width=0.43, height=0.35)
    assert updated[0].source_visual_description == "Qq 讲义左上角迷宫中的女王图像。"
    assert updated[0].generated_image_status == MediaGenerationStatus.ready
    assert updated[0].generated_image_url == "http://testserver/mock-media/hn014/images/queen.svg"
    assert updated[0].generated_image_object_key == "mock_media/hn014/images/queen.svg"
    assert updated[0].tts_us_status == MediaGenerationStatus.ready
    assert updated[0].tts_us_url == "http://testserver/mock-media/hn014/tts/us/queen.m4a"
    assert updated[0].tts_us_object_key == "mock_media/hn014/tts/us/queen.m4a"
    assert updated[0].tts_uk_status == MediaGenerationStatus.ready
    assert updated[0].tts_uk_url == "http://testserver/mock-media/hn014/tts/uk/queen.m4a"
    assert updated[0].tts_uk_object_key == "mock_media/hn014/tts/uk/queen.m4a"


def test_hn014_mock_media_provider_fills_page_two_manifest_metadata() -> None:
    provider = HN014MockMediaProvider(public_base_url="http://testserver")
    assets = [
        LearningAsset(
            id="asset_2",
            text="A rabbit can hop fast.",
            kind="",
            pronunciation_text="A rabbit can hop fast.",
            image_prompt="参考讲义兔子线稿生成彩色图。",
        )
    ]

    updated = provider.apply(assets)

    assert updated[0].source_page_index == 2
    assert updated[0].kind == "sentence"
    assert updated[0].generated_image_status == MediaGenerationStatus.ready
    assert updated[0].generated_image_url == "http://testserver/mock-media/hn014/images/rabbit_hop_fast.svg"
    assert updated[0].tts_us_status == MediaGenerationStatus.ready
    assert updated[0].tts_us_url == "http://testserver/mock-media/hn014/tts/us/rabbit_hop_fast.m4a"
    assert updated[0].tts_uk_status == MediaGenerationStatus.ready
    assert updated[0].tts_uk_url == "http://testserver/mock-media/hn014/tts/uk/rabbit_hop_fast.m4a"


def test_hn014_mock_media_provider_marks_unknown_asset_failed() -> None:
    provider = HN014MockMediaProvider(public_base_url="http://testserver")
    assets = [
        LearningAsset(
            id="asset_unknown",
            text="unknown word",
            kind="phrase",
            source_page_index=1,
            translation="未知词",
            pronunciation_text="unknown word",
            image_prompt="生成彩色图。",
        )
    ]

    updated = provider.apply(assets)

    assert updated[0].text == "unknown word"
    assert updated[0].translation == "未知词"
    assert updated[0].kind == "phrase"
    assert updated[0].generated_image_status == MediaGenerationStatus.failed
    assert updated[0].tts_us_status == MediaGenerationStatus.failed
    assert updated[0].tts_uk_status == MediaGenerationStatus.failed


def test_hn014_mock_media_manifest_paths_exist() -> None:
    provider = HN014MockMediaProvider(public_base_url="http://testserver")
    root = provider.root
    payload = json.loads((root / "manifest.json").read_text(encoding="utf-8"))

    for asset in payload["assets"]:
        for key in ("image", "tts_us", "tts_uk"):
            path = (root / asset[key]).resolve()

            assert root.resolve() in path.parents
            assert path.exists(), f"{asset['text']} {key} missing: {asset[key]}"


def test_hn014_static_media_route_serves_svg() -> None:
    response = TestClient(app).get("/mock-media/hn014/images/queen.svg")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in response.content
