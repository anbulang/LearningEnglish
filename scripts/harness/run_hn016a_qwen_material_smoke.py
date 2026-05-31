from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from time import perf_counter

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def main() -> None:
    evidence_dir = ROOT / "dist" / "harness" / "HN-016A"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    try:
        summary = _run_qwen_material_smoke(evidence_dir=evidence_dir, started=started)
    except Exception as exc:
        failure = {
            "status": "failed",
            "provider": "qwen",
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_seconds": round(perf_counter() - started, 3),
        }
        (evidence_dir / "qwen-material-smoke-summary.json").write_text(
            json.dumps(failure, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(failure, ensure_ascii=False, indent=2))
        raise SystemExit(1) from exc
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _run_qwen_material_smoke(*, evidence_dir: Path, started: float) -> dict:
    if not os.environ.get("DASHSCOPE_API_KEY", "").strip():
        raise RuntimeError("DASHSCOPE_API_KEY is required for HN-016A Qwen material smoke")

    os.environ["APP_ENV"] = os.environ.get("APP_ENV", "development")
    os.environ["AI_PROVIDER"] = os.environ.get("AI_PROVIDER", "qwen")

    from app.core.settings import get_settings  # noqa: E402
    from app.models.contracts import CourseMaterial, JobStatus, MaterialParseJob  # noqa: E402
    from app.services.pipeline import build_pipeline_service  # noqa: E402

    get_settings.cache_clear()
    worksheet_path = evidence_dir / "qwen-real-worksheet.png"
    _write_sample_worksheet(worksheet_path)

    material = CourseMaterial(
        id="material_qwen_real_smoke",
        child_id="child_qwen_real_smoke",
        teacher_name="Emma",
        lesson_date=date(2026, 6, 1),
        title="Animals Around Me",
        topic="English animals",
        status="processing",
    )
    job = MaterialParseJob(
        id="job_qwen_real_smoke",
        material_id=material.id,
        status=JobStatus.processing,
        started_at=datetime.now(timezone.utc),
    )

    service = build_pipeline_service()
    prepared = service.prepare_job(material, job, local_paths=[worksheet_path])
    knowledge_pack, review_tasks, coaching_script = service.build_knowledge_assets(material, prepared)
    learning_assets_with_bbox = sum(1 for asset in prepared.draft_learning_assets if asset.source_bbox is not None)

    summary = {
        "status": (
            "passed"
            if prepared.status == JobStatus.needs_review
            and prepared.draft_learning_assets
            and learning_assets_with_bbox == len(prepared.draft_learning_assets)
            else "failed"
        ),
        "provider": os.environ.get("AI_PROVIDER"),
        "vision_model": os.environ.get("QWEN_VISION_MODEL"),
        "text_model": os.environ.get("QWEN_MODEL"),
        "job_status": prepared.status.value,
        "draft_title": prepared.draft_title,
        "draft_topic": prepared.draft_topic,
        "draft_vocabulary": prepared.draft_vocabulary,
        "draft_sentences": prepared.draft_sentences,
        "image_record_count": len(prepared.draft_image_records),
        "learning_asset_count": len(prepared.draft_learning_assets),
        "learning_assets_with_bbox": learning_assets_with_bbox,
        "learning_assets": [
            {
                "text": asset.text,
                "kind": asset.kind,
                "translation": asset.translation,
                "source_page_index": asset.source_page_index,
                "source_bbox": asset.source_bbox.model_dump() if asset.source_bbox else None,
                "pronunciation_text": asset.pronunciation_text,
                "has_image_prompt": bool(asset.image_prompt.strip()),
            }
            for asset in prepared.draft_learning_assets
        ],
        "knowledge_pack": {
            "topic": knowledge_pack.topic,
            "vocabulary_count": len(knowledge_pack.vocabulary_items),
            "sentence_count": len(knowledge_pack.sentence_patterns),
        },
        "review_task_count": len(review_tasks),
        "coaching_script_title": coaching_script.title,
        "warnings": prepared.warnings,
        "confidence_summary": prepared.confidence_summary,
        "elapsed_seconds": round(perf_counter() - started, 3),
    }
    (evidence_dir / "qwen-material-smoke-job.json").write_text(
        prepared.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (evidence_dir / "qwen-material-smoke-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if summary["status"] != "passed":
        raise RuntimeError(f"Qwen material smoke failed: {summary}")
    return summary


def _write_sample_worksheet(path: Path) -> None:
    image = Image.new("RGB", (1200, 1600), "#fffaf1")
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 72)
        word_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 48)
        sentence_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 48)
        small_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 36)
    except OSError:
        title_font = word_font = sentence_font = small_font = ImageFont.load_default()

    draw.rounded_rectangle((90, 90, 1110, 1510), radius=48, fill="white", outline="#f1d8c7", width=8)
    draw.text((245, 150), "Animals Around Me", font=title_font, fill="#2f2926")
    draw.text((310, 245), "Lesson 3 - Look, listen and say", font=small_font, fill="#8b6b58")
    cards = [
        ("cat", (140, 360), "#ffe3d7", "#f58f75"),
        ("dog", (460, 360), "#e3f4ff", "#7bb8e8"),
        ("bird", (780, 360), "#e3f7e8", "#63c27d"),
    ]
    for word, (x, y), bg, fg in cards:
        draw.rounded_rectangle((x, y, x + 280, y + 260), radius=36, fill=bg)
        draw.ellipse((x + 84, y + 54, x + 196, y + 166), fill=fg)
        draw.ellipse((x + 116, y + 91, x + 132, y + 107), fill="#2f2926")
        draw.ellipse((x + 156, y + 91, x + 172, y + 107), fill="#2f2926")
        draw.arc((x + 112, y + 112, x + 168, y + 154), 20, 160, fill="#2f2926", width=6)
        draw.text((x + 78, y + 198), word, font=word_font, fill="#2f2926")
    for text, y, color in [
        ("What is this?", 720, "#fff0c5"),
        ("It is a cat.", 900, "#dcf4ef"),
        ("I can see a dog.", 1080, "#fce1d8"),
    ]:
        draw.rounded_rectangle((150, y, 1050, y + 125), radius=28, fill=color)
        draw.text((190, y + 28), text, font=sentence_font, fill="#2f2926")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


if __name__ == "__main__":
    main()
