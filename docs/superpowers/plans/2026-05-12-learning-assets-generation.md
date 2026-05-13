# HN-014 讲义学习资产自动生成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 HN-014：从讲义生成核心学习资产，常规讲义目标 8-15 个、绝对范围 1-20 个，在 AI 校对页展示文字资产和讲义裁剪图，确认后异步补齐彩色配图与英式/美式 TTS mock 媒体，并在课程详情中展示。

**Architecture:** 保留当前 `CourseMaterial -> MaterialParseJob -> KnowledgePack -> ReviewTask` 主链。新增 `LearningAsset` 作为讲义学习资产合约，AI 解析阶段写入 `draft_learning_assets`，确认后固化为 `material.learning_assets`，媒体 worker 通过 mock provider 填充彩色配图和英/美 TTS URL。移动端只读展示草稿资产，课程详情展示正式资产、媒体状态和主发音选择。

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Celery, PostgreSQL JSON, Pydantic, Flutter, Riverpod, Dio, flutter_svg, pytest, flutter_test.

---

## File Structure

- Modify: `services/api/app/models/contracts.py`
  - 增加 `LearningAsset`、`SourceBoundingBox`、媒体状态枚举、主发音字段。
  - 给 `CourseMaterial` 和 `MaterialParseJob` 增加学习资产字段。
- Modify: `services/api/app/db/models.py`
  - `course_materials.learning_assets` JSON。
  - `material_parse_jobs.draft_learning_assets` JSON。
- Create: `services/api/alembic/versions/20260512_0003_add_learning_assets.py`
  - 给真实 PostgreSQL 环境补齐 JSON 字段。
- Modify: `services/api/app/services/mappers.py`
  - DB JSON 和 Pydantic 合约互转。
- Modify: `services/api/app/services/pipeline.py`
  - Doubao prompt 和 payload 解析新增 `learning_assets`。
  - fallback 从词汇/句子生成非空学习资产。
  - `KnowledgePack` 和 `ReviewTask` 优先从学习资产派生。
- Create: `services/api/app/services/learning_asset_media.py`
  - 读取 `services/api/app/static/mock_media/hn014/manifest.json`。
  - 给匹配资产填充 mock 彩色图和 US/UK TTS。
- Create: `services/api/app/services/media_queue.py`
  - API 侧入队媒体任务。
- Modify: `services/workers/workers_app/tasks.py`
  - 新增 `materials.process_learning_asset_media`。
- Inspect: `services/workers/workers_app/celery_app.py`
  - 该文件已导入 `workers_app.tasks`；新增任务放在 `tasks.py` 后无需修改注册代码。
- Modify: `services/api/app/main.py`
  - 挂载 mock media 静态目录，例如 `/mock-media/hn014/images/queen.svg`。
- Modify: `services/api/app/api/routes/material_jobs.py`
  - confirm 时固化学习资产并入队媒体任务。
- Modify: `services/api/app/api/routes/materials.py`
  - 增加主发音切换接口。
- Modify: `packages/contracts/lib/src/models.dart`
  - Dart 合约增加 `LearningAsset`、`SourceBoundingBox`。
- Modify: `apps/mobile/pubspec.yaml`
  - 增加 `flutter_svg` 用于显示 SVG mock 彩色配图。
- Modify: `apps/mobile/lib/features/materials/data/app_repository.dart`
  - 解析学习资产、规范化媒体 URL、增加主发音切换方法。
- Modify: `apps/mobile/lib/features/materials/presentation/material_review_screen.dart`
  - 展示学习资产草稿和来源讲义裁剪图。
- Modify: `apps/mobile/lib/features/lessons/presentation/lesson_detail_screen.dart`
  - 展示正式学习资产、彩色配图、TTS 状态和主发音切换。
- Modify: `docs/harness/upload-recognition-loop.md`
  - 增加 HN-014 需求与验收。
- Modify: `docs/harness/mvp-readiness-checklist.md`
  - 增加 HN-014 checkbox 和证据目录。

---

### Task 1: API Contract, DB Schema, and Migration

**Files:**
- Modify: `services/api/app/models/contracts.py`
- Modify: `services/api/app/db/models.py`
- Modify: `services/api/app/services/mappers.py`
- Create: `services/api/alembic/versions/20260512_0003_add_learning_assets.py`
- Test: `services/api/tests/test_learning_assets_contracts.py`

- [ ] **Step 1: Write failing API contract tests**

Create `services/api/tests/test_learning_assets_contracts.py`:

```python
from __future__ import annotations

from datetime import date, datetime, timezone

from app.models.contracts import (
    CourseMaterial,
    JobStatus,
    LearningAsset,
    MaterialParseJob,
    MaterialStatus,
    MediaGenerationStatus,
    PrimaryAccent,
    SourceBoundingBox,
)


def test_learning_asset_round_trips_media_fields() -> None:
    asset = LearningAsset(
        id="asset_queen",
        text="queen",
        kind="word",
        translation="女王",
        source_page_index=1,
        source_bbox=SourceBoundingBox(x=0.05, y=0.14, width=0.43, height=0.35),
        source_visual_description="迷宫里的女王。",
        pronunciation_text="queen",
        image_prompt="参考讲义女王线稿，生成彩色女王插图。",
        difficulty="easy",
        teaching_note="让孩子先找女王，再读 queen。",
        is_core=True,
        generated_image_status=MediaGenerationStatus.ready,
        generated_image_url="http://testserver/mock-media/hn014/images/queen.svg",
        generated_image_object_key="mock_media/hn014/images/queen.svg",
        tts_us_status=MediaGenerationStatus.ready,
        tts_us_url="http://testserver/mock-media/hn014/tts/us/queen.m4a",
        tts_us_object_key="mock_media/hn014/tts/us/queen.m4a",
        tts_uk_status=MediaGenerationStatus.ready,
        tts_uk_url="http://testserver/mock-media/hn014/tts/uk/queen.m4a",
        tts_uk_object_key="mock_media/hn014/tts/uk/queen.m4a",
        primary_accent=PrimaryAccent.us,
    )

    payload = asset.model_dump(mode="json")
    assert payload["source_bbox"] == {"x": 0.05, "y": 0.14, "width": 0.43, "height": 0.35}
    assert payload["generated_image_status"] == "ready"
    assert payload["primary_accent"] == "us"
    assert LearningAsset(**payload).tts_uk_url.endswith("/tts/uk/queen.m4a")


def test_material_and_job_include_learning_assets() -> None:
    asset = LearningAsset(
        id="asset_duck",
        text="duck",
        kind="word",
        translation="鸭子",
        source_page_index=1,
        pronunciation_text="duck",
        image_prompt="参考讲义鸭子线稿，生成彩色鸭子插图。",
        difficulty="easy",
        teaching_note="让孩子指图读 duck。",
    )

    material = CourseMaterial(
        id="material_1",
        child_id="child_1",
        teacher_name="外教课",
        lesson_date=date(2026, 5, 12),
        title="Qq Storybook",
        status=MaterialStatus.ready,
        learning_assets=[asset],
    )
    job = MaterialParseJob(
        id="job_1",
        material_id="material_1",
        status=JobStatus.needs_review,
        started_at=datetime.now(timezone.utc),
        draft_learning_assets=[asset],
    )

    assert material.learning_assets[0].text == "duck"
    assert job.draft_learning_assets[0].translation == "鸭子"
```

- [ ] **Step 2: Run contract tests and verify failure**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_learning_assets_contracts.py -q
```

Expected: fails with import errors for `LearningAsset`, `SourceBoundingBox`, `MediaGenerationStatus`, and `PrimaryAccent`.

- [ ] **Step 3: Add Python contracts**

Modify `services/api/app/models/contracts.py`:

```python
class MediaGenerationStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class PrimaryAccent(str, Enum):
    us = "us"
    uk = "uk"


class SourceBoundingBox(BaseModel):
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 1.0


class LearningAsset(BaseModel):
    id: str
    text: str
    kind: str
    translation: str = ""
    source_page_index: int = 1
    source_bbox: Optional[SourceBoundingBox] = None
    source_visual_description: str = ""
    pronunciation_text: str = ""
    image_prompt: str = ""
    difficulty: str = "easy"
    teaching_note: str = ""
    is_core: bool = True
    generated_image_status: MediaGenerationStatus = MediaGenerationStatus.pending
    generated_image_url: str = ""
    generated_image_object_key: str = ""
    tts_us_status: MediaGenerationStatus = MediaGenerationStatus.pending
    tts_us_url: str = ""
    tts_us_object_key: str = ""
    tts_uk_status: MediaGenerationStatus = MediaGenerationStatus.pending
    tts_uk_url: str = ""
    tts_uk_object_key: str = ""
    primary_accent: PrimaryAccent = PrimaryAccent.us
```

Add fields in `services/api/app/models/contracts.py`:

```python
# CourseMaterial: insert immediately after image_records.
learning_assets: list["LearningAsset"] = Field(default_factory=list)

# MaterialParseJob: insert immediately after draft_image_records.
draft_learning_assets: list["LearningAsset"] = Field(default_factory=list)
```

- [ ] **Step 4: Add SQLAlchemy JSON columns**

Modify `services/api/app/db/models.py`:

```python
# CourseMaterialModel: insert immediately after image_records.
learning_assets: Mapped[list[dict]] = mapped_column(JSON, default=list)

