from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.core.settings import get_settings
from app.db.models import StoredAssetModel
from app.models.contracts import LearningAsset, SourceBoundingBox
from app.services.media_reference import build_reference_image
from app.services.storage import LocalStorageService


def test_local_storage_save_bytes_writes_generated_media(monkeypatch, tmp_path: Path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path / "uploads"))
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://testserver")
    storage = LocalStorageService()

    stored = storage.save_bytes(
        owner_type="generated_media",
        owner_id="material_1",
        object_key="generated/media/material_1/asset_queen/image.png",
        content_type="image/png",
        payload=b"png-bytes",
    )

    assert stored.owner_type == "generated_media"
    assert stored.owner_id == "material_1"
    assert stored.object_key == "generated/media/material_1/asset_queen/image.png"
    assert stored.content_type == "image/png"
    assert stored.size_bytes == len(b"png-bytes")
    assert stored.url == "http://testserver/uploads/generated/media/material_1/asset_queen/image.png"
    assert (tmp_path / "uploads" / stored.object_key).read_bytes() == b"png-bytes"


def test_build_reference_image_crops_source_bbox(monkeypatch, tmp_path: Path) -> None:
    get_settings.cache_clear()
    upload_root = tmp_path / "uploads"
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(upload_root))
    source_path = upload_root / "material" / "material_1" / "worksheet.png"
    source_path.parent.mkdir(parents=True)
    image = Image.new("RGB", (100, 80), color=(255, 255, 255))
    image.save(source_path)
    stored = StoredAssetModel(
        owner_type="material",
        owner_id="material_1",
        bucket="learning-english",
        object_key="material/material_1/worksheet.png",
        content_type="image/png",
        size_bytes=source_path.stat().st_size,
        url="http://testserver/uploads/material/material_1/worksheet.png",
    )
    asset = LearningAsset(
        id="asset_queen",
        text="queen",
        kind="word",
        source_page_index=1,
        source_bbox=SourceBoundingBox(x=0.1, y=0.25, width=0.5, height=0.5),
    )

    reference = build_reference_image(asset, [stored], tmp_path / "refs")

    assert reference is not None
    assert reference.exists()
    with Image.open(reference) as cropped:
        assert cropped.size == (50, 40)
