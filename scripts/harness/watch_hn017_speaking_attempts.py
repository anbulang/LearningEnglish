from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select


ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "services" / "api"
WORKERS_ROOT = ROOT / "services" / "workers"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
if str(WORKERS_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKERS_ROOT))


def main() -> None:
    evidence_dir = ROOT / "dist" / "harness" / "HN-017"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    log_path = evidence_dir / "real-device-speaking-worker.log"
    _write_log(log_path, "watcher started")

    from app.core.db import SessionLocal  # noqa: E402
    from app.db.models import SpeakingAttemptModel  # noqa: E402
    from app.models.contracts import SpeakingAttemptStatus  # noqa: E402
    from app.services.mappers import speaking_attempt_from_model  # noqa: E402
    from workers_app.tasks import score_speaking_attempt  # noqa: E402

    processed: set[str] = set()
    deadline = time.monotonic() + int(os.getenv("HN017_WATCH_SECONDS", "600"))
    while time.monotonic() < deadline:
        with SessionLocal() as db:
            attempts = db.scalars(
                select(SpeakingAttemptModel)
                .where(
                    SpeakingAttemptModel.status.in_(
                        [
                            SpeakingAttemptStatus.recording_uploaded.value,
                            SpeakingAttemptStatus.queued.value,
                        ]
                    )
                )
                .order_by(SpeakingAttemptModel.created_at)
            ).all()
            attempt_ids = [attempt.id for attempt in attempts if attempt.id not in processed]

        for attempt_id in attempt_ids:
            processed.add(attempt_id)
            _write_log(log_path, f"score {attempt_id}")
            _apply_public_audio_url_override(attempt_id, log_path)
            result = score_speaking_attempt(attempt_id)
            _write_log(log_path, f"result {attempt_id}: {result}")
            with SessionLocal() as db:
                attempt = db.get(SpeakingAttemptModel, attempt_id)
                if attempt is not None:
                    payload = speaking_attempt_from_model(attempt).model_dump(mode="json")
                    attempt_path = evidence_dir / "real-device-speaking-attempt.json"
                    attempt_path.write_text(
                        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    summary = {
                        "status": "passed" if payload.get("status") == "scored" else "failed",
                        "source": "physical-device-upload",
                        "public_audio_url_override": os.getenv("HN017_PUBLIC_AUDIO_URL", ""),
                        "attempt_id": attempt_id,
                        "provider": payload.get("provider"),
                        "attempt_status": payload.get("status"),
                        "transcript": payload.get("transcript"),
                        "overall_score": payload.get("overall_score"),
                        "pronunciation_score": payload.get("pronunciation_score"),
                        "captured_at": datetime.now(timezone.utc).isoformat(),
                        "attempt_json": str(attempt_path),
                        "worker_log": str(log_path),
                    }
                    (evidence_dir / "real-device-speaking-summary.json").write_text(
                        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
        time.sleep(2)
    _write_log(log_path, "watcher stopped")


def _write_log(path: Path, message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    with path.open("a", encoding="utf-8") as fp:
        fp.write(f"{timestamp} {message}\n")
    print(message, flush=True)


def _apply_public_audio_url_override(attempt_id: str, log_path: Path) -> None:
    public_audio_url = os.getenv("HN017_PUBLIC_AUDIO_URL", "").strip()
    if not public_audio_url:
        return
    from app.core.db import SessionLocal  # noqa: E402
    from app.db.models import SpeakingAttemptModel  # noqa: E402

    with SessionLocal() as db:
        attempt = db.get(SpeakingAttemptModel, attempt_id)
        if attempt is None:
            return
        attempt.audio_url = public_audio_url
        db.add(attempt)
        db.commit()
    _write_log(log_path, f"public audio url override applied for {attempt_id}")


if __name__ == "__main__":
    main()
