#!/usr/bin/env python3
"""Tests for generate_evidence_index.py."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import generate_evidence_index


class GenerateEvidenceIndexTests(unittest.TestCase):
    def test_build_index_lists_hn_directory_summary_log_and_png_by_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            hn017 = root / "dist/harness/HN-017"
            hn017.mkdir(parents=True)
            (hn017 / "real-device-speaking-summary.json").write_text('{"result":"passed"}\n', encoding="utf-8")
            (hn017 / "real-device-speaking-worker.log").write_text("attempt scored\n", encoding="utf-8")
            (hn017 / "real-device-speaking-result-screen-cropped.png").write_bytes(b"PNG")
            (root / "dist/harness/screens").mkdir(parents=True)
            (root / "dist/harness/screens/report-screen.png").write_text("png", encoding="utf-8")

            index = generate_evidence_index.build_index(root=root)

            self.assertEqual(index["schema_version"], 1)
            self.assertEqual(index["harness_root"], "dist/harness")
            self.assertEqual(len(index["requirements"]), 1)
            requirement = index["requirements"][0]
            self.assertEqual(requirement["id"], "HN-017")
            self.assertEqual(requirement["path"], "dist/harness/HN-017")
            self.assertTrue(requirement["has_summary"])
            self.assertEqual(requirement["file_count"], 3)
            self.assertEqual(
                [item["path"] for item in requirement["files"]],
                [
                    "dist/harness/HN-017/real-device-speaking-result-screen-cropped.png",
                    "dist/harness/HN-017/real-device-speaking-summary.json",
                    "dist/harness/HN-017/real-device-speaking-worker.log",
                ],
            )
            self.assertEqual(
                [item["type"] for item in requirement["files"]],
                ["screenshot", "json", "log"],
            )
            self.assertEqual(
                [item["is_summary"] for item in requirement["files"]],
                [False, True, False],
            )
            self.assertEqual(
                sum(item["size_bytes"] for item in requirement["files"]),
                requirement["total_size_bytes"],
            )

    def test_write_index_creates_valid_json_for_missing_harness_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()

            output = generate_evidence_index.write_index(root=root)

            self.assertEqual(output.relative_to(root).as_posix(), "dist/harness/evidence-index.json")
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["harness_root"], "dist/harness")
            self.assertEqual(payload["requirements"], [])
            self.assertTrue(output.exists())

    def test_ignores_non_hn_harness_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "dist/harness/HN-017").mkdir(parents=True)
            (root / "dist/harness/HN-017/real-device-speaking-summary.json").write_text("{}", encoding="utf-8")
            (root / "dist/harness/screens").mkdir(parents=True)
            (root / "dist/harness/screens/report-screen.png").write_bytes(b"PNG")

            index = generate_evidence_index.build_index(root=root)

            self.assertEqual(
                [requirement["id"] for requirement in index["requirements"]],
                ["HN-017"],
            )
            self.assertNotIn(
                "dist/harness/HN-017/real-device-speaking-summary.json",
                [requirement["path"] for requirement in index["requirements"]],
            )


if __name__ == "__main__":
    unittest.main()
