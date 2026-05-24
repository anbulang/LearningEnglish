from __future__ import annotations

import base64
import binascii
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Protocol

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
                        files={"image[]": (image_path.name, image_file, "image/png")},
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


class DashScopeImageGenerationProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        edit_model: str,
        timeout_seconds: int = 180,
        trust_env: bool = False,
        poll_interval_seconds: int = 10,
        max_poll_seconds: int = 180,
        client: Optional[httpx.Client] = None,
        sleep: Optional[Callable[[float], None]] = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.edit_model = edit_model
        self.poll_interval_seconds = poll_interval_seconds
        self.max_poll_seconds = max_poll_seconds
        self._client = client or httpx.Client(timeout=timeout_seconds, trust_env=trust_env)
        self._owns_client = client is None
        self._sleep = sleep or time.sleep

    def generate(
        self,
        asset: LearningAsset,
        prompt: str,
        reference_image_path: Optional[Path],
    ) -> GeneratedMedia:
        del asset
        task_id = self._create_task(prompt=prompt, reference_image_path=reference_image_path)
        image_url = self._poll_image_url(task_id)
        return self._download_image(image_url)

    def _create_task(self, *, prompt: str, reference_image_path: Optional[Path]) -> str:
        text_prompt = prompt
        if reference_image_path is not None:
            text_prompt = _dashscope_reference_prompt(prompt)
        content: list[dict[str, str]] = [{"text": text_prompt}]
        parameters: dict[str, object] = {
            "prompt_extend": True,
            "watermark": False,
            "max_images": 1,
            "size": "1280*1280",
            "enable_interleave": True,
        }
        if reference_image_path is not None:
            content.append({"image": _image_data_url(reference_image_path)})

        try:
            response = self._client.post(
                f"{self.base_url}/services/aigc/image-generation/generation",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "X-DashScope-Async": "enable",
                },
                json={
                    "model": self.model,
                    "input": {"messages": [{"role": "user", "content": content}]},
                    "parameters": parameters,
                },
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise MediaProviderError("DashScope image task creation failed") from exc
        except (OSError, ValueError) as exc:
            raise MediaProviderError("DashScope image task creation failed") from exc

        try:
            task_id = payload["output"]["task_id"]
        except (KeyError, TypeError) as exc:
            raise MediaProviderError("DashScope image task response missing output.task_id") from exc
        if not isinstance(task_id, str) or not task_id:
            raise MediaProviderError("DashScope image task response missing output.task_id")
        return task_id

    def _poll_image_url(self, task_id: str) -> str:
        started_at = time.monotonic()
        while True:
            output = self._get_task_output(task_id)
            status = output.get("task_status")
            if status == "SUCCEEDED":
                return _dashscope_first_image_url(output)
            if status == "FAILED":
                raise MediaProviderError("DashScope image task failed")
            if time.monotonic() - started_at >= self.max_poll_seconds:
                raise MediaProviderError("DashScope image task polling timed out")
            self._sleep(self.poll_interval_seconds)

    def _get_task_output(self, task_id: str) -> dict[str, Any]:
        try:
            response = self._client.get(
                f"{self.base_url}/tasks/{task_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise MediaProviderError("DashScope image task polling failed") from exc
        except ValueError as exc:
            raise MediaProviderError("DashScope image task polling failed") from exc

        output = payload.get("output") if isinstance(payload, dict) else None
        if not isinstance(output, dict):
            raise MediaProviderError("DashScope image task polling failed")
        return output

    def _download_image(self, image_url: str) -> GeneratedMedia:
        try:
            response = self._client.get(image_url)
            response.raise_for_status()
        except (httpx.HTTPError, httpx.InvalidURL, ValueError) as exc:
            raise MediaProviderError("DashScope image download failed") from exc
        return GeneratedMedia(payload=response.content, content_type="image/png", extension=".png")

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


class DashScopeTTSProvider:
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
        if not voice.strip():
            raise MediaProviderError("DashScope TTS voice is not configured")

        try:
            response = self._client.post(
                f"{self.base_url}/services/audio/tts/SpeechSynthesizer",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": {
                        "text": text,
                        "voice": voice,
                        "format": "mp3",
                        "language_hints": ["en"],
                    },
                },
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            raise MediaProviderError("DashScope TTS generation failed") from exc
        except ValueError as exc:
            raise MediaProviderError("DashScope TTS generation failed") from exc

        audio_url = None
        if isinstance(payload, dict):
            output = payload.get("output")
            if isinstance(output, dict):
                audio = output.get("audio")
                if isinstance(audio, dict):
                    audio_url = audio.get("url")
        if not isinstance(audio_url, str) or not audio_url.strip():
            raise MediaProviderError("DashScope TTS response missing output.audio.url")

        try:
            audio_response = self._client.get(audio_url)
            audio_response.raise_for_status()
        except (httpx.HTTPError, httpx.InvalidURL, ValueError) as exc:
            raise MediaProviderError("DashScope TTS audio download failed") from exc
        return GeneratedMedia(payload=audio_response.content, content_type="audio/mpeg", extension=".mp3")

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
    explicit_media_provider = (os.getenv("MEDIA_PROVIDER") or "").strip()
    media_provider = settings.media_provider.strip().lower()
    if media_provider == "mock" or (settings.app_env.strip().lower() == "testing" and not explicit_media_provider):
        mock_provider = HN014MockMediaProvider(public_base_url or settings.public_base_url)
        return MediaProviderBundle(image_provider=mock_provider, tts_provider=mock_provider, mode="mock")

    if media_provider != "real":
        raise MediaProviderConfigurationError(f"Unsupported MEDIA_PROVIDER: {settings.media_provider}")
    return MediaProviderBundle(
        image_provider=_build_image_provider(settings),
        tts_provider=_build_tts_provider(settings),
        mode="real",
    )


