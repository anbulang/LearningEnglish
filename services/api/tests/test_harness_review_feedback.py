from __future__ import annotations

import sys
from pathlib import Path

from app.models.contracts import LearningAsset, SourceBoundingBox
from app.services.shared.pipeline import _fallback_source_bbox

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.harness import run_hn016a_qwen_material_smoke as hn016a  # noqa: E402
from scripts.harness import run_hn019_real_device_main_chain as hn019  # noqa: E402


def test_hn019_redacts_source_image_urls_from_flutter_command_and_logs() -> None:
    command = [
        "flutter",
        "run",
        "--dart-define=SOURCE_IMAGE_URLS=https://example.com/private/token/path.png?customToken=abc",
    ]

    redacted = hn019._redacted_command(command, {"source_image_count": 1})
    sanitized = hn019._sanitize_log("$ " + " ".join(command))

    assert redacted[-1] == "--dart-define=SOURCE_IMAGE_URLS=<redacted:1 item(s)>"
    assert "customToken" not in sanitized
    assert "private/token/path.png" not in sanitized
    assert "--dart-define=SOURCE_IMAGE_URLS=<redacted>" in sanitized


def test_hn019_reads_exact_material_id_from_flutter_result() -> None:
    assert (
        hn019._flutter_material_id(
            {
                "status": "failed",
                "result": {"status": "failed", "material_id": "material_hn019_exact"},
            }
        )
        == "material_hn019_exact"
    )
    assert hn019._flutter_material_id({"status": "failed", "result": {"status": "failed"}}) == ""


def test_hn016a_counts_provider_and_fallback_bboxes_separately() -> None:
    provider_asset = LearningAsset(
        id="asset_provider",
        text="queen",
        kind="word",
        source_bbox=SourceBoundingBox(x=0.12, y=0.23, width=0.34, height=0.45),
    )
    fallback_asset = LearningAsset(
        id="asset_fallback",
        text="Find the duck.",
        kind="sentence",
        source_bbox=_fallback_source_bbox(index=2, kind="sentence"),
    )

    counts = hn016a._bbox_evidence_counts(
        [provider_asset, fallback_asset],
        _fallback_source_bbox,
    )

    assert counts == {
        "learning_assets_with_bbox": 2,
        "provider_bbox_count": 1,
        "fallback_bbox_count": 1,
    }
