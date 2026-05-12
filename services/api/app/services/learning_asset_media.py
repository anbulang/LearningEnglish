from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models.contracts import LearningAsset, MediaGenerationStatus, SourceBoundingBox


_REQUIRED_MANIFEST_KEYS = {
    "text",
    "kind",
    "translation",
    "source_page_index",
    "source_bbox",
    "source_visual_description",
    "image",
    "tts_us",
    "tts_uk",
}


class HN014MockMediaProvider:
    def __init__(self, public_base_url: str) -> None:
        self.public_base_url = public_base_url.rstrip("/")
        self.root = Path(__file__).resolve().parents[1] / "static" / "mock_media" / "hn014"
        payload = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        assets = payload.get("assets", [])
        if not isinstance(assets, list):
            raise ValueError("HN-014 mock media manifest must contain an assets list")
        for item in assets:
            _validate_manifest_item(item)
        self._by_text = {
            str(item.get("text", "")).strip().lower(): item
            for item in assets
            if str(item.get("text", "")).strip()
        }

    def apply(self, assets: list[LearningAsset]) -> list[LearningAsset]:
        updated: list[LearningAsset] = []
        for asset in assets:
            match = self._by_text.get(asset.text.strip().lower())
            if match is None:
                updated.append(
                    asset.model_copy(
                        update={
                            "generated_image_status": MediaGenerationStatus.failed,
                            "tts_us_status": MediaGenerationStatus.failed,
                            "tts_uk_status": MediaGenerationStatus.failed,
                        }
                    )
                )
                continue

            image_path = str(match["image"])
            tts_us_path = str(match["tts_us"])
            tts_uk_path = str(match["tts_uk"])
            source_page_index = int(match["source_page_index"])
            updated.append(
                asset.model_copy(
                    update={
                        "translation": asset.translation or match.get("translation", ""),
                        "kind": asset.kind or match.get("kind", "word"),
                        "source_page_index": source_page_index,
                        "source_bbox": asset.source_bbox or _source_bbox_from_manifest(match.get("source_bbox")),
                        "source_visual_description": asset.source_visual_description
                        or match.get("source_visual_description", ""),
                        "generated_image_status": MediaGenerationStatus.ready,
                        "generated_image_url": self._url(image_path),
                        "generated_image_object_key": f"mock_media/hn014/{image_path}",
                        "tts_us_status": MediaGenerationStatus.ready,
                        "tts_us_url": self._url(tts_us_path),
                        "tts_us_object_key": f"mock_media/hn014/{tts_us_path}",
                        "tts_uk_status": MediaGenerationStatus.ready,
                        "tts_uk_url": self._url(tts_uk_path),
                        "tts_uk_object_key": f"mock_media/hn014/{tts_uk_path}",
                    }
                )
            )
        return updated

    def _url(self, relative_path: str) -> str:
        return f"{self.public_base_url}/mock-media/hn014/{relative_path}"


def _validate_manifest_item(raw: object) -> None:
    if not isinstance(raw, dict):
        raise ValueError("HN-014 mock media manifest assets must be objects")
    text = str(raw.get("text", "")).strip()
    missing = sorted(key for key in _REQUIRED_MANIFEST_KEYS if key not in raw)
    if missing:
        label = text or "<missing text>"
        raise ValueError(f"HN-014 mock media manifest asset {label} missing keys: {', '.join(missing)}")
    source_page_index = raw.get("source_page_index")
    if not isinstance(source_page_index, int) or source_page_index < 1:
        label = text or "<missing text>"
        raise ValueError(f"HN-014 mock media manifest asset {label} has invalid source_page_index")


def _source_bbox_from_manifest(raw: object) -> SourceBoundingBox | None:
    if not isinstance(raw, dict):
        return None
    values: dict[str, Any] = raw
    return SourceBoundingBox(
        x=float(values.get("x") or 0),
        y=float(values.get("y") or 0),
        width=float(values.get("width") or 1),
        height=float(values.get("height") or 1),
    )
