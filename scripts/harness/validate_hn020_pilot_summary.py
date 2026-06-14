#!/usr/bin/env python3
"""HN-020 家长试用证据校验。

在把一轮家长试用归档进 PR 或交接之前,校验 dist/harness/HN-020/ 下的证据是否
已经从模板状态推进到可复查状态,作为硬门槛:

- parent-pilot-summary.json:status 不再是 `template`,pilot_result 已给出明确结论。
- 5 张主链截图齐全(复用 generate 脚本的 EXPECTED_EVIDENCE,避免清单漂移)。
- parent-pilot-notes.md:总体结论关键行已填,不再是空模板。

输出 result 为 `PASS` 或 `INCOMPLETE`,后者附缺失项清单。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import generate_hn020_parent_pilot_template as template


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_RELATIVE_DIR = Path("dist") / "harness" / "HN-020"
ALLOWED_RESULTS = {"passed", "needs-fix", "blocked"}
SCREENSHOTS = [name for name in template.EXPECTED_EVIDENCE if name.endswith(".png")]


def _field_value(notes_text: str, label: str) -> str:
    """取 notes 中某个 `<label>：<value>` 行冒号后的内容(取首个匹配)。"""
    for line in notes_text.splitlines():
        if label in line:
            return line.split(label, 1)[1].strip()
    return ""


def validate_summary(*, root: Path = ROOT) -> dict:
    evidence_dir = root / EVIDENCE_RELATIVE_DIR
    summary_path = evidence_dir / "parent-pilot-summary.json"
    notes_path = evidence_dir / "parent-pilot-notes.md"
    missing: list[str] = []

    # summary.json
    summary: dict = {}
    if not summary_path.exists():
        missing.append("缺少 parent-pilot-summary.json")
    else:
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            missing.append("parent-pilot-summary.json 不是合法 JSON")
        if summary.get("status") == "template":
            missing.append("summary.status 仍为 template(尚未填写试用结果)")
        result_value = summary.get("pilot_result")
        if result_value not in ALLOWED_RESULTS:
            missing.append(
                f"summary.pilot_result 应为 {sorted(ALLOWED_RESULTS)} 之一,当前为 {result_value!r}"
            )

    # notes.md
    if not notes_path.exists():
        missing.append("缺少 parent-pilot-notes.md")
    else:
        notes_text = notes_path.read_text(encoding="utf-8")
        if not _field_value(notes_text, "是否完成主链："):
            missing.append("notes 未填『是否完成主链』")
        grade = _field_value(notes_text, "总体分级：")
        if grade not in ALLOWED_RESULTS:
            missing.append("notes 未确定『总体分级』(应为 passed / needs-fix / blocked 之一)")

    # 主链截图
    for shot in SCREENSHOTS:
        if not (evidence_dir / shot).exists():
            missing.append(f"缺少截图 {shot}")

    result = "PASS" if not missing else "INCOMPLETE"
    return {
        "schema_version": 1,
        "requirement_id": "HN-020",
        "stage": "validate",
        "result": result,
        "evidence_dir": evidence_dir.as_posix(),
        "missing": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="HN-020 家长试用证据校验。")
    parser.add_argument("--root", default=str(ROOT), help="仓库根。默认本检出。")
    args = parser.parse_args()

    result = validate_summary(root=Path(args.root))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
