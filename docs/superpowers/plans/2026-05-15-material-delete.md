# HN-015 课程资料左滑删除 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 HN-015：资料库课程卡片支持左滑删除，删除后课程详情、知识包、亲子陪练脚本和复习任务对用户不可见，后台任务不会把已删除资料重新写回可见状态。

**Architecture:** 后端采用“课程资料软删除 + 派生复习数据硬删除”：`CourseMaterialModel.status` 置为 `archived`，同步删除 `KnowledgePackModel`、`ReviewTaskModel`、`ParentCoachingScriptModel`。读取接口统一过滤 `archived`，worker 在写回前后检查归档状态。移动端在资料库卡片外层使用 Flutter `Dismissible` 实现 iOS 风格左滑删除，确认后调用 `DELETE /v1/materials/{id}` 并刷新资料库与复习任务 provider。

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic contracts, Celery worker, pytest, Flutter, Riverpod, Dio, GoRouter, flutter_test.

---

## Scope Check

HN-015 是一个垂直功能，不拆成多个独立计划。它包含 API 删除语义、worker 归档保护、Flutter 左滑交互和 Harness 文档，但这些都服务同一个用户结果：家长删除课程资料后，相关可见学习入口同步消失。

## File Structure

- Modify: `services/api/app/api/routes/materials.py`
  - 新增 `DELETE /v1/materials/{material_id}`。
  - `list_materials` 和 `_get_owned_material` 默认过滤 `archived`。
  - 主发音切换接口通过 `_get_owned_material` 自然拒绝已归档资料。
- Modify: `services/api/app/api/routes/material_jobs.py`
  - `_get_owned_job` 过滤已归档资料，阻止校对页读取、确认和重试归档 job。
- Modify: `services/api/app/api/routes/knowledge.py`
  - `GET /knowledge-packs/{material_id}` 过滤已归档资料。
- Modify: `services/api/app/api/routes/parent_coaching.py`
  - `GET /parent-coaching/{material_id}` 过滤已归档资料。
- Modify: `services/api/app/api/routes/review_tasks.py`
  - 复习任务列表联表过滤已归档资料，避免历史脏任务被展示。
- Create: `services/api/tests/test_material_delete.py`
  - 覆盖删除事务、跨家长隔离、幂等删除、归档后的 job/详情/知识包/亲子脚本/复习任务不可见。
- Modify: `services/workers/workers_app/tasks.py`
  - `process_material_job` 和 `process_learning_asset_media` 在开始和写回前检查 `MaterialStatus.archived`。
- Modify: `services/workers/tests/test_material_job_task.py`
  - 覆盖归档资料不被 worker 写回。
- Modify: `apps/mobile/lib/features/materials/data/materials_repository.dart`
  - repository interface 增加 `deleteMaterial(String materialId)`。
- Modify: `apps/mobile/lib/features/materials/data/app_repository.dart`
  - Dio 实现 `DELETE /materials/{materialId}`。
- Modify: `apps/mobile/lib/features/materials/presentation/materials_library_screen.dart`
  - 课程卡片外层增加 `Dismissible`、确认弹窗、删除成功/失败状态和 provider 刷新。
- Modify: `apps/mobile/lib/core/network/api_error.dart`
  - 增加 `isNotFoundApiError`，供课程详情页展示中文删除态。
- Modify: `apps/mobile/lib/features/lessons/presentation/lesson_detail_screen.dart`
  - 404 时显示 `课程资料不存在或已删除` 并提供返回资料库。
- Create: `apps/mobile/test/features/materials/presentation/materials_library_delete_test.dart`
  - 覆盖左滑、取消、确认、失败恢复。
- Create: `apps/mobile/test/features/lessons/presentation/lesson_detail_deleted_test.dart`
  - 覆盖删除后详情页中文错误态。
- Modify: `docs/harness/upload-recognition-loop.md`
  - 增加 HN-015 需求和验收证据目录。
- Modify: `docs/harness/mvp-readiness-checklist.md`
  - 增加 HN-015 checkbox。

---

### Task 1: API 删除事务与资料过滤

**Files:**
- Modify: `services/api/app/api/routes/materials.py`
- Create: `services/api/tests/test_material_delete.py`

- [ ] **Step 1: Write failing API deletion tests**

