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
    ai_provider: str
    ark_api_key: str
    ark_base_url: str
    doubao_vision_model_or_endpoint: str
    doubao_text_model_or_endpoint: str
    ai_request_timeout_seconds: int
    ai_max_image_count: int
    dashscope_api_key: str
    qwen_model: str
    sentry_dsn: str


@lru_cache
def get_settings() -> Settings:
    app_file = Path(__file__).resolve()
    service_root = app_file.parents[2]
    project_root = app_file.parents[4] if len(app_file.parents) > 4 else service_root
    default_storage = project_root / "tmp" / "uploads"
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv("DATABASE_URL", f"sqlite:///{service_root / 'tmp' / 'learning_english.db'}"),
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
        ai_provider=os.getenv("AI_PROVIDER", os.getenv("PROVIDER_MODE", "stub")),
        ark_api_key=os.getenv("ARK_API_KEY", ""),
        ark_base_url=os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
        doubao_vision_model_or_endpoint=os.getenv("DOUBAO_VISION_MODEL_OR_ENDPOINT", ""),
        doubao_text_model_or_endpoint=os.getenv("DOUBAO_TEXT_MODEL_OR_ENDPOINT", ""),
        ai_request_timeout_seconds=int(os.getenv("AI_REQUEST_TIMEOUT_SECONDS", "60")),
        ai_max_image_count=int(os.getenv("AI_MAX_IMAGE_COUNT", "5")),
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY", ""),
        qwen_model=os.getenv("QWEN_MODEL", "qwen-plus"),
        sentry_dsn=os.getenv("SENTRY_DSN", ""),
    )


def ensure_local_paths(settings: Settings) -> None:
    settings.local_storage_path.mkdir(parents=True, exist_ok=True)
    if settings.database_url.startswith("sqlite:///"):
        database_path = Path(settings.database_url.removeprefix("sqlite:///"))
        database_path.parent.mkdir(parents=True, exist_ok=True)
