from __future__ import annotations

import mimetypes
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from fastapi import UploadFile

from app.core.settings import get_settings
from app.db.models import StoredAssetModel

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
except ImportError:  # pragma: no cover - optional runtime dependency
    boto3 = None
    Config = None
    ClientError = Exception


class LocalStorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.settings.local_storage_path.mkdir(parents=True, exist_ok=True)

    def save_upload(self, owner_type: str, owner_id: str, upload: UploadFile) -> StoredAssetModel:
        extension = Path(upload.filename or "upload.bin").suffix or ".bin"
        object_key = f"{owner_type}/{owner_id}/{uuid4().hex}{extension}"
        target = self.settings.local_storage_path / object_key
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = upload.file.read()
        target.write_bytes(payload)
        url = f"{self.settings.public_base_url}/uploads/{object_key}"
        return StoredAssetModel(
            owner_type=owner_type,
            owner_id=owner_id,
            bucket=self.settings.storage_bucket,
            object_key=object_key,
            content_type=upload.content_type or mimetypes.guess_type(upload.filename or "")[0] or "application/octet-stream",
            size_bytes=len(payload),
            url=url,
        )

    def resolve_local_path(self, asset: StoredAssetModel) -> Path:
        return self.settings.local_storage_path / asset.object_key


class S3StorageService:
    def __init__(self) -> None:
        settings = get_settings()
        if boto3 is None:
            raise RuntimeError("boto3 is required for S3 storage backend")
        self.settings = settings
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.object_storage_endpoint or None,
            aws_access_key_id=settings.object_storage_access_key or None,
            aws_secret_access_key=settings.object_storage_secret_key or None,
            region_name=settings.object_storage_region,
            config=Config(s3={"addressing_style": "path"}) if Config is not None and settings.use_path_style_s3 else None,
        )
        self._ensure_bucket()

    def save_upload(self, owner_type: str, owner_id: str, upload: UploadFile) -> StoredAssetModel:
        extension = Path(upload.filename or "upload.bin").suffix or ".bin"
        object_key = f"{owner_type}/{owner_id}/{uuid4().hex}{extension}"
        payload = upload.file.read()
        self.client.put_object(
            Bucket=self.settings.storage_bucket,
            Key=object_key,
            Body=payload,
            ContentType=upload.content_type or "application/octet-stream",
        )
        url = f"{self.settings.object_storage_endpoint.rstrip('/')}/{self.settings.storage_bucket}/{object_key}"
        return StoredAssetModel(
            owner_type=owner_type,
            owner_id=owner_id,
            bucket=self.settings.storage_bucket,
            object_key=object_key,
            content_type=upload.content_type or "application/octet-stream",
            size_bytes=len(payload),
            url=url,
        )

    def resolve_local_path(self, asset: StoredAssetModel) -> Path:
        target = NamedTemporaryFile(delete=False, suffix=Path(asset.object_key).suffix)
        with target as fp:
            self.client.download_fileobj(asset.bucket, asset.object_key, fp)
        return Path(target.name)

    def _ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.settings.storage_bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.settings.storage_bucket)


def get_storage_service():
    settings = get_settings()
    if settings.storage_backend == "s3":
        return S3StorageService()
    return LocalStorageService()