Create `services/api/tests/test_material_delete.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone

from app.core.db import SessionLocal
from app.db.models import (
    CourseMaterialModel,
    KnowledgePackModel,
    MaterialParseJobModel,
    ParentCoachingScriptModel,
    ReviewTaskModel,
)
from app.models.contracts import JobStatus, MaterialStatus
from conftest import auth_headers, configure_test_environment


configure_test_environment("learning-english-api-material-delete-")


def _create_child(api_client, headers: dict[str, str], name: str = "Mia") -> str:
    response = api_client.post(
        "/v1/children",
        json={
            "name": name,
            "age": 6,
            "level": "starter",
            "learning_goal": "课后复习更稳定",
            "preferred_review_duration_minutes": 10,
            "parent_notes": "喜欢看图复习",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_material(api_client, headers: dict[str, str], child_id: str) -> tuple[str, str]:
    response = api_client.post(
        "/v1/materials",
        data={
            "child_id": child_id,
            "teacher_name": "Emma",
            "lesson_date": "2026-05-15",
            "title": "Run, Hop, Go!",
            "topic": "Phonics Rr",
            "tags": "phonics",
        },
        files=[("files", ("worksheet.txt", b"A rabbit can hop fast.", "text/plain"))],
        headers=headers,
    )
    assert response.status_code == 201
    payload = response.json()
    return payload["material"]["id"], payload["job"]["id"]


def _seed_ready_derivatives(material_id: str, job_id: str, child_id: str) -> None:
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, material_id)
        job = db.get(MaterialParseJobModel, job_id)
        assert material is not None
        assert job is not None
        material.status = MaterialStatus.ready.value
        material.learning_assets = [
            {
                "id": "asset_rabbit",
                "text": "rabbit",
                "kind": "word",
                "translation": "兔子",
                "primary_accent": "us",
            }
        ]
        job.status = JobStatus.ready.value
        db.add_all([material, job])
        db.add(
            KnowledgePackModel(
                id="knowledge_delete",
                material_id=material_id,
                topic="Phonics Rr",
                difficulty_band="repeat",
                lesson_summary="复习 rabbit。",
                review_recommendation="先看图再跟读。",
                vocabulary_items=[],
                sentence_patterns=[],
            )
        )
        db.add(
            ParentCoachingScriptModel(
                id="coach_delete",
                material_id=material_id,
                title="亲子陪练",
                intro="和孩子一起读 rabbit。",
                steps=[],
            )
        )
        db.add(
            ReviewTaskModel(
                id="task_delete",
                child_id=child_id,
                material_id=material_id,
                task_type="flashcard",
                difficulty="easy",
                content_json={"asset_id": "asset_rabbit", "word": "rabbit"},
                due_date=datetime.now(timezone.utc),
                status="pending",
            )
        )
        db.commit()


def test_delete_material_archives_material_and_removes_visible_derivatives(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="delete-owner")
    child_id = _create_child(api_client, headers)
    material_id, job_id = _create_material(api_client, headers, child_id)
    _seed_ready_derivatives(material_id, job_id, child_id)

    response = api_client.delete(f"/v1/materials/{material_id}", headers=headers)

    assert response.status_code == 204
    list_response = api_client.get("/v1/materials", headers=headers)
    assert list_response.status_code == 200
    assert material_id not in [item["id"] for item in list_response.json()]
    assert api_client.get(f"/v1/materials/{material_id}", headers=headers).status_code == 404
    assert api_client.get(f"/v1/knowledge-packs/{material_id}", headers=headers).status_code == 404
    assert api_client.get(f"/v1/parent-coaching/{material_id}", headers=headers).status_code == 404
    tasks_response = api_client.get(
        "/v1/review-tasks",
        params={"child_id": child_id, "material_id": material_id},
        headers=headers,
    )
    assert tasks_response.status_code == 200
    assert tasks_response.json()["items"] == []

    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, material_id)
        assert material is not None
        assert material.status == MaterialStatus.archived.value
        assert db.get(MaterialParseJobModel, job_id) is not None
        assert db.get(KnowledgePackModel, "knowledge_delete") is None
        assert db.get(ParentCoachingScriptModel, "coach_delete") is None
        assert db.get(ReviewTaskModel, "task_delete") is None


def test_delete_material_is_parent_scoped_and_idempotent(api_client) -> None:
    owner_headers, _ = auth_headers(api_client, auth_code="delete-owner-scoped")
    child_id = _create_child(api_client, owner_headers)
    material_id, job_id = _create_material(api_client, owner_headers, child_id)
    _seed_ready_derivatives(material_id, job_id, child_id)

    other_headers, _ = auth_headers(api_client, auth_code="delete-other-parent")
    other_response = api_client.delete(f"/v1/materials/{material_id}", headers=other_headers)
    assert other_response.status_code == 404

    first_delete = api_client.delete(f"/v1/materials/{material_id}", headers=owner_headers)
    second_delete = api_client.delete(f"/v1/materials/{material_id}", headers=owner_headers)
    assert first_delete.status_code == 204
    assert second_delete.status_code == 204
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_material_delete.py -q
```

Expected: FAIL because `DELETE /v1/materials/{material_id}` returns `405 Method Not Allowed` or the derivatives remain visible.

- [ ] **Step 3: Implement delete route and material filtering**

Modify `services/api/app/api/routes/materials.py` imports:

```python
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import delete, select
```

Add `ParentCoachingScriptModel` to the existing model import list:

```python
    ParentAccountModel,
    ParentCoachingScriptModel,
    ReviewTaskModel,
    StoredAssetModel,
```

Update `list_materials` query:

```python
    stmt = select(CourseMaterialModel).where(
        CourseMaterialModel.child_id.in_(child_ids or [""]),
        CourseMaterialModel.status != MaterialStatus.archived.value,
    )
```

Insert this endpoint after `get_material`:

```python
@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(
    material_id: str,
    current_parent: ParentAccountModel = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> Response:
    material = _get_owned_material(db, current_parent.id, material_id, include_archived=True)
    if material.status == MaterialStatus.archived.value:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    material.status = MaterialStatus.archived.value
    db.add(material)
    db.execute(delete(KnowledgePackModel).where(KnowledgePackModel.material_id == material.id))
    db.execute(delete(ParentCoachingScriptModel).where(ParentCoachingScriptModel.material_id == material.id))
    db.execute(delete(ReviewTaskModel).where(ReviewTaskModel.material_id == material.id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

Replace `_get_owned_material` with:

```python
def _get_owned_material(
    db: Session,
    parent_account_id: str,
    material_id: str,
    *,
    include_archived: bool = False,
) -> CourseMaterialModel:
    stmt = (
        select(CourseMaterialModel)
        .join(ChildProfileModel, ChildProfileModel.id == CourseMaterialModel.child_id)
        .where(
            CourseMaterialModel.id == material_id,
            ChildProfileModel.parent_account_id == parent_account_id,
        )
    )
    if not include_archived:
        stmt = stmt.where(CourseMaterialModel.status != MaterialStatus.archived.value)
    material = db.scalar(stmt)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    return material
