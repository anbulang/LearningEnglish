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
    ai_http_trust_env: bool
    media_provider: str
    media_image_provider: str
    media_tts_provider: str
    media_image_model: str
    media_image_edit_model: str
    media_tts_model: str
    media_tts_us_voice: str
    media_tts_uk_voice: str
    media_request_timeout_seconds: int
    media_http_trust_env: bool
    media_provider_poll_interval_seconds: int
    media_provider_max_poll_seconds: int
    speech_provider: str
    speech_assessment_provider: str
    speech_assessment_base_url: str
    speech_assessment_app_key: str
    speech_assessment_secret_key: str
    speech_assessment_timeout_seconds: int
    speech_assessment_http_trust_env: bool
    speech_assessment_default_accent: str
    speaking_audio_max_bytes: int
    openai_api_key: str
    openai_base_url: str
    dashscope_api_key: str
    dashscope_base_url: str
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
        ai_request_timeout_seconds=int(os.getenv("AI_REQUEST_TIMEOUT_SECONDS", "180")),
        ai_max_image_count=int(os.getenv("AI_MAX_IMAGE_COUNT", "5")),
        ai_http_trust_env=os.getenv("AI_HTTP_TRUST_ENV", "false").lower() == "true",
        media_provider=os.getenv("MEDIA_PROVIDER", "mock"),
        media_image_provider=os.getenv("MEDIA_IMAGE_PROVIDER", "openai"),
        media_tts_provider=os.getenv("MEDIA_TTS_PROVIDER", "openai"),
        media_image_model=os.getenv("MEDIA_IMAGE_MODEL", "gpt-image-2"),
        media_image_edit_model=os.getenv("MEDIA_IMAGE_EDIT_MODEL", "wanx2.1-imageedit"),
        media_tts_model=os.getenv("MEDIA_TTS_MODEL", "gpt-4o-mini-tts"),
        media_tts_us_voice=os.getenv("MEDIA_TTS_US_VOICE", "coral"),
        media_tts_uk_voice=os.getenv("MEDIA_TTS_UK_VOICE", "cedar"),
        media_request_timeout_seconds=int(os.getenv("MEDIA_REQUEST_TIMEOUT_SECONDS", "180")),
        media_http_trust_env=os.getenv("MEDIA_HTTP_TRUST_ENV", "false").lower() == "true",
        media_provider_poll_interval_seconds=int(os.getenv("MEDIA_PROVIDER_POLL_INTERVAL_SECONDS", "10")),
        media_provider_max_poll_seconds=int(os.getenv("MEDIA_PROVIDER_MAX_POLL_SECONDS", "180")),
        speech_provider=os.getenv("SPEECH_PROVIDER", "stub"),
        speech_assessment_provider=os.getenv("SPEECH_ASSESSMENT_PROVIDER", os.getenv("SPEECH_PROVIDER", "stub")),
        speech_assessment_base_url=os.getenv("SPEECH_ASSESSMENT_BASE_URL", ""),
        speech_assessment_app_key=os.getenv("SPEECH_ASSESSMENT_APP_KEY", ""),
        speech_assessment_secret_key=os.getenv("SPEECH_ASSESSMENT_SECRET_KEY", ""),
        speech_assessment_timeout_seconds=int(os.getenv("SPEECH_ASSESSMENT_TIMEOUT_SECONDS", "120")),
        speech_assessment_http_trust_env=os.getenv("SPEECH_ASSESSMENT_HTTP_TRUST_ENV", "false").lower() == "true",
        speech_assessment_default_accent=os.getenv("SPEECH_ASSESSMENT_DEFAULT_ACCENT", "am"),
        speaking_audio_max_bytes=int(os.getenv("SPEAKING_AUDIO_MAX_BYTES", str(10 * 1024 * 1024))),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY", ""),
        dashscope_base_url=os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/api/v1"),
        qwen_model=os.getenv("QWEN_MODEL", "qwen-plus"),
        sentry_dsn=os.getenv("SENTRY_DSN", ""),
    )


def ensure_local_paths(settings: Settings) -> None:
    settings.local_storage_path.mkdir(parents=True, exist_ok=True)
    if settings.database_url.startswith("sqlite:///"):
        database_path = Path(settings.database_url.removeprefix("sqlite:///"))
        database_path.parent.mkdir(parents=True, exist_ok=True)
