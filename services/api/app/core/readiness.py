"""Provider configuration readiness checks.

Mirrors the credential requirements enforced when the real providers are built
(``build_pipeline_service``, ``build_media_provider_bundle``,
``build_speech_assessment_provider``) so misconfiguration surfaces at startup
and via ``/readyz`` instead of only failing later as a per-job ``failed`` state.

Also guards the single most impactful MVP root cause: a non-public
``PUBLIC_BASE_URL`` in production, which makes every generated image/TTS/recording
URL unreachable from real family devices.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from urllib.parse import urlparse

from .settings import Settings


@dataclass(frozen=True)
class ComponentReadiness:
    component: str
    provider: str
    ready: bool
    missing: tuple[str, ...] = ()
    detail: str = ""


def _missing(pairs: dict[str, str]) -> tuple[str, ...]:
    return tuple(name for name, value in pairs.items() if not str(value or "").strip())


def _ai_readiness(s: Settings) -> ComponentReadiness:
    provider = s.ai_provider.lower().strip()
    if provider == "doubao":
        missing = _missing(
            {
                "ARK_API_KEY": s.ark_api_key,
                "DOUBAO_VISION_MODEL_OR_ENDPOINT": s.doubao_vision_model_or_endpoint,
                "DOUBAO_TEXT_MODEL_OR_ENDPOINT": s.doubao_text_model_or_endpoint,
            }
        )
        return ComponentReadiness("ai", provider, not missing, missing)
    if provider in {"qwen", "dashscope", "bailian", "aliyun"}:
        missing = _missing(
            {
                "DASHSCOPE_API_KEY": s.dashscope_api_key,
                "QWEN_VISION_MODEL": s.qwen_vision_model,
                "QWEN_MODEL": s.qwen_model,
            }
        )
        return ComponentReadiness("ai", provider, not missing, missing)
    # stub / unknown -> falls back to the stub pipeline, no credentials required
    return ComponentReadiness(
        "ai", provider or "stub", True, (), "stub pipeline (no provider credentials required)"
    )


def _media_readiness(s: Settings) -> ComponentReadiness:
    provider = s.media_provider.lower().strip()
    if provider == "mock":
        return ComponentReadiness("media", "mock", True, (), "mock media (no provider credentials required)")
    if provider != "real":
        return ComponentReadiness(
            "media", provider or "?", False, (), f"Unsupported MEDIA_PROVIDER: {s.media_provider}"
        )

    image = s.media_image_provider.lower().strip()
    tts = s.media_tts_provider.lower().strip()
    missing: list[str] = []
    for label, sub in (("MEDIA_IMAGE_PROVIDER", image), ("MEDIA_TTS_PROVIDER", tts)):
        if sub == "openai":
            missing += list(_missing({"OPENAI_API_KEY": s.openai_api_key}))
        elif sub == "dashscope":
            missing += list(_missing({"DASHSCOPE_API_KEY": s.dashscope_api_key}))
        else:
            return ComponentReadiness(
                "media",
                f"real/{sub}",
                False,
                (),
                f"Unsupported {label}: {sub or '?'}",
            )
    dedup = tuple(dict.fromkeys(missing))
    return ComponentReadiness("media", f"real(image={image},tts={tts})", not dedup, dedup)


def _speech_readiness(s: Settings) -> ComponentReadiness:
    provider = s.speech_assessment_provider.lower().strip() or s.speech_provider.lower().strip()
    if provider == "stub":
        return ComponentReadiness("speech", "stub", True, (), "stub assessment (no provider credentials required)")
    if provider in {"dashscope", "qwen", "bailian"}:
        missing = _missing({"DASHSCOPE_API_KEY": s.dashscope_api_key})
        return ComponentReadiness("speech", provider, not missing, missing)
    if provider == "aliyun":
        missing = _missing(
            {
                "SPEECH_ASSESSMENT_APP_KEY": s.speech_assessment_app_key,
                "SPEECH_ASSESSMENT_SECRET_KEY": s.speech_assessment_secret_key,
            }
        )
        return ComponentReadiness("speech", provider, not missing, missing)
    return ComponentReadiness("speech", provider or "?", False, (), f"Unsupported speech assessment provider: {provider}")


def _host_is_non_public(host: str) -> bool:
    if not host:
        return True
    host = host.strip().lower()
    if host in {"localhost", "testserver", "host.docker.internal"}:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_unspecified


def _identity_readiness(s: Settings) -> ComponentReadiness:
    provider = s.identity_provider.strip().lower()
    # In production a stub identity provider would accept fabricated WeChat codes
    # and silently collapse families into one account — refuse to boot.
    if s.app_env.strip().lower() == "production" and provider in {"", "dev"}:
        return ComponentReadiness(
            "identity",
            provider or "dev",
            False,
            (),
            "IDENTITY_PROVIDER must not be a dev stub in production "
            "(set IDENTITY_PROVIDER=pilot with PILOT_ALLOWLIST_JSON, or a real provider).",
        )
    if provider == "pilot" and not s.pilot_allowlist:
        return ComponentReadiness(
            "identity",
            "pilot",
            False,
            (),
            "IDENTITY_PROVIDER=pilot requires a non-empty PILOT_ALLOWLIST_JSON.",
        )
    detail = "" if provider else "dev stub (acceptable outside production)"
    return ComponentReadiness("identity", provider or "dev", True, (), detail)


def _public_base_url_readiness(s: Settings) -> ComponentReadiness:
    host = urlparse(s.public_base_url).hostname or ""
    non_public = _host_is_non_public(host)
    # Only a hard failure in production: real family devices cannot reach a
    # loopback/private host, so every media/audio/recording URL would break.
    if s.app_env.strip().lower() == "production" and non_public:
        return ComponentReadiness(
            "public_base_url",
            s.public_base_url,
            False,
            (),
            "PUBLIC_BASE_URL must be a publicly reachable host in production "
            f"(got non-public host '{host or s.public_base_url}'); generated media/audio/recording "
            "URLs would be unreachable from family devices.",
        )
    detail = "non-public host (acceptable outside production)" if non_public else ""
    return ComponentReadiness("public_base_url", s.public_base_url, True, (), detail)


def provider_readiness(settings: Settings) -> list[ComponentReadiness]:
    return [
        _ai_readiness(settings),
        _media_readiness(settings),
        _speech_readiness(settings),
        _identity_readiness(settings),
        _public_base_url_readiness(settings),
    ]


def readiness_report(settings: Settings) -> dict:
    components = provider_readiness(settings)
    return {
        "ready": all(c.ready for c in components),
        "app_env": settings.app_env,
        "components": [
            {
                "component": c.component,
                "provider": c.provider,
                "ready": c.ready,
                "missing": list(c.missing),
                "detail": c.detail,
            }
            for c in components
        ],
    }


def readiness_problem_summary(report: dict) -> str:
    problems = [c for c in report["components"] if not c["ready"]]
    return "; ".join(
        f"{c['component']}({c['provider']}): "
        + (f"missing {', '.join(c['missing'])}" if c["missing"] else c["detail"])
        for c in problems
    )
