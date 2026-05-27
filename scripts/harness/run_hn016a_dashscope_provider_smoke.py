from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def main() -> None:
    evidence_dir = ROOT / "dist" / "harness" / "HN-016A"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    try:
        summary = _run_provider_smoke(evidence_dir=evidence_dir, started=started)
    except Exception as exc:
        failure = {
            "status": "failed",
            "provider": "dashscope",
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_seconds": round(perf_counter() - started, 3),
        }
        (evidence_dir / "dashscope-provider-smoke-summary.json").write_text(
            json.dumps(failure, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(failure, ensure_ascii=False, indent=2))
        raise SystemExit(1) from exc
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _run_provider_smoke(*, evidence_dir: Path, started: float) -> dict:
    if not os.environ.get("DASHSCOPE_API_KEY", "").strip():
        raise RuntimeError("DASHSCOPE_API_KEY is required for HN-016A DashScope provider smoke")

    os.environ["APP_ENV"] = os.environ.get("APP_ENV", "development")
    os.environ["MEDIA_PROVIDER"] = "real"
    os.environ["MEDIA_IMAGE_PROVIDER"] = "dashscope"
    os.environ["MEDIA_TTS_PROVIDER"] = "dashscope"

    from app.core.settings import get_settings  # noqa: E402
    from app.models.contracts import LearningAsset  # noqa: E402
    from app.services.learning_asset_media import build_media_provider_bundle  # noqa: E402

    get_settings.cache_clear()
    bundle = build_media_provider_bundle(public_base_url="http://testserver")
    try:
        asset = LearningAsset(
            id="asset_rabbit",
            text="rabbit",
            kind="word",
            translation="兔子",
            pronunciation_text="rabbit",
            image_prompt="Colorful child-friendly rabbit flashcard for English phonics practice.",
            source_page_index=1,
            source_visual_description="A rabbit can hop fast.",
        )
        prompt = (
            "Generate a bright, child-friendly color illustration for an English worksheet flashcard. "
            "Show one happy rabbit hopping in a simple classroom-learning style. "
            "No text, no watermark."
        )

        image = bundle.image_provider.generate(asset, prompt, reference_image_path=None)
        image_path = evidence_dir / "dashscope-rabbit-image.png"
        image_path.write_bytes(image.payload)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as reference_file:
            reference_file.write(image.payload)
            reference_path = Path(reference_file.name)
        try:
            reference_edit = bundle.image_provider.generate(
                asset,
                (
                    "参考讲义图片，生成更适合儿童英语学习的彩色教学配图。"
                    "保留 rabbit 主题，画面明亮，无文字，无水印。"
                ),
                reference_image_path=reference_path,
            )
        finally:
            reference_path.unlink(missing_ok=True)
        reference_edit_path = evidence_dir / "dashscope-reference-edit-image.png"
        reference_edit_path.write_bytes(reference_edit.payload)

        tts_us = bundle.tts_provider.synthesize("rabbit", "us")
        tts_us_path = evidence_dir / "dashscope-tts-us.mp3"
        tts_us_path.write_bytes(tts_us.payload)

        tts_uk = bundle.tts_provider.synthesize("rabbit", "uk")
        tts_uk_path = evidence_dir / "dashscope-tts-uk.mp3"
        tts_uk_path.write_bytes(tts_uk.payload)
    finally:
        bundle.close()

    summary = {
        "status": "passed",
        "provider": "dashscope",
        "media_provider": "real",
        "media_image_provider": "dashscope",
        "media_tts_provider": "dashscope",
        "image": {
            "path": str(image_path),
            "content_type": image.content_type,
            "size_bytes": image_path.stat().st_size,
        },
        "reference_edit_image": {
            "path": str(reference_edit_path),
            "content_type": reference_edit.content_type,
            "size_bytes": reference_edit_path.stat().st_size,
        },
        "tts_us": {
            "path": str(tts_us_path),
            "content_type": tts_us.content_type,
            "size_bytes": tts_us_path.stat().st_size,
        },
        "tts_uk": {
            "path": str(tts_uk_path),
            "content_type": tts_uk.content_type,
            "size_bytes": tts_uk_path.stat().st_size,
        },
        "elapsed_seconds": round(perf_counter() - started, 3),
    }
    (evidence_dir / "dashscope-provider-smoke-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


if __name__ == "__main__":
    main()