```

- [ ] **Step 4: Run deletion tests and verify pass**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_material_delete.py -q
```

Expected: PASS for both deletion tests.

- [ ] **Step 5: Commit API deletion route**

Run:

```bash
git add services/api/app/api/routes/materials.py services/api/tests/test_material_delete.py
git commit -m "feat: add material delete endpoint"
```

Expected: commit succeeds and contains only API deletion route plus focused tests.

---

### Task 2: API 归档资料访问保护

**Files:**
- Modify: `services/api/app/api/routes/material_jobs.py`
- Modify: `services/api/app/api/routes/knowledge.py`
- Modify: `services/api/app/api/routes/parent_coaching.py`
- Modify: `services/api/app/api/routes/review_tasks.py`
- Test: `services/api/tests/test_material_delete.py`

- [ ] **Step 1: Write failing archived access tests**

Append to `services/api/tests/test_material_delete.py`:

```python
def test_archived_material_blocks_job_and_primary_accent_routes(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="delete-archived-job-parent")
    child_id = _create_child(api_client, headers)
    material_id, job_id = _create_material(api_client, headers, child_id)
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, material_id)
        job = db.get(MaterialParseJobModel, job_id)
        assert material is not None
        assert job is not None
        material.status = MaterialStatus.archived.value
        material.learning_assets = [
            {
                "id": "asset_rabbit",
                "text": "rabbit",
                "kind": "word",
                "translation": "兔子",
                "primary_accent": "us",
            }
        ]
        job.status = JobStatus.needs_review.value
        db.add_all([material, job])
        db.commit()

    assert api_client.get(f"/v1/material-jobs/{job_id}", headers=headers).status_code == 404
    confirm_response = api_client.post(
        f"/v1/material-jobs/{job_id}/confirm",
        json={"draft_title": "Run, Hop, Go!"},
        headers=headers,
    )
    assert confirm_response.status_code == 404
    assert api_client.post(f"/v1/material-jobs/{job_id}/retry", headers=headers).status_code == 404
    accent_response = api_client.patch(
        f"/v1/materials/{material_id}/learning-assets/asset_rabbit/primary-accent",
        json={"primary_accent": "uk"},
        headers=headers,
    )
    assert accent_response.status_code == 404


def test_review_tasks_route_filters_archived_material_even_if_task_row_exists(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="delete-archived-task-parent")
    child_id = _create_child(api_client, headers)
    material_id, job_id = _create_material(api_client, headers, child_id)
    _seed_ready_derivatives(material_id, job_id, child_id)
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, material_id)
        assert material is not None
        material.status = MaterialStatus.archived.value
        db.add(material)
        db.commit()

    response = api_client.get(
        "/v1/review-tasks",
        params={"child_id": child_id},
        headers=headers,
    )

    assert response.status_code == 200
    assert all(item["material_id"] != material_id for item in response.json()["items"])
```

- [ ] **Step 2: Run archived access tests and verify failure**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_material_delete.py::test_archived_material_blocks_job_and_primary_accent_routes services/api/tests/test_material_delete.py::test_review_tasks_route_filters_archived_material_even_if_task_row_exists -q
```

Expected: FAIL because `material-jobs` still returns archived jobs or `review-tasks` still returns stale task rows.

- [ ] **Step 3: Filter archived material jobs**

Modify `_get_owned_job` in `services/api/app/api/routes/material_jobs.py`:

```python
    row = db.execute(stmt.where(CourseMaterialModel.status != MaterialStatus.archived.value)).first()
```

The full function tail should be:

```python
    row = db.execute(stmt.where(CourseMaterialModel.status != MaterialStatus.archived.value)).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material job not found")
    return row[0], row[1]
```

- [ ] **Step 4: Filter archived knowledge packs**

Modify `services/api/app/api/routes/knowledge.py` imports:

```python
from app.models.contracts import KnowledgePackDetailResponse, MaterialStatus
```

Add the status condition in `get_knowledge_pack_detail`:

```python
        .where(
            CourseMaterialModel.id == material_id,
            ChildProfileModel.parent_account_id == current_parent.id,
            CourseMaterialModel.status != MaterialStatus.archived.value,
        )
```

- [ ] **Step 5: Filter archived parent coaching scripts**

Modify `services/api/app/api/routes/parent_coaching.py` imports:

```python
from app.models.contracts import MaterialStatus, ParentCoachingScript
```

Add the status condition:

```python
        .where(
            ParentCoachingScriptModel.material_id == material_id,
            ChildProfileModel.parent_account_id == current_parent.id,
            CourseMaterialModel.status != MaterialStatus.archived.value,
        )
```

- [ ] **Step 6: Filter archived review tasks**

Modify `services/api/app/api/routes/review_tasks.py` imports:

```python
from app.db.models import ChildProfileModel, CourseMaterialModel, ParentAccountModel, ReviewTaskModel
from app.models.contracts import MaterialStatus, ReviewTaskListResponse
```

Replace the query start with:

```python
    stmt = (
        select(ReviewTaskModel)
        .join(ChildProfileModel, ChildProfileModel.id == ReviewTaskModel.child_id)
        .join(CourseMaterialModel, CourseMaterialModel.id == ReviewTaskModel.material_id)
        .where(
            ChildProfileModel.parent_account_id == current_parent.id,
            CourseMaterialModel.status != MaterialStatus.archived.value,
        )
    )
```

- [ ] **Step 7: Run API deletion suite and verify pass**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_material_delete.py -q
```

