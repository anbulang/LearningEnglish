from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image, UnidentifiedImageError

from app.core.settings import get_settings
from app.db.models import StoredAssetModel
from app.models.contracts import LearningAsset


def build_reference_image(
    *,
    asset: LearningAsset,
    source_assets: list[StoredAssetModel],
    work_dir: Path,
) -> Optional[Path]:
    if asset.source_bbox is None:
        return None
    if asset.source_page_index < 1 or asset.source_page_index > len(source_assets):
        return None
    source = source_assets[asset.source_page_index - 1]
    if not source.content_type.startswith("image/"):
        return None

    source_path = get_settings().local_storage_path / source.object_key
    if not source_path.exists():
        return None

    work_dir.mkdir(parents=True, exist_ok=True)
    target_path = work_dir / f"{asset.id}-reference.png"
    try:
        with Image.open(source_path) as image:
            width, height = image.size
            left = _clamp(int(asset.source_bbox.x * width), 0, width - 1)
            top = _clamp(int(asset.source_bbox.y * height), 0, height - 1)
            right = _clamp(int((asset.source_bbox.x + asset.source_bbox.width) * width), left + 1, width)
            bottom = _clamp(int((asset.source_bbox.y + asset.source_bbox.height) * height), top + 1, height)
            image.crop((left, top, right, bottom)).convert("RGB").save(target_path, format="PNG")
    except (OSError, UnidentifiedImageError):
        return None
    return target_path


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))
