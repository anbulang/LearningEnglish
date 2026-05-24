# HN-017 录音上传与 AI 语音评分 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 孩子可以围绕讲义学习资产录音，系统保存音频、异步转写与评分，并在 speaking 结果页和周报中展示结果。

**Architecture:** 采用异步任务链路：移动端录音后 multipart 上传，API 保存音频并创建 `SpeakingAttempt`，worker 调用 `SpeechAssessmentProvider` 写回评分结果，结果页轮询 attempt 状态。默认 provider 为 deterministic stub，真实 provider 通过 `SPEECH_PROVIDER` 和 `SPEECH_ASSESSMENT_*` 配置启用，失败不静默回退 stub。

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Celery, local/S3-compatible storage, pytest, Flutter, Riverpod, Dio, `record: ^6.2.1`, `path_provider: ^2.1.5`.

---

## File Structure

- Modify: `services/api/app/models/contracts.py`
  - 扩展 `SpeakingAttempt`、新增 `SpeakingWordFeedback`、新增 multipart 创建响应需要的字段。
- Modify: `services/api/app/db/models.py`
  - 扩展 `SpeakingAttemptModel`，保存音频 object key、目标文本、维度分、逐词反馈、provider、失败原因和更新时间。
- Create: `services/api/alembic/versions/20260525_0004_extend_speaking_attempts.py`
  - 为现有 speaking 表补列。
- Modify: `services/api/app/services/mappers.py`
  - 映射扩展后的 speaking attempt。
- Create: `services/api/app/services/speaking_assessment.py`
  - 定义 `SpeechAssessmentProvider`、`SpeechAssessmentResult`、stub provider、provider factory 和错误类型。
- Create: `services/api/app/services/speaking_queue.py`
  - API 层入队 `speaking.score_attempt`。
- Modify: `services/api/app/api/routes/speaking_attempts.py`
  - multipart 上传、attempt 详情、retry、权限过滤和 archived material 防御。
- Modify: `services/api/app/core/settings.py`
  - 增加 `SPEECH_PROVIDER`、`SPEECH_ASSESSMENT_*` 配置。
- Modify: `services/workers/workers_app/tasks.py`
  - 注册 `speaking.score_attempt` worker task。
- Modify: `services/workers/tests/test_material_job_task.py`
  - 保留现有 worker 注册测试，并增加 speaking task 注册或新测试文件。
- Create: `services/api/tests/test_speaking_attempts.py`
  - API 上传、详情、retry、权限和状态测试。
- Create: `services/api/tests/test_speaking_assessment_provider.py`
  - provider factory、stub 评分、错误脱敏测试。
- Create: `services/workers/tests/test_speaking_attempt_task.py`
  - worker 成功、失败、archived material 跳过、周报累计测试。
- Modify: `packages/contracts/lib/src/models.dart`
  - 扩展 `SpeakingAttempt` 和逐词反馈模型。
- Modify: `packages/contracts/lib/src/enums.dart`
  - 只在需要时扩展 enum；当前 `SpeakingAttemptStatus` 已足够。
- Modify: `apps/mobile/pubspec.yaml`
  - 增加 `record` 和 `path_provider`。
- Modify: `apps/mobile/ios/Runner/Info.plist`
  - 增加 `NSMicrophoneUsageDescription`。
- Modify: `apps/mobile/ios/Runner/Runner.entitlements` only if current iOS build requires microphone entitlement; otherwise do not create one.
- Modify: `apps/mobile/android/app/src/main/AndroidManifest.xml`
  - 增加 `android.permission.RECORD_AUDIO`。
- Modify: `apps/mobile/lib/features/materials/data/app_repository.dart`
  - 增加 multipart speaking upload、attempt detail、retry 方法。
- Modify: `apps/mobile/lib/features/speaking/presentation/speaking_partner_screen.dart`
  - 替换 stub 按钮为录音、上传、轮询和结果展示。
- Create: `apps/mobile/lib/features/speaking/data/speaking_recorder_controller.dart`
  - 封装录音权限、开始、停止、临时文件路径和状态。
- Create: `apps/mobile/test/features/speaking/presentation/speaking_partner_screen_test.dart`
  - 覆盖录音状态、上传后处理中、成功结果、失败重试。
- Modify: `docs/harness/upload-recognition-loop.md`
  - 增加 HN-017 需求和证据目录。
- Modify: `docs/harness/mvp-readiness-checklist.md`
  - 增加 HN-017 readiness 未完成项。
- Modify: `docs/project/2026-05-25-status-and-todo.md`
  - 更新项目状态和 ToDo；如果保留旧日期文件，先重命名最新状态快照。

## Task 1: 合同、数据库模型和迁移

**Files:**
- Modify: `services/api/app/models/contracts.py`
- Modify: `services/api/app/db/models.py`
- Modify: `services/api/app/services/mappers.py`
- Create: `services/api/alembic/versions/20260525_0004_extend_speaking_attempts.py`
- Modify: `packages/contracts/lib/src/models.dart`
- Test: `services/api/tests/test_speaking_attempts.py`

- [ ] **Step 1: 写失败的 Python 合同测试**

Create `services/api/tests/test_speaking_attempts.py`:

```python
from __future__ import annotations

from app.models.contracts import SpeakingAttempt, SpeakingAttemptStatus, SpeakingWordFeedback


def test_speaking_attempt_contract_includes_scoring_details() -> None:
    attempt = SpeakingAttempt(
        id="attempt_test",
        child_id="child_test",
        material_id="material_test",
        review_task_id="task_test",
        learning_asset_id="asset_test",
        prompt_text="跟读：A rabbit can hop fast.",
        target_text="A rabbit can hop fast.",
        audio_url="http://testserver/uploads/speaking_attempt/attempt_test/input.m4a",
        audio_object_key="speaking_attempt/attempt_test/input.m4a",
        audio_content_type="audio/mp4",
        audio_size_bytes=1024,
        audio_duration_ms=3200,
        transcript="A rabbit can hop fast.",
        pronunciation_score=0.86,
        overall_score=88,
        accuracy_score=91,
        fluency_score=82,
        completeness_score=95,
        feedback="整体读得很清楚。",
        word_feedback=[
            SpeakingWordFeedback(word="rabbit", score=92, status="good", tip="读得清楚。"),
            SpeakingWordFeedback(word="hop", score=74, status="needs_practice", tip="注意 h 的轻出气。"),
        ],
        suggestions=["再跟读一次 hop。"],
        provider="stub",
        raw_result={"source": "test"},
        failure_reason="",
        status=SpeakingAttemptStatus.scored,
    )

    payload = attempt.model_dump(mode="json")

    assert payload["target_text"] == "A rabbit can hop fast."
    assert payload["overall_score"] == 88
    assert payload["word_feedback"][1]["status"] == "needs_practice"
    assert payload["audio_object_key"] == "speaking_attempt/attempt_test/input.m4a"
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_speaking_attempts.py::test_speaking_attempt_contract_includes_scoring_details -q
```

Expected:

```text
FAILED with ImportError or ValidationError because SpeakingWordFeedback and new SpeakingAttempt fields do not exist yet
```

- [ ] **Step 3: 扩展 Python 合同**

Modify `services/api/app/models/contracts.py` near `SpeakingAttempt`:

```python
class SpeakingWordFeedback(BaseModel):
    word: str
    score: float = 0
    status: str = "ok"
    tip: str = ""


class SpeakingAttempt(BaseModel):
    id: str
    child_id: str
    material_id: str
    review_task_id: str = ""
    learning_asset_id: str = ""
    prompt_text: str
    target_text: str = ""
    audio_url: str = ""
    audio_object_key: str = ""
    audio_content_type: str = ""
    audio_size_bytes: int = 0
    audio_duration_ms: int = 0
    transcript: str = ""
    pronunciation_score: Optional[float] = None
    overall_score: Optional[float] = None
    accuracy_score: Optional[float] = None
    fluency_score: Optional[float] = None
    completeness_score: Optional[float] = None
    feedback: str = ""
    word_feedback: list[SpeakingWordFeedback] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    provider: str = ""
    raw_result: dict[str, Any] = Field(default_factory=dict)
    failure_reason: str = ""
    status: SpeakingAttemptStatus
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

Keep `SpeakingAttemptCreate` temporarily for old test compile compatibility, but stop using it from the route after Task 2.

- [ ] **Step 4: 扩展 SQLAlchemy model**

Modify `services/api/app/db/models.py` `SpeakingAttemptModel`:

```python
    review_task_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    learning_asset_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    target_text: Mapped[str] = mapped_column(Text, default="")
    audio_object_key: Mapped[str] = mapped_column(Text, default="")
    audio_content_type: Mapped[str] = mapped_column(String(255), default="")
    audio_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    audio_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    accuracy_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fluency_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    completeness_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    word_feedback: Mapped[list[dict]] = mapped_column(JSON, default=list)
    suggestions: Mapped[list[str]] = mapped_column(JSON, default=list)
    provider: Mapped[str] = mapped_column(String(64), default="")
    raw_result: Mapped[dict] = mapped_column(JSON, default=dict)
    failure_reason: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