Expected: PASS for all tests in `test_material_delete.py`.

- [ ] **Step 8: Commit archived access guards**

Run:

```bash
git add services/api/app/api/routes/material_jobs.py services/api/app/api/routes/knowledge.py services/api/app/api/routes/parent_coaching.py services/api/app/api/routes/review_tasks.py services/api/tests/test_material_delete.py
git commit -m "fix: hide archived material data"
```

Expected: commit succeeds with archived filtering changes only.

---

### Task 3: Worker 归档保护

**Files:**
- Modify: `services/workers/workers_app/tasks.py`
- Modify: `services/workers/tests/test_material_job_task.py`

- [ ] **Step 1: Write failing worker tests**

Append to `services/workers/tests/test_material_job_task.py`:

```python
def test_process_material_job_skips_archived_material() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        parent = ParentAccountModel(
            id="parent_archived_job",
            display_name="家长",
            wechat_union_id="wechat_union_archived_job",
            wechat_open_id="wechat_open_archived_job",
        )
        child = ChildProfileModel(
            id="child_archived_job",
            parent_account_id=parent.id,
            name="Mia",
            age=6,
            level="starter",
            learning_goal="稳定复习",
            preferred_review_duration_minutes=10,
            parent_notes="",
        )
        material = CourseMaterialModel(
            id="material_archived_job",
            child_id=child.id,
            teacher_name="Emma",
            lesson_date=date(2026, 5, 15),
            title="Archived Worksheet",
            topic="Phonics",
            status=MaterialStatus.archived.value,
            uploaded_at=datetime.now(timezone.utc),
            tags=[],
        )
        job = MaterialParseJobModel(
            id="job_archived",
            material_id=material.id,
            status=JobStatus.processing.value,
            confidence_summary="等待 OCR 与解析。",
            draft_title=material.title,
            draft_topic=material.topic,
            draft_vocabulary=[],
            draft_sentences=[],
        )
        db.add_all([parent, child, material, job])
        db.commit()
    finally:
        db.close()

    result = process_material_job("job_archived")

    assert result == {"job_id": "job_archived", "status": "archived"}
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, "material_archived_job")
        job = db.get(MaterialParseJobModel, "job_archived")
        assert material is not None
        assert job is not None
        assert material.status == MaterialStatus.archived.value
        assert job.status == JobStatus.processing.value
        assert job.draft_vocabulary == []


def test_process_learning_asset_media_skips_archived_material() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        parent = ParentAccountModel(
            id="parent_archived_media",
            display_name="家长",
            wechat_union_id="wechat_union_archived_media",
            wechat_open_id="wechat_open_archived_media",
        )
        child = ChildProfileModel(
            id="child_archived_media",
            parent_account_id=parent.id,
            name="Mia",
            age=6,
            level="starter",
            learning_goal="稳定复习",
            preferred_review_duration_minutes=10,
            parent_notes="",
        )
        material = CourseMaterialModel(
            id="material_archived_media",
            child_id=child.id,
            teacher_name="Emma",
            lesson_date=date(2026, 5, 15),
            title="Qq Queen",
            topic="Phonics Qq",
            status=MaterialStatus.archived.value,
            uploaded_at=datetime.now(timezone.utc),
            learning_assets=[
                {
                    "id": "asset_queen",
                    "text": "queen",
                    "kind": "word",
                    "translation": "女王",
                    "primary_accent": "us",
                }
            ],
        )
        db.add_all([parent, child, material])
        db.commit()
    finally:
        db.close()

    result = process_learning_asset_media("material_archived_media")

    assert result == {"material_id": "material_archived_media", "status": "archived"}
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, "material_archived_media")
        assert material is not None
        assert material.status == MaterialStatus.archived.value
        assert material.learning_assets[0].get("generated_image_status") is None
```

- [ ] **Step 2: Run worker archived tests and verify failure**

Run:

```bash
services/workers/.venv/bin/python -m pytest services/workers/tests/test_material_job_task.py::test_process_material_job_skips_archived_material services/workers/tests/test_material_job_task.py::test_process_learning_asset_media_skips_archived_material -q
```

Expected: FAIL because the worker currently processes archived materials.

- [ ] **Step 3: Add archived guard to `process_material_job`**

Modify `services/workers/workers_app/tasks.py` inside `process_material_job`, immediately after `job, material = row`:

```python
        if material.status == MaterialStatus.archived.value:
            return {"job_id": job.id, "status": "archived"}
```

Insert this check immediately before the successful writeback block that assigns `job.status = prepared.status.value`:

```python
        db.refresh(material)
        if material.status == MaterialStatus.archived.value:
            return {"job_id": job.id, "status": "archived"}
```

Insert this check inside the `except Exception as exc:` block before setting `job.status = JobStatus.failed.value`:

```python
            db.refresh(material)
            if material.status == MaterialStatus.archived.value:
                return {"job_id": job.id, "status": "archived"}
```

- [ ] **Step 4: Add archived guard to `process_learning_asset_media`**

Modify `services/workers/workers_app/tasks.py` inside `process_learning_asset_media`, immediately after the missing-material check:

```python
        if material.status == MaterialStatus.archived.value:
            return {"material_id": material_id, "status": "archived"}
```

Insert this check immediately after `current_material = db.get(CourseMaterialModel, material_id)`:

```python
        if current_material is not None and current_material.status == MaterialStatus.archived.value:
            return {"material_id": material_id, "status": "archived"}
```

- [ ] **Step 5: Run worker tests and verify pass**

Run:

```bash
services/workers/.venv/bin/python -m pytest services/workers/tests/test_material_job_task.py -q
```

