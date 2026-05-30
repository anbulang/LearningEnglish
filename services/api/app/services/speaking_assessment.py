from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.parse import quote, urlparse

import httpx

from app.core.settings import get_settings
from app.models.contracts import SpeakingWordFeedback


class SpeechAssessmentError(Exception):
    pass


class SpeechAssessmentConfigurationError(SpeechAssessmentError):
    pass


@dataclass(frozen=True)
class SpeechAssessmentResult:
    transcript: str
    overall_score: float
    pronunciation_score: float
    accuracy_score: float
    fluency_score: float
    completeness_score: float
    feedback: str
    word_feedback: list[SpeakingWordFeedback] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    provider: str = "stub"
    raw_result: dict[str, Any] = field(default_factory=dict)


class SpeechAssessmentProvider(Protocol):
    def assess(
        self,
        *,
        audio_path: Path,
        audio_url: str = "",
        target_text: str,
        prompt_text: str,
        attempt_id: str,
        accent: str,
    ) -> SpeechAssessmentResult:
        ...


class StubSpeechAssessmentProvider:
    def assess(
        self,
        *,
        audio_path: Path,
        audio_url: str = "",
        target_text: str,
        prompt_text: str,
        attempt_id: str,
        accent: str,
    ) -> SpeechAssessmentResult:
        if not audio_path.exists():
            raise SpeechAssessmentError("audio file not found")
        words = [word.strip(".,!?").lower() for word in target_text.split() if word.strip(".,!?")]
        word_feedback = [
            SpeakingWordFeedback(
                word=word,
                score=92 if index % 3 else 78,
                status="good" if index % 3 else "needs_practice",
                tip="读得清楚。" if index % 3 else f"再练一次 {word}。",
            )
            for index, word in enumerate(words)
        ]
        return SpeechAssessmentResult(
            transcript=target_text,
            overall_score=88,
            pronunciation_score=0.88,
            accuracy_score=90,
            fluency_score=84,
            completeness_score=94,
            feedback="整体读得很清楚，个别词可以再慢一点。",
            word_feedback=word_feedback,
            suggestions=[item.tip for item in word_feedback if item.status == "needs_practice"],
            provider="stub",
            raw_result={"attempt_id": attempt_id, "accent": accent, "prompt_text": prompt_text},
        )


class DashScopeSpeechAssessmentProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        compatible_base_url: str,
        asr_model: str,
        scoring_model: str,
        timeout_seconds: int,
        poll_interval_seconds: float = 1.0,
        max_poll_seconds: int = 120,
        trust_env: bool = False,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        if not api_key:
            raise SpeechAssessmentConfigurationError("DashScope speech assessment requires DASHSCOPE_API_KEY")
        if not asr_model or not scoring_model:
            raise SpeechAssessmentConfigurationError("DashScope speech assessment requires ASR and scoring models")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.compatible_base_url = compatible_base_url.rstrip("/")
        self.asr_model = asr_model
        self.scoring_model = scoring_model
        self.poll_interval_seconds = poll_interval_seconds
        self.max_poll_seconds = max_poll_seconds
        self._client = client or httpx.Client(timeout=timeout_seconds, trust_env=trust_env)
        self._owns_client = client is None
        self._sleep = sleep or time.sleep

    def assess(
        self,
        *,
        audio_path: Path,
        audio_url: str = "",
        target_text: str,
        prompt_text: str,
        attempt_id: str,
        accent: str,
    ) -> SpeechAssessmentResult:
        if not audio_path.exists():
            raise SpeechAssessmentError("audio file not found")
        if not _is_public_audio_url(audio_url):
            raise SpeechAssessmentError("DashScope speech assessment requires a public audio URL")

        task_id = self._submit_transcription(audio_url)
        task_output = self._wait_for_transcription(task_id)
        transcription_url = _transcription_result_url(task_output)
        transcription_payload = self._download_transcription(transcription_url)
        transcript = _transcript_text(transcription_payload)
        if not transcript:
            raise SpeechAssessmentError("DashScope transcription result is empty")

        score_payload = self._score_transcript(
            transcript=transcript,
            target_text=target_text,
            prompt_text=prompt_text,
            attempt_id=attempt_id,
            accent=accent,
        )
        return _speech_assessment_result_from_payload(
            score_payload,
            transcript=transcript,
            provider="dashscope",
            raw_result={
                "attempt_id": attempt_id,
                "accent": accent,
                "asr_task_id": task_id,
                "transcription": transcription_payload,
                "score": score_payload,
            },
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _submit_transcription(self, audio_url: str) -> str:
        try:
            response = self._client.post(
                f"{self.base_url}/services/audio/asr/transcription",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "X-DashScope-Async": "enable",
                },
                json={
                    "model": self.asr_model,
                    "input": {"file_urls": [audio_url]},
                    "parameters": {
                        "language_hints": ["zh", "en"],
                        "disfluency_removal_enabled": False,
                    },
                },
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise SpeechAssessmentError("DashScope ASR task creation failed") from exc
        except ValueError as exc:
            raise SpeechAssessmentError("DashScope ASR task creation returned invalid JSON") from exc

        output = payload.get("output") if isinstance(payload, dict) else None
        task_id = output.get("task_id") if isinstance(output, dict) else None
        if not isinstance(task_id, str) or not task_id:
            raise SpeechAssessmentError("DashScope ASR task response missing task_id")
        return task_id

    def _wait_for_transcription(self, task_id: str) -> dict[str, Any]:
        started_at = time.monotonic()
        while True:
            try:
                response = self._client.post(
                    f"{self.base_url}/tasks/{task_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPError as exc:
                raise SpeechAssessmentError("DashScope ASR task polling failed") from exc
            except ValueError as exc:
                raise SpeechAssessmentError("DashScope ASR task polling returned invalid JSON") from exc

            output = payload.get("output") if isinstance(payload, dict) else None
            if not isinstance(output, dict):
                raise SpeechAssessmentError("DashScope ASR task polling response missing output")
            status = output.get("task_status")
            if status == "SUCCEEDED":
                return output
            if status in {"FAILED", "CANCELED", "UNKNOWN"}:
                raise SpeechAssessmentError("DashScope ASR task failed")
            if time.monotonic() - started_at >= self.max_poll_seconds:
                raise SpeechAssessmentError("DashScope ASR task polling timed out")
            self._sleep(self.poll_interval_seconds)

    def _download_transcription(self, transcription_url: str) -> dict[str, Any]:
        try:
            response = self._client.get(transcription_url)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise SpeechAssessmentError("DashScope transcription download failed") from exc
        except ValueError as exc:
            raise SpeechAssessmentError("DashScope transcription download returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise SpeechAssessmentError("DashScope transcription result must be an object")
        return payload

    def _score_transcript(
        self,
        *,
        transcript: str,
        target_text: str,
        prompt_text: str,
        attempt_id: str,
        accent: str,
    ) -> dict[str, Any]:
        prompt = {
            "attempt_id": attempt_id,
            "target_text": target_text,
            "prompt_text": prompt_text,
            "transcript": transcript,
            "accent": accent,
            "output_schema": {
                "overall_score": "0-100 number",
                "pronunciation_score": "0-1 number",
                "accuracy_score": "0-100 number",
                "fluency_score": "0-100 number",
                "completeness_score": "0-100 number",
                "feedback": "short Chinese feedback",
                "word_feedback": [
                    {"word": "English word", "score": "0-100 number", "status": "good|needs_practice", "tip": "Chinese tip"}
                ],
                "suggestions": ["short Chinese suggestion"],
            },
        }
        try:
            response = self._client.post(
                f"{self.compatible_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.scoring_model,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "你是儿童英语跟读评分助手。根据目标文本和 ASR 转写结果给出结构化评分。"
                                "只输出 JSON，不要输出 Markdown。"
                            ),
                        },
                        {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                    ],
                },
            )
            response.raise_for_status()
            root = response.json()
        except httpx.HTTPError as exc:
            raise SpeechAssessmentError("DashScope Qwen speech scoring failed") from exc
        except ValueError as exc:
            raise SpeechAssessmentError("DashScope Qwen speech scoring returned invalid JSON") from exc

        content = _chat_completion_content(root)
        try:
            payload = json.loads(_extract_json_object_text(content))
        except json.JSONDecodeError as exc:
            raise SpeechAssessmentError("DashScope Qwen speech scoring content must be JSON") from exc
        if not isinstance(payload, dict):
            raise SpeechAssessmentError("DashScope Qwen speech scoring payload must be an object")
        return payload


