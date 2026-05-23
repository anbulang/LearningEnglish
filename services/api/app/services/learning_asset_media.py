from __future__ import annotations

import base64
import binascii
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Protocol

import httpx

from app.core.settings import get_settings
from app.models.contracts import LearningAsset, MediaGenerationStatus, SourceBoundingBox


_REQUIRED_MANIFEST_KEYS = {
    "text",
    "kind",
    "translation",
    "source_page_index",
    "source_bbox",
    "source_visual_description",
    "image",
    "tts_us",
    "tts_uk",
}


@dataclass(frozen=True)
class GeneratedMedia:
    payload: bytes
    content_type: str
    extension: str


@dataclass(frozen=True)
class MediaProviderBundle:
    image_provider: ImageGenerationProvider
    tts_provider: TTSProvider
    mode: str

    def close(self) -> None:
        seen: set[int] = set()
        for provider in (self.image_provider, self.tts_provider):
            provider_id = id(provider)
            if provider_id in seen:
                continue
            seen.add(provider_id)
            close = getattr(provider, "close", None)
            if callable(close):
                close()


class ImageGenerationProvider(Protocol):
    def generate(
        self,
        asset: LearningAsset,
        prompt: str,
        reference_image_path: Optional[Path],
    ) -> GeneratedMedia:
        ...


class TTSProvider(Protocol):
    def synthesize(self, text: str, accent: str) -> GeneratedMedia:
        ...


class MediaProviderError(Exception):
    pass


class MediaProviderConfigurationError(MediaProviderError):
    pass


class OpenAIImageGenerationProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: int = 180,
        trust_env: bool = False,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = client or httpx.Client(timeout=timeout_seconds, trust_env=trust_env)
        self._owns_client = client is None

    def generate(
        self,
        asset: LearningAsset,
        prompt: str,
        reference_image_path: Optional[Path],
    ) -> GeneratedMedia:
        del asset
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            if reference_image_path is None:
                response = self._client.post(
                    f"{self.base_url}/images/generations",
                    headers=headers,
                    json={"model": self.model, "prompt": prompt, "size": "1024x1024"},
                )
            else:
                image_path = Path(reference_image_path)
                with image_path.open("rb") as image_file:
                    response = self._client.post(
                        f"{self.base_url}/images/edits",
                        headers=headers,
                        data={"model": self.model, "prompt": prompt, "size": "1024x1024"},
                        files={"image": (image_path.name, image_file, "image/png")},
                    )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise MediaProviderError("OpenAI image generation failed") from exc
        except (OSError, ValueError) as exc:
            raise MediaProviderError("OpenAI image generation failed") from exc

        try:
            image_b64 = payload["data"][0]["b64_json"]
        except (KeyError, IndexError, TypeError) as exc:
            raise MediaProviderError("OpenAI image response missing data[0].b64_json") from exc
        if not isinstance(image_b64, str):
            raise MediaProviderError("OpenAI image response missing data[0].b64_json")

        try:
            image_payload = base64.b64decode(image_b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise MediaProviderError("OpenAI image response has invalid base64") from exc
        return GeneratedMedia(
            payload=image_payload,
            content_type="image/png",
            extension=".png",
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


class OpenAITTSProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        us_voice: str,
        uk_voice: str,
        timeout_seconds: int = 180,
        trust_env: bool = False,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.us_voice = us_voice
        self.uk_voice = uk_voice
        self._client = client or httpx.Client(timeout=timeout_seconds, trust_env=trust_env)
        self._owns_client = client is None

    def synthesize(self, text: str, accent: str) -> GeneratedMedia:
        accent_key = accent.strip().lower()
        if accent_key not in {"us", "uk"}:
            raise MediaProviderError(f"Unsupported TTS accent: {accent}")
        voice = self.uk_voice if accent_key == "uk" else self.us_voice
        pronunciation = "British English pronunciation" if accent_key == "uk" else "American English pronunciation"
        try:
            response = self._client.post(
                f"{self.base_url}/audio/speech",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "voice": voice,
                    "input": text,
                    "instructions": f"Use clear {pronunciation} for a young English learner.",
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise MediaProviderError("OpenAI TTS generation failed") from exc
        return GeneratedMedia(payload=response.content, content_type="audio/mpeg", extension=".mp3")

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


class HN014MockMediaProvider:
    def __init__(self, public_base_url: str) -> None:
        self.public_base_url = public_base_url.rstrip("/")
        self.root = Path(__file__).resolve().parents[1] / "static" / "mock_media" / "hn014"
        payload = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        assets = payload.get("assets", [])
        if not isinstance(assets, list):
            raise ValueError("HN-014 mock media manifest must contain an assets list")
        for item in assets:
            _validate_manifest_item(item)
        self._by_text = {
            str(item.get("text", "")).strip().lower(): item
            for item in assets
            if str(item.get("text", "")).strip()
        }

    def apply(self, assets: list[LearningAsset]) -> list[LearningAsset]:
        updated: list[LearningAsset] = []
        for asset in assets:
            match = self._by_text.get(asset.text.strip().lower())
            if match is None:
                updated.append(
                    asset.model_copy(
                        update={
                            "generated_image_status": MediaGenerationStatus.failed,
                            "generated_image_error": "HN-014 mock media asset not found",
                            "tts_us_status": MediaGenerationStatus.failed,
                            "tts_us_error": "HN-014 mock media asset not found",
                            "tts_uk_status": MediaGenerationStatus.failed,
                            "tts_uk_error": "HN-014 mock media asset not found",
                        }
                    )
                )
                continue

            image_path = str(match["image"])
            tts_us_path = str(match["tts_us"])
            tts_uk_path = str(match["tts_uk"])
            source_page_index = int(match["source_page_index"])
            updated.append(
                asset.model_copy(
                    update={
                        "translation": asset.translation or match.get("translation", ""),
                        "kind": asset.kind or match.get("kind", "word"),
                        "source_page_index": source_page_index,
                        "source_bbox": asset.source_bbox or _source_bbox_from_manifest(match.get("source_bbox")),
                        "source_visual_description": asset.source_visual_description
                        or match.get("source_visual_description", ""),
                        "generated_image_status": MediaGenerationStatus.ready,
                        "generated_image_url": self._url(image_path),
                        "generated_image_object_key": f"mock_media/hn014/{image_path}",
                        "generated_image_error": "",
                        "tts_us_status": MediaGenerationStatus.ready,
                        "tts_us_url": self._url(tts_us_path),
                        "tts_us_object_key": f"mock_media/hn014/{tts_us_path}",
                        "tts_us_error": "",
                        "tts_uk_status": MediaGenerationStatus.ready,
                        "tts_uk_url": self._url(tts_uk_path),
                        "tts_uk_object_key": f"mock_media/hn014/{tts_uk_path}",
                        "tts_uk_error": "",
                    }
                )
            )
        return updated

    def generate(
        self,
        asset: LearningAsset,
        prompt: str,
        reference_image_path: Optional[Path],
    ) -> GeneratedMedia:
        del asset, prompt, reference_image_path
        return GeneratedMedia(
            payload=b"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1 1'></svg>",
            content_type="image/svg+xml",
            extension=".svg",
        )

    def synthesize(self, text: str, accent: str) -> GeneratedMedia:
        del text, accent
        return GeneratedMedia(payload=b"mock-tts", content_type="audio/mp4", extension=".m4a")

    def _url(self, relative_path: str) -> str:
        return f"{self.public_base_url}/mock-media/hn014/{relative_path}"


def build_media_provider_bundle(public_base_url: Optional[str] = None) -> MediaProviderBundle:
    settings = get_settings()
    explicit_media_provider = os.getenv("MEDIA_PROVIDER")
    media_provider = settings.media_provider.strip().lower()
    if media_provider == "mock" or (settings.app_env.strip().lower() == "testing" and explicit_media_provider is None):
        mock_provider = HN014MockMediaProvider(public_base_url or settings.public_base_url)
        return MediaProviderBundle(image_provider=mock_provider, tts_provider=mock_provider, mode="mock")

    if media_provider != "real":
        raise MediaProviderConfigurationError(f"Unsupported MEDIA_PROVIDER: {settings.media_provider}")
    if settings.media_image_provider.strip().lower() != "openai":
        raise MediaProviderConfigurationError(f"Unsupported MEDIA_IMAGE_PROVIDER: {settings.media_image_provider}")
    if settings.media_tts_provider.strip().lower() != "openai":
        raise MediaProviderConfigurationError(f"Unsupported MEDIA_TTS_PROVIDER: {settings.media_tts_provider}")
    if not settings.openai_api_key:
        raise MediaProviderConfigurationError("OPENAI_API_KEY is required when MEDIA_PROVIDER=real")

    image_provider = OpenAIImageGenerationProvider(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.media_image_model,
        timeout_seconds=settings.media_request_timeout_seconds,
        trust_env=settings.media_http_trust_env,
    )
    tts_provider = OpenAITTSProvider(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.media_tts_model,
        us_voice=settings.media_tts_us_voice,
        uk_voice=settings.media_tts_uk_voice,
        timeout_seconds=settings.media_request_timeout_seconds,
        trust_env=settings.media_http_trust_env,
    )
    return MediaProviderBundle(image_provider=image_provider, tts_provider=tts_provider, mode="real")


def _validate_manifest_item(raw: object) -> None:
    if not isinstance(raw, dict):
        raise ValueError("HN-014 mock media manifest assets must be objects")
    text = str(raw.get("text", "")).strip()
    missing = sorted(key for key in _REQUIRED_MANIFEST_KEYS if key not in raw)
    if missing:
        label = text or "<missing text>"
        raise ValueError(f"HN-014 mock media manifest asset {label} missing keys: {', '.join(missing)}")
    source_page_index = raw.get("source_page_index")
    if not isinstance(source_page_index, int) or source_page_index < 1:
        label = text or "<missing text>"
        raise ValueError(f"HN-014 mock media manifest asset {label} has invalid source_page_index")


def _source_bbox_from_manifest(raw: object) -> Optional[SourceBoundingBox]:
    if not isinstance(raw, dict):
        return None
    values: dict[str, Any] = raw
    return SourceBoundingBox(
        x=float(values.get("x") or 0),
        y=float(values.get("y") or 0),
        width=float(values.get("width") or 1),
        height=float(values.get("height") or 1),
    )
