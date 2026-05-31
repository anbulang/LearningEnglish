#!/usr/bin/env python3
"""Generate a lightweight index for local harness evidence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_NAME = "evidence-index.json"
HARNESS_RELATIVE = Path("dist") / "harness"
EVIDENCE_SUFFIXES = {
    ".json": "json",
    ".log": "log",
    ".png": "screenshot",
    ".jpg": "screenshot",
    ".jpeg": "screenshot",
    ".mp3": "audio",
    ".wav": "audio",
    ".m4a": "audio",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _iter_requirement_dirs(harness_root: Path) -> list[Path]:
    return sorted(
        [path for path in harness_root.iterdir() if path.is_dir() and path.name.startswith("HN-")],
        key=lambda path: path.name,
    )


def _evidence_files(requirement_dir: Path) -> list[Path]:
    return sorted(
        [
            path
            for path in requirement_dir.rglob("*")
            if path.is_file() and path.name != OUTPUT_NAME and path.suffix.lower() in EVIDENCE_SUFFIXES
        ],
        key=lambda path: path.relative_to(requirement_dir).as_posix(),
    )


def _is_summary(path: Path) -> bool:
    name = path.name.lower()
    return path.suffix.lower() == ".json" and "summary" in name


def _file_entry(root: Path, path: Path) -> dict[str, Any]:
    stat = path.stat()
    modified_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    return {
        "path": path.relative_to(root).as_posix(),
        "type": EVIDENCE_SUFFIXES[path.suffix.lower()],
        "size_bytes": stat.st_size,
        "modified_at": modified_at.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "is_summary": _is_summary(path),
    }


def _requirement_entry(root: Path, requirement_dir: Path) -> dict[str, Any]:
    files = [_file_entry(root, path) for path in _evidence_files(requirement_dir)]
    return {
        "id": requirement_dir.name,
        "path": requirement_dir.relative_to(root).as_posix(),
        "has_summary": any(file["is_summary"] for file in files),
        "file_count": len(files),
        "total_size_bytes": sum(int(file["size_bytes"]) for file in files),
        "files": files,
    }


def build_index(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    harness_root = root / HARNESS_RELATIVE
    requirements = []
    if harness_root.exists():
        requirements = [_requirement_entry(root, path) for path in _iter_requirement_dirs(harness_root)]

    return {
        "schema_version": 1,
        "generated_at": _utc_now(),
        "harness_root": HARNESS_RELATIVE.as_posix(),
        "requirements": requirements,
    }


def write_index(root: Path = ROOT) -> Path:
    root = root.resolve()
    output_path = root / HARNESS_RELATIVE / OUTPUT_NAME
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(build_index(root=root), ensure_ascii=False, indent=2) + "\n"
    output_path.write_text(payload, encoding="utf-8")
    return output_path


def main() -> int:
    output_path = write_index()
    print(output_path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
