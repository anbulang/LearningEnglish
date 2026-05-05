# 上传识别链路重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把讲义上传从“开发期表单上传”改成“拍照/选图后自动进入 AI 识别与校对”的用户流程。

**Architecture:** 保留现有 `CourseMaterial -> MaterialParseJob -> KnowledgePack` 主模型，但让上传页只负责采集图片并创建待识别材料。API 响应需要携带未就绪材料的最新 job id，移动端资料库据此把 `processing / needs_review / failed` 材料导向 AI 状态页，只有 `ready` 材料进入课程详情。

**Tech Stack:** Flutter、Riverpod、GoRouter、image_picker、FastAPI、SQLAlchemy、pytest、Flutter widget tests、Markdown Harness 文档。

---

## 文件结构

- 修改：`services/api/app/models/contracts.py`
  - 为 `CourseMaterial` 增加可选 `parse_job_id`；为 `MaterialStatus` 增加 `failed`。
- 修改：`services/api/app/services/mappers.py`
  - 支持从 route 层注入 `parse_job_id`。
- 修改：`services/api/app/api/routes/materials.py`
  - 上传材料允许默认元数据；列表和详情返回最新 job id。
- 修改：`services/api/app/api/routes/material_jobs.py`
  - 处理失败时同步 material 状态；retry 时同步回 processing。
- 修改：`packages/contracts/lib/src/enums.dart`
  - 增加 `MaterialStatus.failed`。
- 修改：`packages/contracts/lib/src/models.dart`
  - 增加 `CourseMaterial.parseJobId`。
- 修改：`apps/mobile/lib/core/widgets/status_chip.dart`
  - 展示失败状态。
- 修改：`apps/mobile/lib/features/materials/data/app_repository.dart`
  - 上传时用默认元数据兜底。
- 修改：`apps/mobile/lib/features/materials/data/scan_draft_controller.dart`
  - 默认标题、老师、主题改为空，由 repository 填默认值。
- 修改：`apps/mobile/lib/features/materials/presentation/scan_upload_screen.dart`
  - 去掉前置表单，增加拍照/相册入口，按钮文案改为“开始识别”。
- 修改：`apps/mobile/lib/features/materials/presentation/materials_library_screen.dart`
  - 未就绪材料点击进入 AI 状态页。
- 修改：`apps/mobile/lib/features/materials/presentation/material_review_screen.dart`
  - timeout/失败说明中文化，失败态重试按钮更明确。
- 修改测试：
  - `services/api/tests/test_material_failures.py`
  - `apps/mobile/test/features/materials/presentation/scan_review_navigation_test.dart`
  - 新增 `apps/mobile/test/features/materials/presentation/materials_library_routing_test.dart`
- 修改文档：
  - `docs/harness/mvp-readiness-checklist.md`
  - `README.md`

## Task 1: API 返回最新 job id 并同步失败状态

**Files:**
- Modify: `services/api/app/models/contracts.py`
- Modify: `services/api/app/services/mappers.py`
- Modify: `services/api/app/api/routes/materials.py`
- Modify: `services/api/app/api/routes/material_jobs.py`
- Test: `services/api/tests/test_material_failures.py`

- [x] **Step 1: 写 API 失败状态回归测试**

在 `services/api/tests/test_material_failures.py` 中更新 `test_polling_job_marks_failed_when_pipeline_errors`，增加 material 状态断言：

```python
    material_response = api_client.get(f"/v1/materials/{upload_response.json()['material']['id']}", headers=headers)
    assert material_response.status_code == 200
    assert material_response.json()["material"]["status"] == "failed"
    assert material_response.json()["material"]["parse_job_id"] == job_id
```

并在 `test_retry_failed_job_requeues_processing` 中增加 retry 后 material 状态断言：

