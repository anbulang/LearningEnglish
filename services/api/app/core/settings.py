from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    jwt_secret: str
    access_token_minutes: int
    refresh_token_days: int
    bind_token_minutes: int
    otp_expiration_minutes: int
    public_base_url: str
    storage_backend: str
    local_storage_path: Path
    storage_bucket: str
    object_storage_endpoint: str
    object_storage_access_key: str
    object_storage_secret_key: str
    object_storage_region: str
    use_path_style_s3: bool
    wechat_app_id: str
    wechat_app_secret: str
    dashscope_api_key: str
    qwen_model: str
    sentry_dsn: str


@lru_cache
def get_settings() -> Settings:
    root = Path(__file__).resolve().parents[3]
    default_storage = root / "tmp" / "uploads"
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv("DATABASE_URL", f"sqlite:///{root / 'tmp' / 'learning_english.db'}"),
        jwt_secret=os.getenv("JWT_SECRET", "learning-english-dev-secret"),
        access_token_minutes=int(os.getenv("ACCESS_TOKEN_MINUTES", "30")),
        refresh_token_days=int(os.getenv("REFRESH_TOKEN_DAYS", "14")),
        bind_token_minutes=int(os.getenv("BIND_TOKEN_MINUTES", "15")),
        otp_expiration_minutes=int(os.getenv("OTP_EXPIRATION_MINUTES", "10")),
        public_base_url=os.getenv("PUBLIC_BASE_URL", "http://localhost:8000"),
        storage_backend=os.getenv("STORAGE_BACKEND", "local"),
        local_storage_path=Path(os.getenv("LOCAL_STORAGE_PATH", str(default_storage))),
        storage_bucket=os.getenv("OBJECT_STORAGE_BUCKET", "learning-english"),
        object_storage_endpoint=os.getenv("OBJECT_STORAGE_ENDPOINT", ""),
        object_storage_access_key=os.getenv("OBJECT_STORAGE_ACCESS_KEY", ""),
        object_storage_secret_key=os.getenv("OBJECT_STORAGE_SECRET_KEY", ""),
        object_storage_region=os.getenv("OBJECT_STORAGE_REGION", "cn-hangzhou"),
        use_path_style_s3=os.getenv("OBJECT_STORAGE_USE_PATH_STYLE", "true").lower() == "true",
        wechat_app_id=os.getenv("WECHAT_APP_ID", ""),
        wechat_app_secret=os.getenv("WECHAT_APP_SECRET", ""),
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY", ""),
        qwen_model=os.getenv("QWEN_MODEL", "qwen-plus"),
        sentry_dsn=os.getenv("SENTRY_DSN", ""),
    )
