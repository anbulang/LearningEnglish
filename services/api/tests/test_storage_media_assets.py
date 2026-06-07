from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from app.core.settings import get_settings
from app.db.models import StoredAssetModel
from app.models.contracts import LearningAsset, SourceBoundingBox
from app.services.shared.media_reference import build_reference_image
from app.services.shared.storage import LocalStorageService


class _FakeStorage:
    def __init__(self, source_path: Path) -> None:
        self.source_path = source_path
        self.resolved_asset: StoredAssetModel | None = None

    def resolve_local_path(self, asset: StoredAssetModel) -> Path:
        self.resolved_asset = asset
        return self.source_path


class _FailingStorage:
    def resolve_local_path(self, asset: StoredAssetModel) -> Path:
        raise RuntimeError("download failed")


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


@pytest.mark.parametrize("object_key", ["/tmp/escape.png", "../escape.png", "generated/../escape.png"])
def test_local_storage_save_bytes_rejects_unsafe_object_key(
    monkeypatch,
    tmp_path: Path,
    object_key: str,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path / "uploads"))
    storage = LocalStorageService()

    with pytest.raises(ValueError, match="object_key"):
        storage.save_bytes(
            owner_type="generated_media",
            owner_id="material_1",
            object_key=object_key,
            content_type="image/png",
            payload=b"png-bytes",
        )

    assert not (tmp_path / "escape.png").exists()


def test_build_reference_image_crops_source_bbox(monkeypatch, tmp_path: Path) -> None:
    get_settings.cache_clear()
    upload_root = tmp_path / "uploads"
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(upload_root))
    source_path = upload_root / "material" / "material_1" / "worksheet.png"
    source_path.parent.mkdir(parents=True)
    image = Image.new("RGB", (100, 80), color=(255, 255, 255))
    image.paste((255, 0, 0), (10, 20, 60, 60))
    image.paste((0, 0, 255), (0, 0, 10, 20))
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
        id="../asset:queen",
        text="queen",
        kind="word",
        source_page_index=1,
        source_bbox=SourceBoundingBox(x=0.1, y=0.25, width=0.5, height=0.5),
    )
    fake_storage = _FakeStorage(source_path)

    reference = build_reference_image(asset, [stored], tmp_path / "refs", storage=fake_storage)

    assert reference is not None
    assert reference.exists()
    assert reference.parent == tmp_path / "refs"
    assert reference.name == "asset_queen-reference.png"
    assert fake_storage.resolved_asset is stored
    with Image.open(reference) as cropped:
        assert cropped.size == (512, 512)
        assert cropped.getpixel((256, 256)) == (255, 0, 0)


def test_build_reference_image_pads_thin_bbox_without_huge_resize(monkeypatch, tmp_path: Path) -> None:
    get_settings.cache_clear()
    upload_root = tmp_path / "uploads"
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(upload_root))
    source_path = upload_root / "material" / "material_1" / "worksheet.png"
    source_path.parent.mkdir(parents=True)
    image = Image.new("RGB", (1000, 80), color=(255, 255, 255))
    image.paste((255, 0, 0), (0, 32, 1000, 48))
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
        id="asset_sentence",
        text="A rabbit can hop fast.",
        kind="sentence",
        source_page_index=1,
        source_bbox=SourceBoundingBox(x=0, y=0.4, width=1, height=0.2),
    )

    reference = build_reference_image(asset, [stored], tmp_path / "refs", storage=_FakeStorage(source_path))

    assert reference is not None
    with Image.open(reference) as cropped:
        assert cropped.size == (512, 512)
        assert cropped.getpixel((256, 256)) == (255, 0, 0)


def test_build_reference_image_returns_none_when_storage_resolve_fails(tmp_path: Path) -> None:
    stored = StoredAssetModel(
        owner_type="material",
        owner_id="material_1",
        bucket="learning-english",
        object_key="material/material_1/worksheet.png",
        content_type="image/png",
        size_bytes=123,
        url="http://testserver/uploads/material/material_1/worksheet.png",
    )
    asset = LearningAsset(
        id="asset_queen",
        text="queen",
        kind="word",
        source_page_index=1,
        source_bbox=SourceBoundingBox(x=0.1, y=0.25, width=0.5, height=0.5),
    )

    assert build_reference_image(asset, [stored], tmp_path / "refs", storage=_FailingStorage()) is None