class AliyunSpeechAssessmentProvider:
    def __init__(
        self,
        *,
        app_key: str,
        secret_key: str,
        base_url: str,
        timeout_seconds: int,
        trust_env: bool,
        client: httpx.Client | None = None,
    ) -> None:
        if not app_key or not secret_key:
            raise SpeechAssessmentConfigurationError("Aliyun speech assessment credentials are required")
        self.app_key = app_key
        self.secret_key = secret_key
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout_seconds, trust_env=trust_env)
        self._owns_client = client is None

    def assess(
        self,
        *,
        audio_path: Path,
        audio_url: str = "",
        target_text: str,
        prompt_text: str,
        attempt_id: str,
        accent: str,
    ) -> SpeechAssessmentResult:
        raise SpeechAssessmentConfigurationError(
            "Aliyun speech assessment adapter requires signed request implementation before use"
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


def build_speech_assessment_provider() -> SpeechAssessmentProvider:
    settings = get_settings()
    provider = settings.speech_assessment_provider.lower().strip() or settings.speech_provider.lower().strip()
    if provider == "stub":
        return StubSpeechAssessmentProvider()
    if provider in {"dashscope", "qwen", "bailian"}:
        return DashScopeSpeechAssessmentProvider(
            api_key=settings.dashscope_api_key,
            base_url=settings.speech_assessment_base_url or settings.dashscope_base_url,
            compatible_base_url=settings.dashscope_compatible_base_url,
            asr_model=settings.speech_assessment_asr_model,
            scoring_model=settings.speech_assessment_scoring_model,
            timeout_seconds=settings.speech_assessment_timeout_seconds,
            poll_interval_seconds=settings.speech_assessment_poll_interval_seconds,
            max_poll_seconds=settings.speech_assessment_max_poll_seconds,
            trust_env=settings.speech_assessment_http_trust_env,
        )
    if provider == "aliyun":
        return AliyunSpeechAssessmentProvider(
            app_key=settings.speech_assessment_app_key,
            secret_key=settings.speech_assessment_secret_key,
            base_url=settings.speech_assessment_base_url,
            timeout_seconds=settings.speech_assessment_timeout_seconds,
            trust_env=settings.speech_assessment_http_trust_env,
        )
    raise SpeechAssessmentConfigurationError(f"Unsupported speech assessment provider: {provider}")


def build_speech_assessment_audio_url(*, stored_audio_url: str, object_key: str, public_base_url: str) -> str:
    base_url = public_base_url.strip().rstrip("/")
    if not base_url or not object_key.strip():
        return stored_audio_url
    encoded_key = "/".join(quote(part, safe="") for part in object_key.strip("/").split("/"))
    uploads_prefix = "" if base_url.endswith("/uploads") else "/uploads"
    return f"{base_url}{uploads_prefix}/{encoded_key}"


def _is_public_audio_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"}:
        return False
    hostname = (parsed.hostname or "").lower()
    if not hostname or hostname in {"localhost", "testserver"}:
        return False
    try:
        address = ip_address(hostname)
    except ValueError:
        return "." in hostname
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
    )


def _transcription_result_url(output: dict[str, Any]) -> str:
    results = output.get("results")
    if not isinstance(results, list):
        raise SpeechAssessmentError("DashScope ASR result missing results")
    for item in results:
        if not isinstance(item, dict):
            continue
        if item.get("subtask_status") not in {None, "SUCCEEDED"}:
            continue
        url = item.get("transcription_url")
        if isinstance(url, str) and url.strip():
            return url.strip()
    raise SpeechAssessmentError("DashScope ASR result missing transcription_url")


def _transcript_text(payload: dict[str, Any]) -> str:
    transcripts = payload.get("transcripts")
    if not isinstance(transcripts, list):
        return ""
    parts: list[str] = []
    for transcript in transcripts:
        if not isinstance(transcript, dict):
            continue
        text = transcript.get("text")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    return " ".join(parts).strip()


def _chat_completion_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise SpeechAssessmentError("DashScope Qwen speech scoring missing choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise SpeechAssessmentError("DashScope Qwen speech scoring choice must be an object")
    message = first.get("message")
    if not isinstance(message, dict):
        raise SpeechAssessmentError("DashScope Qwen speech scoring missing message")
    content = message.get("content")
    if isinstance(content, str):
        return content
    raise SpeechAssessmentError("DashScope Qwen speech scoring message content must be text")


def _extract_json_object_text(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = [line for line in stripped.splitlines() if not line.strip().startswith("```")]
        stripped = "\n".join(lines).strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise json.JSONDecodeError("JSON object not found", content, 0)
    return stripped[start : end + 1]


def _speech_assessment_result_from_payload(
    payload: dict[str, Any],
    *,
    transcript: str,
    provider: str,
    raw_result: dict[str, Any],
) -> SpeechAssessmentResult:
    word_feedback = [
        SpeakingWordFeedback(
            word=_clean_text(item.get("word")),
            score=_score_0_to_100(item.get("score")),
            status=_clean_text(item.get("status")) or "needs_practice",
            tip=_clean_text(item.get("tip")),
        )
        for item in payload.get("word_feedback", [])
        if isinstance(item, dict) and _clean_text(item.get("word"))
    ]
    return SpeechAssessmentResult(
        transcript=transcript,
        overall_score=_score_0_to_100(payload.get("overall_score")),
        pronunciation_score=_score_0_to_1(payload.get("pronunciation_score")),
        accuracy_score=_score_0_to_100(payload.get("accuracy_score")),
        fluency_score=_score_0_to_100(payload.get("fluency_score")),
        completeness_score=_score_0_to_100(payload.get("completeness_score")),
        feedback=_clean_text(payload.get("feedback")) or "已完成真实语音转写和评分，请查看逐词反馈。",
        word_feedback=word_feedback,
        suggestions=[_clean_text(item) for item in payload.get("suggestions", []) if _clean_text(item)],
        provider=provider,
        raw_result=raw_result,
    )


def _clean_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _score_0_to_100(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    return max(0.0, min(100.0, number))


def _score_0_to_1(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    if number > 1:
        number = number / 100
    return max(0.0, min(1.0, number))
