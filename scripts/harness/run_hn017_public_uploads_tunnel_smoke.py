from __future__ import annotations

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

from app.services.speaking_assessment import DashScopeSpeechAssessmentProvider  # noqa: E402


SAMPLE_AUDIO_URL = (
    "https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav"
)
TUNNEL_URL_PATTERN = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")


def main() -> None:
    evidence_dir = ROOT / "dist" / "harness" / "HN-017"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    api_process: subprocess.Popen[str] | None = None
    tunnel_process: subprocess.Popen[str] | None = None
    tunnel_logs: list[str] = []
    try:
        summary, api_process, tunnel_process = _run_smoke(evidence_dir, started, tunnel_logs)
    except Exception as exc:
        failure = {
            "status": "failed",
            "provider": "dashscope",
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_seconds": round(perf_counter() - started, 3),
        }
        (evidence_dir / "public-uploads-tunnel-smoke-summary.json").write_text(
            json.dumps(failure, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if tunnel_logs:
            (evidence_dir / "public-uploads-tunnel-cloudflared.log").write_text(
                "".join(tunnel_logs),
                encoding="utf-8",
            )
        print(json.dumps(failure, ensure_ascii=False, indent=2))
        raise SystemExit(1) from exc
    finally:
        _terminate(tunnel_process)
        _terminate(api_process)

    (evidence_dir / "public-uploads-tunnel-cloudflared.log").write_text(
        "".join(tunnel_logs),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _run_smoke(evidence_dir: Path, started: float, tunnel_logs: list[str]):
    if not os.environ.get("DASHSCOPE_API_KEY", "").strip():
        raise RuntimeError("DASHSCOPE_API_KEY is required for HN-017 public uploads tunnel smoke")
    cloudflared = shutil.which("cloudflared")
    if not cloudflared:
        raise RuntimeError("cloudflared is required for public uploads tunnel smoke")

    work_dir = Path(tempfile.mkdtemp(prefix="learning-english-hn017-public-uploads-"))
    uploads_root = work_dir / "uploads"
    object_key = "speaking_attempt/attempt_public_uploads/input.wav"
    audio_path = uploads_root / object_key
    audio_path.parent.mkdir(parents=True, exist_ok=True)

    provider_trust_env = os.environ.get("SPEECH_ASSESSMENT_HTTP_TRUST_ENV", "false").lower() == "true"
    tunnel_check_trust_env = os.environ.get("HN017_TUNNEL_HTTP_TRUST_ENV", "true").lower() == "true"
    with httpx.Client(timeout=30, trust_env=provider_trust_env) as client:
        sample_response = client.get(SAMPLE_AUDIO_URL)
        sample_response.raise_for_status()
        audio_path.write_bytes(sample_response.content)

    port = _free_port()
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "testing",
            "DATABASE_URL": f"sqlite:///{work_dir / 'api.db'}",
            "LOCAL_STORAGE_PATH": str(uploads_root),
            "PUBLIC_BASE_URL": f"http://127.0.0.1:{port}",
            "STORAGE_BACKEND": "local",
            "JWT_SECRET": "learning-english-hn017-public-uploads-test-secret",
        }
    )
    api_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(API_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    _wait_for_http(f"http://127.0.0.1:{port}/healthz", timeout_seconds=20, trust_env=False)

    tunnel_process = subprocess.Popen(
        [
            cloudflared,
            "tunnel",
            "--url",
            f"http://127.0.0.1:{port}",
            "--no-autoupdate",
            "--loglevel",
            "info",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    tunnel_base_url = _wait_for_tunnel_ready(tunnel_process, tunnel_logs, timeout_seconds=150)
    _wait_for_public_http(
        f"{tunnel_base_url}/healthz",
        timeout_seconds=120,
        use_system_proxy=tunnel_check_trust_env,
    )
    public_audio_url = f"{tunnel_base_url}/uploads/{object_key}"
    public_audio_bytes = _download_public_url(public_audio_url, use_system_proxy=tunnel_check_trust_env)
    if public_audio_bytes != audio_path.read_bytes():
        raise RuntimeError("public /uploads audio bytes did not match local audio")

    provider = DashScopeSpeechAssessmentProvider(
        api_key=os.environ["DASHSCOPE_API_KEY"].strip(),
        base_url=os.environ.get("SPEECH_ASSESSMENT_BASE_URL", os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/api/v1")),
        compatible_base_url=os.environ.get(
            "DASHSCOPE_COMPATIBLE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        asr_model=os.environ.get("SPEECH_ASSESSMENT_ASR_MODEL", "paraformer-v2"),
        scoring_model=os.environ.get("SPEECH_ASSESSMENT_SCORING_MODEL", os.environ.get("QWEN_MODEL", "qwen-plus")),
        timeout_seconds=int(os.environ.get("SPEECH_ASSESSMENT_TIMEOUT_SECONDS", "120")),
        poll_interval_seconds=float(os.environ.get("SPEECH_ASSESSMENT_POLL_INTERVAL_SECONDS", "1")),
        max_poll_seconds=int(os.environ.get("SPEECH_ASSESSMENT_MAX_POLL_SECONDS", "120")),
        trust_env=provider_trust_env,
    )
    try:
        result = provider.assess(
            audio_path=audio_path,
            audio_url=public_audio_url,
            target_text="Hello world.",
            prompt_text="跟读：Hello world.",
            attempt_id="hn017_public_uploads_tunnel",
            accent="am",
        )
    finally:
        provider.close()

    result_payload = {
        "status": "passed",
        "provider": result.provider,
        "public_base_url": tunnel_base_url,
        "public_audio_url": public_audio_url,
        "object_key": object_key,
        "audio_size_bytes": len(public_audio_bytes),
        "tunnel_http_trust_env": tunnel_check_trust_env,
        "provider_http_trust_env": provider_trust_env,
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
    result_path = evidence_dir / "public-uploads-tunnel-smoke-result.json"
    result_path.write_text(json.dumps(result_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "status": "passed",
        "provider": result.provider,
        "public_base_url": tunnel_base_url,
        "public_audio_url": public_audio_url,
        "object_key": object_key,
        "audio_size_bytes": len(public_audio_bytes),
        "tunnel_http_trust_env": tunnel_check_trust_env,
        "provider_http_trust_env": provider_trust_env,
        "transcript": result.transcript,
        "overall_score": result.overall_score,
        "pronunciation_score": result.pronunciation_score,
        "elapsed_seconds": result_payload["elapsed_seconds"],
        "result_json": str(result_path),
    }
    summary_path = evidence_dir / "public-uploads-tunnel-smoke-summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary, api_process, tunnel_process


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
                response = client.get(url)
                if response.status_code < 500:
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
        completed = subprocess.run(
            ["curl", "-fsSL", "-m", "5", "-o", os.devnull, url],
            capture_output=True,
            text=True,
            check=False,
        )
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
    completed = subprocess.run(
        ["curl", "-fsSL", "-m", "30", url],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        error = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"public URL download failed: {error}")
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
        raise RuntimeError("cloudflared published a trycloudflare URL but did not register a tunnel connection")
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
