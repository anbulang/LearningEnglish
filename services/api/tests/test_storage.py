from __future__ import annotations

from io import BytesIO

import pytest
from fastapi import UploadFile

from app.core.settings import get_settings
from app.services import storage


class _FakeS3Client:
    def head_bucket(self, Bucket: str) -> None:  # noqa: N803 - boto3 shape
        self.bucket = Bucket

    def put_object(self, **kwargs) -> None:
        self.put_kwargs = kwargs


class _FakeBoto3:
    def __init__(self, client: _FakeS3Client) -> None:
        self.client_instance = client

    def client(self, *_args, **_kwargs) -> _FakeS3Client:
        return self.client_instance


def test_s3_upload_url_uses_public_api_uploads(monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("OBJECT_STORAGE_ENDPOINT", "http://minio:9000")
    get_settings.cache_clear()

    fake_client = _FakeS3Client()
    monkeypatch.setattr(storage, "boto3", _FakeBoto3(fake_client))
    monkeypatch.setattr(storage, "Config", None)

    try:
        service = storage.S3StorageService()
        upload = UploadFile(filename="worksheet.jpg", file=BytesIO(b"image"))
        upload.headers = {"content-type": "image/jpeg"}

        asset = service.save_upload("material", "material_1", upload)

        assert asset.url.startswith(
            "http://127.0.0.1:8000/uploads/material/material_1/"
        )
        assert "minio" not in asset.url
        assert fake_client.put_kwargs["Bucket"] == "learning-english"
        assert fake_client.put_kwargs["ContentType"] == "image/jpeg"
    finally:
        get_settings.cache_clear()


def test_s3_save_bytes_puts_generated_media(monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000/")
    monkeypatch.setenv("OBJECT_STORAGE_ENDPOINT", "http://minio:9000")
    get_settings.cache_clear()

    fake_client = _FakeS3Client()
    monkeypatch.setattr(storage, "boto3", _FakeBoto3(fake_client))
    monkeypatch.setattr(storage, "Config", None)

    try:
        service = storage.S3StorageService()

        asset = service.save_bytes(
            owner_type="generated_media",
            owner_id="material_1",
            object_key="generated/media/material_1/asset_queen/image.png",
            content_type="image/png",
            payload=b"png-bytes",
        )

        assert asset.url == "http://127.0.0.1:8000/uploads/generated/media/material_1/asset_queen/image.png"
        assert asset.size_bytes == len(b"png-bytes")
        assert fake_client.put_kwargs == {
            "Bucket": "learning-english",
            "Key": "generated/media/material_1/asset_queen/image.png",
            "Body": b"png-bytes",
            "ContentType": "image/png",
        }
    finally:
        get_settings.cache_clear()


def test_s3_save_bytes_rejects_unsafe_object_key_before_put(monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("OBJECT_STORAGE_ENDPOINT", "http://minio:9000")
    get_settings.cache_clear()

    fake_client = _FakeS3Client()
    monkeypatch.setattr(storage, "boto3", _FakeBoto3(fake_client))
    monkeypatch.setattr(storage, "Config", None)

    try:
        service = storage.S3StorageService()

        with pytest.raises(ValueError, match="object_key"):
            service.save_bytes(
                owner_type="generated_media",
                owner_id="material_1",
                object_key="../escape.png",
                content_type="image/png",
                payload=b"png-bytes",
            )

        assert not hasattr(fake_client, "put_kwargs")
    finally:
        get_settings.cache_clear()
