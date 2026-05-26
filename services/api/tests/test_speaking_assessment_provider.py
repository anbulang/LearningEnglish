from __future__ import annotations

from pathlib import Path

import pytest

from app.core.settings import get_settings
from app.models.contracts import SpeakingWordFeedback
from app.services.speaking_assessment import (
    SpeechAssessmentConfigurationError,
    StubSpeechAssessmentProvider,
    build_speech_assessment_provider,
)


def test_stub_speech_assessment_scores_target_words(tmp_path: Path) -> None:
    audio_path = tmp_path / "attempt.m4a"
    audio_path.write_bytes(b"fake-audio")
    provider = StubSpeechAssessmentProvider()

    result = provider.assess(
        audio_path=audio_path,
        target_text="A rabbit can hop fast.",
        prompt_text="跟读：A rabbit can hop fast.",
        attempt_id="attempt_test",
        accent="am",
    )

    assert result.provider == "stub"
    assert result.transcript == "A rabbit can hop fast."
    assert result.overall_score >= 80
    assert result.word_feedback
    assert all(isinstance(item, SpeakingWordFeedback) for item in result.word_feedback)


def test_real_speech_provider_requires_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEECH_PROVIDER", "aliyun")
    monkeypatch.delenv("SPEECH_ASSESSMENT_APP_KEY", raising=False)
    monkeypatch.delenv("SPEECH_ASSESSMENT_SECRET_KEY", raising=False)
    get_settings.cache_clear()

    with pytest.raises(SpeechAssessmentConfigurationError):
        build_speech_assessment_provider()

    get_settings.cache_clear()