# MaterialParseJobModel: insert immediately after draft_image_records.
draft_learning_assets: Mapped[list[dict]] = mapped_column(JSON, default=list)
```

- [ ] **Step 5: Add Alembic migration**

Create `services/api/alembic/versions/20260512_0003_add_learning_assets.py`:

```python
"""add learning assets

Revision ID: 20260512_0003
Revises: 20260505_0002
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260512_0003"
down_revision = "20260505_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "course_materials",
        sa.Column("learning_assets", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.add_column(
        "material_parse_jobs",
        sa.Column("draft_learning_assets", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.alter_column("course_materials", "learning_assets", server_default=None)
    op.alter_column("material_parse_jobs", "draft_learning_assets", server_default=None)


def downgrade() -> None:
    op.drop_column("material_parse_jobs", "draft_learning_assets")
    op.drop_column("course_materials", "learning_assets")
```

迁移目标是 PostgreSQL。测试环境通过 SQLAlchemy metadata 建表覆盖字段存在性，不在 SQLite 上执行该 Alembic 脚本。

- [ ] **Step 6: Update mappers**

Modify `services/api/app/services/mappers.py` imports and conversions:

```python
from app.models.contracts import LearningAsset
```

In `course_material_from_model`:

```python
learning_assets=[LearningAsset(**item) for item in (model.learning_assets or [])],
```

In `material_job_from_model`:

```python
draft_learning_assets=[LearningAsset(**item) for item in (model.draft_learning_assets or [])],
```

- [ ] **Step 7: Run tests**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_learning_assets_contracts.py -q
```

Expected: `2 passed`.

- [ ] **Step 8: Commit**

```bash
git add services/api/app/models/contracts.py services/api/app/db/models.py services/api/app/services/mappers.py services/api/alembic/versions/20260512_0003_add_learning_assets.py services/api/tests/test_learning_assets_contracts.py
git commit -m "feat: add learning asset contracts"
```

---

### Task 2: Pipeline Learning Asset Extraction and Fallback

**Files:**
- Modify: `services/api/app/services/pipeline.py`
- Test: `services/api/tests/test_doubao_pipeline.py`
- Test: `services/api/tests/test_material_failures.py`

- [ ] **Step 1: Write failing pipeline tests**

Append to `services/api/tests/test_doubao_pipeline.py`:

```python
def test_doubao_extracts_learning_assets_with_bbox() -> None:
    payload = {
        "ocr_text": "Find the queen. A rabbit can hop fast.",
        "title": "Qq Rr Storybook",
        "topic": "phonics",
        "vocabulary": ["queen", "rabbit"],
        "sentences": ["Find the queen.", "A rabbit can hop fast."],
        "warnings": [],
        "confidence_summary": "high",
        "image_records": [
            {"page_index": 1, "image_title": "Qq page", "vocabulary": ["queen"], "sentences": ["Find the queen."]},
            {"page_index": 2, "image_title": "Rr page", "vocabulary": ["rabbit"], "sentences": ["A rabbit can hop fast."]},
        ],
        "learning_assets": [
            {
                "text": "queen",
                "kind": "word",
                "translation": "女王",
                "source_page_index": 1,
                "source_bbox": {"x": 0.05, "y": 0.14, "width": 0.43, "height": 0.35},
                "source_visual_description": "迷宫里的女王。",
                "pronunciation_text": "queen",
                "image_prompt": "参考讲义女王线稿生成彩色图。",
                "difficulty": "easy",
                "teaching_note": "让孩子找女王并读 queen。",
            },
            {
                "text": "A rabbit can hop fast.",
                "kind": "sentence",
                "translation": "兔子能跳得很快。",
                "source_page_index": 2,
                "source_bbox": {"x": 0.51, "y": 0.16, "width": 0.43, "height": 0.33},
                "source_visual_description": "跳跃的兔子。",
                "pronunciation_text": "A rabbit can hop fast.",
                "image_prompt": "参考讲义兔子跳跃线稿生成彩色图。",
                "difficulty": "easy",
                "teaching_note": "让孩子模仿兔子跳并跟读。",
            },
        ],
    }
    provider = _provider_with_json_payload(payload)
    draft = provider.extract(_material_with_two_images(), [_fixture_image_path(), _fixture_image_path()])

    assert [asset.text for asset in draft.learning_assets] == ["queen", "A rabbit can hop fast."]
    assert draft.learning_assets[0].source_bbox.x == 0.05
    assert draft.learning_assets[1].source_page_index == 2
```

Append fallback test:

```python
def test_learning_assets_fallback_uses_vocabulary_and_sentences() -> None:
    material = _material_with_two_images()
    assets = _fallback_learning_assets(
        material,
        vocabulary=["queen", "duck"],
        sentences=["Find the queen."],
    )

    assert [asset.text for asset in assets] == ["queen", "duck", "Find the queen."]
    assert all(asset.source_page_index >= 1 for asset in assets)
    assert all(asset.pronunciation_text for asset in assets)
    assert len(assets) <= 20
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_doubao_pipeline.py::test_doubao_extracts_learning_assets_with_bbox services/api/tests/test_doubao_pipeline.py::test_learning_assets_fallback_uses_vocabulary_and_sentences -q
```

Expected: fails because `OCRDraft.learning_assets` and `_fallback_learning_assets` do not exist.

- [ ] **Step 3: Extend OCRDraft and imports**

Add these names to the existing `from app.models.contracts import` block in `services/api/app/services/pipeline.py`:

```python
LearningAsset,
MediaGenerationStatus,
PrimaryAccent,
SourceBoundingBox,
```

Modify `OCRDraft`:

```python
@dataclass(frozen=True)
class OCRDraft:
    ocr_text: str
    title: str
    topic: str
    vocabulary: list[str]
    sentences: list[str]
    image_records: list[MaterialImageRecord]
    learning_assets: list[LearningAsset]
    warnings: list[str]
    confidence_summary: str
```

- [ ] **Step 4: Update StubOCRProvider and PaddleOCRProvider**

In both providers, add:

```python
learning_assets=_fallback_learning_assets(
    material,
    vocabulary=vocabulary,
    sentences=sentences,
),
```

Use this inside the returned `OCRDraft`.

- [ ] **Step 5: Update Doubao prompt**

Modify Doubao prompt text to include:

```python
"json 字段必须包含：ocr_text, title, topic, vocabulary, sentences, warnings, confidence_summary, image_records, learning_assets。"
"learning_assets 常规目标 8 到 15 个，绝对总量 1 到 20 个，每项包含 text, kind, translation, source_page_index, source_bbox, source_visual_description, pronunciation_text, image_prompt, difficulty, teaching_note。"
"source_bbox 使用 0 到 1 的相对坐标；无法定位时可为空。"
"不要把教师说明、页码、版权或出版社信息放入 learning_assets。"
```

- [ ] **Step 6: Parse learning assets from provider payload**

Add helpers near `_image_records_from_payload`:

```python
def _learning_assets_from_payload(
    material: CourseMaterial,
    raw_assets: Any,
    *,
    vocabulary: list[str],
    sentences: list[str],
) -> list[LearningAsset]:
    fallback = _fallback_learning_assets(material, vocabulary=vocabulary, sentences=sentences)
    if not isinstance(raw_assets, list):
        return fallback

    assets: list[LearningAsset] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_assets, start=1):
        if not isinstance(raw, dict):
            continue
        text = _clean_text_value(raw.get("text"))
        if not text or text.lower() in seen:
            continue
        seen.add(text.lower())
        assets.append(_learning_asset_from_raw(material, raw, index=index, text=text))
        if len(assets) == 20:
            break
    return assets or fallback


def _learning_asset_from_raw(
    material: CourseMaterial,
    raw: dict[str, Any],
    *,
    index: int,
    text: str,
) -> LearningAsset:
    bbox = raw.get("source_bbox")
    source_bbox = None
    if isinstance(bbox, dict):
        source_bbox = SourceBoundingBox(
            x=_clamp_float(bbox.get("x"), 0.0, 1.0),
            y=_clamp_float(bbox.get("y"), 0.0, 1.0),
            width=_clamp_float(bbox.get("width"), 0.05, 1.0),
            height=_clamp_float(bbox.get("height"), 0.05, 1.0),
        )
    kind = _clean_text_value(raw.get("kind")).lower()
    if kind not in {"word", "phrase", "sentence"}:
        kind = "sentence" if " " in text or text.endswith((".", "?", "!")) else "word"
    page_index = int(raw.get("source_page_index") or 1)
    if material.image_records:
        page_index = max(1, min(page_index, len(material.image_records)))
    return LearningAsset(
        id=_clean_text_value(raw.get("id")) or f"asset_{uuid4().hex[:12]}",
        text=text,
        kind=kind,
        translation=_clean_text_value(raw.get("translation")),
        source_page_index=page_index,
        source_bbox=source_bbox,
        source_visual_description=_clean_text_value(raw.get("source_visual_description")),
        pronunciation_text=_clean_text_value(raw.get("pronunciation_text")) or text,
        image_prompt=_clean_text_value(raw.get("image_prompt")) or f"参考讲义内容，为 {text} 生成彩色插图。",
        difficulty=_clean_text_value(raw.get("difficulty")) or "easy",
        teaching_note=_clean_text_value(raw.get("teaching_note")),
        is_core=bool(raw.get("is_core", True)),
    )


def _clamp_float(value: Any, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return minimum
    return max(minimum, min(maximum, parsed))
```

- [ ] **Step 7: Add fallback learning assets**

Add:

```python
def _fallback_learning_assets(
    material: CourseMaterial,
    *,
    vocabulary: list[str],
    sentences: list[str],
) -> list[LearningAsset]:
    candidates = [*vocabulary, *sentences]
    assets: list[LearningAsset] = []
    seen: set[str] = set()
    page_count = max(1, len(material.image_records))
    for index, text in enumerate(candidates, start=1):
        clean = _clean_text_value(text)
        if not clean or clean.lower() in seen:
            continue
        seen.add(clean.lower())
        kind = "sentence" if clean.endswith((".", "?", "!")) or len(clean.split()) > 3 else ("phrase" if " " in clean else "word")
        assets.append(
            LearningAsset(
                id=f"asset_{uuid4().hex[:12]}",
                text=clean,
                kind=kind,
                translation="",
                source_page_index=((index - 1) % page_count) + 1,
                pronunciation_text=clean,
                image_prompt=f"参考讲义内容，为 {clean} 生成清晰彩色儿童插图。",
                difficulty="easy",
                teaching_note="让孩子先看图，再读英文。",
                is_core=True,
            )
        )
        if len(assets) == 20:
            break
    return assets
```

- [ ] **Step 8: Wire Doubao extraction**

In `DoubaoOCRProvider.extract`, add:

```python
learning_assets=_learning_assets_from_payload(
    material,
    payload.get("learning_assets"),
    vocabulary=vocabulary or _extract_candidate_vocabulary(ocr_text)[:8],
    sentences=sentences or _extract_candidate_sentences([ocr_text])[:6],
),
```

- [ ] **Step 9: Run tests**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_doubao_pipeline.py::test_doubao_extracts_learning_assets_with_bbox services/api/tests/test_doubao_pipeline.py::test_learning_assets_fallback_uses_vocabulary_and_sentences -q
```

Expected: `2 passed`.

- [ ] **Step 10: Commit**

```bash
git add services/api/app/services/pipeline.py services/api/tests/test_doubao_pipeline.py
git commit -m "feat: extract learning assets from worksheets"
```

---

### Task 3: Persist Draft Learning Assets in Worker Results

**Files:**
- Modify: `services/api/app/api/routes/material_jobs.py`
- Modify: `services/workers/workers_app/tasks.py`
- Test: `services/api/tests/test_material_failures.py`
- Test: `services/workers/tests/test_material_job_task.py`

- [ ] **Step 1: Write failing API and worker tests**

In `services/api/tests/test_material_failures.py`, add an assertion to the existing successful processing test:

```python
assert response.json()["draft_learning_assets"]
assert response.json()["draft_learning_assets"][0]["text"]
```

In `services/workers/tests/test_material_job_task.py`, add:

```python
def test_worker_writes_draft_learning_assets() -> None:
    job_id, material_id = _seed_processing_material_with_image()

    result = process_material_job.run(job_id)

    assert result["status"] == "needs_review"
    with SessionLocal() as db:
        job = db.get(MaterialParseJobModel, job_id)
        material = db.get(CourseMaterialModel, material_id)
        assert job.draft_learning_assets
        assert job.draft_learning_assets[0]["text"]
        assert material.image_records
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
services/workers/.venv/bin/python -m pytest services/workers/tests/test_material_job_task.py::test_worker_writes_draft_learning_assets -q
```

Expected: fails because `draft_learning_assets` is not written.

- [ ] **Step 3: Write draft assets in API synchronous preparation path**

Where `prepared` is written in `services/api/app/api/routes/material_jobs.py`, add:

```python
job.draft_learning_assets = [item.model_dump(mode="json") for item in prepared.draft_learning_assets]
```

- [ ] **Step 4: Write draft assets in worker task**

In `services/workers/workers_app/tasks.py`, where `prepared` is applied to `job`, add:

```python
job.draft_learning_assets = [item.model_dump(mode="json") for item in prepared.draft_learning_assets]
```

Make sure failure paths leave existing draft assets untouched unless retry resets the job.

- [ ] **Step 5: Run tests**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_material_failures.py -q
services/workers/.venv/bin/python -m pytest services/workers/tests/test_material_job_task.py -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit**

```bash
git add services/api/app/api/routes/material_jobs.py services/workers/workers_app/tasks.py services/api/tests/test_material_failures.py services/workers/tests/test_material_job_task.py
git commit -m "feat: persist draft learning assets"
```

---

### Task 4: Mock Media Provider and Static Media Serving

**Files:**
- Create: `services/api/app/services/learning_asset_media.py`
- Modify: `services/api/app/main.py`
- Test: `services/api/tests/test_learning_asset_media.py`

- [ ] **Step 1: Write failing media provider tests**

Create `services/api/tests/test_learning_asset_media.py`:

```python
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.models.contracts import LearningAsset, MediaGenerationStatus
from app.services.learning_asset_media import HN014MockMediaProvider


def test_hn014_mock_media_provider_fills_urls_for_known_asset() -> None:
    provider = HN014MockMediaProvider(public_base_url="http://testserver")
    assets = [
        LearningAsset(
            id="asset_1",
            text="queen",
            kind="word",
            source_page_index=1,
            pronunciation_text="queen",
            image_prompt="参考讲义女王线稿生成彩色图。",
        )
    ]

    updated = provider.apply(assets)

    assert updated[0].generated_image_status == MediaGenerationStatus.ready
    assert updated[0].generated_image_url == "http://testserver/mock-media/hn014/images/queen.svg"
    assert updated[0].tts_us_url == "http://testserver/mock-media/hn014/tts/us/queen.m4a"
    assert updated[0].tts_uk_url == "http://testserver/mock-media/hn014/tts/uk/queen.m4a"


def test_hn014_mock_media_provider_marks_unknown_asset_failed() -> None:
    provider = HN014MockMediaProvider(public_base_url="http://testserver")
    assets = [
        LearningAsset(
            id="asset_unknown",
            text="unknown word",
            kind="phrase",
            source_page_index=1,
            pronunciation_text="unknown word",
            image_prompt="生成彩色图。",
        )
    ]

    updated = provider.apply(assets)

    assert updated[0].generated_image_status == MediaGenerationStatus.failed
    assert updated[0].tts_us_status == MediaGenerationStatus.failed
    assert updated[0].tts_uk_status == MediaGenerationStatus.failed


def test_hn014_static_media_route_serves_svg() -> None:
    response = TestClient(app).get("/mock-media/hn014/images/queen.svg")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in response.content
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_learning_asset_media.py -q
```

Expected: fails because `app.services.learning_asset_media` does not exist.

- [ ] **Step 3: Implement mock media provider**

Create `services/api/app/services/learning_asset_media.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from app.models.contracts import LearningAsset, MediaGenerationStatus, SourceBoundingBox


class HN014MockMediaProvider:
    def __init__(self, public_base_url: str) -> None:
        self.public_base_url = public_base_url.rstrip("/")
        self.root = Path(__file__).resolve().parents[1] / "static" / "mock_media" / "hn014"
        payload = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        self._by_text = {item["text"].strip().lower(): item for item in payload["assets"]}

    def apply(self, assets: list[LearningAsset]) -> list[LearningAsset]:
        updated: list[LearningAsset] = []
        for asset in assets:
            match = self._by_text.get(asset.text.strip().lower())
            if match is None:
                updated.append(
                    asset.model_copy(
                        update={
                            "generated_image_status": MediaGenerationStatus.failed,
                            "tts_us_status": MediaGenerationStatus.failed,
                            "tts_uk_status": MediaGenerationStatus.failed,
                        }
                    )
                )
                continue
            updated.append(
                asset.model_copy(
                    update={
                        "id": asset.id or match.get("id", ""),
                        "kind": asset.kind or match.get("kind", "word"),
                        "translation": asset.translation or match.get("translation", ""),
                        "source_bbox": asset.source_bbox or _source_bbox_from_manifest(match.get("source_bbox")),
                        "source_visual_description": asset.source_visual_description or match.get("source_visual_description", ""),
                        "generated_image_status": MediaGenerationStatus.ready,
                        "generated_image_url": self._url(match["image"]),
                        "generated_image_object_key": f"mock_media/hn014/{match['image']}",
                        "tts_us_status": MediaGenerationStatus.ready,
                        "tts_us_url": self._url(match["tts_us"]),
                        "tts_us_object_key": f"mock_media/hn014/{match['tts_us']}",
                        "tts_uk_status": MediaGenerationStatus.ready,
                        "tts_uk_url": self._url(match["tts_uk"]),
                        "tts_uk_object_key": f"mock_media/hn014/{match['tts_uk']}",
                    }
                )
            )
        return updated

    def _url(self, relative_path: str) -> str:
        return f"{self.public_base_url}/mock-media/hn014/{relative_path}"


def _source_bbox_from_manifest(raw: object) -> SourceBoundingBox | None:
    if not isinstance(raw, dict):
        return None
    return SourceBoundingBox(
        x=float(raw.get("x") or 0),
        y=float(raw.get("y") or 0),
        width=float(raw.get("width") or 1),
        height=float(raw.get("height") or 1),
    )
```

- [ ] **Step 4: Mount static mock media**

Modify `services/api/app/main.py`:

```python
from pathlib import Path
from fastapi.staticfiles import StaticFiles

mock_media_root = Path(__file__).resolve().parent / "static" / "mock_media"
app.mount("/mock-media", StaticFiles(directory=mock_media_root), name="mock-media")
```

Place this before `app.include_router(api_router)`.

- [ ] **Step 5: Run tests and static smoke**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_learning_asset_media.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 6: Commit**

```bash
git add services/api/app/services/learning_asset_media.py services/api/app/main.py services/api/tests/test_learning_asset_media.py
git commit -m "feat: add mock learning asset media provider"
```

---

### Task 5: Confirm Flow and Async Media Worker

**Files:**
- Create: `services/api/app/services/media_queue.py`
- Modify: `services/api/app/api/routes/material_jobs.py`
- Modify: `services/workers/workers_app/tasks.py`
- Test: `services/api/tests/test_material_failures.py`
- Test: `services/workers/tests/test_material_job_task.py`

- [ ] **Step 1: Write failing confirm and media worker tests**

In `services/api/tests/test_material_failures.py`, add:

```python
def test_confirm_persists_learning_assets_and_enqueues_media(api_client, monkeypatch) -> None:
    headers, _ = auth_headers(api_client, auth_code="learning-assets-confirm-parent")
    child_id = _create_child(api_client, headers)
    material_id, job_id = _create_material(api_client, headers, child_id)
    enqueued: list[str] = []
    monkeypatch.setattr("app.api.routes.material_jobs.enqueue_learning_asset_media_job", enqueued.append)

    with SessionLocal() as db:
        job = db.get(MaterialParseJobModel, job_id)
        job.status = JobStatus.needs_review.value
        job.draft_title = "Qq Rr Storybook"
        job.draft_topic = "phonics"
        job.draft_vocabulary = ["queen"]
        job.draft_sentences = ["Find the queen."]
        job.draft_learning_assets = [
            {
                "id": "asset_queen",
                "text": "queen",
                "kind": "word",
                "translation": "女王",
                "source_page_index": 1,
                "pronunciation_text": "queen",
                "image_prompt": "参考讲义女王线稿生成彩色图。",
                "difficulty": "easy",
                "teaching_note": "让孩子读 queen。",
                "is_core": True,
            }
        ]
        db.add(job)
        db.commit()

    response = api_client.post(f"/v1/material-jobs/{job_id}/confirm", json={}, headers=headers)

    assert response.status_code == 200
    assert enqueued == [material_id]
    material_response = api_client.get(f"/v1/materials/{material_id}", headers=headers)
    assert material_response.json()["material"]["learning_assets"][0]["text"] == "queen"
```

In `services/workers/tests/test_material_job_task.py`, add:

```python
def test_media_worker_fills_mock_image_and_tts_urls() -> None:
    material_id = _seed_ready_material_with_learning_assets()

    result = process_learning_asset_media.run(material_id)

    assert result["status"] == "ready"
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, material_id)
        asset = material.learning_assets[0]
        assert asset["generated_image_status"] == "ready"
        assert asset["generated_image_url"].endswith("/mock-media/hn014/images/queen.svg")
        assert asset["tts_us_url"].endswith("/mock-media/hn014/tts/us/queen.m4a")
        assert asset["tts_uk_url"].endswith("/mock-media/hn014/tts/uk/queen.m4a")
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_material_failures.py::test_confirm_persists_learning_assets_and_enqueues_media -q
services/workers/.venv/bin/python -m pytest services/workers/tests/test_material_job_task.py::test_media_worker_fills_mock_image_and_tts_urls -q
```

Expected: failures because media queue and worker task do not exist.

- [ ] **Step 3: Add API queue helper**

Create `services/api/app/services/media_queue.py`:

```python
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def enqueue_learning_asset_media_job(material_id: str) -> None:
    if os.getenv("APP_ENV") == "testing":
        logger.info("test environment skipped learning asset media enqueue %s", material_id)
        return

    try:
        from celery import Celery
    except ModuleNotFoundError as exc:
        raise RuntimeError("Celery is required to enqueue learning asset media jobs") from exc

    broker_url = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or "redis://localhost:6379/0"
    result_backend = os.getenv("CELERY_RESULT_BACKEND") or _default_result_backend(broker_url)
    celery_app = Celery("learning_english_api_media", broker=broker_url, backend=result_backend)
    celery_app.conf.update(task_default_queue="learning_english")
    celery_app.send_task("materials.process_learning_asset_media", args=[material_id], queue="learning_english")
    logger.info("enqueued learning asset media job %s", material_id)


def _default_result_backend(broker_url: str) -> str:
    if broker_url.endswith("/0"):
        return f"{broker_url[:-2]}/1"
    return broker_url
```

- [ ] **Step 4: Update confirm route**

Modify `services/api/app/api/routes/material_jobs.py` imports:

```python
from app.services.media_queue import enqueue_learning_asset_media_job
```

In `confirm_material_job`, update the existing `prepared.model_copy` block to include draft learning assets:

```python
prepared = prepared.model_copy(
    update={
        "status": JobStatus.ready,
        "draft_title": payload.draft_title or prepared.draft_title,
        "draft_topic": payload.draft_topic or prepared.draft_topic,
        "draft_vocabulary": payload.draft_vocabulary or prepared.draft_vocabulary,
        "draft_sentences": payload.draft_sentences or prepared.draft_sentences,
        "draft_learning_assets": prepared.draft_learning_assets,
    }
)
```

Before commit:

```python
material.learning_assets = [item.model_dump(mode="json") for item in prepared.draft_learning_assets]
```

After commit:

```python
enqueue_learning_asset_media_job(material.id)
```

Also update the contract passed into `build_knowledge_assets` so local knowledge/review generation can see the confirmed learning assets before the SQLAlchemy row is committed:

```python
material_contract = course_material_from_model(material).model_copy(
    update={"learning_assets": prepared.draft_learning_assets}
)
knowledge_pack, review_tasks, coaching_script = pipeline.build_knowledge_assets(material_contract, prepared)
```

- [ ] **Step 5: Add worker task**

Modify `services/workers/workers_app/tasks.py`:

```python
@shared_task(name="materials.process_learning_asset_media")
def process_learning_asset_media(material_id: str) -> dict[str, str]:
    from app.core.settings import get_settings
    from app.core.db import SessionLocal
    from app.db.models import CourseMaterialModel
    from app.models.contracts import LearningAsset, MediaGenerationStatus
    from app.services.learning_asset_media import HN014MockMediaProvider

    settings = get_settings()
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, material_id)
        if material is None:
            return {"material_id": material_id, "status": "missing"}
        assets = [LearningAsset(**item) for item in (material.learning_assets or [])]
        processing_assets = [
            asset.model_copy(
                update={
                    "generated_image_status": MediaGenerationStatus.processing,
                    "tts_us_status": MediaGenerationStatus.processing,
                    "tts_uk_status": MediaGenerationStatus.processing,
                }
            )
            for asset in assets
        ]
        material.learning_assets = [asset.model_dump(mode="json") for asset in processing_assets]
        db.add(material)
        db.commit()

        provider = HN014MockMediaProvider(public_base_url=settings.public_base_url)
        ready_assets = provider.apply(processing_assets)
        material.learning_assets = [asset.model_dump(mode="json") for asset in ready_assets]
        db.add(material)
        db.commit()
    return {"material_id": material_id, "status": "ready"}
```

- [ ] **Step 6: Run tests**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_material_failures.py::test_confirm_persists_learning_assets_and_enqueues_media -q
services/workers/.venv/bin/python -m pytest services/workers/tests/test_material_job_task.py::test_media_worker_fills_mock_image_and_tts_urls -q
```

Expected: both pass.

- [ ] **Step 7: Commit**

```bash
git add services/api/app/services/media_queue.py services/api/app/api/routes/material_jobs.py services/workers/workers_app/tasks.py services/api/tests/test_material_failures.py services/workers/tests/test_material_job_task.py
git commit -m "feat: process learning asset media"
```

---

### Task 6: Knowledge Pack and Review Tasks from Learning Assets

**Files:**
- Modify: `services/api/app/services/pipeline.py`
- Test: `services/api/tests/test_material_failures.py`
- Test: `services/api/tests/test_vertical_slice.py`

- [ ] **Step 1: Write failing knowledge pack test**

Add to `services/api/tests/test_material_failures.py`:

```python
def test_confirm_builds_knowledge_pack_from_learning_assets(api_client, monkeypatch) -> None:
    headers, _ = auth_headers(api_client, auth_code="learning-assets-pack-parent")
    child_id = _create_child(api_client, headers)
    material_id, job_id = _create_material(api_client, headers, child_id)
    monkeypatch.setattr("app.api.routes.material_jobs.enqueue_learning_asset_media_job", lambda _: None)

    with SessionLocal() as db:
        job = db.get(MaterialParseJobModel, job_id)
        job.status = JobStatus.needs_review.value
        job.draft_title = "Qq Rr Storybook"
        job.draft_topic = "phonics"
        job.draft_vocabulary = ["queen"]
        job.draft_sentences = ["Find the queen."]
        job.draft_learning_assets = [
            {
                "id": "asset_queen",
                "text": "queen",
                "kind": "word",
                "translation": "女王",
                "source_page_index": 1,
                "pronunciation_text": "queen",
                "image_prompt": "参考讲义女王线稿生成彩色图。",
                "difficulty": "easy",
                "teaching_note": "让孩子读 queen。",
                "generated_image_url": "http://testserver/mock-media/hn014/images/queen.svg",
                "tts_us_url": "http://testserver/mock-media/hn014/tts/us/queen.m4a",
            },
            {
                "id": "asset_find_the_queen",
                "text": "Find the queen.",
                "kind": "sentence",
                "translation": "找到女王。",
                "source_page_index": 1,
                "pronunciation_text": "Find the queen.",
                "image_prompt": "参考讲义女王迷宫生成彩色图。",
                "difficulty": "easy",
                "teaching_note": "让孩子跟读整句。",
                "tts_us_url": "http://testserver/mock-media/hn014/tts/us/find_the_queen.m4a",
            },
        ]
        db.add(job)
        db.commit()

    response = api_client.post(f"/v1/material-jobs/{job_id}/confirm", json={}, headers=headers)
    assert response.status_code == 200

    pack_response = api_client.get(f"/v1/knowledge-packs/{material_id}", headers=headers)
    pack = pack_response.json()["knowledge_pack"]
    assert pack["vocabulary_items"][0]["word"] == "queen"
    assert pack["vocabulary_items"][0]["meaning_cn"] == "女王"
    assert pack["sentence_patterns"][0]["sentence"] == "Find the queen."
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_material_failures.py::test_confirm_builds_knowledge_pack_from_learning_assets -q
```

Expected: fails because `build_knowledge_assets` ignores `draft_learning_assets`.

- [ ] **Step 3: Update local parser to prefer learning assets**

Modify `StubLanguageParsingProvider.generate_knowledge_pack` so the first branch uses confirmed learning assets:

```python
def generate_knowledge_pack(self, material: CourseMaterial, job: MaterialParseJob) -> KnowledgePack:
    if job.draft_learning_assets or material.learning_assets:
        return _knowledge_pack_from_learning_assets(material, job)
```

Add the helper below `StubLanguageParsingProvider`:

```python
def _knowledge_pack_from_learning_assets(material: CourseMaterial, job: MaterialParseJob) -> KnowledgePack:
    knowledge_pack_id = f"knowledge_{uuid4().hex[:8]}"
    assets = job.draft_learning_assets or material.learning_assets
    vocabulary_items = [
        VocabularyItem(
            id=f"word_{uuid4().hex[:8]}",
            knowledge_pack_id=knowledge_pack_id,
            word=asset.text,
            meaning_cn=asset.translation,
            image_url=asset.generated_image_url,
            audio_url=asset.tts_us_url if asset.primary_accent == PrimaryAccent.us else asset.tts_uk_url,
            example_sentence=next((item.text for item in assets if item.kind == "sentence" and asset.text.lower() in item.text.lower()), ""),
        )
        for asset in assets
        if asset.kind in {"word", "phrase"}
    ]
    sentence_patterns = [
        SentencePattern(
            id=f"sentence_{uuid4().hex[:8]}",
            knowledge_pack_id=knowledge_pack_id,
            sentence=asset.text,
            meaning_cn=asset.translation,
            usage_type="跟读句型",
            audio_url=asset.tts_us_url if asset.primary_accent == PrimaryAccent.us else asset.tts_uk_url,
        )
        for asset in assets
        if asset.kind == "sentence"
    ]
    return KnowledgePack(
        id=knowledge_pack_id,
        material_id=material.id,
        topic=job.draft_topic or material.topic or "课堂复习",
        difficulty_band=DifficultyBand.repeat,
        lesson_summary=f"本课围绕 {job.draft_topic or material.topic or material.title} 展开，重点复习 {', '.join(item.word for item in vocabulary_items[:3])}。",
        review_recommendation="先看彩色图和听发音，再进行跟读与选择题练习。",
        vocabulary_items=vocabulary_items,
        sentence_patterns=sentence_patterns,
    )
```

- [ ] **Step 4: Update review task generation**

When learning assets exist, create tasks with `asset_id`:

```python
ReviewTask(
    id=f"task_{uuid4().hex[:8]}",
    child_id=material.child_id,
    material_id=material.id,
    task_type=TaskType.flashcard,
    difficulty="easy",
    content_json={
        "asset_id": asset.id,
        "prompt": f"看图并跟读：{asset.text}",
        "word": asset.text,
        "translation": asset.translation,
        "image_url": asset.generated_image_url,
        "audio_url": asset.tts_us_url if asset.primary_accent == PrimaryAccent.us else asset.tts_uk_url,
    },
    due_date=datetime.now(timezone.utc),
    status=ReviewTaskStatus.pending,
)
```

For sentence assets, create `TaskType.flashcard` tasks with `prompt=f"跟读句子：{asset.text}"`. Keep total tasks small by using `assets[:5]`.

- [ ] **Step 5: Run tests**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_material_failures.py::test_confirm_builds_knowledge_pack_from_learning_assets services/api/tests/test_vertical_slice.py -q
```

Expected: selected tests pass.

- [ ] **Step 6: Commit**

```bash
git add services/api/app/services/pipeline.py services/api/tests/test_material_failures.py services/api/tests/test_vertical_slice.py
git commit -m "feat: derive review content from learning assets"
```

---

### Task 7: Primary Accent API

**Files:**
- Modify: `services/api/app/api/routes/materials.py`
- Modify: `services/api/app/models/contracts.py`
- Test: `services/api/tests/test_material_failures.py`

- [ ] **Step 1: Write failing API test**

Add:

```python
def test_update_learning_asset_primary_accent(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="primary-accent-parent")
    child_id = _create_child(api_client, headers)
    material_id, _ = _create_material(api_client, headers, child_id)
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, material_id)
        material.learning_assets = [
            {
                "id": "asset_queen",
                "text": "queen",
                "kind": "word",
                "translation": "女王",
                "source_page_index": 1,
                "pronunciation_text": "queen",
                "image_prompt": "参考讲义生成彩色图。",
                "difficulty": "easy",
                "teaching_note": "读 queen。",
                "primary_accent": "us",
            }
        ]
        db.add(material)
        db.commit()

    response = api_client.patch(
        f"/v1/materials/{material_id}/learning-assets/asset_queen/primary-accent",
        json={"primary_accent": "uk"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["material"]["learning_assets"][0]["primary_accent"] == "uk"
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_material_failures.py::test_update_learning_asset_primary_accent -q
```

Expected: `404 Not Found`.

- [ ] **Step 3: Add request model**

In `services/api/app/models/contracts.py`:

```python
class LearningAssetPrimaryAccentUpdate(BaseModel):
    primary_accent: PrimaryAccent
```

- [ ] **Step 4: Add route**

In `services/api/app/api/routes/materials.py`:

```python
from app.models.contracts import (
    CourseMaterial,
    JobStatus,
    LearningAssetPrimaryAccentUpdate,
    MaterialCreateResponse,
    MaterialDetailResponse,
    MaterialStatus,
)


@router.patch("/{material_id}/learning-assets/{asset_id}/primary-accent", response_model=MaterialDetailResponse)
def update_learning_asset_primary_accent(
    material_id: str,
    asset_id: str,
    payload: LearningAssetPrimaryAccentUpdate,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> MaterialDetailResponse:
    material = _get_owned_material(db, current_parent.id, material_id)
    assets = []
    found = False
    for item in material.learning_assets or []:
        if item.get("id") == asset_id:
            item = {**item, "primary_accent": payload.primary_accent.value}
            found = True
        assets.append(item)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning asset not found")
    material.learning_assets = assets
    db.add(material)
    db.commit()
    db.refresh(material)
    latest_job_ids = _latest_job_ids(db, [material.id])
    return MaterialDetailResponse(
        material=course_material_from_model(material, parse_job_id=latest_job_ids.get(material.id, ""))
    )
```

- [ ] **Step 5: Run test**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_material_failures.py::test_update_learning_asset_primary_accent -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add services/api/app/api/routes/materials.py services/api/app/models/contracts.py services/api/tests/test_material_failures.py
git commit -m "feat: update learning asset primary accent"
```

---

### Task 8: Dart Contracts and Repository Support

**Files:**
- Modify: `packages/contracts/lib/src/models.dart`
- Modify: `apps/mobile/pubspec.yaml`
- Modify: `apps/mobile/lib/features/materials/data/app_repository.dart`
- Test: `apps/mobile/test/features/materials/data/app_repository_test.dart`

- [ ] **Step 1: Write failing Flutter repository test**

Append to `apps/mobile/test/features/materials/data/app_repository_test.dart`:

```dart
test('parses learning assets and rewrites mock media URLs', () async {
  final dio = Dio(BaseOptions(baseUrl: 'http://127.0.0.1:8000/v1'))
    ..httpClientAdapter = SequenceDioAdapter([
      (_) => ResponseBody.fromString(
            jsonEncode(<String, dynamic>{
              'material': <String, dynamic>{
                'id': 'material_1',
                'child_id': 'child_1',
                'teacher_name': '外教课',
                'lesson_date': '2026-05-12',
                'title': 'Qq Rr Storybook',
                'topic': 'phonics',
                'status': 'ready',
                'source_images': <String>[],
                'pdf_url': '',
                'ocr_text': '',
                'tags': <String>[],
                'image_records': <Map<String, dynamic>>[],
                'learning_assets': <Map<String, dynamic>>[
                  <String, dynamic>{
                    'id': 'asset_queen',
                    'text': 'queen',
                    'kind': 'word',
                    'translation': '女王',
                    'source_page_index': 1,
                    'source_bbox': <String, dynamic>{'x': 0.05, 'y': 0.14, 'width': 0.43, 'height': 0.35},
                    'source_visual_description': '迷宫里的女王。',
                    'pronunciation_text': 'queen',
                    'image_prompt': '参考讲义生成彩色图。',
                    'difficulty': 'easy',
                    'teaching_note': '读 queen。',
                    'generated_image_status': 'ready',
                    'generated_image_url': 'http://localhost:8000/mock-media/hn014/images/queen.svg',
                    'tts_us_status': 'ready',
                    'tts_us_url': 'http://localhost:8000/mock-media/hn014/tts/us/queen.m4a',
                    'tts_uk_status': 'ready',
                    'tts_uk_url': 'http://localhost:8000/mock-media/hn014/tts/uk/queen.m4a',
                    'primary_accent': 'us',
                  },
                ],
              },
            }),
            200,
            headers: <String, List<String>>{Headers.contentTypeHeader: <String>['application/json']},
          ),
    ]);
  final repository = AppRepository(dio, accessToken: () => 'token', refreshSession: () async => false);

  final material = await repository.getMaterial('material_1');

  expect(material.learningAssets.single.text, 'queen');
  expect(material.learningAssets.single.sourceBbox?.x, 0.05);
  expect(material.learningAssets.single.generatedImageUrl, 'http://127.0.0.1:8000/mock-media/hn014/images/queen.svg');
});
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
flutter test test/features/materials/data/app_repository_test.dart
```

Expected: fails because `learningAssets` does not exist.

- [ ] **Step 3: Add Dart models**

Modify `packages/contracts/lib/src/models.dart`:

```dart
@immutable
class SourceBoundingBox {
  const SourceBoundingBox({
    required this.x,
    required this.y,
    required this.width,
    required this.height,
  });

  final double x;
  final double y;
  final double width;
  final double height;

  factory SourceBoundingBox.fromJson(JsonMap json) => SourceBoundingBox(
        x: doubleFromJson(json['x']) ?? 0,
        y: doubleFromJson(json['y']) ?? 0,
        width: doubleFromJson(json['width']) ?? 1,
        height: doubleFromJson(json['height']) ?? 1,
      );

  JsonMap toJson() => <String, dynamic>{
        'x': x,
        'y': y,
        'width': width,
        'height': height,
      };
}

@immutable
class LearningAsset {
  const LearningAsset({
    required this.id,
    required this.text,
    required this.kind,
    required this.translation,
    required this.sourcePageIndex,
    required this.sourceBbox,
    required this.sourceVisualDescription,
    required this.pronunciationText,
    required this.imagePrompt,
    required this.difficulty,
    required this.teachingNote,
    required this.isCore,
    required this.generatedImageStatus,
    required this.generatedImageUrl,
    required this.generatedImageObjectKey,
    required this.ttsUsStatus,
    required this.ttsUsUrl,
    required this.ttsUsObjectKey,
    required this.ttsUkStatus,
    required this.ttsUkUrl,
    required this.ttsUkObjectKey,
    required this.primaryAccent,
  });

  final String id;
  final String text;
  final String kind;
  final String translation;
  final int sourcePageIndex;
  final SourceBoundingBox? sourceBbox;
  final String sourceVisualDescription;
  final String pronunciationText;
  final String imagePrompt;
  final String difficulty;
  final String teachingNote;
  final bool isCore;
  final String generatedImageStatus;
  final String generatedImageUrl;
  final String generatedImageObjectKey;
  final String ttsUsStatus;
  final String ttsUsUrl;
  final String ttsUsObjectKey;
  final String ttsUkStatus;
  final String ttsUkUrl;
  final String ttsUkObjectKey;
  final String primaryAccent;

  factory LearningAsset.fromJson(JsonMap json) => LearningAsset(
        id: json['id'] as String? ?? '',
        text: json['text'] as String? ?? '',
        kind: json['kind'] as String? ?? 'word',
        translation: json['translation'] as String? ?? '',
        sourcePageIndex: json['source_page_index'] as int? ?? 1,
        sourceBbox: json['source_bbox'] is JsonMap
            ? SourceBoundingBox.fromJson(json['source_bbox'] as JsonMap)
            : null,
        sourceVisualDescription: json['source_visual_description'] as String? ?? '',
        pronunciationText: json['pronunciation_text'] as String? ?? '',
        imagePrompt: json['image_prompt'] as String? ?? '',
        difficulty: json['difficulty'] as String? ?? 'easy',
        teachingNote: json['teaching_note'] as String? ?? '',
        isCore: json['is_core'] as bool? ?? true,
        generatedImageStatus: json['generated_image_status'] as String? ?? 'pending',
        generatedImageUrl: json['generated_image_url'] as String? ?? '',
        generatedImageObjectKey: json['generated_image_object_key'] as String? ?? '',
        ttsUsStatus: json['tts_us_status'] as String? ?? 'pending',
        ttsUsUrl: json['tts_us_url'] as String? ?? '',
        ttsUsObjectKey: json['tts_us_object_key'] as String? ?? '',
        ttsUkStatus: json['tts_uk_status'] as String? ?? 'pending',
        ttsUkUrl: json['tts_uk_url'] as String? ?? '',
        ttsUkObjectKey: json['tts_uk_object_key'] as String? ?? '',
        primaryAccent: json['primary_accent'] as String? ?? 'us',
      );
}
```

Add `learningAssets` to `CourseMaterial` and `draftLearningAssets` to `MaterialParseJob`.

- [ ] **Step 4: Add flutter_svg dependency**

Modify `apps/mobile/pubspec.yaml`:

```yaml
dependencies:
  flutter_svg: ^2.2.0
```

Run:

```bash
flutter pub get
```

Expected: `pubspec.lock` updates and no resolver error.

- [ ] **Step 5: Normalize media URLs**

In `AppRepository._normalizeMaterialImageUrls`, also normalize `learning_assets`:

```dart
final assets = normalized['learning_assets'];
if (assets is List) {
  normalized['learning_assets'] = assets.map((asset) {
    if (asset is! Map<String, dynamic>) {
      return asset;
    }
    final normalizedAsset = Map<String, dynamic>.from(asset);
    for (final key in <String>['generated_image_url', 'tts_us_url', 'tts_uk_url']) {
      normalizedAsset[key] = _publicRuntimeUrl(normalizedAsset[key] as String? ?? '');
    }
    return normalizedAsset;
  }).toList();
}
```

Rename `_publicUploadUrl` to `_publicRuntimeUrl`, and support both `minio` and `localhost`:

```dart
String _publicRuntimeUrl(String url) {
  final parsed = Uri.tryParse(url);
  if (parsed == null) {
    return url;
  }
  if (parsed.host == 'minio') {
    final segments = parsed.pathSegments;
    if (segments.length < 2) {
      return url;
    }
    final apiBase = Uri.parse(_dio.options.baseUrl);
    return apiBase.replace(pathSegments: <String>['uploads', ...segments.skip(1)], queryParameters: null, fragment: null).toString();
  }
  if (parsed.host == 'localhost') {
    final apiBase = Uri.parse(_dio.options.baseUrl);
    return parsed.replace(scheme: apiBase.scheme, host: apiBase.host, port: apiBase.port).toString();
  }
  return url;
}
```

- [ ] **Step 6: Add repository method for primary accent**

```dart
Future<CourseMaterial> updateLearningAssetPrimaryAccent({
  required String materialId,
  required String assetId,
  required String primaryAccent,
}) async {
  final response = await _authorizedRequest<Map<String, dynamic>>(
    (options) => _dio.patch<Map<String, dynamic>>(
      '/materials/$materialId/learning-assets/$assetId/primary-accent',
      data: <String, dynamic>{'primary_accent': primaryAccent},
      options: options,
    ),
  );
  final payload = response.data ?? const <String, dynamic>{};
  return _courseMaterialFromJson(payload['material'] as Map<String, dynamic>);
}
```

- [ ] **Step 7: Run tests**

Run:

```bash
flutter test test/features/materials/data/app_repository_test.dart
```

Expected: all tests in the file pass.

- [ ] **Step 8: Commit**

```bash
git add packages/contracts/lib/src/models.dart apps/mobile/pubspec.yaml apps/mobile/pubspec.lock apps/mobile/lib/features/materials/data/app_repository.dart apps/mobile/test/features/materials/data/app_repository_test.dart
git commit -m "feat: parse learning assets in mobile contracts"
```

---

### Task 9: AI Review Learning Asset UI with Source Crop Preview

**Files:**
- Modify: `apps/mobile/lib/features/materials/presentation/material_review_screen.dart`
- Test: `apps/mobile/test/features/materials/presentation/scan_review_navigation_test.dart`

- [ ] **Step 1: Write failing widget test**

Add to `scan_review_navigation_test.dart`:

```dart
testWidgets('AI review page shows learning assets with source page label', (tester) async {
  final job = MaterialParseJob(
    id: 'job_1',
    materialId: 'material_1',
    status: JobStatus.needsReview,
    confidenceSummary: 'high',
    warnings: const <String>[],
    startedAt: DateTime(2026, 5, 12),
    finishedAt: null,
    draftTitle: 'Qq Rr Storybook',
    draftTopic: 'phonics',
    draftVocabulary: const <String>['queen'],
    draftSentences: const <String>['Find the queen.'],
    draftLearningAssets: const <LearningAsset>[
      LearningAsset(
        id: 'asset_queen',
        text: 'queen',
        kind: 'word',
        translation: '女王',
        sourcePageIndex: 1,
        sourceBbox: SourceBoundingBox(x: 0.05, y: 0.14, width: 0.43, height: 0.35),
        sourceVisualDescription: '迷宫里的女王。',
        pronunciationText: 'queen',
        imagePrompt: '参考讲义生成彩色图。',
        difficulty: 'easy',
        teachingNote: '读 queen。',
        isCore: true,
        generatedImageStatus: 'pending',
        generatedImageUrl: '',
        generatedImageObjectKey: '',
        ttsUsStatus: 'pending',
        ttsUsUrl: '',
        ttsUsObjectKey: '',
        ttsUkStatus: 'pending',
        ttsUkUrl: '',
        ttsUkObjectKey: '',
        primaryAccent: 'us',
      ),
    ],
  );

  await pumpMaterialReviewScreen(tester, job: job);

  expect(find.text('核心学习资产'), findsOneWidget);
  expect(find.text('queen'), findsWidgets);
  expect(find.text('女王'), findsOneWidget);
  expect(find.text('第 1 页'), findsWidgets);
});
```

- [ ] **Step 2: Run widget test and verify failure**

Run:

```bash
flutter test test/features/materials/presentation/scan_review_navigation_test.dart
```

Expected: fails because the learning asset section is absent.

- [ ] **Step 3: Add learning asset section**

In `material_review_screen.dart`, after `_ImageRecordsSection`, add:

```dart
if (job.draftLearningAssets.isNotEmpty) ...<Widget>[
  const SizedBox(height: AppSpacing.md),
  _LearningAssetsSection(
    assets: job.draftLearningAssets,
    imageRecords: job.draftImageRecords,
  ),
],
```

Add widget:

```dart
class _LearningAssetsSection extends StatelessWidget {
  const _LearningAssetsSection({
    required this.assets,
    required this.imageRecords,
  });

  final List<LearningAsset> assets;
  final List<MaterialImageRecord> imageRecords;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: const <Widget>[
            Text('核心学习资产', style: AppTextStyles.cardTitle),
            SizedBox(width: AppSpacing.sm),
            StickerBadge(label: '1-20 个', color: AppColors.butterYellow),
          ],
        ),
        const SizedBox(height: AppSpacing.xs),
        ...assets.map((asset) => _LearningAssetReviewTile(asset: asset, imageRecords: imageRecords)),
      ],
    );
  }
}
```

Add tile:

```dart
class _LearningAssetReviewTile extends StatelessWidget {
  const _LearningAssetReviewTile({required this.asset, required this.imageRecords});

  final LearningAsset asset;
  final List<MaterialImageRecord> imageRecords;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: AppColors.softSheet,
          borderRadius: BorderRadius.circular(AppRadii.card),
        ),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.sm),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              _SourceCropPreview(asset: asset, imageRecords: imageRecords),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(asset.text, style: AppTextStyles.cardTitle),
                    if (asset.translation.isNotEmpty) Text(asset.translation),
                    Text('${_assetKindLabel(asset.kind)} · 第 ${asset.sourcePageIndex} 页', style: AppTextStyles.helper),
                    if (asset.teachingNote.isNotEmpty) Text(asset.teachingNote, style: AppTextStyles.helper),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 4: Add source crop preview with page-thumbnail fallback**

```dart
class _SourceCropPreview extends StatelessWidget {
  const _SourceCropPreview({required this.asset, required this.imageRecords});

  final LearningAsset asset;
  final List<MaterialImageRecord> imageRecords;

  @override
  Widget build(BuildContext context) {
    MaterialImageRecord? record;
    for (final item in imageRecords) {
      if (item.pageIndex == asset.sourcePageIndex) {
        record = item;
        break;
      }
    }
    if (record == null || record.url.isEmpty) {
      return Container(
        width: 72,
        height: 72,
        decoration: BoxDecoration(
          color: AppColors.paperWhite,
          borderRadius: BorderRadius.circular(AppRadii.input),
        ),
        child: const Icon(Icons.crop_rounded),
      );
    }
    final bbox = asset.sourceBbox;
    if (bbox == null) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(AppRadii.input),
        child: Image.network(record.url, width: 72, height: 72, fit: BoxFit.cover),
      );
    }
    final width = _boundedFraction(bbox.width, minimum: 0.05);
    final height = _boundedFraction(bbox.height, minimum: 0.05);
    final x = _boundedFraction(bbox.x);
    final y = _boundedFraction(bbox.y);
    final scaledWidth = 72 / width;
    final scaledHeight = 72 / height;
    return ClipRRect(
      borderRadius: BorderRadius.circular(AppRadii.input),
      child: SizedBox(
        width: 72,
        height: 72,
        child: ClipRect(
          child: OverflowBox(
            alignment: Alignment.topLeft,
            minWidth: scaledWidth,
            maxWidth: scaledWidth,
            minHeight: scaledHeight,
            maxHeight: scaledHeight,
            child: Transform.translate(
              offset: Offset(-x * scaledWidth, -y * scaledHeight),
              child: Image.network(
                record.url,
                width: scaledWidth,
                height: scaledHeight,
                fit: BoxFit.fill,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

double _boundedFraction(double value, {double minimum = 0, double maximum = 1}) {
  return value.clamp(minimum, maximum).toDouble();
}
```

- [ ] **Step 5: Run widget test**

Run:

```bash
flutter test test/features/materials/presentation/scan_review_navigation_test.dart
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add apps/mobile/lib/features/materials/presentation/material_review_screen.dart apps/mobile/test/features/materials/presentation/scan_review_navigation_test.dart
git commit -m "feat: show learning assets in review"
```

---

### Task 10: Lesson Detail Learning Asset Media UI

**Files:**
- Modify: `apps/mobile/lib/features/lessons/presentation/lesson_detail_screen.dart`
- Test: `apps/mobile/test/features/materials/presentation/scan_review_navigation_test.dart`

- [ ] **Step 1: Write failing lesson detail test**

Add:

```dart
testWidgets('lesson detail shows learning asset media and tts status', (tester) async {
  final material = readyMaterial(
    learningAssets: const <LearningAsset>[
      LearningAsset(
        id: 'asset_queen',
        text: 'queen',
        kind: 'word',
        translation: '女王',
        sourcePageIndex: 1,
        sourceBbox: null,
        sourceVisualDescription: '迷宫里的女王。',
        pronunciationText: 'queen',
        imagePrompt: '参考讲义生成彩色图。',
        difficulty: 'easy',
        teachingNote: '读 queen。',
        isCore: true,
        generatedImageStatus: 'ready',
        generatedImageUrl: 'http://127.0.0.1:8000/mock-media/hn014/images/queen.svg',
        generatedImageObjectKey: '',
        ttsUsStatus: 'ready',
        ttsUsUrl: 'http://127.0.0.1:8000/mock-media/hn014/tts/us/queen.m4a',
        ttsUsObjectKey: '',
        ttsUkStatus: 'ready',
        ttsUkUrl: 'http://127.0.0.1:8000/mock-media/hn014/tts/uk/queen.m4a',
        ttsUkObjectKey: '',
        primaryAccent: 'us',
      ),
    ],
  );

  await pumpLessonDetailScreen(tester, material: material);

  expect(find.text('核心学习资产'), findsOneWidget);
  expect(find.text('queen'), findsWidgets);
  expect(find.text('女王'), findsOneWidget);
  expect(find.text('美式'), findsOneWidget);
  expect(find.text('英式'), findsOneWidget);
});
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
flutter test test/features/materials/presentation/scan_review_navigation_test.dart
```

Expected: fails because lesson detail does not render `learningAssets`.

- [ ] **Step 3: Add SVG/Network media widget**

At top of `lesson_detail_screen.dart`:

```dart
import 'package:flutter_svg/flutter_svg.dart';
```

Add helper:

```dart
class _GeneratedAssetImage extends StatelessWidget {
  const _GeneratedAssetImage({required this.asset});

  final LearningAsset asset;

  @override
  Widget build(BuildContext context) {
    if (asset.generatedImageStatus != 'ready' || asset.generatedImageUrl.isEmpty) {
      return Container(
        width: 88,
        height: 88,
        decoration: BoxDecoration(
          color: AppColors.softSheet,
          borderRadius: BorderRadius.circular(AppRadii.input),
        ),
        child: Icon(
          asset.generatedImageStatus == 'failed' ? Icons.error_outline_rounded : Icons.hourglass_top_rounded,
          color: AppColors.cocoaCoral,
        ),
      );
    }
    if (asset.generatedImageUrl.toLowerCase().endsWith('.svg')) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(AppRadii.input),
        child: SvgPicture.network(asset.generatedImageUrl, width: 88, height: 88, fit: BoxFit.cover),
      );
    }
    return ClipRRect(
      borderRadius: BorderRadius.circular(AppRadii.input),
      child: Image.network(asset.generatedImageUrl, width: 88, height: 88, fit: BoxFit.cover),
    );
  }
}
```

- [ ] **Step 4: Add learning assets card**

In lesson detail after `_SourceImagesCard`, add:

```dart
if (material.learningAssets.isNotEmpty) ...<Widget>[
  const SizedBox(height: AppSpacing.md),
  _LearningAssetsCard(
    materialId: material.id,
    assets: material.learningAssets,
  ),
],
```

Add:

```dart
class _LearningAssetsCard extends ConsumerWidget {
  const _LearningAssetsCard({required this.materialId, required this.assets});

  final String materialId;
  final List<LearningAsset> assets;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('核心学习资产', style: AppTextStyles.sectionTitle),
          const SizedBox(height: AppSpacing.sm),
          ...assets.map((asset) => _LearningAssetDetailTile(materialId: materialId, asset: asset)),
        ],
      ),
    );
  }
}
```

Add detail tile:

```dart
class _LearningAssetDetailTile extends ConsumerWidget {
  const _LearningAssetDetailTile({required this.materialId, required this.asset});

  final String materialId;
  final LearningAsset asset;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: AppColors.softSheet,
          borderRadius: BorderRadius.circular(AppRadii.card),
        ),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.sm),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              _GeneratedAssetImage(asset: asset),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(asset.text, style: AppTextStyles.cardTitle),
                    if (asset.translation.isNotEmpty) Text(asset.translation),
                    Text('${_assetKindLabel(asset.kind)} · 第 ${asset.sourcePageIndex} 页', style: AppTextStyles.helper),
                    Text('配图：${_mediaStatusLabel(asset.generatedImageStatus)}', style: AppTextStyles.helper),
                    Text('美式：${_mediaStatusLabel(asset.ttsUsStatus)} · 英式：${_mediaStatusLabel(asset.ttsUkStatus)}', style: AppTextStyles.helper),
                    const SizedBox(height: AppSpacing.xs),
                    SegmentedButton<String>(
                      segments: const <ButtonSegment<String>>[
                        ButtonSegment<String>(value: 'us', label: Text('美式')),
                        ButtonSegment<String>(value: 'uk', label: Text('英式')),
                      ],
                      selected: <String>{asset.primaryAccent},
                      onSelectionChanged: (selection) async {
                        final selected = selection.single;
                        await ref.read(appRepositoryProvider).updateLearningAssetPrimaryAccent(
                              materialId: materialId,
                              assetId: asset.id,
                              primaryAccent: selected,
                            );
                        ref.invalidate(materialProvider(materialId));
                      },
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

Add labels:

```dart
String _assetKindLabel(String kind) {
  return switch (kind) {
    'sentence' => '句子',
    'phrase' => '短语',
    _ => '单词',
  };
}

String _mediaStatusLabel(String status) {
  return switch (status) {
    'ready' => '已生成',
    'processing' => '生成中',
    'failed' => '失败',
    _ => '等待生成',
  };
}
```

- [ ] **Step 5: Run widget tests**

Run:

```bash
flutter test test/features/materials/presentation/scan_review_navigation_test.dart
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add apps/mobile/lib/features/lessons/presentation/lesson_detail_screen.dart apps/mobile/test/features/materials/presentation/scan_review_navigation_test.dart
git commit -m "feat: show learning asset media in lessons"
```

---

### Task 11: Harness Documentation and Evidence Hooks

**Files:**
- Modify: `docs/harness/upload-recognition-loop.md`
- Modify: `docs/harness/mvp-readiness-checklist.md`
- Create: `dist/harness/HN-014/.gitkeep`

- [ ] **Step 1: Update upload recognition requirements**

In `docs/harness/upload-recognition-loop.md`, add section:

```markdown
### HN-014：讲义学习资产自动生成

**目标：** 讲义识别后生成核心学习资产，常规目标 8-15 个、绝对范围 1-20 个，每条资产保留英文、中文释义、来源页、讲义裁剪区域、发音文本、配图提示、媒体状态和主发音。

**范围：**
- AI 校对页展示文字学习资产和来源讲义裁剪图。
- 家长确认后固化到课程详情。
- 后台异步填充彩色配图和英式/美式 TTS mock 媒体。
- 本期使用 Qq/Rr 预置 mock 媒体，不接真实外部图片/TTS provider。

**验收：**
- `job.draft_learning_assets` 数量为 1-20；常规讲义优先保留 8-15 个核心词、短语或句子。
- `material.learning_assets` 确认后存在。
- 每条资产包含 `source_bbox` 或能回退到来源页缩略图。
- 课程详情展示彩色配图状态和英式/美式 TTS 状态。

**证据目录：** `dist/harness/HN-014/`
```

- [ ] **Step 2: Update readiness checklist**

In `docs/harness/mvp-readiness-checklist.md`, add:

```markdown
- [ ] `HN-014` 讲义学习资产自动生成：需要保存 job/material JSON 摘录、AI 校对页截图和课程详情媒体状态截图。
```

Add evidence note:

```markdown
`HN-014` 验收证据：
- `dist/harness/HN-014/job-learning-assets.json`
- `dist/harness/HN-014/material-learning-assets.json`
- `dist/harness/HN-014/review-learning-assets.png`
- `dist/harness/HN-014/lesson-learning-assets.png`
```

- [ ] **Step 3: Create evidence directory marker**

Run:

```bash
mkdir -p dist/harness/HN-014
touch dist/harness/HN-014/.gitkeep
```

- [ ] **Step 4: Commit**

```bash
git add docs/harness/upload-recognition-loop.md docs/harness/mvp-readiness-checklist.md dist/harness/HN-014/.gitkeep
git commit -m "docs: add hn014 learning asset harness"
```

---

### Task 12: End-to-End Verification

**Files:**
- Source files are not modified in this verification task.
- Evidence output: `dist/harness/HN-014/`

- [ ] **Step 1: Run backend tests**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests
```

Expected: all API tests pass.

- [ ] **Step 2: Run worker tests**

Run:

```bash
services/workers/.venv/bin/python -m pytest services/workers/tests
```

Expected: all worker tests pass.

- [ ] **Step 3: Run Flutter tests and analyze**

Run:

```bash
cd apps/mobile
flutter test
flutter analyze
```

Expected: all Flutter tests pass and `No issues found`.

- [ ] **Step 4: Apply DB migration and rebuild API/worker**

Run:

```bash
make api-migrate
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d --build api worker
curl -sS http://127.0.0.1:8000/healthz
```

Expected:

```json
{"status":"ok"}
```

- [ ] **Step 5: Simulator upload loop**

Use the existing Qq/Rr images:

- `/Users/chaucermini/Pictures/Photos Library.photoslibrary/resources/derivatives/5/51F1DABE-5F4E-4706-AE97-C6F8AF2F44EB_1_105_c.jpeg`
- `/Users/chaucermini/Pictures/Photos Library.photoslibrary/resources/derivatives/F/F718C9F0-B90B-4D97-A017-52DDA6631E0D_1_105_c.jpeg`

Run app:

```bash
cd apps/mobile
flutter run -d BB68E4D7-5773-4A3C-9556-37D0B0DE24EF --dart-define=API_BASE_URL=http://127.0.0.1:8000/v1
```

Expected manual result:

- 上传页显示两张缩略图。
- AI 校对页显示 `核心学习资产`。
- 每个学习资产显示英文、中文释义、来源页和讲义裁剪预览。
- 确认后课程详情可立即打开。
- 稍后刷新课程详情，彩色配图和英式/美式 TTS 状态显示为已生成。

- [ ] **Step 6: Save JSON evidence**

Replace `material_id` and `job_id` with the IDs from the run:

```bash
mkdir -p dist/harness/HN-014
docker exec learning-english-postgres psql -U learning_english -d learning_english -t -A -c "select jsonb_pretty(draft_learning_assets::jsonb) from material_parse_jobs where id='job_id';" > dist/harness/HN-014/job-learning-assets.json
docker exec learning-english-postgres psql -U learning_english -d learning_english -t -A -c "select jsonb_pretty(learning_assets::jsonb) from course_materials where id='material_id';" > dist/harness/HN-014/material-learning-assets.json
```

Expected:

- `job-learning-assets.json` contains `text`, `source_bbox`, and `image_prompt`.
- `material-learning-assets.json` contains `generated_image_status`, `tts_us_status`, and `tts_uk_status`.

- [ ] **Step 7: Final full status**

Run:

```bash
git status --short
```

Expected: source files are clean. Generated JSON and screenshots under `dist/harness/HN-014/` remain local evidence and are listed in the final handoff.

---

## Self-Review

- Spec coverage:
  - `LearningAsset` model, `source_bbox`, media statuses, primary accent: Task 1 and Task 8.
  - Doubao `learning_assets` output and fallback: Task 2.
  - Draft and confirmed persistence: Task 3 and Task 5.
  - Mock media provider with Qq/Rr pre-generated images and TTS: Task 4 and Task 5.
  - AI 校对页文字资产和来源讲义预览: Task 9.
  - 课程详情彩色配图、TTS 状态和主发音选择: Task 10.
  - Harness docs and evidence: Task 11 and Task 12.
- Placeholder scan:
  - 未发现未落地的占位写法或未定义任务。
  - Each code-changing task includes concrete file paths and code shape.
- Type consistency:
  - Python and Dart both use `source_bbox`, `generated_image_status`, `tts_us_status`, `tts_uk_status`, and `primary_accent`.
  - API field names stay snake_case; Dart properties use camelCase.
