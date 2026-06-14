#!/usr/bin/env python3
"""HN-020 家长试用前置 preflight。

在组织一轮家长试用之前快速确认环境是否就绪,避免把环境问题误判成产品问题
(对应 docs/harness/hn020-parent-pilot-acceptance.md 的 Batch 0 末项)。

检查项:
- api_reachable(必需):试用设备要连的 API 是否健康可达。
- worker_running(可选):若提供 worker 探测 URL 则探测,否则提示人工确认。
- public_uploads_base_url(提醒):口语录音公网可拉取性;本期口语不计入 HN-020
  通过判定,故仅作提醒而非阻断。
- provider_config(提醒):当前 provider 路径是否已显式声明。

结果写入 dist/harness/HN-020/preflight.json,status 为 `ready` 或 `env_blocked`。
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from ipaddress import ip_address
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_RELATIVE_DIR = Path("dist") / "harness" / "HN-020"
DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/v1"

HttpProbe = Callable[[str], "int | None"]


def http_status_probe(url: str, timeout: float = 5.0) -> int | None:
    """返回 HTTP 状态码;连接失败返回 None。"""
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return response.getcode()
    except urllib.error.HTTPError as error:
        return error.code
    except (urllib.error.URLError, OSError, ValueError):
        return None


def health_url_for(api_base_url: str) -> str:
    """从家长端 API base(通常以 /v1 结尾)推导 /healthz 根路径。"""
    base = api_base_url.strip().rstrip("/")
    if base.endswith("/v1"):
        base = base[: -len("/v1")]
    return base.rstrip("/") + "/healthz"


def is_public_base_url(value: str) -> bool:
    """与后端 speaking_assessment._is_public_audio_url 保持同款判定。"""
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


def run_preflight(
    *,
    api_base_url: str,
    public_uploads_base_url: str | None = None,
    provider_summary: str | None = None,
    worker_probe_url: str | None = None,
    checked_at: str,
    root: Path = ROOT,
    http_probe: HttpProbe = http_status_probe,
    write: bool = True,
) -> dict:
    checks: list[dict] = []

    # api_reachable —— 必需
    health_url = health_url_for(api_base_url)
    code = http_probe(health_url)
    checks.append(
        {
            "name": "api_reachable",
            "required": True,
            "status": "pass" if code == 200 else "fail",
            "target": health_url,
            "detail": (
                f"{health_url} 返回 {code}" if code is not None else f"无法连接 {health_url}"
            ),
        }
    )

    # worker_running —— 可选探测,否则提示人工确认
    if worker_probe_url:
        worker_code = http_probe(worker_probe_url)
        checks.append(
            {
                "name": "worker_running",
                "required": True,
                "status": "pass" if worker_code == 200 else "fail",
                "target": worker_probe_url,
                "detail": (
                    f"{worker_probe_url} 返回 {worker_code}"
                    if worker_code is not None
                    else f"无法连接 {worker_probe_url}"
                ),
            }
        )
    else:
        checks.append(
            {
                "name": "worker_running",
                "required": False,
                "status": "skipped",
                "target": None,
                "detail": "未提供 worker 探测 URL;请人工确认 `make worker-dev` 进程在跑。",
            }
        )

    # public_uploads_base_url —— 提醒(口语不计入 HN-020 通过判定)
    if public_uploads_base_url:
        public_ok = is_public_base_url(public_uploads_base_url)
        checks.append(
            {
                "name": "public_uploads_base_url",
                "required": False,
                "status": "pass" if public_ok else "warn",
                "target": public_uploads_base_url,
                "detail": (
                    "公网可拉取,口语录音链路可用。"
                    if public_ok
                    else "非公网地址(localhost/127.*/192.168.*/testserver 等),口语录音评分会失败;"
                    "本期 HN-020 不计入口语,可忽略,但请知悉。"
                ),
            }
        )
    else:
        checks.append(
            {
                "name": "public_uploads_base_url",
                "required": False,
                "status": "skipped",
                "target": None,
                "detail": "未配置公网 uploads 根;本期 HN-020 不评口语,可忽略。",
            }
        )

    # provider_config —— 提醒
    checks.append(
        {
            "name": "provider_config",
            "required": False,
            "status": "pass" if provider_summary else "warn",
            "target": provider_summary,
            "detail": (
                f"provider 路径已声明:{provider_summary}"
                if provider_summary
                else "未声明 provider 路径;请在 notes 中记录 qwen/stub 等组合,避免事后无法归因。"
            ),
        }
    )

    required_failed = [c for c in checks if c["required"] and c["status"] == "fail"]
    warnings = [c["name"] for c in checks if c["status"] == "warn"]
    status = "env_blocked" if required_failed else "ready"

    result = {
        "schema_version": 1,
        "requirement_id": "HN-020",
        "stage": "preflight",
        "status": status,
        "checked_at": checked_at,
        "api_base_url": api_base_url,
        "checks": checks,
        "warnings": warnings,
        "blocking": [c["name"] for c in required_failed],
    }

    if write:
        evidence_dir = root / EVIDENCE_RELATIVE_DIR
        evidence_dir.mkdir(parents=True, exist_ok=True)
        preflight_path = evidence_dir / "preflight.json"
        preflight_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        result["preflight_path"] = preflight_path.as_posix()

    return result


def _default_provider_summary() -> str | None:
    parts = []
    for key in ("AI_PROVIDER", "MEDIA_PROVIDER", "SPEECH_PROVIDER", "SPEECH_ASSESSMENT_PROVIDER"):
        value = os.getenv(key)
        if value:
            parts.append(f"{key}={value}")
    return ", ".join(parts) if parts else None


def main() -> int:
    parser = argparse.ArgumentParser(description="HN-020 家长试用前置 preflight。")
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("API_BASE_URL", DEFAULT_API_BASE_URL),
        help="试用设备要连的家长端 API base,通常以 /v1 结尾。",
    )
    parser.add_argument(
        "--public-uploads-base-url",
        default=os.getenv("SPEECH_ASSESSMENT_AUDIO_PUBLIC_BASE_URL")
        or os.getenv("PUBLIC_BASE_URL"),
        help="口语录音公网根地址(可选,本期不评口语)。",
    )
    parser.add_argument(
        "--worker-probe-url",
        default=os.getenv("WORKER_PROBE_URL"),
        help="可选的 worker 健康探测 URL;不提供则提示人工确认。",
    )
    parser.add_argument(
        "--provider-summary",
        default=_default_provider_summary(),
        help="当前 provider 路径概要;默认从环境变量拼装。",
    )
    parser.add_argument("--root", default=str(ROOT), help="仓库根。默认本检出。")
    parser.add_argument("--no-write", action="store_true", help="只打印,不写 preflight.json。")
    args = parser.parse_args()

    result = run_preflight(
        api_base_url=args.api_base_url,
        public_uploads_base_url=args.public_uploads_base_url,
        provider_summary=args.provider_summary,
        worker_probe_url=args.worker_probe_url,
        checked_at=datetime.now().isoformat(timespec="seconds"),
        root=Path(args.root),
        write=not args.no_write,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