def _build_image_provider(settings: Any) -> ImageGenerationProvider:
    provider = settings.media_image_provider.strip().lower()
    if provider == "openai":
        if not settings.openai_api_key:
            raise MediaProviderConfigurationError("OPENAI_API_KEY is required when MEDIA_PROVIDER=real")
        return OpenAIImageGenerationProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.media_image_model,
            timeout_seconds=settings.media_request_timeout_seconds,
            trust_env=settings.media_http_trust_env,
        )
    if provider == "dashscope":
        if not settings.dashscope_api_key:
            raise MediaProviderConfigurationError("DASHSCOPE_API_KEY is required when MEDIA_IMAGE_PROVIDER=dashscope")
        return DashScopeImageGenerationProvider(
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
            model=settings.media_image_model,
            edit_model=settings.media_image_edit_model,
            timeout_seconds=settings.media_request_timeout_seconds,
            trust_env=settings.media_http_trust_env,
            poll_interval_seconds=settings.media_provider_poll_interval_seconds,
            max_poll_seconds=settings.media_provider_max_poll_seconds,
        )
    raise MediaProviderConfigurationError(f"Unsupported MEDIA_IMAGE_PROVIDER: {settings.media_image_provider}")


def _build_tts_provider(settings: Any) -> TTSProvider:
    provider = settings.media_tts_provider.strip().lower()
    if provider == "openai":
        if not settings.openai_api_key:
            raise MediaProviderConfigurationError("OPENAI_API_KEY is required when MEDIA_PROVIDER=real")
        return OpenAITTSProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.media_tts_model,
            us_voice=settings.media_tts_us_voice,
            uk_voice=settings.media_tts_uk_voice,
            timeout_seconds=settings.media_request_timeout_seconds,
            trust_env=settings.media_http_trust_env,
        )
    if provider == "dashscope":
        if not settings.dashscope_api_key:
            raise MediaProviderConfigurationError("DASHSCOPE_API_KEY is required when MEDIA_TTS_PROVIDER=dashscope")
        return DashScopeTTSProvider(
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
            model=settings.media_tts_model,
            us_voice=settings.media_tts_us_voice,
            uk_voice=settings.media_tts_uk_voice,
            timeout_seconds=settings.media_request_timeout_seconds,
            trust_env=settings.media_http_trust_env,
        )
    raise MediaProviderConfigurationError(f"Unsupported MEDIA_TTS_PROVIDER: {settings.media_tts_provider}")


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


def _image_data_url(path: Path) -> str:
    try:
        image_payload = Path(path).read_bytes()
    except OSError as exc:
        raise MediaProviderError("DashScope image reference file could not be read") from exc
    image_b64 = base64.b64encode(image_payload).decode("ascii")
    return f"data:image/png;base64,{image_b64}"


def _dashscope_reference_prompt(prompt: str) -> str:
    if "参考讲义图片" in prompt and ("彩色教学配图" in prompt or "彩色教学图片" in prompt):
        return prompt
    return f"{prompt}\n\n请参考讲义图片，生成适合儿童英语学习的彩色教学配图。"


def _dashscope_first_image_url(output: dict[str, Any]) -> str:
    choices = output.get("choices")
    if isinstance(choices, list):
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message")
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for item in content:
                if isinstance(item, dict):
                    url = item.get("image")
                    if isinstance(url, str) and url:
                        return url

    results = output.get("results")
    if isinstance(results, list):
        for result in results:
            if isinstance(result, dict):
                url = result.get("url") or result.get("image_url") or result.get("orig_url")
                if isinstance(url, str) and url:
                    return url

    task_results = output.get("task_results")
    if isinstance(task_results, list):
        for result in task_results:
            if isinstance(result, dict):
                url = result.get("url")
                if isinstance(url, str) and url:
                    return url

    image_url = output.get("image_url")
    if isinstance(image_url, str) and image_url:
        return image_url
    raise MediaProviderError("DashScope image task response missing image URL")