```python
    material_id, job_id = _create_material(api_client, headers, child_id)
    ...
    material_response = api_client.get(f"/v1/materials/{material_id}", headers=headers)
    assert material_response.status_code == 200
    assert material_response.json()["material"]["status"] == "processing"
    assert material_response.json()["material"]["parse_job_id"] == job_id
```

- [x] **Step 2: 运行测试确认失败**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_material_failures.py::test_polling_job_marks_failed_when_pipeline_errors services/api/tests/test_material_failures.py::test_retry_failed_job_requeues_processing
```

Expected: FAIL，原因是响应中没有 `parse_job_id` 或 material 状态未同步为 `failed`。

- [x] **Step 3: 实现 API 状态和 job id**

在 `services/api/app/models/contracts.py` 增加：

```python
class MaterialStatus(str, Enum):
    uploaded = "uploaded"
    processing = "processing"
    needs_review = "needs_review"
    ready = "ready"
    failed = "failed"
    archived = "archived"
```

在 `CourseMaterial` 增加：

```python
parse_job_id: str = ""
```

在 `services/api/app/services/mappers.py` 调整函数签名：

```python
def course_material_from_model(model: CourseMaterialModel, parse_job_id: str = "") -> CourseMaterial:
```

并在返回值中加入：

```python
parse_job_id=parse_job_id,
```

在 `services/api/app/api/routes/materials.py` 增加 helper：

```python
def _latest_job_ids(db: Session, material_ids: list[str]) -> dict[str, str]:
    if not material_ids:
        return {}
    rows = db.execute(
        select(MaterialParseJobModel.material_id, MaterialParseJobModel.id)
        .where(MaterialParseJobModel.material_id.in_(material_ids))
        .order_by(MaterialParseJobModel.started_at.desc())
    ).all()
    result: dict[str, str] = {}
    for material_id, job_id in rows:
        result.setdefault(material_id, job_id)
    return result
```

列表和详情返回时使用 `course_material_from_model(material, parse_job_id=latest_ids.get(material.id, ""))`。

在 `services/api/app/api/routes/material_jobs.py` 的异常分支中同步：

```python
material.status = MaterialStatus.failed.value
db.add_all([job, material])
```

在 retry 中同步：

```python
material.status = MaterialStatus.processing.value
db.add_all([job, material])
```

- [x] **Step 4: 运行 API 回归测试**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_material_failures.py
```

Expected: PASS。

## Task 2: 移动端 contracts 支持 failed 和 parseJobId

**Files:**
- Modify: `packages/contracts/lib/src/enums.dart`
- Modify: `packages/contracts/lib/src/models.dart`
- Modify: `apps/mobile/lib/core/widgets/status_chip.dart`

- [x] **Step 1: 更新 Dart enum 和 model**

在 `MaterialStatus` 增加：

```dart
failed('failed'),
```

在 `CourseMaterial` 构造函数和字段中增加：

```dart
required this.parseJobId,
final String parseJobId;
```

在 `fromJson` 中增加：

```dart
parseJobId: json['parse_job_id'] as String? ?? '',
```

在 `toJson` 中增加：

```dart
'parse_job_id': parseJobId,
```

- [x] **Step 2: 更新状态 chip**

在 `MaterialStatusChip` 的 switch 中增加：

```dart
MaterialStatus.failed => ('识别失败', AppColors.errorSurface),
```

- [x] **Step 3: 运行 Flutter 测试**

Run:

```bash
cd apps/mobile && /private/tmp/learningenglish-flutter/bin/flutter test
```

Expected: PASS。

## Task 3: 上传页去表单化并默认元数据兜底

**Files:**
- Modify: `apps/mobile/lib/features/materials/data/scan_draft_controller.dart`
- Modify: `apps/mobile/lib/features/materials/data/app_repository.dart`
- Modify: `apps/mobile/lib/features/materials/presentation/scan_upload_screen.dart`
- Test: `apps/mobile/test/features/materials/presentation/scan_review_navigation_test.dart`

