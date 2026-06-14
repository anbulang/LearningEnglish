#!/usr/bin/env python3
"""Tests for run_hn020_pilot_preflight.py."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import run_hn020_pilot_preflight as preflight


CHECKED_AT = "2026-06-14T10:00:00"


def _check(result: dict, name: str) -> dict:
    return next(c for c in result["checks"] if c["name"] == name)


class HealthUrlTests(unittest.TestCase):
    def test_strips_v1_suffix(self) -> None:
        self.assertEqual(
            preflight.health_url_for("http://192.0.2.10:8000/v1"),
            "http://192.0.2.10:8000/healthz",
        )

    def test_handles_trailing_slash_and_missing_v1(self) -> None:
        self.assertEqual(
            preflight.health_url_for("http://127.0.0.1:8000/"),
            "http://127.0.0.1:8000/healthz",
        )


class IsPublicBaseUrlTests(unittest.TestCase):
    def test_rejects_private_and_loopback_and_testserver(self) -> None:
        for value in (
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://192.168.2.5:8000",
            "http://testserver",
            "ftp://example.com",
        ):
            self.assertFalse(preflight.is_public_base_url(value), value)

    def test_accepts_public_host(self) -> None:
        self.assertTrue(preflight.is_public_base_url("https://uploads.example.com"))


class RunPreflightTests(unittest.TestCase):
    def test_ready_when_api_healthy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = preflight.run_preflight(
                api_base_url="http://192.0.2.10:8000/v1",
                public_uploads_base_url="https://uploads.example.com",
                provider_summary="AI_PROVIDER=qwen",
                checked_at=CHECKED_AT,
                root=Path(tmpdir),
                http_probe=lambda url: 200,
            )

            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["blocking"], [])
            self.assertEqual(_check(result, "api_reachable")["status"], "pass")
            self.assertEqual(_check(result, "public_uploads_base_url")["status"], "pass")
            self.assertEqual(_check(result, "provider_config")["status"], "pass")
            # worker 未提供探测 URL -> skipped,不阻断
            self.assertEqual(_check(result, "worker_running")["status"], "skipped")

            written = json.loads(
                (Path(tmpdir) / "dist/harness/HN-020/preflight.json").read_text(encoding="utf-8")
            )
            self.assertEqual(written["status"], "ready")

    def test_env_blocked_when_api_unreachable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = preflight.run_preflight(
                api_base_url="http://192.0.2.10:8000/v1",
                checked_at=CHECKED_AT,
                root=Path(tmpdir),
                http_probe=lambda url: None,
            )

            self.assertEqual(result["status"], "env_blocked")
            self.assertIn("api_reachable", result["blocking"])
            self.assertEqual(_check(result, "api_reachable")["status"], "fail")

    def test_non_public_uploads_warns_but_does_not_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = preflight.run_preflight(
                api_base_url="http://192.0.2.10:8000/v1",
                public_uploads_base_url="http://192.168.2.5:8000",
                checked_at=CHECKED_AT,
                root=Path(tmpdir),
                http_probe=lambda url: 200,
            )

            self.assertEqual(result["status"], "ready")
            self.assertEqual(_check(result, "public_uploads_base_url")["status"], "warn")
            self.assertIn("public_uploads_base_url", result["warnings"])

    def test_worker_probe_failure_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = preflight.run_preflight(
                api_base_url="http://192.0.2.10:8000/v1",
                worker_probe_url="http://192.0.2.10:5555/healthz",
                checked_at=CHECKED_AT,
                root=Path(tmpdir),
                http_probe=lambda url: 200 if "8000" in url else None,
            )

            self.assertEqual(result["status"], "env_blocked")
            self.assertIn("worker_running", result["blocking"])


if __name__ == "__main__":
    unittest.main()