Expected: PASS for all worker material-job tests.

- [ ] **Step 6: Commit worker archived guards**

Run:

```bash
git add services/workers/workers_app/tasks.py services/workers/tests/test_material_job_task.py
git commit -m "fix: skip archived materials in workers"
```

Expected: commit succeeds with worker guard changes only.

---

### Task 4: Flutter repository 与资料库左滑删除

**Files:**
- Modify: `apps/mobile/lib/features/materials/data/materials_repository.dart`
- Modify: `apps/mobile/lib/features/materials/data/app_repository.dart`
- Modify: `apps/mobile/lib/features/materials/presentation/materials_library_screen.dart`
- Create: `apps/mobile/test/features/materials/presentation/materials_library_delete_test.dart`

- [ ] **Step 1: Write failing Flutter delete tests**

Create `apps/mobile/test/features/materials/presentation/materials_library_delete_test.dart`:

```dart
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';
import 'package:learning_english_mobile/features/materials/presentation/materials_library_screen.dart';
import 'package:learning_english_mobile/features/profiles/data/demo_data.dart';

void main() {
  testWidgets('left swipe cancel keeps material and does not call delete', (tester) async {
    final repository = _FakeDeleteRepository(materials: <CourseMaterial>[_material()]);
    await _pumpLibrary(tester, repository);

    await tester.drag(
      find.byKey(const ValueKey<String>('material-dismissible-material_1')),
      const Offset(-500, 0),
    );
    await tester.pumpAndSettle();
    expect(find.text('删除这份课程资料？'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey<String>('cancel-delete-material')));
    await tester.pumpAndSettle();

    expect(repository.deletedMaterialIds, isEmpty);
    expect(find.byKey(const ValueKey<String>('material-card-material_1')), findsOneWidget);
  });

  testWidgets('left swipe confirm deletes material and refreshes list', (tester) async {
    final repository = _FakeDeleteRepository(materials: <CourseMaterial>[_material()]);
    await _pumpLibrary(tester, repository);

    await tester.drag(
      find.byKey(const ValueKey<String>('material-dismissible-material_1')),
      const Offset(-500, 0),
    );
    await tester.pumpAndSettle();
    expect(find.text('删除这份课程资料？'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey<String>('confirm-delete-material')));
    await tester.pumpAndSettle();

    expect(repository.deletedMaterialIds, <String>['material_1']);
    expect(find.text('还没有课程资料'), findsOneWidget);
  });

  testWidgets('delete failure restores material and shows Chinese error', (tester) async {
    final repository = _FakeDeleteRepository(
      materials: <CourseMaterial>[_material()],
      deleteError: DioException(
        requestOptions: RequestOptions(path: '/materials/material_1'),
        message: 'network failed',
      ),
    );
    await _pumpLibrary(tester, repository);

    await tester.drag(
      find.byKey(const ValueKey<String>('material-dismissible-material_1')),
      const Offset(-500, 0),
    );
    await tester.pumpAndSettle();
    expect(find.text('删除这份课程资料？'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey<String>('confirm-delete-material')));
    await tester.pumpAndSettle();

    expect(repository.deletedMaterialIds, <String>['material_1']);
    expect(find.text('删除失败，请稍后重试。'), findsOneWidget);
    expect(find.byKey(const ValueKey<String>('material-card-material_1')), findsOneWidget);
  });
}

Future<void> _pumpLibrary(
  WidgetTester tester,
  _FakeDeleteRepository repository,
) async {
  tester.view.devicePixelRatio = 1;
  tester.view.physicalSize = const Size(390, 1600);
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final router = GoRouter(
    initialLocation: '/materials',
    routes: <RouteBase>[
      GoRoute(
        path: '/materials',
        builder: (context, state) => const MaterialsLibraryScreen(),
      ),
      GoRoute(
        path: '/materials/scan',
        builder: (context, state) => const Text('scan'),
      ),
      GoRoute(
        path: '/lessons/:materialId',
        builder: (context, state) => Text('lesson:${state.pathParameters['materialId']}'),
      ),
      GoRoute(
        path: '/materials/review/:jobId',
        builder: (context, state) => Text('review:${state.pathParameters['jobId']}'),
      ),
    ],
  );

  await tester.pumpWidget(
    ProviderScope(
      overrides: <Override>[
        appRepositoryProvider.overrideWithValue(repository),
        activeChildProvider.overrideWithValue(_childProfile()),
      ],
      child: MaterialApp.router(routerConfig: router),
    ),
  );
  await tester.pumpAndSettle();
}

class _FakeDeleteRepository extends AppRepository {
  _FakeDeleteRepository({
    required this.materials,
    this.deleteError,
  }) : super(
          Dio(),
          accessToken: () => 'access-token',
          refreshSession: () async => false,
        );

  List<CourseMaterial> materials;
  final Object? deleteError;
  final List<String> deletedMaterialIds = <String>[];

  @override
  Future<List<CourseMaterial>> listMaterials({required String childId}) async {
    return materials;
  }

  @override
  Future<void> deleteMaterial(String materialId) async {
    deletedMaterialIds.add(materialId);
    final error = deleteError;
    if (error != null) {
      throw error;
    }
    materials = materials.where((material) => material.id != materialId).toList();
  }
}

ChildProfile _childProfile() {
  return const ChildProfile(
    id: 'child_1',
    name: 'Mia',
    avatarUrl: '',
    age: 6,
    level: 'starter',
    learningGoal: '课后复习更稳定',
    preferredReviewDurationMinutes: 10,
    parentNotes: '',
  );
}

CourseMaterial _material() {
  return CourseMaterial(
    id: 'material_1',
    childId: 'child_1',
    parseJobId: 'job_1',
    teacherName: '外教课',
    lessonDate: DateTime(2026, 5, 15),
    title: 'Run, Hop, Go!',
    topic: 'Phonics Rr',
    status: MaterialStatus.ready,
    sourceImages: const <String>[],
    pdfUrl: '',
    ocrText: '',
    tags: const <String>[],
  );
}
```

