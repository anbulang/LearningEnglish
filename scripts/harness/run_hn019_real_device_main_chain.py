from __future__ import annotations

import json
import os
import re
import select
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[2]
MOBILE_ROOT = ROOT / "apps" / "mobile"
EVIDENCE_DIR = ROOT / "dist" / "harness" / "HN-019"
COMPOSE_FILE = ROOT / "infra" / "docker-compose.yml"
COMPOSE_ENV_FILE = ROOT / "infra" / ".env"
TITLE_PREFIX = "HN-019 Device Main Chain"
POSTGRES_USER = os.environ.get("HN019_POSTGRES_USER", "learning_english")
POSTGRES_DB = os.environ.get("HN019_POSTGRES_DB", "learning_english")


def main() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    context = _read_context()
    summary_path = EVIDENCE_DIR / "real-device-main-chain-summary.json"
    try:
        summary = _run(context=context, started=started)
    except Exception as exc:  # noqa: BLE001
        restore = _safe_restore_normal_app(context)
        summary = {
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_seconds": round(perf_counter() - started, 3),
            "context": _public_context(context),
            "restore_normal_app": restore,
        }
        _write_json(summary_path, summary)
        _capture_logs(EVIDENCE_DIR)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        raise SystemExit(1) from exc
    _write_json(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _run(*, context: dict, started: float) -> dict:
    _wait_for_health(context["api_base_url"], timeout_seconds=20)
    flutter = _run_flutter_harness(context)
    material_id = _flutter_material_id(flutter)
    if not material_id and flutter.get("status") == "failed":
        _capture_logs(EVIDENCE_DIR)
        restore = _restore_normal_app(context)
        return {
            "status": "failed",
            "run_id": context["run_id"],
            "started_at": context["started_at"],
            "elapsed_seconds": round(perf_counter() - started, 3),
            "context": _public_context(context),
            "flutter": flutter,
            "restore_normal_app": restore,
            "failure_hint": "Flutter harness 在创建 material 前失败；请优先查看 flutter log 中的真实错误。",
            "evidence_files": [
                str(EVIDENCE_DIR / "real-device-main-chain-flutter.log"),
                str(EVIDENCE_DIR / "real-device-main-chain-api.log"),
                str(EVIDENCE_DIR / "real-device-main-chain-worker.log"),
            ],
        }
    if not material_id:
        raise RuntimeError(f"Flutter harness did not emit material_id: {flutter}")

    material = _wait_for_material(material_id=material_id, timeout_seconds=30)
    job = _query_job(material["id"])
    media = _query_media_summary(material["id"])

    deadline = time.monotonic() + int(context["backend_timeout_seconds"])
    while time.monotonic() < deadline:
        material = _query_material(material["id"]) or material
        job = _query_job(material["id"]) or job
        media = _query_media_summary(material["id"]) or media
        if material.get("status") == "failed" or job.get("status") == "failed":
            break
        if material.get("status") == "ready" and job.get("status") == "ready" and _media_ready(media):
            break
        time.sleep(5)

    knowledge_pack = _query_knowledge_pack(material["id"])
    review_tasks = _query_review_tasks(material["id"])
    _write_json(EVIDENCE_DIR / "real-device-main-chain-material.json", material)
    _write_json(EVIDENCE_DIR / "real-device-main-chain-job.json", job)
    _write_json(EVIDENCE_DIR / "real-device-main-chain-knowledge-pack.json", knowledge_pack)
    _write_json(EVIDENCE_DIR / "real-device-main-chain-review-tasks.json", review_tasks)
    _write_json(EVIDENCE_DIR / "real-device-main-chain-media-summary.json", media)
    _capture_logs(EVIDENCE_DIR)
    restore = _restore_normal_app(context)

    passed = (
        _flutter_passed(flutter)
        and material.get("status") == "ready"
        and job.get("status") == "ready"
        and int(material.get("image_record_count") or 0) == context["source_image_count"]
        and int(material.get("learning_asset_count") or 0) > 0
        and int(review_tasks.get("count") or 0) > 0
        and _media_ready(media)
    )
    summary = {
        "status": "passed" if passed else "failed",
        "run_id": context["run_id"],
        "started_at": context["started_at"],
        "elapsed_seconds": round(perf_counter() - started, 3),
        "context": _public_context(context),
        "flutter": flutter,
        "restore_normal_app": restore,
        "material": material,
        "job": job,
        "knowledge_pack": knowledge_pack,
        "review_tasks": review_tasks,
        "media": media,
        "evidence_files": [
            str(EVIDENCE_DIR / "real-device-main-chain-flutter.log"),
            str(EVIDENCE_DIR / "real-device-main-chain-material.json"),
            str(EVIDENCE_DIR / "real-device-main-chain-job.json"),
            str(EVIDENCE_DIR / "real-device-main-chain-knowledge-pack.json"),
            str(EVIDENCE_DIR / "real-device-main-chain-review-tasks.json"),
            str(EVIDENCE_DIR / "real-device-main-chain-media-summary.json"),
            str(EVIDENCE_DIR / "real-device-main-chain-api.log"),
            str(EVIDENCE_DIR / "real-device-main-chain-worker.log"),
        ],
    }
    if summary["status"] != "passed":
        summary["failure_hint"] = (
            "请先看 material/job/media 三份 JSON，再看 API/worker 日志定位是上传、确认、媒体生成还是复习/报告链路异常。"
        )
    return summary


def _read_context() -> dict:
    api_base_url = os.environ.get("API_BASE_URL") or os.environ.get("HN019_API_BASE_URL")
    if not api_base_url:
        raise RuntimeError("API_BASE_URL is required, for example http://<LAN_IP>:8000/v1")
    source_image_urls = os.environ.get("SOURCE_IMAGE_URLS") or os.environ.get("HN019_SOURCE_IMAGE_URLS")
    if not source_image_urls:
        raise RuntimeError("SOURCE_IMAGE_URLS is required")
    source_count = len([item for item in source_image_urls.split(",") if item.strip()])
    if source_count == 0:
        raise RuntimeError("SOURCE_IMAGE_URLS must contain at least one image URL")
    return {
        "run_id": datetime.now(timezone.utc).strftime("hn019-%Y%m%dT%H%M%SZ"),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "api_base_url": api_base_url.rstrip("/"),
        "source_image_urls": source_image_urls,
        "source_image_count": source_count,
        "flutter_device_id": os.environ.get("DEVICE_ID", "00008150-00094D0A0A78401C"),
        "devicectl_device_id": os.environ.get("DEVICETL_DEVICE_ID", "19586D29-7FF4-5289-8B83-30AA8C3F273D"),
        "mobile_timeout_seconds": os.environ.get("HN019_MOBILE_TIMEOUT_SECONDS", "420"),
        "backend_timeout_seconds": os.environ.get("HN019_BACKEND_TIMEOUT_SECONDS", "900"),
        "restore_normal_app": os.environ.get("HN019_RESTORE_APP", "1") != "0",
        "restore_ipa_path": os.environ.get(
            "RESTORE_IPA_PATH",
            str(ROOT / "dist" / "ios" / "export" / "learning_english_mobile.ipa"),
        ),
        "bundle_id": os.environ.get("HN019_BUNDLE_ID", "com.anbulang.learningenglish"),
    }


def _public_context(context: dict) -> dict:
    public = dict(context)
    public.pop("source_image_urls", None)
    public["source_image_urls"] = f"{context['source_image_count']} item(s)"
    return public


def _run_flutter_harness(context: dict) -> dict:
    command = [
        "flutter",
        "run",
        "-d",
        context["flutter_device_id"],
        "--profile",
        "-t",
        "tool/harness/real_device_material_main_chain_harness.dart",
        f"--dart-define=API_BASE_URL={context['api_base_url']}",
        f"--dart-define=SOURCE_IMAGE_URLS={context['source_image_urls']}",
    ]
    process = subprocess.Popen(
        command,
        cwd=MOBILE_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    lines = ["$ " + " ".join(_redacted_command(command, context)), ""]
    result: dict | None = None
    deadline = time.monotonic() + int(context["mobile_timeout_seconds"])
    while time.monotonic() < deadline:
        if process.stdout is None:
            break
        ready, _, _ = select.select([process.stdout], [], [], 1)
        if ready:
            line = process.stdout.readline()
            if not line:
                break
            lines.append(line.rstrip("\n"))
            parsed = _parse_flutter_result(line)
            if parsed is not None:
                result = parsed
                break
        if process.poll() is not None:
            break
    timed_out = result is None and process.poll() is None
    if process.poll() is None:
        _terminate_process(process)
    returncode = process.returncode
    if result is None and timed_out:
        result = {"status": "failed", "error": "timed out waiting for HN019_RESULT"}
    elif result is None:
        result = {"status": "failed", "error": "flutter run exited before HN019_RESULT"}
    log = "\n".join(lines)
    (EVIDENCE_DIR / "real-device-main-chain-flutter.log").write_text(
        _sanitize_log(log),
        encoding="utf-8",
    )
    return {
        "returncode": returncode,
        "status": result.get("status"),
        "result": result,
        "timed_out": timed_out,
        "log": str(EVIDENCE_DIR / "real-device-main-chain-flutter.log"),
    }


def _parse_flutter_result(line: str) -> dict | None:
    marker = "HN019_RESULT:"
    if marker not in line:
        return None
    payload = line.split(marker, 1)[1].strip()
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return {"status": "failed", "error": f"invalid HN019_RESULT payload: {payload}"}
    return parsed if isinstance(parsed, dict) else {"status": "failed", "error": "HN019_RESULT was not an object"}


def _flutter_passed(flutter: dict) -> bool:
    result = flutter.get("result")
    if not isinstance(result, dict):
        return False
    return result.get("status") == "passed" and int(result.get("report_asset_count") or 0) > 0


def _flutter_material_id(flutter: dict) -> str:
    result = flutter.get("result")
    if not isinstance(result, dict):
        return ""
    value = result.get("material_id")
    return value if isinstance(value, str) and value else ""


def _redacted_command(command: list[str], context: dict) -> list[str]:
    redacted: list[str] = []
    for item in command:
        if item.startswith("--dart-define=SOURCE_IMAGE_URLS="):
            redacted.append(f"--dart-define=SOURCE_IMAGE_URLS=<redacted:{context['source_image_count']} item(s)>")
        else:
            redacted.append(item)
    return redacted


def _terminate_process(process: subprocess.Popen[str]) -> None:
    process.send_signal(signal.SIGINT)
    try:
        process.wait(timeout=10)
        return
    except subprocess.TimeoutExpired:
        process.terminate()
    try:
        process.wait(timeout=10)
        return
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def _restore_normal_app(context: dict) -> dict:
    if not context["restore_normal_app"]:
        return {"status": "skipped", "reason": "HN019_RESTORE_APP=0"}
    ipa_path = Path(context["restore_ipa_path"])
    if not ipa_path.exists():
        return {"status": "skipped", "reason": f"restore IPA not found: {ipa_path}"}
    install = subprocess.run(
        [
            "xcrun",
            "devicectl",
            "device",
            "install",
            "app",
            "--device",
            context["devicectl_device_id"],
            str(ipa_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    launch = subprocess.run(
        [
            "xcrun",
            "devicectl",
            "device",
            "process",
            "launch",
            "--device",
            context["devicectl_device_id"],
            "--terminate-existing",
            context["bundle_id"],
            "--timeout",
            "60",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    restore_log = "\n".join(
        [
            "$ xcrun devicectl device install app ...",
            install.stdout,
            install.stderr,
            "$ xcrun devicectl device process launch ...",
            launch.stdout,
            launch.stderr,
        ]
    )
    (EVIDENCE_DIR / "real-device-main-chain-restore.log").write_text(
        _sanitize_log(restore_log),
        encoding="utf-8",
    )
    return {
        "status": "passed" if install.returncode == 0 and launch.returncode == 0 else "failed",
        "install_returncode": install.returncode,
        "launch_returncode": launch.returncode,
        "log": str(EVIDENCE_DIR / "real-device-main-chain-restore.log"),
    }


def _safe_restore_normal_app(context: dict) -> dict:
    try:
        return _restore_normal_app(context)
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}


def _wait_for_material(*, material_id: str, timeout_seconds: int) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        material = _query_material(material_id)
        if material and material.get("id") == material_id:
            return material
        time.sleep(2)
    raise RuntimeError(f"timed out waiting for material {material_id}")


def _query_material(material_id: str) -> dict:
    sql = f"""
SELECT row_to_json(t)::text
FROM (
  SELECT
    id,
    child_id,
    title,
    topic,
    status,
    uploaded_at,
    created_at,
    updated_at,
    COALESCE(jsonb_array_length(source_images::jsonb), 0) AS source_image_count,
    COALESCE(jsonb_array_length(source_image_keys::jsonb), 0) AS source_image_key_count,
    COALESCE(jsonb_array_length(image_records::jsonb), 0) AS image_record_count,
    COALESCE(jsonb_array_length(learning_assets::jsonb), 0) AS learning_asset_count,
    COALESCE((learning_assets::jsonb -> 0 ->> 'text'), '') AS first_asset_text
  FROM course_materials
  WHERE id = {_sql_literal(material_id)}
) t;
"""
    return _psql_json(sql)


def _query_job(material_id: str) -> dict:
    sql = f"""
SELECT row_to_json(t)::text
FROM (
  SELECT
    id,
    material_id,
    status,
    confidence_summary,
    warnings,
    started_at,
    finished_at,
    draft_title,
    draft_topic,
    COALESCE(jsonb_array_length(draft_vocabulary::jsonb), 0) AS draft_vocabulary_count,
    COALESCE(jsonb_array_length(draft_sentences::jsonb), 0) AS draft_sentence_count,
    COALESCE(jsonb_array_length(draft_image_records::jsonb), 0) AS draft_image_record_count,
    COALESCE(jsonb_array_length(draft_learning_assets::jsonb), 0) AS draft_learning_asset_count
  FROM material_parse_jobs
  WHERE material_id = {_sql_literal(material_id)}
) t;
"""
    return _psql_json(sql)


def _query_knowledge_pack(material_id: str) -> dict:
    sql = f"""
SELECT row_to_json(t)::text
FROM (
  SELECT
    id,
    material_id,
    topic,
    difficulty_band,
    COALESCE(jsonb_array_length(vocabulary_items::jsonb), 0) AS vocabulary_count,
    COALESCE(jsonb_array_length(sentence_patterns::jsonb), 0) AS sentence_count
  FROM knowledge_packs
  WHERE material_id = {_sql_literal(material_id)}
) t;
"""
    return _psql_json(sql)


def _query_review_tasks(material_id: str) -> dict:
    sql = f"""
SELECT row_to_json(t)::text
FROM (
  SELECT
    (SELECT count(*)::int FROM review_tasks WHERE material_id = {_sql_literal(material_id)}) AS count,
    COALESCE(
      (
        SELECT json_object_agg(status, count)
        FROM (
          SELECT status, count(*)::int AS count
          FROM review_tasks
          WHERE material_id = {_sql_literal(material_id)}
          GROUP BY status
        ) s
      ),
      '{{}}'::json
    ) AS status_counts
) t;
"""
    return _psql_json(sql)


def _query_media_summary(material_id: str) -> dict:
    material_literal = _sql_literal(material_id)
    sql = f"""
WITH assets AS (
  SELECT asset
  FROM course_materials c
  CROSS JOIN LATERAL jsonb_array_elements(c.learning_assets::jsonb) AS asset
  WHERE c.id = {material_literal}
)
SELECT row_to_json(t)::text
FROM (
  SELECT
    (SELECT count(*)::int FROM assets) AS learning_asset_count,
    COALESCE(
      (
        SELECT json_object_agg(status, count)
        FROM (
          SELECT COALESCE(asset ->> 'generated_image_status', 'missing') AS status, count(*)::int AS count
          FROM assets
          GROUP BY 1
        ) s
      ),
      '{{}}'::json
    ) AS generated_image_status_counts,
    COALESCE(
      (
        SELECT json_object_agg(status, count)
        FROM (
          SELECT COALESCE(asset ->> 'tts_us_status', 'missing') AS status, count(*)::int AS count
          FROM assets
          GROUP BY 1
        ) s
      ),
      '{{}}'::json
    ) AS tts_us_status_counts,
    COALESCE(
      (
        SELECT json_object_agg(status, count)
        FROM (
          SELECT COALESCE(asset ->> 'tts_uk_status', 'missing') AS status, count(*)::int AS count
          FROM assets
          GROUP BY 1
        ) s
      ),
      '{{}}'::json
    ) AS tts_uk_status_counts,
    (SELECT count(*)::int FROM stored_assets WHERE owner_id = {material_literal} AND owner_type = 'generated_media')
      AS generated_media_asset_count,
    COALESCE(
      (
        SELECT json_object_agg(owner_type, count)
        FROM (
          SELECT owner_type, count(*)::int AS count
          FROM stored_assets
          WHERE owner_id = {material_literal}
          GROUP BY owner_type
        ) s
      ),
      '{{}}'::json
    ) AS stored_asset_owner_counts,
    COALESCE(
      (SELECT sum(size_bytes)::int FROM stored_assets WHERE owner_id = {material_literal} AND owner_type = 'generated_media'),
      0
    ) AS generated_media_size_bytes
) t;
"""
    return _psql_json(sql)


def _media_ready(media: dict) -> bool:
    total = int(media.get("learning_asset_count") or 0)
    if total <= 0:
        return False
    for key in ("generated_image_status_counts", "tts_us_status_counts", "tts_uk_status_counts"):
        counts = media.get(key) if isinstance(media.get(key), dict) else {}
        if int(counts.get("ready") or 0) != total:
            return False
    return True


def _wait_for_health(api_base_url: str, *, timeout_seconds: int) -> None:
    parsed = urlparse(api_base_url)
    health_url = urlunparse((parsed.scheme, parsed.netloc, "/healthz", "", "", ""))
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with urlopen(health_url, timeout=3) as response:  # noqa: S310
                if response.status < 500:
                    return
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(1)
    raise RuntimeError(f"timed out waiting for {health_url}: {last_error}")


def _psql_json(sql: str) -> dict:
    command = [
        "docker",
        "compose",
        "--env-file",
        str(COMPOSE_ENV_FILE),
        "-f",
        str(COMPOSE_FILE),
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        POSTGRES_USER,
        "-d",
        POSTGRES_DB,
        "-t",
        "-A",
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        sql,
    ]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(_sanitize_log(completed.stderr or completed.stdout))
    for line in reversed(completed.stdout.splitlines()):
        candidate = line.strip()
        if candidate.startswith("{"):
            return json.loads(candidate)
    return {}


def _capture_logs(evidence_dir: Path) -> None:
    for service in ("api", "worker"):
        command = [
            "docker",
            "compose",
            "--env-file",
            str(COMPOSE_ENV_FILE),
            "-f",
            str(COMPOSE_FILE),
            "logs",
            "--no-color",
            "--timestamps",
            "--tail",
            "260",
            service,
        ]
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        log = completed.stdout if completed.returncode == 0 else completed.stderr or completed.stdout
        (evidence_dir / f"real-device-main-chain-{service}.log").write_text(
            _sanitize_log(log),
            encoding="utf-8",
        )


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sanitize_log(text: str) -> str:
    sanitized = re.sub(r"(?i)(Authorization:\s*Bearer\s+)[^\s]+", r"\1<redacted>", text)
    sanitized = re.sub(r"(sk-)[A-Za-z0-9_-]{8,}", r"\1<redacted>", sanitized)
    sanitized = re.sub(
        r"(--dart-define=SOURCE_IMAGE_URLS=)[^\s]+",
        r"\1<redacted>",
        sanitized,
    )
    for key in ("Signature", "OSSAccessKeyId", "Expires", "SecurityToken", "X-Amz-Signature", "X-Amz-Credential"):
        sanitized = re.sub(fr"([?&]{key}=)[^&\s]+", rf"\1<redacted>", sanitized)
    return sanitized


if __name__ == "__main__":
    main()
