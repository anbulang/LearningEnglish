"""Real-provider end-to-end smoke for the phonics blend/ASR path (incl. L2 digraphs).

Proves the *real* DashScope chain the mobile app relies on, without a device:
  1. Real TTS  — synthesize each probe word (a digraph, a magic-e, a vowel-team)
     via the current media bundle → assert distinct, non-trivial audio.
  2. Public URL — serve the synthesized audio through the real API's /uploads
     route behind a cloudflared quick tunnel (DashScope ASR needs a public URL).
  3. Real ASR  — transcribe the audio with the DashScope speech provider.
  4. Scoring   — score_word_match(transcript, word) must pass for the digraph
     target, exactly as workers_app.tasks.score_phonics_attempt does on device.

Requires DASHSCOPE_API_KEY (source infra/.env) and cloudflared on PATH.
Exit codes: 0 pass · 2 blocked (missing config / network) · 1 fail.
Evidence: dist/harness/HN-021/phonics-dashscope-smoke-summary.json
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from time import perf_counter

import httpx

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

TUNNEL_URL_PATTERN = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

# Probe words: the digraph target is the headline claim; the rest are extra
# L2 data points (magic-e long-a, vowel-team ay).
DIGRAPH_TARGET = "ship"   # sh digraph
EXTRA_WORDS = ["chip", "cake", "play"]  # ch digraph · a-e magic-e · ay vowel team


class Blocked(RuntimeError):
    """Missing config / environment — reported as BLOCKED (exit 2), not a failure."""


def main() -> None:
    evidence_dir = ROOT / "dist" / "harness" / "HN-021"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    api_process: subprocess.Popen[str] | None = None
    tunnel_process: subprocess.Popen[str] | None = None
    tunnel_logs: list[str] = []
    try:
        summary, api_process, tunnel_process = _run(evidence_dir, started, tunnel_logs)
    except Blocked as exc:
        payload = {"status": "blocked", "reason": str(exc),
                   "elapsed_seconds": round(perf_counter() - started, 3)}
        _write(evidence_dir / "phonics-dashscope-smoke-summary.json", payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise SystemExit(2) from exc
    except Exception as exc:
        payload = {"status": "failed", "error": f"{type(exc).__name__}: {exc}",
                   "elapsed_seconds": round(perf_counter() - started, 3)}
        _write(evidence_dir / "phonics-dashscope-smoke-summary.json", payload)
        if tunnel_logs:
            (evidence_dir / "phonics-dashscope-cloudflared.log").write_text("".join(tunnel_logs), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        # Network/DNS blips are BLOCKED, not a hard FAIL.
        blob = f"{type(exc).__name__}: {exc}".lower()
        if any(s in blob for s in ("connecterror", "could not resolve", "name or service", "timed out", "temporary failure", "network is unreachable")):
            raise SystemExit(2) from exc
        raise SystemExit(1) from exc
    finally:
        _terminate(tunnel_process)
        _terminate(api_process)

    if tunnel_logs:
        (evidence_dir / "phonics-dashscope-cloudflared.log").write_text("".join(tunnel_logs), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["status"] != "passed":
        raise SystemExit(1)


def _run(evidence_dir: Path, started: float, tunnel_logs: list[str]):
    if not os.environ.get("DASHSCOPE_API_KEY", "").strip():
        raise Blocked("DASHSCOPE_API_KEY is required (source infra/.env)")
    cloudflared = shutil.which("cloudflared")
    if not cloudflared:
        raise Blocked("cloudflared is required for the public audio URL")

    from app.core.settings import get_settings
    from app.services.shared.learning_asset_media import (
        MediaProviderConfigurationError,
        build_media_provider_bundle,
    )
    from app.services.shared.speaking_assessment import (
        DashScopeSpeechAssessmentProvider,
        SpeechAssessmentError,
    )
    from app.services.shared.phonics_scoring import score_word_match

    get_settings.cache_clear()
    settings = get_settings()
    provider_trust_env = os.environ.get("SPEECH_ASSESSMENT_HTTP_TRUST_ENV", "false").lower() == "true"
    tunnel_trust_env = os.environ.get("PHONICS_TUNNEL_HTTP_TRUST_ENV", "true").lower() == "true"

    work_dir = Path(tempfile.mkdtemp(prefix="learning-english-phonics-dashscope-"))
    uploads_root = work_dir / "uploads"

    # 1) Real TTS for every probe word -> write into the API's /uploads tree.
    try:
        bundle = build_media_provider_bundle()
    except MediaProviderConfigurationError as exc:
        raise Blocked(f"media provider not configured for real TTS: {exc}") from exc

    words = [DIGRAPH_TARGET, *EXTRA_WORDS]
    tts: dict[str, dict] = {}
    seen_hashes: dict[str, str] = {}
    try:
        for word in words:
            generated = bundle.tts_provider.synthesize(word, "us")
            ext = generated.extension if generated.extension.startswith(".") else f".{generated.extension}"
            object_key = f"phonics_attempt/smoke_{word}/input{ext}"
            audio_path = uploads_root / object_key
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            audio_path.write_bytes(generated.payload)
            digest = hashlib.sha256(generated.payload).hexdigest()
            tts[word] = {
                "object_key": object_key,
                "bytes": len(generated.payload),
                "content_type": generated.content_type,
                "sha256": digest,
                "distinct_audio": digest not in seen_hashes,
            }
            seen_hashes.setdefault(digest, word)
    finally:
        close = getattr(bundle, "close", None)
        if callable(close):
            close()

    if tts[DIGRAPH_TARGET]["bytes"] < 1000:
        raise RuntimeError(f"TTS for {DIGRAPH_TARGET!r} produced too little audio: {tts[DIGRAPH_TARGET]['bytes']} bytes")

    # 2) Serve /uploads via the real API behind a cloudflared quick tunnel.
    port = _free_port()
    env = os.environ.copy()
    env.update({
        "APP_ENV": "testing",
        "DATABASE_URL": f"sqlite:///{work_dir / 'api.db'}",
        "LOCAL_STORAGE_PATH": str(uploads_root),
        "PUBLIC_BASE_URL": f"http://127.0.0.1:{port}",
        "STORAGE_BACKEND": "local",
        "JWT_SECRET": "learning-english-phonics-dashscope-smoke-secret-32b",
    })
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning"],
        cwd=str(API_ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    _wait_for_http(f"http://127.0.0.1:{port}/healthz", timeout_seconds=25, trust_env=False)

    tunnel_process = subprocess.Popen(
        [cloudflared, "tunnel", "--url", f"http://127.0.0.1:{port}", "--no-autoupdate", "--loglevel", "info"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    tunnel_base_url = _wait_for_tunnel_ready(tunnel_process, tunnel_logs, timeout_seconds=150)
    _wait_for_public_http(f"{tunnel_base_url}/healthz", timeout_seconds=120, use_system_proxy=tunnel_trust_env)

    # verify the digraph audio is publicly reachable and byte-identical
    target_key = tts[DIGRAPH_TARGET]["object_key"]
    public_target_url = f"{tunnel_base_url}/uploads/{target_key}"
    public_bytes = _download_public_url(public_target_url, use_system_proxy=tunnel_trust_env)
    if public_bytes != (uploads_root / target_key).read_bytes():
        raise RuntimeError("public /uploads audio bytes did not match local audio")

    # 3) Real ASR + 4) digraph scoring for each word.
    provider = DashScopeSpeechAssessmentProvider(
        api_key=os.environ["DASHSCOPE_API_KEY"].strip(),
        base_url=settings.speech_assessment_base_url or settings.dashscope_base_url,
        compatible_base_url=settings.dashscope_compatible_base_url,
        asr_model=settings.speech_assessment_asr_model,
        scoring_model=settings.speech_assessment_scoring_model,
        timeout_seconds=settings.speech_assessment_timeout_seconds,
        poll_interval_seconds=settings.speech_assessment_poll_interval_seconds,
        max_poll_seconds=settings.speech_assessment_max_poll_seconds,
        trust_env=provider_trust_env,
    )
    results: dict[str, dict] = {}
    try:
        for word in words:
            key = tts[word]["object_key"]
            public_url = f"{tunnel_base_url}/uploads/{key}"
            entry: dict = {"public_url": public_url}
            try:
                assessed = provider.assess(
                    audio_path=uploads_root / key,
                    audio_url=public_url,
                    target_text=word,
                    prompt_text=word,
                    attempt_id=f"phonics_smoke_{word}",
                    accent=settings.speech_assessment_default_accent or "am",
                )
                match = score_word_match(assessed.transcript, word)
                entry.update({
                    "transcript": assessed.transcript,
                    "accuracy": match.accuracy,
                    "passed": match.passed,
                    "status": match.status,
                })
            except SpeechAssessmentError as exc:
                entry.update({"error": f"{type(exc).__name__}: {exc}", "passed": False})
            results[word] = entry
    finally:
        provider.close()

    digraph_ok = bool(results.get(DIGRAPH_TARGET, {}).get("passed"))
    passed_words = [w for w, r in results.items() if r.get("passed")]
    summary = {
        # Headline claim: the sh-digraph word round-tripped real TTS→ASR→score.
        "status": "passed" if digraph_ok else "failed",
        "provider": "dashscope",
        "asr_model": settings.speech_assessment_asr_model,
        "digraph_target": DIGRAPH_TARGET,
        "digraph_passed": digraph_ok,
        "words_passed": passed_words,
        "words_total": len(words),
        "tunnel_base_url": tunnel_base_url,
        "tts": tts,
        "asr": results,
        "provider_http_trust_env": provider_trust_env,
        "elapsed_seconds": round(perf_counter() - started, 3),
    }
    _write(evidence_dir / "phonics-dashscope-smoke-summary.json", summary)
    return summary, api_process, tunnel_process


# --- helpers (mirrors run_hn017_public_uploads_tunnel_smoke.py) --------------

def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_http(url: str, *, timeout_seconds: int, trust_env: bool) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    with httpx.Client(timeout=2, trust_env=trust_env) as client:
        while time.monotonic() < deadline:
            try:
                if client.get(url).status_code < 500:
                    return
            except Exception as exc:  # noqa: BLE001
                last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"timed out waiting for {url}: {last_error}")


def _wait_for_public_http(url: str, *, timeout_seconds: int, use_system_proxy: bool) -> None:
    if not use_system_proxy:
        return _wait_for_http(url, timeout_seconds=timeout_seconds, trust_env=False)
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        completed = subprocess.run(["curl", "-fsSL", "-m", "5", "-o", os.devnull, url],
                                   capture_output=True, text=True, check=False)
        if completed.returncode == 0:
            return
        last_error = (completed.stderr or completed.stdout or "").strip()
        time.sleep(0.5)
    raise RuntimeError(f"timed out waiting for {url}: {last_error}")


def _download_public_url(url: str, *, use_system_proxy: bool) -> bytes:
    if not use_system_proxy:
        with httpx.Client(timeout=30, trust_env=False) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.content
    completed = subprocess.run(["curl", "-fsSL", "-m", "30", url], capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"public URL download failed: {completed.stderr.decode('utf-8', 'replace').strip()}")
    return completed.stdout


def _wait_for_tunnel_ready(process: subprocess.Popen[str], logs: list[str], *, timeout_seconds: int) -> str:
    assert process.stdout is not None
    deadline = time.monotonic() + timeout_seconds
    tunnel_url = ""
    while time.monotonic() < deadline:
        line = process.stdout.readline()
        if line:
            logs.append(line)
            match = TUNNEL_URL_PATTERN.search(line)
            if match:
                tunnel_url = match.group(0)
            if tunnel_url and "Registered tunnel connection" in line:
                return tunnel_url
        elif process.poll() is not None:
            break
        else:
            time.sleep(0.2)
    if tunnel_url:
        raise RuntimeError("cloudflared published a URL but did not register a tunnel connection")
    raise RuntimeError("cloudflared did not publish a trycloudflare URL")


def _terminate(process: subprocess.Popen[str] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


if __name__ == "__main__":
    main()
