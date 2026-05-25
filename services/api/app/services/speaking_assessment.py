from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

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
    if provider == "aliyun":
        return AliyunSpeechAssessmentProvider(
            app_key=settings.speech_assessment_app_key,
            secret_key=settings.speech_assessment_secret_key,
            base_url=settings.speech_assessment_base_url,
            timeout_seconds=settings.speech_assessment_timeout_seconds,
            trust_env=settings.speech_assessment_http_trust_env,
        )
    raise SpeechAssessmentConfigurationError(f"Unsupported speech assessment provider: {provider}")
