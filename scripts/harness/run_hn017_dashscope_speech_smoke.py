from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.services.speaking_assessment import (  # noqa: E402
    DashScopeSpeechAssessmentProvider,
    SpeechAssessmentError,
)


SAMPLE_AUDIO_URL = (
    "https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav"
)


def main() -> None:
    evidence_dir = ROOT / "dist" / "harness" / "HN-017"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    try:
        result = _run_smoke()
    except Exception as exc:
        failure = {
            "status": "failed",
            "provider": "dashscope",
            "audio_url": SAMPLE_AUDIO_URL,
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_seconds": round(perf_counter() - started, 3),
        }
        (evidence_dir / "dashscope-speech-smoke-summary.json").write_text(
            json.dumps(failure, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(failure, ensure_ascii=False, indent=2))
        raise SystemExit(1) from exc

    payload = {
        "status": "passed",
        "provider": result.provider,
        "audio_url": SAMPLE_AUDIO_URL,
        "transcript": result.transcript,
        "overall_score": result.overall_score,
        "pronunciation_score": result.pronunciation_score,
        "accuracy_score": result.accuracy_score,
        "fluency_score": result.fluency_score,
        "completeness_score": result.completeness_score,
        "feedback": result.feedback,
        "word_feedback": [item.model_dump(mode="json") for item in result.word_feedback],
        "suggestions": result.suggestions,
        "raw_result": result.raw_result,
        "elapsed_seconds": round(perf_counter() - started, 3),
    }
    result_path = evidence_dir / "dashscope-speech-smoke-result.json"
    summary_path = evidence_dir / "dashscope-speech-smoke-summary.json"
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "status": "passed",
        "provider": result.provider,
        "audio_url": SAMPLE_AUDIO_URL,
        "transcript": result.transcript,
        "overall_score": result.overall_score,
        "pronunciation_score": result.pronunciation_score,
        "elapsed_seconds": payload["elapsed_seconds"],
        "result_json": str(result_path),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _run_smoke():
    api_key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise SpeechAssessmentError("DASHSCOPE_API_KEY is required for HN-017 DashScope speech smoke")
    provider = DashScopeSpeechAssessmentProvider(
        api_key=api_key,
        base_url=os.environ.get("SPEECH_ASSESSMENT_BASE_URL", "https://dashscope.aliyuncs.com/api/v1"),
        compatible_base_url=os.environ.get(
            "DASHSCOPE_COMPATIBLE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        asr_model=os.environ.get("SPEECH_ASSESSMENT_ASR_MODEL", "paraformer-v2"),
        scoring_model=os.environ.get("SPEECH_ASSESSMENT_SCORING_MODEL", os.environ.get("QWEN_MODEL", "qwen-plus")),
        timeout_seconds=int(os.environ.get("SPEECH_ASSESSMENT_TIMEOUT_SECONDS", "120")),
        poll_interval_seconds=float(os.environ.get("SPEECH_ASSESSMENT_POLL_INTERVAL_SECONDS", "1")),
        max_poll_seconds=int(os.environ.get("SPEECH_ASSESSMENT_MAX_POLL_SECONDS", "120")),
        trust_env=os.environ.get("SPEECH_ASSESSMENT_HTTP_TRUST_ENV", "false").lower() == "true",
    )
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav") as audio_placeholder:
            audio_placeholder.write(b"public-url-smoke")
            audio_placeholder.flush()
            return provider.assess(
                audio_path=Path(audio_placeholder.name),
                audio_url=SAMPLE_AUDIO_URL,
                target_text="Hello world.",
                prompt_text="跟读：Hello world.",
                attempt_id="hn017_dashscope_smoke",
                accent="am",
            )
    finally:
        provider.close()


if __name__ == "__main__":
    main()