- [ ] **Step 2: Run Flutter delete tests and verify failure**

Run:

```bash
cd apps/mobile && /private/tmp/learningenglish-flutter/bin/flutter test test/features/materials/presentation/materials_library_delete_test.dart
```

Expected: FAIL because `deleteMaterial` is not defined and no `material-dismissible-material_1` widget exists.

- [ ] **Step 3: Add repository delete method**

Modify `apps/mobile/lib/features/materials/data/materials_repository.dart`:

```dart
abstract class MaterialsRepository {
  Future<List<CourseMaterial>> listMaterials({required String childId});
  Future<void> deleteMaterial(String materialId);
  Future<MaterialParseJob> getMaterialJob(String jobId);
  Future<KnowledgePack> getKnowledgePack(String materialId);
  Future<List<ReviewTask>> listReviewTasks({
    required String childId,
    String? materialId,
  });
}
```

Add to `apps/mobile/lib/features/materials/data/app_repository.dart` after `listMaterials`:

```dart
  @override
  Future<void> deleteMaterial(String materialId) async {
    await _authorizedRequest<void>(
      (options) => _dio.delete<void>(
        '/materials/$materialId',
        options: options,
      ),
    );
  }
```

- [ ] **Step 4: Add Dismissible UI and delete helpers**

Modify `apps/mobile/lib/features/materials/presentation/materials_library_screen.dart`.

Add the repository import near the existing feature imports:

```dart
import '../data/app_repository.dart';
```

Replace the material item mapping body:

```dart
                  (material) => Padding(
                    padding: const EdgeInsets.only(bottom: AppSpacing.md),
                    child: Dismissible(
                      key: ValueKey<String>('material-dismissible-${material.id}'),
                      direction: DismissDirection.endToStart,
                      background: _DeleteMaterialBackground(),
                      confirmDismiss: (_) => _confirmAndDeleteMaterial(context, ref, material),
                      child: AppCard(
                        child: InkWell(
                          key: ValueKey<String>('material-card-${material.id}'),
                          borderRadius: BorderRadius.circular(AppRadii.card),
                          onTap: () => context.go(_materialDestination(material)),
                          child: Row(
                            children: <Widget>[
                              LessonCoverThumbnail(
                                title: material.title,
                                subtitle: material.topic,
                                icon: _libraryIcon(material.topic),
                                accent: _libraryAccent(material.topic),
                                assetPath: AppIllustrations.topicFor(material.topic),
                              ),
                              const SizedBox(width: AppSpacing.md),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: <Widget>[
                                    Row(
                                      children: <Widget>[
                                        Expanded(
                                          child: Text(
                                            material.title,
                                            style: AppTextStyles.cardTitle,
                                          ),
                                        ),
                                        MaterialStatusChip(material.status),
                                      ],
                                    ),
                                    const SizedBox(height: AppSpacing.xs),
                                    Text('${material.lessonDate.month}/${material.lessonDate.day} · ${material.teacherName}'),
                                    const SizedBox(height: AppSpacing.xs),
                                    Text('主题：${material.topic}', style: AppTextStyles.helper),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
```

Add below `MaterialsLibraryScreen`:

```dart
class _DeleteMaterialBackground extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      alignment: Alignment.centerRight,
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
      decoration: BoxDecoration(
        color: const Color(0xFFB3261E),
        borderRadius: BorderRadius.circular(AppRadii.card),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        mainAxisSize: MainAxisSize.min,
        children: const <Widget>[
          Icon(Icons.delete_outline_rounded, color: AppColors.paperWhite),
          SizedBox(height: AppSpacing.xs),
          Text('删除', style: TextStyle(color: AppColors.paperWhite)),
        ],
      ),
    );
  }
}

Future<bool> _confirmAndDeleteMaterial(
  BuildContext context,
  WidgetRef ref,
  CourseMaterial material,
) async {
  final confirmed = await showDialog<bool>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const Text('删除这份课程资料？'),
          content: const Text('删除后课程详情、知识点和复习任务将一起移除。'),
          actions: <Widget>[
            TextButton(
              key: const ValueKey<String>('cancel-delete-material'),
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('取消'),
            ),
            FilledButton(
              key: const ValueKey<String>('confirm-delete-material'),
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text('删除'),
            ),
          ],
        ),
      ) ??
      false;
  if (!confirmed) {
    return false;
  }
  try {
    await ref.read(appRepositoryProvider).deleteMaterial(material.id);
    ref.invalidate(materialsProvider);
    ref.invalidate(reviewTasksProvider);
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('已删除课程资料')),
      );
    }
    return true;
  } catch (_) {
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('删除失败，请稍后重试。')),
      );
    }
    return false;
  }
}
```

- [ ] **Step 5: Run Flutter delete tests and verify pass**

Run:

```bash
cd apps/mobile && /private/tmp/learningenglish-flutter/bin/flutter test test/features/materials/presentation/materials_library_delete_test.dart
```

Expected: PASS for all delete UI tests.

- [ ] **Step 6: Run existing material routing tests**

Run:

```bash
cd apps/mobile && /private/tmp/learningenglish-flutter/bin/flutter test test/features/materials/presentation/materials_library_routing_test.dart
```