- [x] **Step 1: 写上传页 UI 回归测试**

在 `scan_review_navigation_test.dart` 增加测试：

```dart
testWidgets('scan page is image-first and does not require metadata form', (tester) async {
  _useTallPhoneViewport(tester);
  final repository = _FakeAppRepository();
  final router = GoRouter(
    initialLocation: '/materials/scan',
    routes: <RouteBase>[
      GoRoute(path: '/materials/scan', builder: (context, state) => const ScanUploadScreen()),
    ],
  );
  await _pumpTestApp(
    tester,
    router: router,
    repository: repository,
    overrides: <Override>[activeChildProvider.overrideWithValue(_childProfile())],
  );
  expect(find.text('课程标题'), findsNothing);
  expect(find.text('老师名'), findsNothing);
  expect(find.text('主题'), findsNothing);
  expect(find.text('拍照'), findsWidgets);
  expect(find.text('从相册选择'), findsWidgets);
  expect(find.text('开始识别'), findsOneWidget);
});
```

- [x] **Step 2: 运行测试确认失败**

Run:

```bash
cd apps/mobile && /private/tmp/learningenglish-flutter/bin/flutter test test/features/materials/presentation/scan_review_navigation_test.dart
```

Expected: FAIL，原因是旧表单仍存在。

- [x] **Step 3: 实现上传页简化**

在 `scan_draft_controller.dart` 默认值改为空：

```dart
title: '',
teacherName: '',
topic: '',
```

在 `app_repository.dart` 上传 FormData 前兜底：

```dart
final safeTitle = title.trim().isEmpty ? '待识别讲义' : title.trim();
final safeTeacherName = teacherName.trim().isEmpty ? '外教课' : teacherName.trim();
final safeTopic = topic.trim();
```

并用 `safeTitle`、`safeTeacherName`、`safeTopic` 写入 FormData。

在 `scan_upload_screen.dart` 增加：

```dart
Future<void> _takePhoto() async {
  final image = await _picker.pickImage(source: ImageSource.camera, imageQuality: 90);
  if (image == null) {
    return;
  }
  final draft = ref.read(scanDraftProvider);
  ref.read(scanDraftProvider.notifier).setPages(<XFile>[...draft.pages, image]);
}
```

保留 `_pickPage()` 作为相册入口；删除标题、老师、主题输入框；按钮文案改为 `开始识别`；空状态 action 改成两个按钮：`拍照`、`从相册选择`。

- [x] **Step 4: 运行移动端测试**

Run:

```bash
cd apps/mobile && /private/tmp/learningenglish-flutter/bin/flutter test
```

Expected: PASS。

## Task 4: 资料库未就绪材料路由到 AI 状态页

**Files:**
- Modify: `apps/mobile/lib/features/materials/presentation/materials_library_screen.dart`
- Test: `apps/mobile/test/features/materials/presentation/materials_library_routing_test.dart`

- [x] **Step 1: 新增资料库路由测试**

Create `apps/mobile/test/features/materials/presentation/materials_library_routing_test.dart`，覆盖：

```dart
// processing/needsReview/failed + parseJobId -> /materials/review/{jobId}?materialId={materialId}
// ready -> /lessons/{materialId}
```

- [x] **Step 2: 实现路由 helper**

在 `materials_library_screen.dart` 增加：

```dart
String _materialDestination(CourseMaterial material) {
  if (material.status == MaterialStatus.ready || material.parseJobId.isEmpty) {
    return '/lessons/${material.id}';
  }
  return '/materials/review/${material.parseJobId}?materialId=${material.id}';
}
```

并把卡片 `onTap` 改为：

```dart
onTap: () => context.go(_materialDestination(material)),
```

- [x] **Step 3: 运行移动端测试**

Run:

```bash
cd apps/mobile && /private/tmp/learningenglish-flutter/bin/flutter test
```

Expected: PASS。

## Task 5: 失败页和重试文案清晰化