```

- [ ] **Step 5: 添加 Alembic migration**

Create `services/api/alembic/versions/20260525_0004_extend_speaking_attempts.py`:

```python
"""extend speaking attempts

Revision ID: 20260525_0004
Revises: 20260512_0003
Create Date: 2026-05-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260525_0004"
down_revision = "20260512_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("speaking_attempts", sa.Column("review_task_id", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("speaking_attempts", sa.Column("learning_asset_id", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("speaking_attempts", sa.Column("target_text", sa.Text(), nullable=False, server_default=""))
    op.add_column("speaking_attempts", sa.Column("audio_object_key", sa.Text(), nullable=False, server_default=""))
    op.add_column("speaking_attempts", sa.Column("audio_content_type", sa.String(length=255), nullable=False, server_default=""))
    op.add_column("speaking_attempts", sa.Column("audio_size_bytes", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("speaking_attempts", sa.Column("audio_duration_ms", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("speaking_attempts", sa.Column("overall_score", sa.Float(), nullable=True))
    op.add_column("speaking_attempts", sa.Column("accuracy_score", sa.Float(), nullable=True))
    op.add_column("speaking_attempts", sa.Column("fluency_score", sa.Float(), nullable=True))
    op.add_column("speaking_attempts", sa.Column("completeness_score", sa.Float(), nullable=True))
    op.add_column("speaking_attempts", sa.Column("word_feedback", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("speaking_attempts", sa.Column("suggestions", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("speaking_attempts", sa.Column("provider", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("speaking_attempts", sa.Column("raw_result", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("speaking_attempts", sa.Column("failure_reason", sa.Text(), nullable=False, server_default=""))
    op.add_column("speaking_attempts", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_speaking_attempts_review_task_id", "speaking_attempts", ["review_task_id"])
    op.create_index("ix_speaking_attempts_learning_asset_id", "speaking_attempts", ["learning_asset_id"])


def downgrade() -> None:
    op.drop_index("ix_speaking_attempts_learning_asset_id", table_name="speaking_attempts")
    op.drop_index("ix_speaking_attempts_review_task_id", table_name="speaking_attempts")
    op.drop_column("speaking_attempts", "updated_at")
    op.drop_column("speaking_attempts", "failure_reason")
    op.drop_column("speaking_attempts", "raw_result")
    op.drop_column("speaking_attempts", "provider")
    op.drop_column("speaking_attempts", "suggestions")
    op.drop_column("speaking_attempts", "word_feedback")
    op.drop_column("speaking_attempts", "completeness_score")
    op.drop_column("speaking_attempts", "fluency_score")
    op.drop_column("speaking_attempts", "accuracy_score")
    op.drop_column("speaking_attempts", "overall_score")
    op.drop_column("speaking_attempts", "audio_duration_ms")
    op.drop_column("speaking_attempts", "audio_size_bytes")
    op.drop_column("speaking_attempts", "audio_content_type")
    op.drop_column("speaking_attempts", "audio_object_key")
    op.drop_column("speaking_attempts", "target_text")
    op.drop_column("speaking_attempts", "learning_asset_id")
    op.drop_column("speaking_attempts", "review_task_id")
```

- [ ] **Step 6: 更新 mapper**

Modify `speaking_attempt_from_model()` in `services/api/app/services/mappers.py`:

```python
def speaking_attempt_from_model(model: SpeakingAttemptModel) -> SpeakingAttempt:
    return SpeakingAttempt(
        id=model.id,
        child_id=model.child_id,
        material_id=model.material_id,
        review_task_id=model.review_task_id or "",
        learning_asset_id=model.learning_asset_id or "",
        prompt_text=model.prompt_text,
        target_text=model.target_text or "",
        audio_url=model.audio_url,
        audio_object_key=model.audio_object_key or "",
        audio_content_type=model.audio_content_type or "",
        audio_size_bytes=model.audio_size_bytes or 0,
        audio_duration_ms=model.audio_duration_ms or 0,
        transcript=model.transcript,
        pronunciation_score=model.pronunciation_score,
        overall_score=model.overall_score,
        accuracy_score=model.accuracy_score,
        fluency_score=model.fluency_score,
        completeness_score=model.completeness_score,
        feedback=model.feedback,
        word_feedback=model.word_feedback or [],
        suggestions=model.suggestions or [],
        provider=model.provider or "",
        raw_result=model.raw_result or {},
        failure_reason=model.failure_reason or "",
        status=SpeakingAttemptStatus(model.status),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
```

- [ ] **Step 7: 更新 Dart 合同**

Modify `packages/contracts/lib/src/models.dart` by adding:

```dart
@immutable
class SpeakingWordFeedback {
  const SpeakingWordFeedback({
    required this.word,
    required this.score,
    required this.status,
    required this.tip,
  });

  final String word;
  final double score;
  final String status;
  final String tip;

  factory SpeakingWordFeedback.fromJson(JsonMap json) {
    return SpeakingWordFeedback(
      word: json['word'] as String? ?? '',
      score: doubleFromJson(json['score']) ?? 0,
      status: json['status'] as String? ?? 'ok',
      tip: json['tip'] as String? ?? '',
    );
  }

  JsonMap toJson() => {
        'word': word,
        'score': score,
        'status': status,
        'tip': tip,
      };
}
```

Then extend `SpeakingAttempt` with the same fields as Python. Keep defaults in `fromJson()` so older fixture payloads still parse.

- [ ] **Step 8: Run focused tests**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_speaking_attempts.py::test_speaking_attempt_contract_includes_scoring_details -q
cd apps/mobile && flutter test test/features/materials/data/app_repository_test.dart
```

Expected:

```text
Python focused test passes.
Existing Flutter repository tests still compile and pass.
```

- [ ] **Step 9: Commit**

```bash
git add services/api/app/models/contracts.py services/api/app/db/models.py services/api/app/services/mappers.py services/api/alembic/versions/20260525_0004_extend_speaking_attempts.py packages/contracts/lib/src/models.dart services/api/tests/test_speaking_attempts.py
git commit -m "feat: extend speaking attempt contract"
```

## Task 2: 录音上传 API、storage 和入队

**Files:**
- Modify: `services/api/app/api/routes/speaking_attempts.py`
- Create: `services/api/app/services/speaking_queue.py`
- Modify: `services/api/app/core/settings.py`
- Test: `services/api/tests/test_speaking_attempts.py`

- [ ] **Step 1: 写上传 API 失败测试**

Append to `services/api/tests/test_speaking_attempts.py`:

```python
from datetime import date, datetime, timezone

from app.core.db import SessionLocal
from app.db.models import ChildProfileModel, CourseMaterialModel, ParentAccountModel, StoredAssetModel
from app.models.contracts import MaterialStatus
from conftest import auth_headers, configure_test_environment


configure_test_environment("learning-english-speaking-")


def _create_child_and_material(api_client, headers: dict[str, str]) -> tuple[str, str]:
    child_response = api_client.post(
        "/v1/children",
        json={
            "name": "Mia",
            "age": 6,
            "level": "starter",
            "learning_goal": "课后复习更稳定",
            "preferred_review_duration_minutes": 10,
            "parent_notes": "",
        },
        headers=headers,
    )
    assert child_response.status_code == 201
    child_id = child_response.json()["id"]
    with SessionLocal() as db:
        material = CourseMaterialModel(
            child_id=child_id,
            teacher_name="Emma",
            lesson_date=date(2026, 5, 25),
            title="Run Hop Go",
            topic="Phonics",
            status=MaterialStatus.ready.value,
            source_images=[],
            source_image_keys=[],
            normalized_image_keys=[],
            uploaded_at=datetime.now(timezone.utc),
            learning_assets=[
                {
                    "id": "asset_rabbit",
                    "text": "A rabbit can hop fast.",
                    "kind": "sentence",
                    "translation": "兔子能跳得很快。",
                    "pronunciation_text": "A rabbit can hop fast.",
                    "primary_accent": "us",
                }
            ],
        )
        db.add(material)
        db.commit()
        db.refresh(material)
        return child_id, material.id


def test_create_speaking_attempt_uploads_audio_and_enqueues(api_client, monkeypatch) -> None:
    headers, _ = auth_headers(api_client, auth_code="speaking-upload-parent")
    child_id, material_id = _create_child_and_material(api_client, headers)
    enqueued: list[str] = []
    monkeypatch.setattr("app.api.routes.speaking_attempts.enqueue_speaking_attempt_job", enqueued.append)

    response = api_client.post(
        "/v1/speaking-attempts",
        data={
            "child_id": child_id,
            "material_id": material_id,
            "prompt_text": "跟读：A rabbit can hop fast.",
            "target_text": "A rabbit can hop fast.",
            "learning_asset_id": "asset_rabbit",
            "audio_duration_ms": "3100",
        },
        files={"audio": ("rabbit.m4a", b"fake-audio", "audio/mp4")},
        headers=headers,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "recording_uploaded"
    assert payload["audio_url"].startswith("http://testserver/uploads/speaking_attempt/")
    assert payload["audio_object_key"].startswith("speaking_attempt/")
    assert payload["audio_size_bytes"] == len(b"fake-audio")
    assert enqueued == [payload["id"]]
    with SessionLocal() as db:
        stored = db.query(StoredAssetModel).filter_by(owner_type="speaking_attempt", owner_id=payload["id"]).one()
        assert stored.object_key == payload["audio_object_key"]
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_speaking_attempts.py::test_create_speaking_attempt_uploads_audio_and_enqueues -q
```

Expected:

```text
FAILED because current POST /speaking-attempts expects JSON and enqueue_speaking_attempt_job does not exist
```

- [ ] **Step 3: Add settings**

Modify `services/api/app/core/settings.py`:

```python
    speech_provider: str
    speech_assessment_provider: str
    speech_assessment_base_url: str
    speech_assessment_app_key: str
    speech_assessment_secret_key: str
    speech_assessment_timeout_seconds: int
    speech_assessment_http_trust_env: bool
    speech_assessment_default_accent: str
    speaking_audio_max_bytes: int
```

Add to `get_settings()`:

```python
        speech_provider=os.getenv("SPEECH_PROVIDER", "stub"),
        speech_assessment_provider=os.getenv("SPEECH_ASSESSMENT_PROVIDER", os.getenv("SPEECH_PROVIDER", "stub")),
        speech_assessment_base_url=os.getenv("SPEECH_ASSESSMENT_BASE_URL", ""),
        speech_assessment_app_key=os.getenv("SPEECH_ASSESSMENT_APP_KEY", ""),
        speech_assessment_secret_key=os.getenv("SPEECH_ASSESSMENT_SECRET_KEY", ""),
        speech_assessment_timeout_seconds=int(os.getenv("SPEECH_ASSESSMENT_TIMEOUT_SECONDS", "120")),
        speech_assessment_http_trust_env=os.getenv("SPEECH_ASSESSMENT_HTTP_TRUST_ENV", "false").lower() == "true",
        speech_assessment_default_accent=os.getenv("SPEECH_ASSESSMENT_DEFAULT_ACCENT", "am"),
        speaking_audio_max_bytes=int(os.getenv("SPEAKING_AUDIO_MAX_BYTES", str(10 * 1024 * 1024))),
```

- [ ] **Step 4: Add queue helper**

Create `services/api/app/services/speaking_queue.py`:

```python
from __future__ import annotations

import logging

from app.core.settings import get_settings

logger = logging.getLogger(__name__)


def enqueue_speaking_attempt_job(attempt_id: str) -> None:
    if get_settings().app_env == "testing":
        logger.info("test environment skipped speaking attempt enqueue %s", attempt_id)
        return
    try:
        from workers_app.celery_app import celery_app
    except ImportError as exc:
        raise RuntimeError("Celery is required to enqueue speaking attempt jobs") from exc
    celery_app.send_task("speaking.score_attempt", args=[attempt_id], queue="learning_english")
    logger.info("enqueued speaking attempt job %s", attempt_id)
```

- [ ] **Step 5: Implement multipart route**

Modify `services/api/app/api/routes/speaking_attempts.py`:

```python
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import File, Form, UploadFile

from app.core.config import get_storage
from app.core.settings import get_settings
from app.services.speaking_queue import enqueue_speaking_attempt_job
```

Replace current JSON `create_speaking_attempt()` with multipart:

```python
@router.post("", response_model=SpeakingAttempt, status_code=status.HTTP_201_CREATED)
def create_speaking_attempt(
    child_id: str = Form(...),
    material_id: str = Form(...),
    prompt_text: str = Form(...),
    target_text: str = Form(""),
    review_task_id: str = Form(""),
    learning_asset_id: str = Form(""),
    audio_duration_ms: int = Form(0),
    audio: UploadFile = File(...),
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
    storage=Depends(get_storage),
) -> SpeakingAttempt:
    child = _get_owned_child(db, current_parent.id, child_id)
    material = _get_owned_ready_material(db, child.id, material_id)
    _validate_audio_upload(audio)

    attempt = SpeakingAttemptModel(
        id=f"attempt_{uuid4().hex[:12]}",
        child_id=child.id,
        material_id=material.id,
        review_task_id=review_task_id.strip(),
        learning_asset_id=learning_asset_id.strip(),
        prompt_text=prompt_text.strip() or "跟读这句话。",
        target_text=target_text.strip() or prompt_text.strip(),
        audio_duration_ms=max(audio_duration_ms, 0),
        status=SpeakingAttemptStatus.recording_uploaded.value,
        created_at=datetime.now(timezone.utc),
    )
    db.add(attempt)
    db.flush()

    stored = storage.save_upload("speaking_attempt", attempt.id, audio)
    attempt.audio_url = stored.url
    attempt.audio_object_key = stored.object_key
    attempt.audio_content_type = stored.content_type
    attempt.audio_size_bytes = stored.size_bytes
    db.add(stored)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    enqueue_speaking_attempt_job(attempt.id)
    return speaking_attempt_from_model(attempt)
```

Add helper functions in the same route file:

```python
_ALLOWED_AUDIO_TYPES = {
    "audio/m4a",
    "audio/mp4",
    "audio/aac",
    "audio/wav",
    "audio/mpeg",
    "application/octet-stream",
}


def _get_owned_child(db: Session, parent_id: str, child_id: str) -> ChildProfileModel:
    child = db.scalar(
        select(ChildProfileModel).where(
            ChildProfileModel.id == child_id,
            ChildProfileModel.parent_account_id == parent_id,
        )
    )
    if child is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")
    return child


def _get_owned_ready_material(db: Session, child_id: str, material_id: str) -> CourseMaterialModel:
    material = db.scalar(
        select(CourseMaterialModel).where(
            CourseMaterialModel.id == material_id,
            CourseMaterialModel.child_id == child_id,
            CourseMaterialModel.status != MaterialStatus.archived.value,
        )
    )
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    return material


def _validate_audio_upload(audio: UploadFile) -> None:
    content_type = audio.content_type or "application/octet-stream"
    if content_type not in _ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported audio type")
```

- [ ] **Step 6: Add detail and retry endpoints**

Add:

```python
@router.get("/{attempt_id}", response_model=SpeakingAttempt)
def get_speaking_attempt(
    attempt_id: str,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> SpeakingAttempt:
    attempt = _get_owned_attempt(db, current_parent.id, attempt_id)
    return speaking_attempt_from_model(attempt)


@router.post("/{attempt_id}/retry", response_model=SpeakingAttempt)
def retry_speaking_attempt(
    attempt_id: str,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> SpeakingAttempt:
    attempt = _get_owned_attempt(db, current_parent.id, attempt_id)
    attempt.status = SpeakingAttemptStatus.recording_uploaded.value
    attempt.failure_reason = ""
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    enqueue_speaking_attempt_job(attempt.id)
    return speaking_attempt_from_model(attempt)
```

Implement `_get_owned_attempt()` by joining child and material, filtering `parent_account_id` and `CourseMaterialModel.status != archived`.

- [ ] **Step 7: Add validation tests**

Add tests for:

```python
def test_create_speaking_attempt_rejects_archived_material(...): ...
def test_create_speaking_attempt_rejects_unsupported_audio_type(...): ...
def test_get_speaking_attempt_requires_owner(...): ...
def test_retry_speaking_attempt_requeues_failed_attempt(...): ...
```

Each test must assert exact status code and Chinese-safe behavior:

```python
assert response.status_code == 404
assert response.json()["detail"] == "Material not found"
```

- [ ] **Step 8: Run API speaking tests**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_speaking_attempts.py -q
```

Expected:

```text
all speaking API tests pass
```

- [ ] **Step 9: Commit**

```bash
git add services/api/app/api/routes/speaking_attempts.py services/api/app/services/speaking_queue.py services/api/app/core/settings.py services/api/tests/test_speaking_attempts.py
git commit -m "feat: add speaking audio upload api"
```

## Task 3: SpeechAssessmentProvider 和 worker 评分任务

**Files:**
- Create: `services/api/app/services/speaking_assessment.py`
- Modify: `services/workers/workers_app/tasks.py`
- Create: `services/api/tests/test_speaking_assessment_provider.py`
- Create: `services/workers/tests/test_speaking_attempt_task.py`
- Modify: `services/workers/tests/test_material_job_task.py`

- [ ] **Step 1: 写 provider 失败测试**

Create `services/api/tests/test_speaking_assessment_provider.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from app.models.contracts import SpeakingWordFeedback
from app.services.speaking_assessment import (
    SpeechAssessmentConfigurationError,
    StubSpeechAssessmentProvider,
    build_speech_assessment_provider,
)


def test_stub_speech_assessment_scores_target_words(tmp_path: Path) -> None:
    audio_path = tmp_path / "attempt.m4a"
    audio_path.write_bytes(b"fake-audio")
    provider = StubSpeechAssessmentProvider()

    result = provider.assess(
        audio_path=audio_path,
        target_text="A rabbit can hop fast.",
        prompt_text="跟读：A rabbit can hop fast.",
        attempt_id="attempt_test",
        accent="am",
    )

    assert result.provider == "stub"
    assert result.transcript == "A rabbit can hop fast."
    assert result.overall_score >= 80
    assert result.word_feedback
    assert all(isinstance(item, SpeakingWordFeedback) for item in result.word_feedback)


def test_real_speech_provider_requires_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEECH_PROVIDER", "aliyun")
    monkeypatch.delenv("SPEECH_ASSESSMENT_APP_KEY", raising=False)
    monkeypatch.delenv("SPEECH_ASSESSMENT_SECRET_KEY", raising=False)

    with pytest.raises(SpeechAssessmentConfigurationError):
        build_speech_assessment_provider()
```

- [ ] **Step 2: Run provider tests to verify failure**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_speaking_assessment_provider.py -q
```

Expected:

```text
FAILED because speaking_assessment module does not exist
```

- [ ] **Step 3: Implement provider module**

Create `services/api/app/services/speaking_assessment.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import httpx

from app.core.settings import get_settings
from app.models.contracts import SpeakingWordFeedback


class SpeechAssessmentError(Exception):
    pass


class SpeechAssessmentConfigurationError(SpeechAssessmentError):
    pass


@dataclass(frozen=True)
class SpeechAssessmentResult:
    transcript: str
    overall_score: float
    pronunciation_score: float
    accuracy_score: float
    fluency_score: float
    completeness_score: float
    feedback: str
    word_feedback: list[SpeakingWordFeedback] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    provider: str = "stub"
    raw_result: dict[str, Any] = field(default_factory=dict)


class SpeechAssessmentProvider(Protocol):
    def assess(
        self,
        *,
        audio_path: Path,
        target_text: str,
        prompt_text: str,
        attempt_id: str,
        accent: str,
    ) -> SpeechAssessmentResult:
        ...


class StubSpeechAssessmentProvider:
    def assess(
        self,
        *,
        audio_path: Path,
        target_text: str,
        prompt_text: str,
        attempt_id: str,
        accent: str,
    ) -> SpeechAssessmentResult:
        if not audio_path.exists():
            raise SpeechAssessmentError("audio file not found")
        words = [word.strip(".,!?").lower() for word in target_text.split() if word.strip(".,!?")]
        feedback = [
            SpeakingWordFeedback(word=word, score=92 if index % 3 else 78, status="good" if index % 3 else "needs_practice", tip="读得清楚。" if index % 3 else f"再练一次 {word}。")
            for index, word in enumerate(words)
        ]
        return SpeechAssessmentResult(
            transcript=target_text,
            overall_score=88,
            pronunciation_score=0.88,
            accuracy_score=90,
            fluency_score=84,
            completeness_score=94,
            feedback="整体读得很清楚，个别词可以再慢一点。",
            word_feedback=feedback,
            suggestions=[item.tip for item in feedback if item.status == "needs_practice"],
            provider="stub",
            raw_result={"attempt_id": attempt_id, "accent": accent, "prompt_text": prompt_text},
        )


class AliyunSpeechAssessmentProvider:
    def __init__(
        self,
        *,
        app_key: str,
        secret_key: str,
        base_url: str,
        timeout_seconds: int,
        trust_env: bool,
        client: httpx.Client | None = None,
    ) -> None:
        if not app_key or not secret_key:
            raise SpeechAssessmentConfigurationError("Aliyun speech assessment credentials are required")
        self.app_key = app_key
        self.secret_key = secret_key
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout_seconds, trust_env=trust_env)
        self._owns_client = client is None

    def assess(
        self,
        *,
        audio_path: Path,
        target_text: str,
        prompt_text: str,
        attempt_id: str,
        accent: str,
    ) -> SpeechAssessmentResult:
        raise SpeechAssessmentConfigurationError(
            "Aliyun speech assessment adapter requires signed request implementation before use"
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


def build_speech_assessment_provider() -> SpeechAssessmentProvider:
    settings = get_settings()
    provider = settings.speech_assessment_provider.lower().strip() or settings.speech_provider.lower().strip()
    if provider == "stub":
        return StubSpeechAssessmentProvider()
    if provider == "aliyun":
        return AliyunSpeechAssessmentProvider(
            app_key=settings.speech_assessment_app_key,
            secret_key=settings.speech_assessment_secret_key,
            base_url=settings.speech_assessment_base_url,
            timeout_seconds=settings.speech_assessment_timeout_seconds,
            trust_env=settings.speech_assessment_http_trust_env,
        )
    raise SpeechAssessmentConfigurationError(f"Unsupported speech assessment provider: {provider}")
```

This task intentionally makes `aliyun` fail closed until the signed request adapter is implemented and verified. The production environment must not silently return stub scores when real provider is selected.

- [ ] **Step 4: Write worker task tests**

Create `services/workers/tests/test_speaking_attempt_task.py` with fixtures similar to `test_material_job_task.py`. Include:

```python
def test_speaking_attempt_task_is_registered() -> None:
    assert "speaking.score_attempt" in celery_app.tasks
```

Add a seeded attempt with `status="recording_uploaded"` and stored audio, then assert:

```python
result = score_speaking_attempt("attempt_test")
assert result == {"attempt_id": "attempt_test", "status": "scored"}
attempt = db.get(SpeakingAttemptModel, "attempt_test")
assert attempt.status == "scored"
assert attempt.transcript == "A rabbit can hop fast."
assert attempt.overall_score == 88
assert attempt.word_feedback
report = db.scalar(select(WeeklyReportModel).where(WeeklyReportModel.child_id == "child_test"))
assert report.speaking_attempts == 1
assert "rabbit" in report.weak_items or "a" in report.weak_items
```

- [ ] **Step 5: Implement worker task**

Modify `services/workers/workers_app/tasks.py` imports:

```python
from app.db.models import SpeakingAttemptModel
from app.models.contracts import SpeakingAttemptStatus
from app.services.speaking_assessment import SpeechAssessmentError, build_speech_assessment_provider
```

Add task:

```python
@shared_task(name="speaking.score_attempt")
def score_speaking_attempt(attempt_id: str) -> dict[str, str]:
    db = SessionLocal()
    provider = None
    try:
        row = db.execute(
            select(SpeakingAttemptModel, CourseMaterialModel)
            .join(CourseMaterialModel, CourseMaterialModel.id == SpeakingAttemptModel.material_id)
            .where(SpeakingAttemptModel.id == attempt_id)
        ).first()
        if row is None:
            return {"attempt_id": attempt_id, "status": "missing"}
        attempt, material = row
        if material.status == MaterialStatus.archived.value:
            return {"attempt_id": attempt.id, "status": "archived"}
        if attempt.status not in {
            SpeakingAttemptStatus.queued.value,
            SpeakingAttemptStatus.recording_uploaded.value,
            SpeakingAttemptStatus.transcribing.value,
        }:
            return {"attempt_id": attempt.id, "status": attempt.status}

        attempt.status = SpeakingAttemptStatus.transcribing.value
        db.add(attempt)
        db.commit()

        storage = get_storage_service()
        audio_asset = db.scalar(
            select(StoredAssetModel).where(
                StoredAssetModel.owner_type == "speaking_attempt",
                StoredAssetModel.owner_id == attempt.id,
                StoredAssetModel.object_key == attempt.audio_object_key,
            )
        )
        if audio_asset is None:
            raise SpeechAssessmentError("录音文件不存在。")
        audio_path = storage.resolve_local_path(audio_asset)
        provider = build_speech_assessment_provider()
        result = provider.assess(
            audio_path=audio_path,
            target_text=attempt.target_text or attempt.prompt_text,
            prompt_text=attempt.prompt_text,
            attempt_id=attempt.id,
            accent=get_settings().speech_assessment_default_accent,
        )

        db.refresh(material)
        if material.status == MaterialStatus.archived.value:
            return {"attempt_id": attempt.id, "status": "archived"}
        attempt.status = SpeakingAttemptStatus.scored.value
        attempt.transcript = result.transcript
        attempt.overall_score = result.overall_score
        attempt.pronunciation_score = result.pronunciation_score
        attempt.accuracy_score = result.accuracy_score
        attempt.fluency_score = result.fluency_score
        attempt.completeness_score = result.completeness_score
        attempt.feedback = result.feedback
        attempt.word_feedback = [item.model_dump(mode="json") for item in result.word_feedback]
        attempt.suggestions = result.suggestions
        attempt.provider = result.provider
        attempt.raw_result = result.raw_result
        attempt.failure_reason = ""
        _update_speaking_report(db, attempt)
        db.add(attempt)
        db.commit()
        return {"attempt_id": attempt.id, "status": attempt.status}
    except Exception as exc:
        attempt = db.get(SpeakingAttemptModel, attempt_id)
        if attempt is not None:
            attempt.status = SpeakingAttemptStatus.failed.value
            attempt.failure_reason = f"口语评分失败：{exc}"
            attempt.feedback = "口语评分失败，请稍后重试。"
            db.add(attempt)
            db.commit()
        return {"attempt_id": attempt_id, "status": "failed"}
    finally:
        close = getattr(provider, "close", None)
        if callable(close):
            close()
        db.close()
```

Add `_update_speaking_report()`:

```python
def _update_speaking_report(db: Session, attempt: SpeakingAttemptModel) -> None:
    child = db.get(ChildProfileModel, attempt.child_id)
    if child is None:
        return
    report = db.scalar(select(WeeklyReportModel).where(WeeklyReportModel.child_id == attempt.child_id))
    if report is None:
        start = child.created_at.date()
        report = WeeklyReportModel(
            child_id=attempt.child_id,
            week_start=start,
            week_end=start + timedelta(days=6),
            recommended_actions=["保持每周至少完成一次口语跟读。"],
        )
        db.add(report)
    report.speaking_attempts += 1
    weak_words = [
        item.get("word", "")
        for item in (attempt.word_feedback or [])
        if item.get("status") == "needs_practice" and item.get("word")
    ]
    report.weak_items = list(dict.fromkeys([*(report.weak_items or []), *weak_words]))
    db.add(report)
```

Ensure `timedelta` and `Session` are imported.

- [ ] **Step 6: Run worker tests**

Run:

```bash
services/workers/.venv/bin/python -m pytest services/workers/tests/test_speaking_attempt_task.py -q
services/workers/.venv/bin/python -m pytest services/workers/tests/test_material_job_task.py::test_material_job_task_is_registered -q
```

Expected:

```text
speaking worker tests pass and existing material task registration still passes
```

- [ ] **Step 7: Commit**

```bash
git add services/api/app/services/speaking_assessment.py services/workers/workers_app/tasks.py services/api/tests/test_speaking_assessment_provider.py services/workers/tests/test_speaking_attempt_task.py services/workers/tests/test_material_job_task.py
git commit -m "feat: score speaking attempts asynchronously"
```

## Task 4: Flutter 录音状态机和 repository 上传

**Files:**
- Modify: `apps/mobile/pubspec.yaml`
- Modify: `apps/mobile/ios/Runner/Info.plist`
- Modify: `apps/mobile/android/app/src/main/AndroidManifest.xml`
- Create: `apps/mobile/lib/features/speaking/data/speaking_recorder_controller.dart`
- Modify: `apps/mobile/lib/features/materials/data/app_repository.dart`
- Test: `apps/mobile/test/features/materials/data/app_repository_test.dart`

- [ ] **Step 1: Add dependencies**

Modify `apps/mobile/pubspec.yaml`:

```yaml
dependencies:
  path_provider: ^2.1.5
  record: ^6.2.1
```

Keep existing dependencies sorted with local style.

- [ ] **Step 2: Add permissions**

Modify `apps/mobile/ios/Runner/Info.plist`:

```xml
<key>NSMicrophoneUsageDescription</key>
<string>用于录制孩子跟读英语的音频，并生成发音反馈。</string>
```

Modify `apps/mobile/android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
```

Place it beside existing app-level permissions, outside `<application>`.

- [ ] **Step 3: Write repository multipart test**

Modify `apps/mobile/test/features/materials/data/app_repository_test.dart` by adding a fake adapter assertion for `POST /speaking-attempts` multipart. The expected request must include:

```dart
expect(request.path, '/speaking-attempts');
expect(request.data, isA<FormData>());
```

Return:

```dart
{
  'id': 'attempt_test',
  'child_id': 'child_test',
  'material_id': 'material_test',
  'review_task_id': 'task_test',
  'learning_asset_id': 'asset_rabbit',
  'prompt_text': '跟读：A rabbit can hop fast.',
  'target_text': 'A rabbit can hop fast.',
  'audio_url': 'http://testserver/uploads/speaking_attempt/attempt_test/input.m4a',
  'audio_object_key': 'speaking_attempt/attempt_test/input.m4a',
  'audio_content_type': 'audio/mp4',
  'audio_size_bytes': 10,
  'audio_duration_ms': 3100,
  'transcript': '',
  'pronunciation_score': null,
  'overall_score': null,
  'accuracy_score': null,
  'fluency_score': null,
  'completeness_score': null,
  'feedback': '',
  'word_feedback': [],
  'suggestions': [],
  'provider': '',
  'raw_result': {},
  'failure_reason': '',
  'status': 'recording_uploaded',
}
```

- [ ] **Step 4: Implement repository methods**

Modify `apps/mobile/lib/features/materials/data/app_repository.dart`:

```dart
Future<SpeakingAttempt> uploadSpeakingAttempt({
  required String childId,
  required String materialId,
  required String promptText,
  required String targetText,
  required String audioPath,
  String reviewTaskId = '',
  String learningAssetId = '',
  int audioDurationMs = 0,
}) async {
  final form = FormData.fromMap(<String, dynamic>{
    'child_id': childId,
    'material_id': materialId,
    'prompt_text': promptText,
    'target_text': targetText,
    'review_task_id': reviewTaskId,
    'learning_asset_id': learningAssetId,
    'audio_duration_ms': audioDurationMs,
    'audio': await MultipartFile.fromFile(
      audioPath,
      filename: 'speaking-attempt.m4a',
      contentType: DioMediaType('audio', 'mp4'),
    ),
  });
  final response = await _authorizedRequest<Map<String, dynamic>>(
    (options) => _dio.post<Map<String, dynamic>>(
      '/speaking-attempts',
      data: form,
      options: options,
    ),
  );
  return SpeakingAttempt.fromJson(response.data ?? const <String, dynamic>{});
}

Future<SpeakingAttempt> getSpeakingAttempt(String attemptId) async {
  final response = await _authorizedRequest<Map<String, dynamic>>(
    (options) => _dio.get<Map<String, dynamic>>('/speaking-attempts/$attemptId', options: options),
  );
  return SpeakingAttempt.fromJson(response.data ?? const <String, dynamic>{});
}

Future<SpeakingAttempt> retrySpeakingAttempt(String attemptId) async {
  final response = await _authorizedRequest<Map<String, dynamic>>(
    (options) => _dio.post<Map<String, dynamic>>('/speaking-attempts/$attemptId/retry', options: options),
  );
  return SpeakingAttempt.fromJson(response.data ?? const <String, dynamic>{});
}
```

If `DioMediaType` is unavailable in the current dio import style, import `package:http_parser/http_parser.dart` and use `MediaType('audio', 'mp4')`.

- [ ] **Step 5: Add recorder controller**

Create `apps/mobile/lib/features/speaking/data/speaking_recorder_controller.dart`:

```dart
import 'dart:async';
import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

final speakingRecorderControllerProvider =
    AutoDisposeAsyncNotifierProvider<SpeakingRecorderController, SpeakingRecorderState>(
  SpeakingRecorderController.new,
);

class SpeakingRecorderState {
  const SpeakingRecorderState({
    this.isRecording = false,
    this.audioPath = '',
    this.durationMs = 0,
    this.errorMessage = '',
  });

  final String audioPath;
  final int durationMs;
  final String errorMessage;
  final bool isRecording;

  SpeakingRecorderState copyWith({
    String? audioPath,
    int? durationMs,
    String? errorMessage,
    bool? isRecording,
  }) {
    return SpeakingRecorderState(
      audioPath: audioPath ?? this.audioPath,
      durationMs: durationMs ?? this.durationMs,
      errorMessage: errorMessage ?? this.errorMessage,
      isRecording: isRecording ?? this.isRecording,
    );
  }
}

class SpeakingRecorderController extends AutoDisposeAsyncNotifier<SpeakingRecorderState> {
  final AudioRecorder _recorder = AudioRecorder();
  DateTime? _startedAt;

  @override
  FutureOr<SpeakingRecorderState> build() {
    ref.onDispose(_recorder.dispose);
    return const SpeakingRecorderState();
  }

  Future<void> start() async {
    final hasPermission = await _recorder.hasPermission();
    if (!hasPermission) {
      state = const AsyncData(SpeakingRecorderState(errorMessage: '没有麦克风权限，请在系统设置中允许录音。'));
      return;
    }
    final dir = await getTemporaryDirectory();
    final path = '${dir.path}/speaking-${DateTime.now().millisecondsSinceEpoch}.m4a';
    _startedAt = DateTime.now();
    await _recorder.start(
      const RecordConfig(encoder: AudioEncoder.aacLc, sampleRate: 16000, numChannels: 1),
      path: path,
    );
    state = AsyncData(SpeakingRecorderState(isRecording: true, audioPath: path));
  }

  Future<void> stop() async {
    final path = await _recorder.stop();
    final startedAt = _startedAt;
    final durationMs = startedAt == null ? 0 : DateTime.now().difference(startedAt).inMilliseconds;
    state = AsyncData(
      SpeakingRecorderState(
        isRecording: false,
        audioPath: path ?? state.valueOrNull?.audioPath ?? '',
        durationMs: durationMs,
      ),
    );
  }

  Future<void> clear() async {
    final current = state.valueOrNull;
    if (current != null && current.audioPath.isNotEmpty) {
      final file = File(current.audioPath);
      if (await file.exists()) {
        await file.delete();
      }
    }
    state = const AsyncData(SpeakingRecorderState());
  }
}
```

- [ ] **Step 6: Run Flutter repository tests**

Run:

```bash
cd apps/mobile && flutter pub get
cd apps/mobile && flutter test test/features/materials/data/app_repository_test.dart
```

Expected:

```text
repository tests pass and pubspec.lock updates with record/path_provider dependencies
```

- [ ] **Step 7: Commit**

```bash
git add apps/mobile/pubspec.yaml apps/mobile/pubspec.lock apps/mobile/ios/Runner/Info.plist apps/mobile/android/app/src/main/AndroidManifest.xml apps/mobile/lib/features/speaking/data/speaking_recorder_controller.dart apps/mobile/lib/features/materials/data/app_repository.dart apps/mobile/test/features/materials/data/app_repository_test.dart
git commit -m "feat: add speaking audio upload client"
```

## Task 5: Speaking 结果页、轮询和周报联动

**Files:**
- Modify: `apps/mobile/lib/features/speaking/presentation/speaking_partner_screen.dart`
- Modify: `apps/mobile/lib/features/review/presentation/review_runner_screen.dart`
- Modify: `apps/mobile/lib/features/profiles/data/demo_data.dart`
- Create: `apps/mobile/test/features/speaking/presentation/speaking_partner_screen_test.dart`
- Modify: `services/api/tests/test_vertical_slice.py`

- [ ] **Step 1: 写 Flutter 页面测试**

Create `apps/mobile/test/features/speaking/presentation/speaking_partner_screen_test.dart`. Use existing fake repository patterns. Cover:

```dart
testWidgets('speaking page shows target text and record action', (tester) async {
  await tester.pumpWidget(buildTestApp(const SpeakingPartnerScreen(materialId: 'material_test')));
  expect(find.text('口语陪练'), findsOneWidget);
  expect(find.textContaining('开始录音'), findsOneWidget);
});

testWidgets('speaking page shows scored result', (tester) async {
  final attempt = SpeakingAttempt(
    id: 'attempt_test',
    childId: 'child_test',
    materialId: 'material_test',
    promptText: '跟读：A rabbit can hop fast.',
    targetText: 'A rabbit can hop fast.',
    audioUrl: 'http://testserver/audio.m4a',
    audioObjectKey: 'speaking_attempt/attempt_test/input.m4a',
    audioContentType: 'audio/mp4',
    audioSizeBytes: 10,
    audioDurationMs: 3000,
    transcript: 'A rabbit can hop fast.',
    pronunciationScore: 0.88,
    overallScore: 88,
    accuracyScore: 90,
    fluencyScore: 84,
    completenessScore: 94,
    feedback: '整体读得很清楚。',
    wordFeedback: const <SpeakingWordFeedback>[
      SpeakingWordFeedback(word: 'rabbit', score: 92, status: 'good', tip: '读得清楚。'),
    ],
    suggestions: const <String>['再跟读一次 hop。'],
    provider: 'stub',
    rawResult: const <String, dynamic>{},
    failureReason: '',
    status: SpeakingAttemptStatus.scored,
  );
  await tester.pumpWidget(buildTestAppWithSpeakingAttempt(attempt));
  expect(find.text('88'), findsOneWidget);
  expect(find.text('整体读得很清楚。'), findsOneWidget);
  expect(find.text('rabbit'), findsOneWidget);
});
```

Use local test helpers already present in the mobile test suite; if no shared `buildTestApp` exists, create a small helper in this test file using `ProviderScope` and `MaterialApp`.

- [ ] **Step 2: Replace stub UI with recording UI**

Modify `SpeakingPartnerScreen`:

- Read `speakingRecorderControllerProvider`.
- Resolve `targetText` from route context or use first available material learning asset after loading material detail.
- Show:
  - `开始录音`
  - `停止录音`
  - `重新录音`
  - `提交评分`
  - `评分中`
  - `重新评分`

The submit handler should call:

```dart
final created = await ref.read(appRepositoryProvider).uploadSpeakingAttempt(
  childId: child.id,
  materialId: widget.materialId,
  promptText: '跟读：$targetText',
  targetText: targetText,
  audioPath: recorder.audioPath,
  audioDurationMs: recorder.durationMs,
);
ref.read(lastSpeakingAttemptProvider.notifier).state = created;
```

- [ ] **Step 3: Add polling**

In `SpeakingPartnerScreen`, when last attempt status is `recordingUploaded` or `transcribing`, start a `Timer.periodic` every 3 seconds:

```dart
_pollTimer = Timer.periodic(const Duration(seconds: 3), (_) async {
  final attempt = ref.read(lastSpeakingAttemptProvider);
  if (attempt == null) {
    return;
  }
  final latest = await ref.read(appRepositoryProvider).getSpeakingAttempt(attempt.id);
  ref.read(lastSpeakingAttemptProvider.notifier).state = latest;
  if (latest.status == SpeakingAttemptStatus.scored || latest.status == SpeakingAttemptStatus.failed) {
    _pollTimer?.cancel();
    ref.invalidate(weeklyReportProvider);
  }
});
```

Cancel the timer in `dispose()`.

- [ ] **Step 4: Update result rendering**

Show scored fields:

```dart
Text('${attempt.overallScore?.round() ?? 0}', style: AppTextStyles.pageTitle)
Text('发音 ${(attempt.pronunciationScore ?? 0) * 100 ~/ 1} · 准确 ${attempt.accuracyScore?.round() ?? 0} · 流利 ${attempt.fluencyScore?.round() ?? 0} · 完整 ${attempt.completenessScore?.round() ?? 0}')
Text('识别文本：${attempt.transcript}')
Text(attempt.feedback)
```

For word feedback, use compact chips:

```dart
Wrap(
  spacing: AppSpacing.xs,
  runSpacing: AppSpacing.xs,
  children: attempt.wordFeedback.map((item) => Chip(label: Text('${item.word} ${item.score.round()}'))).toList(),
)
```

Failed state:

```dart
StatePanel(
  title: '口语评分失败',
  description: attempt.failureReason.isNotEmpty ? attempt.failureReason : '请稍后重新评分。',
  action: FilledButton(onPressed: _retryAttempt, child: const Text('重新评分')),
)
```

- [ ] **Step 5: Update vertical slice test**

Modify `services/api/tests/test_vertical_slice.py` speaking section from JSON to multipart:

```python
speaking_response = api_client.post(
    "/v1/speaking-attempts",
    data={
        "child_id": child_id,
        "material_id": material_id,
        "prompt_text": "跟读：A queen can sing.",
        "target_text": "A queen can sing.",
    },
    files={"audio": ("queen.m4a", b"fake-audio", "audio/mp4")},
    headers=headers,
)
assert speaking_response.status_code == 201
assert speaking_response.json()["status"] == "recording_uploaded"
```

Do not assert `speaking_attempts >= 1` in the same API-only vertical slice until worker scoring is invoked. Add a worker-level assertion in `test_speaking_attempt_task.py`.

- [ ] **Step 6: Run focused Flutter and API tests**

Run:

```bash
cd apps/mobile && flutter test test/features/speaking/presentation/speaking_partner_screen_test.dart
services/api/.venv/bin/python -m pytest services/api/tests/test_vertical_slice.py services/api/tests/test_speaking_attempts.py -q
```

Expected:

```text
Flutter speaking screen tests pass.
API vertical slice uses multipart speaking upload and passes.
```

- [ ] **Step 7: Commit**

```bash
git add apps/mobile/lib/features/speaking/presentation/speaking_partner_screen.dart apps/mobile/lib/features/review/presentation/review_runner_screen.dart apps/mobile/lib/features/profiles/data/demo_data.dart apps/mobile/test/features/speaking/presentation/speaking_partner_screen_test.dart services/api/tests/test_vertical_slice.py
git commit -m "feat: show speaking assessment results"
```

## Task 6: Harness、文档和全量验证

**Files:**
- Modify: `docs/harness/upload-recognition-loop.md`
- Modify: `docs/harness/mvp-readiness-checklist.md`
- Modify: `docs/project/2026-05-25-status-and-todo.md`
- Modify: `README.md`
- Modify: `services/api/README.md`
- Modify: `services/workers/README.md`
- Modify: `apps/mobile/README.md`

- [ ] **Step 1: Update Harness requirements**

Add `HN-017` to `docs/harness/upload-recognition-loop.md`:

```markdown
### HN-017：孩子录音上传与 AI 语音评分

**目标：** 孩子围绕讲义核心词句录音后，系统保存音频、异步转写评分，并在结果页和周报中展示反馈。

**验收标准：**
- `POST /v1/speaking-attempts` multipart 上传音频后返回 `recording_uploaded`。
- storage 中存在 `owner_type=speaking_attempt` 的音频对象。
- worker `speaking.score_attempt` 成功后 attempt 进入 `scored`。
- scored attempt 包含 transcript、overall_score、pronunciation_score、accuracy_score、fluency_score、completeness_score、word_feedback 和中文 feedback。
- failed attempt 在移动端显示中文失败原因，并可重新评分。
- 真机录音上传后保存 API 日志、worker 日志、attempt JSON 和结果页截图。

**证据位置：**
- `dist/harness/HN-017/`
```

- [ ] **Step 2: Update readiness checklist**

Add unchecked HN-017 item to `docs/harness/mvp-readiness-checklist.md`:

```markdown
- [ ] `HN-017` 孩子录音上传与 AI 语音评分：录音上传、音频 storage、worker 评分、结果页和真机证据待完成。
```

Add evidence paths:

```markdown
- HN-017 speaking evidence：`dist/harness/HN-017/`
```

- [ ] **Step 3: Update status docs**

Update `docs/project/2026-05-25-status-and-todo.md` after implementation finishes.

Update HN-017 row:

```markdown
| `HN-017` 孩子录音上传与 AI 语音评分 | 设计与实施计划已完成，代码待实现 | 已确定异步录音上传、worker 评分和结果页方案 |
```

- [ ] **Step 4: Update service READMEs**

Update:

- `services/api/README.md`: `/v1/speaking-attempts` is now multipart upload after HN-017 implementation.
- `services/workers/README.md`: registered worker includes `speaking.score_attempt`.
- `apps/mobile/README.md`: speaking page supports recording and async assessment.
- `README.md`: product chain wording says speaking includes recording/scoring only after tests pass.

Do not claim real provider readiness unless Harness evidence exists.

- [ ] **Step 5: Run verification**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests -q
services/workers/.venv/bin/python -m pytest services/workers/tests -q
cd apps/mobile && flutter test
cd apps/mobile && flutter analyze
rg -n "stub transcript|当前阶段还是 stub|真实录音上传与 AI 评分尚未完成|speaking.generate_tts|speaking.score_attempt" README.md apps/mobile/README.md services/api/README.md services/workers/README.md docs/harness docs/project
git diff --check
```

Expected:

```text
API tests pass.
Worker tests pass.
Flutter tests pass.
Flutter analyze reports no issues.
Stale-term rg returns no stale current-state wording except intentional historical notes.
git diff --check has no output.
```

- [ ] **Step 6: Collect Harness evidence**

Create local ignored evidence after implementation:

```bash
mkdir -p dist/harness/HN-017
```

Save:

```text
dist/harness/HN-017/speaking-attempt-upload.json
dist/harness/HN-017/speaking-attempt-scored.json
dist/harness/HN-017/speaking-worker.log
dist/harness/HN-017/speaking-result-screen.png
```

For true device verification, also save:

```text
dist/harness/HN-017/real-device-speaking-summary.json
```

- [ ] **Step 7: Commit**

```bash
git add README.md apps/mobile/README.md services/api/README.md services/workers/README.md docs/harness/upload-recognition-loop.md docs/harness/mvp-readiness-checklist.md docs/project/2026-05-25-status-and-todo.md
git commit -m "docs: record HN-017 speaking assessment readiness"
```

## Final Verification

Before opening the PR, run:

```bash
git status --short --branch
services/api/.venv/bin/python -m pytest services/api/tests -q
services/workers/.venv/bin/python -m pytest services/workers/tests -q
cd apps/mobile && flutter test
cd apps/mobile && flutter analyze
git diff --check
```

Expected final state:

```text
Only ignored dist/harness/HN-017 evidence remains untracked.
All API, worker, Flutter tests pass.
Flutter analyze reports no issues.
No whitespace errors.
```

## Execution Notes

- Keep `SPEECH_PROVIDER=stub` as the local default so main-chain tests stay deterministic.
- If real Aliyun speech assessment is enabled, missing credentials must fail visibly and never fall back to stub.
- `WeeklyReport.speaking_attempts` increments only after scoring succeeds.
- Do not expose provider raw errors, secrets, signatures or temporary audio URLs to mobile UI.
- Do not physically delete speaking audio when material is archived in HN-017; archived material filtering is enough for this iteration.
