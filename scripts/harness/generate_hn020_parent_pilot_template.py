#!/usr/bin/env python3
"""Generate HN-020 parent pilot evidence templates."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_RELATIVE_DIR = Path("dist") / "harness" / "HN-020"
EXPECTED_EVIDENCE = [
    "parent-pilot-notes.md",
    "parent-pilot-upload-screen.png",
    "parent-pilot-ai-review-screen.png",
    "parent-pilot-lesson-detail-screen.png",
    "parent-pilot-review-screen.png",
    "parent-pilot-report-screen.png",
]


def write_template(*, root: Path = ROOT, today: date | None = None, force: bool = False) -> dict:
    current_date = today or date.today()
    evidence_dir = root / EVIDENCE_RELATIVE_DIR
    evidence_dir.mkdir(parents=True, exist_ok=True)
    notes_path = evidence_dir / "parent-pilot-notes.md"
    summary_path = evidence_dir / "parent-pilot-summary.json"

    notes_written = _write_text_if_needed(
        notes_path,
        _build_notes(current_date),
        force=force,
    )
    summary_written = _write_text_if_needed(
        summary_path,
        json.dumps(_build_summary(current_date), ensure_ascii=False, indent=2) + "\n",
        force=force,
    )

    return {
        "schema_version": 1,
        "requirement_id": "HN-020",
        "evidence_dir": evidence_dir.as_posix(),
        "notes_path": notes_path.as_posix(),
        "summary_path": summary_path.as_posix(),
        "notes_written": notes_written,
        "summary_written": summary_written,
    }


def _write_text_if_needed(path: Path, content: str, *, force: bool) -> bool:
    if path.exists() and not force:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def _build_summary(current_date: date) -> dict:
    return {
        "schema_version": 1,
        "requirement_id": "HN-020",
        "status": "template",
        "created_at": current_date.isoformat(),
        "pilot_result": "pending",
        "main_chain": [
            "上传讲义",
            "AI 校对",
            "课程详情",
            "复习",
            "报告",
        ],
        "severity_levels": ["P0", "P1", "P2"],
        "repair_batches": ["Batch 0", "Batch 1", "Batch 2", "Batch 3", "Batch 4"],
        "expected_evidence": EXPECTED_EVIDENCE,
    }


def _build_notes(current_date: date) -> str:
    return f"""# HN-020 家长试用记录

- 日期：{current_date.isoformat()}
- 试用者角色：
- 设备：
- App 包：
- API 地址：
- Provider 配置：
- 讲义素材：

## 总体结论

- 是否完成主链：
- 是否需要开发口头提示：
- 总体分级：passed / blocked / needs-fix

## 分阶段记录

| 阶段 | 结果 | 问题等级 | 现象 | 截图 / 证据 |
| --- | --- | --- | --- | --- |
| 上传讲义 |  | P0/P1/P2 |  | parent-pilot-upload-screen.png |
| AI 校对 |  | P0/P1/P2 |  | parent-pilot-ai-review-screen.png |
| 课程详情 |  | P0/P1/P2 |  | parent-pilot-lesson-detail-screen.png |
| 复习 |  | P0/P1/P2 |  | parent-pilot-review-screen.png |
| 报告 |  | P0/P1/P2 |  | parent-pilot-report-screen.png |

## 待修复问题

| 优先级 | 所属批次 | 问题 | 建议修复方向 |
| --- | --- | --- | --- |
| P0/P1/P2 | Batch 0-4 |  |  |

## 判定说明

- P0：阻断试用，家长无法继续主链。
- P1：严重困惑，主链能继续但家长明显不理解或不信任。
- P2：体验打磨，不阻断但影响试用质量。
- Batch 0-4：对应试用前置、上传与 AI 校对、课程详情与复习、报告可信度、异常与恢复路径。
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate HN-020 parent pilot evidence templates.")
    parser.add_argument("--root", default=str(ROOT), help="Repository root. Defaults to this checkout.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing template files.")
    args = parser.parse_args()

    result = write_template(root=Path(args.root), force=args.force)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