**Files:**
- Modify: `apps/mobile/lib/features/materials/presentation/material_review_screen.dart`

- [x] **Step 1: 增加错误文案 helper**

在 `MaterialReviewScreen` 文件中增加：

```dart
String _recognitionFailureMessage(MaterialParseJob job, String? actionError) {
  final message = actionError ?? job.confidenceSummary;
  if (message.toLowerCase().contains('timeout')) {
    return '识别超时，请确认网络稳定后重新识别。原始讲义已经保留，不需要重新上传。';
  }
  if (message.trim().isEmpty) {
    return '识别失败，请重新识别。原始讲义已经保留，不需要重新上传。';
  }
  return message;
}
```

失败态 `StatePanel.description` 使用该 helper，按钮文案改为 `重新识别`。

- [x] **Step 2: 运行移动端测试**

Run:

```bash
cd apps/mobile && /private/tmp/learningenglish-flutter/bin/flutter test
```

Expected: PASS。

## Task 6: 文档和验证

**Files:**
- Modify: `docs/harness/mvp-readiness-checklist.md`
- Modify: `README.md`

- [x] **Step 1: 更新 Harness 文档**

在 readiness checklist 中追加 `HN-008` 到 `HN-012` 的实施状态和真机验证注意事项，明确当前真机 API 使用 `http://<mac-ip>:8000/v1`。

- [x] **Step 2: 运行全量验证**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests
cd apps/mobile && /private/tmp/learningenglish-flutter/bin/flutter test
```

Expected: API 和 Flutter 测试均 PASS。

- [ ] **Step 3: 真机/Profile 验证**

Run:

```bash
cd apps/mobile && /private/tmp/learningenglish-flutter/bin/flutter build ios --profile --dart-define=API_BASE_URL=http://192.168.2.5:8000/v1
xcrun devicectl device install app --device 19586D29-7FF4-5289-8B83-30AA8C3F273D apps/mobile/build/ios/iphoneos/Runner.app
xcrun devicectl device process launch --device 19586D29-7FF4-5289-8B83-30AA8C3F273D --terminate-existing com.anbulang.learningenglish
```

Expected: 真机可启动；拍照或相册上传后进入 AI 状态页；失败时显示可重试，成功时显示待校对。

2026-05-05 执行记录：
- Profile 构建、真机安装、真机启动均已通过。
- 首次点击“拍照”出现真机闪退，crash report 为 TCC 隐私权限错误：缺少 `NSCameraUsageDescription`。
- 已补充 iOS 相机/相册用途说明并重新安装启动。
- 仍未观察到新的 `POST /v1/materials` 上传请求，完整上传识别证据未完成，因此本步骤保持未勾选。

## Task 7: 图片级讲义记录与解析留存

**Files:**
- Modify: API contracts, DB models, material routes, material job routes, pipeline
- Modify: Dart contracts, upload draft/repository, upload/review/detail screens
- Modify: Harness docs

- [x] **Step 1: 上传时创建图片级记录**

`CourseMaterial` 增加 `image_records`，每张上传图片保留页码、来源、文件名、URL、object key、content type 和大小。移动端上传 multipart 同步提交 `file_sources`，来源只使用 `camera` 或 `gallery`。

- [x] **Step 2: 解析后保留图片级草稿**

`MaterialParseJob` 增加 `draft_image_records`。Doubao 提示词要求返回逐页 `image_records`；stub/fallback provider 在缺少逐页结果时生成非空图片级明细。

- [x] **Step 3: 校对和课程详情展示图片级明细**

上传页展示图片来源；AI 校对页展示每页标题、单词、句子和细节；课程详情页继续展示确认后的图片级记录。

- [x] **Step 4: 自动化验证**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests
cd apps/mobile && /private/tmp/learningenglish-flutter/bin/flutter test
```

Expected: API `35 passed`，Flutter `10 passed`。