Expected: PASS; ready material still opens lesson detail and non-ready material still opens AI review.

- [ ] **Step 7: Commit Flutter delete UI**

Run:

```bash
git add apps/mobile/lib/features/materials/data/materials_repository.dart apps/mobile/lib/features/materials/data/app_repository.dart apps/mobile/lib/features/materials/presentation/materials_library_screen.dart apps/mobile/test/features/materials/presentation/materials_library_delete_test.dart
git commit -m "feat: add swipe delete for materials"
```

Expected: commit succeeds with mobile delete UI and repository changes only.

---

### Task 5: 课程详情删除态中文提示

**Files:**
- Modify: `apps/mobile/lib/core/network/api_error.dart`
- Modify: `apps/mobile/lib/features/lessons/presentation/lesson_detail_screen.dart`
- Create: `apps/mobile/test/features/lessons/presentation/lesson_detail_deleted_test.dart`

- [ ] **Step 1: Write failing lesson-detail deleted-state test**

Create `apps/mobile/test/features/lessons/presentation/lesson_detail_deleted_test.dart`:

```dart
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_mobile/features/lessons/presentation/lesson_detail_screen.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';

void main() {
  testWidgets('deleted material detail shows Chinese not-found state', (tester) async {
    final repository = _DeletedMaterialRepository();
    final router = GoRouter(
      initialLocation: '/lessons/material_deleted',
      routes: <RouteBase>[
        GoRoute(
          path: '/lessons/:materialId',
          builder: (context, state) => LessonDetailScreen(
            materialId: state.pathParameters['materialId']!,
          ),
        ),
        GoRoute(
          path: '/materials',
          builder: (context, state) => const Text('materials-list'),
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          appRepositoryProvider.overrideWithValue(repository),
        ],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('课程资料不存在或已删除'), findsOneWidget);
    expect(find.text('回到资料库'), findsOneWidget);

    await tester.tap(find.text('回到资料库'));
    await tester.pumpAndSettle();
    expect(find.text('materials-list'), findsOneWidget);
  });
}

class _DeletedMaterialRepository extends AppRepository {
  _DeletedMaterialRepository()
      : super(
          Dio(),
          accessToken: () => 'access-token',
          refreshSession: () async => false,
        );

  @override
  Future<CourseMaterial> getMaterial(String materialId) async {
    throw DioException(
      requestOptions: RequestOptions(path: '/materials/$materialId'),
      response: Response<dynamic>(
        requestOptions: RequestOptions(path: '/materials/$materialId'),
        statusCode: 404,
        data: <String, dynamic>{'detail': 'Material not found'},
      ),
    );
  }

  @override
  Future<KnowledgePack> getKnowledgePack(String materialId) async {
    throw DioException(
      requestOptions: RequestOptions(path: '/knowledge-packs/$materialId'),
      response: Response<dynamic>(
        requestOptions: RequestOptions(path: '/knowledge-packs/$materialId'),
        statusCode: 404,
        data: <String, dynamic>{'detail': 'Knowledge pack not available yet'},
      ),
    );
  }
}
```

- [ ] **Step 2: Run deleted-state test and verify failure**

Run:

```bash
cd apps/mobile && /private/tmp/learningenglish-flutter/bin/flutter test test/features/lessons/presentation/lesson_detail_deleted_test.dart
```

Expected: FAIL because the page currently shows the generic `课程详情加载失败` state.

- [ ] **Step 3: Add not-found helper**

Append to `apps/mobile/lib/core/network/api_error.dart`:

```dart
bool isNotFoundApiError(Object error) {
  return error is DioException && error.response?.statusCode == 404;
}
```

- [ ] **Step 4: Show deleted-state copy in lesson detail**

Modify the `materialAsync.when(error: ...)` branch in `apps/mobile/lib/features/lessons/presentation/lesson_detail_screen.dart`:

```dart
      error: (error, _) {
        final notFound = isNotFoundApiError(error);
        return StatePanel(
          title: notFound ? '课程资料不存在或已删除' : '课程详情加载失败',
          description: notFound
              ? '这份课程资料可能已经被删除，请回到资料库查看最新列表。'
              : describeApiError(error, fallback: '课程详情加载失败，请稍后重试。'),
          assetPath: AppIllustrations.stateError,
          action: notFound
              ? OutlinedButton(
                  onPressed: () => context.go('/materials'),
                  child: const Text('回到资料库'),
                )
              : FilledButton(
                  onPressed: () => ref.invalidate(materialProvider(materialId)),
                  child: const Text('重新加载'),
                ),
        );
      },
```

- [ ] **Step 5: Run lesson-detail deleted-state test and verify pass**

Run:

```bash
cd apps/mobile && /private/tmp/learningenglish-flutter/bin/flutter test test/features/lessons/presentation/lesson_detail_deleted_test.dart
```

Expected: PASS.

- [ ] **Step 6: Commit lesson-detail deleted state**

Run:

```bash
git add apps/mobile/lib/core/network/api_error.dart apps/mobile/lib/features/lessons/presentation/lesson_detail_screen.dart apps/mobile/test/features/lessons/presentation/lesson_detail_deleted_test.dart
git commit -m "fix: show deleted material state"
```

Expected: commit succeeds with lesson detail error-state changes only.

---

### Task 6: Harness 文档与最终验证

**Files:**
- Modify: `docs/harness/upload-recognition-loop.md`
- Modify: `docs/harness/mvp-readiness-checklist.md`

- [ ] **Step 1: Update HN-015 harness requirement**

Append to `docs/harness/upload-recognition-loop.md` after HN-014:

