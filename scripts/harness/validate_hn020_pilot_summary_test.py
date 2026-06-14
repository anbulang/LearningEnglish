#!/usr/bin/env python3
"""Tests for validate_hn020_pilot_summary.py."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import generate_hn020_parent_pilot_template as template
import validate_hn020_pilot_summary as validate


def _evidence_dir(root: Path) -> Path:
    return root / "dist/harness/HN-020"


def _write_filled_pilot(root: Path) -> None:
    """写出一份"已完成一轮试用"的证据集。"""
    evidence_dir = _evidence_dir(root)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "schema_version": 1,
        "requirement_id": "HN-020",
        "status": "recorded",
        "created_at": "2026-06-14",
        "pilot_result": "needs-fix",
        "main_chain": ["上传讲义", "AI 校对", "课程详情", "复习", "报告"],
    }
    (evidence_dir / "parent-pilot-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (evidence_dir / "parent-pilot-notes.md").write_text(
        "# HN-020 家长试用记录\n\n"
        "## 总体结论\n\n"
        "- 是否完成主链：是\n"
        "- 总体分级：needs-fix\n",
        encoding="utf-8",
    )
    for shot in validate.SCREENSHOTS:
        (evidence_dir / shot).write_bytes(b"\x89PNG\r\n")


class ValidateSummaryTests(unittest.TestCase):
    def test_fresh_template_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            template.write_template(root=root, today=date(2026, 6, 14))

            result = validate.validate_summary(root=root)

            self.assertEqual(result["result"], "INCOMPLETE")
            joined = " ".join(result["missing"])
            self.assertIn("template", joined)
            self.assertIn("总体分级", joined)
            # 模板未创建任何截图
            self.assertTrue(any("缺少截图" in m for m in result["missing"]))

    def test_filled_pilot_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_filled_pilot(root)

            result = validate.validate_summary(root=root)

            self.assertEqual(result["result"], "PASS", result["missing"])
            self.assertEqual(result["missing"], [])

    def test_missing_one_screenshot_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_filled_pilot(root)
            (_evidence_dir(root) / validate.SCREENSHOTS[0]).unlink()

            result = validate.validate_summary(root=root)

            self.assertEqual(result["result"], "INCOMPLETE")
            self.assertTrue(
                any(validate.SCREENSHOTS[0] in m for m in result["missing"]),
                result["missing"],
            )

    def test_missing_evidence_dir_reports_core_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate.validate_summary(root=Path(tmpdir))

            self.assertEqual(result["result"], "INCOMPLETE")
            joined = " ".join(result["missing"])
            self.assertIn("parent-pilot-summary.json", joined)
            self.assertIn("parent-pilot-notes.md", joined)


if __name__ == "__main__":
    unittest.main()
