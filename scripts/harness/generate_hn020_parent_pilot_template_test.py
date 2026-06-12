#!/usr/bin/env python3
"""Tests for generate_hn020_parent_pilot_template.py."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import generate_hn020_parent_pilot_template as hn020


class GenerateHN020ParentPilotTemplateTests(unittest.TestCase):
    def test_write_template_creates_notes_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            result = hn020.write_template(root=root, today=date(2026, 6, 12))

            evidence_dir = root / "dist/harness/HN-020"
            notes = evidence_dir / "parent-pilot-notes.md"
            summary = evidence_dir / "parent-pilot-summary.json"
            self.assertEqual(result["notes_path"], notes.as_posix())
            self.assertEqual(result["summary_path"], summary.as_posix())
            self.assertTrue(notes.exists())
            self.assertTrue(summary.exists())

            notes_text = notes.read_text(encoding="utf-8")
            for expected in ("上传讲义", "AI 校对", "课程详情", "复习", "报告", "P0/P1/P2", "Batch 0-4"):
                self.assertIn(expected, notes_text)

            summary_json = json.loads(summary.read_text(encoding="utf-8"))
            self.assertEqual(summary_json["schema_version"], 1)
            self.assertEqual(summary_json["requirement_id"], "HN-020")
            self.assertEqual(summary_json["status"], "template")
            self.assertEqual(summary_json["created_at"], "2026-06-12")
            self.assertEqual(
                summary_json["expected_evidence"],
                [
                    "parent-pilot-notes.md",
                    "parent-pilot-upload-screen.png",
                    "parent-pilot-ai-review-screen.png",
                    "parent-pilot-lesson-detail-screen.png",
                    "parent-pilot-review-screen.png",
                    "parent-pilot-report-screen.png",
                ],
            )

    def test_write_template_does_not_overwrite_existing_notes_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            notes = root / "dist/harness/HN-020/parent-pilot-notes.md"
            notes.parent.mkdir(parents=True)
            notes.write_text("existing notes\n", encoding="utf-8")

            result = hn020.write_template(root=root, today=date(2026, 6, 12))

            self.assertFalse(result["notes_written"])
            self.assertEqual(notes.read_text(encoding="utf-8"), "existing notes\n")


if __name__ == "__main__":
    unittest.main()