```markdown
### HN-015：课程资料左滑删除

**目标：** 家长可以在资料库左滑删除课程资料；删除后课程详情、知识包、亲子陪练脚本和复习任务一起从用户可见入口移除。

**范围内：**
- 资料库课程卡片支持左滑删除。
- 删除前弹出确认框，说明课程详情、知识点和复习任务会一起移除。
- 后端将课程资料状态更新为 `archived`。
- 后端删除该资料对应的 `KnowledgePackModel`、`ReviewTaskModel` 和 `ParentCoachingScriptModel`。
- 已归档资料不再出现在资料库、首页最近课程、课程详情、AI 校对和复习任务接口中。
- worker 识别和媒体任务跳过已归档资料，不把资料重新写回可见状态。

**范围外：**
- 删除孩子档案、家长账号或全量用户数据。
- 回收站、撤销删除或恢复课程。
- 物理删除对象存储中的原始图片、彩色配图和 TTS 音频。
- 回算历史周报和历史练习记录。

**验收标准：**
- 删除当前家长拥有的资料返回 `204`。
- 删除后 `GET /materials` 不再返回该资料。
- 删除后 `GET /materials/{material_id}`、`GET /knowledge-packs/{material_id}`、`GET /parent-coaching/{material_id}` 返回 `404`。
- 删除后该资料对应复习任务不再返回。
- 归档资料对应的 job 不能继续读取、确认或重试。
- 移动端左滑删除支持取消、确认、失败恢复和中文错误提示。

**Harness：**
- 自动化：`services/api/.venv/bin/python -m pytest services/api/tests/test_material_delete.py -q`
- 自动化：`services/workers/.venv/bin/python -m pytest services/workers/tests/test_material_job_task.py -q`
- 自动化：`cd apps/mobile && /private/tmp/learningenglish-flutter/bin/flutter test test/features/materials/presentation/materials_library_delete_test.dart test/features/lessons/presentation/lesson_detail_deleted_test.dart`
- 人工：模拟器或真机上传并确认一份讲义后，左滑删除并保存截图/API 摘录。

**证据位置：**
- `dist/harness/HN-015/`
```

- [ ] **Step 2: Update readiness checklist**

Modify `docs/harness/mvp-readiness-checklist.md` under “下一批需求编号”:

```markdown
- `HN-015`：课程资料左滑删除。
```

Modify “当前实施状态”:

```markdown
- [ ] `HN-015` 课程资料左滑删除：需要补齐 API、worker、Flutter 左滑删除和 Harness 证据。
```

Add evidence placeholders near the HN-014 evidence section:

```markdown
`HN-015` 验收证据：
- `dist/harness/HN-015/material-delete-api.log`
- `dist/harness/HN-015/material-delete-worker.log`
- `dist/harness/HN-015/material-delete-mobile.log`
- `dist/harness/HN-015/material-delete-screen.png`
```

- [ ] **Step 3: Run full backend and mobile regression**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests -q
services/workers/.venv/bin/python -m pytest services/workers/tests -q
cd apps/mobile && /private/tmp/learningenglish-flutter/bin/flutter test
cd apps/mobile && /private/tmp/learningenglish-flutter/bin/flutter analyze
git diff --check
```

Expected:

```text
services/api/tests: all tests pass
services/workers/tests: all tests pass
flutter test: all tests pass
flutter analyze: No issues found
git diff --check: no output
```

- [ ] **Step 4: Save local Harness logs**

Run:

```bash
mkdir -p dist/harness/HN-015
services/api/.venv/bin/python -m pytest services/api/tests/test_material_delete.py -q | tee dist/harness/HN-015/material-delete-api.log
services/workers/.venv/bin/python -m pytest services/workers/tests/test_material_job_task.py -q | tee dist/harness/HN-015/material-delete-worker.log
cd apps/mobile && /private/tmp/learningenglish-flutter/bin/flutter test test/features/materials/presentation/materials_library_delete_test.dart test/features/lessons/presentation/lesson_detail_deleted_test.dart | tee /Users/chaucermini/Code/LearningEnglish/dist/harness/HN-015/material-delete-mobile.log
```

Expected: three log files exist under `dist/harness/HN-015/`; `dist/` remains untracked.

- [ ] **Step 5: Commit docs and final verification**

Run:

```bash
git add docs/harness/upload-recognition-loop.md docs/harness/mvp-readiness-checklist.md
git commit -m "docs: add material delete harness"
```

Expected: commit succeeds with Harness docs only.

- [ ] **Step 6: Final branch status**

Run:

```bash
git status --short --branch
git log --oneline -6
```

Expected: branch contains the HN-015 commits and no untracked source files except ignored `dist/` evidence.

---

## Self-Review

- Spec coverage: Task 1 implements delete route, soft-delete material, hard-delete knowledge pack/review tasks/parent coaching and idempotency. Task 2 covers archived read guards for materials, jobs, knowledge, coaching and review tasks. Task 3 covers worker start/writeback protection. Task 4 covers left-swipe UI, confirmation, refresh and failure restore. Task 5 covers deleted detail-page copy. Task 6 covers Harness docs and evidence.
- Placeholder scan: plan contains no placeholder keywords and no unspecified “write tests” step; every code-changing task has concrete snippets and commands.
- Type consistency: backend uses existing `MaterialStatus.archived`, `JobStatus`, `CourseMaterialModel`, `MaterialParseJobModel`, `KnowledgePackModel`, `ReviewTaskModel`, `ParentCoachingScriptModel`; mobile uses existing `AppRepository`, `materialsProvider`, `reviewTasksProvider`, `CourseMaterial`, `MaterialStatus`, `DioException`.
