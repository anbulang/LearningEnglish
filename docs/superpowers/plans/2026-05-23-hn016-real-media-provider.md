# HN-016 Real Media Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 HN-016：课程确认后用真实 provider 生成彩色配图、英式 TTS 和美式 TTS，写入 storage 并回填学习资产、知识包和复习任务。

**Architecture:** 在现有 `materials.process_learning_asset_media` worker 上替换 mock-only 路径，新增可配置的 `ImageGenerationProvider` 和 `TTSProvider`。正式运行使用 OpenAI Image API 与 Speech API；测试环境继续使用 mock provider，且 `MEDIA_PROVIDER=real` 缺配置时必须失败可见，不静默回退 mock。移动端只消费 API 返回的媒体状态、URL 和中文错误说明。

**Tech Stack:** FastAPI, SQLAlchemy, Celery, httpx, Pillow, PostgreSQL JSON, local/S3 storage, Flutter, Riverpod, flutter_test, pytest.

---

## Source Checks

实施前已核对官方接口：

- OpenAI 图片生成文档说明 GPT Image 支持 Image API 的 generation/edit endpoints，并支持 `gpt-image-2` 等模型；Image API 返回 `data[0].b64_json` 可解码为图片文件：<https://developers.openai.com/api/docs/guides/image-generation>
- OpenAI TTS 文档说明 Speech API 使用 `/v1/audio/speech`，示例模型为 `gpt-4o-mini-tts`，默认输出 MP3，并支持通过 instructions 控制口音：<https://developers.openai.com/api/docs/guides/text-to-speech>

## Scope Check

这份计划覆盖一个连续闭环：配置和合约、storage 写入、provider、worker 回填、移动端展示和 Harness 证据。HN-017 孩子录音评分不在本计划内。

## File Structure

- Modify: `services/api/pyproject.toml`
  - 增加 `Pillow`，用于根据 `source_bbox` 生成讲义参考裁剪图。
- Modify: `services/workers/pyproject.toml`
  - 增加 `Pillow`，worker 直接导入 API 服务模块时也需要同一依赖。
- Modify: `services/api/app/core/settings.py`
  - 增加 `MEDIA_PROVIDER`、OpenAI key、图片/TTS 模型、voice、超时和代理配置。
- Modify: `services/api/app/models/contracts.py`
  - 给 `LearningAsset` 增加只读错误字段。
- Modify: `packages/contracts/lib/src/models.dart`
  - Dart 合约同步 `generatedImageError`、`ttsUsError`、`ttsUkError`。
- Modify: `services/api/app/services/storage.py`
  - 增加 `save_bytes`，让 worker 保存 provider 生成的图片和音频。
- Create: `services/api/app/services/media_reference.py`
  - 根据 `StoredAssetModel` 和 `LearningAsset.source_bbox` 生成临时参考裁剪图。
- Replace: `services/api/app/services/learning_asset_media.py`
  - 保留 mock manifest 支持，同时新增 provider 协议、结果类型、factory、OpenAI provider。
- Modify: `services/workers/workers_app/tasks.py`
  - 重写 `process_learning_asset_media` 的媒体生成主流程，支持图片/US TTS/UK TTS 独立成功或失败。
- Modify: `services/api/app/api/routes/material_jobs.py`
  - 媒体入队失败时回填错误字段。
- Modify: `apps/mobile/lib/features/lessons/presentation/lesson_detail_screen.dart`
  - 显示中文失败原因，并在目标口音音频不可用时禁用切换。
- Modify: `infra/env/local.example.env`
  - 增加真实媒体 provider 配置示例。
- Modify: `docs/harness/upload-recognition-loop.md`
  - 新增 `HN-016` 需求、验收和证据目录。
- Modify: `docs/harness/mvp-readiness-checklist.md`
  - 增加 HN-016 readiness 条目。
- Test: `services/api/tests/test_learning_asset_media_contracts.py`
- Test: `services/api/tests/test_storage_media_assets.py`
- Test: `services/api/tests/test_learning_asset_media_provider.py`
- Test: `services/workers/tests/test_material_job_task.py`
- Test: `apps/mobile/test/features/materials/data/app_repository_test.dart`
- Test: `apps/mobile/test/features/lessons/presentation/lesson_detail_media_test.dart`

---

### Task 1: Contract, Settings, and Dependencies

**Files:**
- Modify: `services/api/pyproject.toml`
- Modify: `services/workers/pyproject.toml`
- Modify: `services/api/app/core/settings.py`
- Modify: `services/api/app/models/contracts.py`
- Modify: `packages/contracts/lib/src/models.dart`
- Test: `services/api/tests/test_learning_asset_media_contracts.py`
- Test: `apps/mobile/test/features/materials/data/app_repository_test.dart`

- [ ] **Step 1: Write failing API contract tests**

Create `services/api/tests/test_learning_asset_media_contracts.py`:

```python
from __future__ import annotations

from app.core.settings import get_settings
from app.models.contracts import LearningAsset, MediaGenerationStatus


def test_learning_asset_includes_media_error_fields() -> None:
    asset = LearningAsset(
        id="asset_queen",
        text="queen",
        kind="word",
        generated_image_status=MediaGenerationStatus.failed,
        generated_image_error="图片生成失败：provider timeout",
        tts_us_status=MediaGenerationStatus.failed,
        tts_us_error="美式发音生成失败：provider timeout",
        tts_uk_status=MediaGenerationStatus.ready,
        tts_uk_url="http://testserver/uploads/generated/media/material_1/asset_queen/tts-uk.mp3",
    )

    payload = asset.model_dump(mode="json")

    assert payload["generated_image_error"] == "图片生成失败：provider timeout"
    assert payload["tts_us_error"] == "美式发音生成失败：provider timeout"
    assert payload["tts_uk_error"] == ""
    assert LearningAsset(**payload).tts_uk_url.endswith("/tts-uk.mp3")


def test_media_provider_settings_default_to_mock_safe_values(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.delenv("MEDIA_PROVIDER", raising=False)
    monkeypatch.delenv("MEDIA_IMAGE_PROVIDER", raising=False)
    monkeypatch.delenv("MEDIA_TTS_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    settings = get_settings()

    assert settings.media_provider == "mock"
    assert settings.media_image_provider == "openai"
    assert settings.media_tts_provider == "openai"
    assert settings.media_image_model == "gpt-image-2"
    assert settings.media_tts_model == "gpt-4o-mini-tts"
    assert settings.media_tts_us_voice == "coral"
    assert settings.media_tts_uk_voice == "cedar"
    assert settings.media_request_timeout_seconds == 180
    assert settings.media_http_trust_env is False


def test_media_provider_settings_read_environment(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("MEDIA_PROVIDER", "real")
    monkeypatch.setenv("MEDIA_IMAGE_MODEL", "gpt-image-1.5")
    monkeypatch.setenv("MEDIA_TTS_MODEL", "gpt-4o-mini-tts")
    monkeypatch.setenv("MEDIA_TTS_US_VOICE", "marin")
    monkeypatch.setenv("MEDIA_TTS_UK_VOICE", "fable")
    monkeypatch.setenv("MEDIA_REQUEST_TIMEOUT_SECONDS", "90")
    monkeypatch.setenv("MEDIA_HTTP_TRUST_ENV", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    settings = get_settings()

    assert settings.media_provider == "real"
    assert settings.media_image_model == "gpt-image-1.5"
    assert settings.media_tts_us_voice == "marin"
    assert settings.media_tts_uk_voice == "fable"
    assert settings.media_request_timeout_seconds == 90
    assert settings.media_http_trust_env is True
    assert settings.openai_api_key == "sk-test"
```

- [ ] **Step 2: Run API contract tests and verify failure**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_learning_asset_media_contracts.py -q
```

Expected: fails because `LearningAsset` lacks error fields and `Settings` lacks media provider fields.

- [ ] **Step 3: Add Python dependencies**

Modify both `services/api/pyproject.toml` and `services/workers/pyproject.toml` dependencies:

```toml
  "pillow>=11.0.0,<12.0.0",
```

Place it next to `httpx` / `boto3` dependencies.

- [ ] **Step 4: Add settings fields**

Modify `services/api/app/core/settings.py`.

Add fields to `Settings`:

```python
    media_provider: str
    media_image_provider: str
    media_tts_provider: str
    media_image_model: str
    media_tts_model: str
    media_tts_us_voice: str
    media_tts_uk_voice: str
    media_request_timeout_seconds: int
    media_http_trust_env: bool
    openai_api_key: str
    openai_base_url: str
```

Add values in `get_settings()`:

```python
        media_provider=os.getenv("MEDIA_PROVIDER", "mock").lower().strip(),
        media_image_provider=os.getenv("MEDIA_IMAGE_PROVIDER", "openai").lower().strip(),
        media_tts_provider=os.getenv("MEDIA_TTS_PROVIDER", "openai").lower().strip(),
        media_image_model=os.getenv("MEDIA_IMAGE_MODEL", "gpt-image-2"),
        media_tts_model=os.getenv("MEDIA_TTS_MODEL", "gpt-4o-mini-tts"),
        media_tts_us_voice=os.getenv("MEDIA_TTS_US_VOICE", "coral"),
        media_tts_uk_voice=os.getenv("MEDIA_TTS_UK_VOICE", "cedar"),
        media_request_timeout_seconds=int(os.getenv("MEDIA_REQUEST_TIMEOUT_SECONDS", "180")),
        media_http_trust_env=os.getenv("MEDIA_HTTP_TRUST_ENV", "false").lower() == "true",
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
```

- [ ] **Step 5: Add Python contract fields**

Modify `services/api/app/models/contracts.py` inside `LearningAsset`:

```python
    generated_image_error: str = ""
    tts_us_error: str = ""
    tts_uk_error: str = ""
```

Place each error field immediately after its matching object key field:

```python
    generated_image_object_key: str = ""
    generated_image_error: str = ""
```

```python
    tts_us_object_key: str = ""
    tts_us_error: str = ""
```

```python
    tts_uk_object_key: str = ""
    tts_uk_error: str = ""
```

- [ ] **Step 6: Add Dart contract failing test**

Append to `apps/mobile/test/features/materials/data/app_repository_test.dart` in the existing repository parsing group:

```dart
    test('parses learning asset media error fields', () async {
      final asset = LearningAsset.fromJson(<String, dynamic>{
        'id': 'asset_queen',
        'text': 'queen',
        'kind': 'word',
        'generated_image_status': 'failed',
        'generated_image_error': '图片生成失败：provider timeout',
        'tts_us_status': 'failed',
        'tts_us_error': '美式发音生成失败：provider timeout',
        'tts_uk_status': 'ready',
        'tts_uk_error': '',
      });

      expect(asset.generatedImageError, '图片生成失败：provider timeout');
      expect(asset.ttsUsError, '美式发音生成失败：provider timeout');
      expect(asset.ttsUkError, '');
    });
```

- [ ] **Step 7: Add Dart contract fields**

Modify `packages/contracts/lib/src/models.dart`.

Add constructor parameters:

```dart
    this.generatedImageError = '',
    this.ttsUsError = '',
    this.ttsUkError = '',
```

Add fields:

```dart
  final String generatedImageError;
  final String ttsUsError;
  final String ttsUkError;
```

Add parsing:

```dart
      generatedImageError: json['generated_image_error'] as String? ?? '',
      ttsUsError: json['tts_us_error'] as String? ?? '',
      ttsUkError: json['tts_uk_error'] as String? ?? '',
```

Add serialization:

```dart
        'generated_image_error': generatedImageError,
        'tts_us_error': ttsUsError,
        'tts_uk_error': ttsUkError,
```

- [ ] **Step 8: Run contract tests**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_learning_asset_media_contracts.py -q
cd apps/mobile && flutter test test/features/materials/data/app_repository_test.dart --plain-name "parses learning asset media error fields"
```

Expected: both pass.

- [ ] **Step 9: Commit**

```bash
git add services/api/pyproject.toml services/workers/pyproject.toml services/api/app/core/settings.py services/api/app/models/contracts.py packages/contracts/lib/src/models.dart services/api/tests/test_learning_asset_media_contracts.py apps/mobile/test/features/materials/data/app_repository_test.dart
git commit -m "feat: add media provider contract fields"
```

---

### Task 2: Storage Bytes and Worksheet Reference Crops

**Files:**
- Modify: `services/api/app/services/storage.py`
- Create: `services/api/app/services/media_reference.py`
- Test: `services/api/tests/test_storage_media_assets.py`

- [ ] **Step 1: Write failing storage and crop tests**

Create `services/api/tests/test_storage_media_assets.py`:

```python
from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.core.settings import get_settings
from app.db.models import StoredAssetModel
from app.models.contracts import LearningAsset, SourceBoundingBox
from app.services.media_reference import build_reference_image
from app.services.storage import LocalStorageService


def test_local_storage_save_bytes_writes_generated_media(monkeypatch, tmp_path: Path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path / "uploads"))
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://testserver")
    storage = LocalStorageService()

    stored = storage.save_bytes(
        owner_type="generated_media",
        owner_id="material_1",
        object_key="generated/media/material_1/asset_queen/image.png",
        content_type="image/png",
        payload=b"png-bytes",
    )

    assert stored.owner_type == "generated_media"
    assert stored.owner_id == "material_1"
    assert stored.object_key == "generated/media/material_1/asset_queen/image.png"
    assert stored.content_type == "image/png"
    assert stored.size_bytes == len(b"png-bytes")
    assert stored.url == "http://testserver/uploads/generated/media/material_1/asset_queen/image.png"
    assert (tmp_path / "uploads" / stored.object_key).read_bytes() == b"png-bytes"


def test_build_reference_image_crops_source_bbox(monkeypatch, tmp_path: Path) -> None:
    get_settings.cache_clear()
    upload_root = tmp_path / "uploads"
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(upload_root))
    source_path = upload_root / "material" / "material_1" / "worksheet.png"
    source_path.parent.mkdir(parents=True)
    image = Image.new("RGB", (100, 80), color=(255, 255, 255))
    image.save(source_path)
    stored = StoredAssetModel(
        owner_type="material",
        owner_id="material_1",
        bucket="learning-english",
        object_key="material/material_1/worksheet.png",
        content_type="image/png",
        size_bytes=source_path.stat().st_size,
        url="http://testserver/uploads/material/material_1/worksheet.png",
    )
    asset = LearningAsset(
        id="asset_queen",
        text="queen",
        kind="word",
        source_page_index=1,
        source_bbox=SourceBoundingBox(x=0.1, y=0.25, width=0.5, height=0.5),
    )

    reference = build_reference_image(asset=asset, source_assets=[stored], work_dir=tmp_path / "refs")

    assert reference is not None
    assert reference.exists()
    with Image.open(reference) as cropped:
        assert cropped.size == (50, 40)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_storage_media_assets.py -q
```

Expected: fails because `save_bytes` and `build_reference_image` do not exist.

- [ ] **Step 3: Implement `save_bytes`**

Modify `services/api/app/services/storage.py`.

Add to `LocalStorageService`:

```python
    def save_bytes(
        self,
        owner_type: str,
        owner_id: str,
        object_key: str,
        content_type: str,
        payload: bytes,
    ) -> StoredAssetModel:
        target = self.settings.local_storage_path / object_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        url = f"{self.settings.public_base_url.rstrip()}/uploads/{object_key}"
        return StoredAssetModel(
            owner_type=owner_type,
            owner_id=owner_id,
            bucket=self.settings.storage_bucket,
            object_key=object_key,
            content_type=content_type,
            size_bytes=len(payload),
            url=url,
        )
```

Add to `S3StorageService`:

```python
    def save_bytes(
        self,
        owner_type: str,
        owner_id: str,
        object_key: str,
        content_type: str,
        payload: bytes,
    ) -> StoredAssetModel:
        self.client.put_object(
            Bucket=self.settings.storage_bucket,
            Key=object_key,
            Body=payload,
            ContentType=content_type,
        )
        url = f"{self.settings.public_base_url.rstrip('/')}/uploads/{object_key}"
        return StoredAssetModel(
            owner_type=owner_type,
            owner_id=owner_id,
            bucket=self.settings.storage_bucket,
            object_key=object_key,
            content_type=content_type,
            size_bytes=len(payload),
            url=url,
        )
```

Fix the local URL line if copied exactly:

```python
        url = f"{self.settings.public_base_url.rstrip('/')}/uploads/{object_key}"
```

- [ ] **Step 4: Implement reference crop helper**

Create `services/api/app/services/media_reference.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image, UnidentifiedImageError

from app.core.settings import get_settings
from app.db.models import StoredAssetModel
from app.models.contracts import LearningAsset


def build_reference_image(
    *,
    asset: LearningAsset,
    source_assets: list[StoredAssetModel],
    work_dir: Path,
) -> Optional[Path]:
    if asset.source_bbox is None:
        return None
    if asset.source_page_index < 1 or asset.source_page_index > len(source_assets):
        return None
    source = source_assets[asset.source_page_index - 1]
    if not source.content_type.startswith("image/"):
        return None

    source_path = get_settings().local_storage_path / source.object_key
    if not source_path.exists():
        return None

    work_dir.mkdir(parents=True, exist_ok=True)
    target_path = work_dir / f"{asset.id}-reference.png"
    try:
        with Image.open(source_path) as image:
            width, height = image.size
            left = _clamp(int(asset.source_bbox.x * width), 0, width - 1)
            top = _clamp(int(asset.source_bbox.y * height), 0, height - 1)
            right = _clamp(int((asset.source_bbox.x + asset.source_bbox.width) * width), left + 1, width)
            bottom = _clamp(int((asset.source_bbox.y + asset.source_bbox.height) * height), top + 1, height)
            image.crop((left, top, right, bottom)).convert("RGB").save(target_path, format="PNG")
    except (OSError, UnidentifiedImageError):
        return None
    return target_path


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))
```

- [ ] **Step 5: Run storage tests**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_storage_media_assets.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add services/api/app/services/storage.py services/api/app/services/media_reference.py services/api/tests/test_storage_media_assets.py
git commit -m "feat: add generated media storage helpers"
```

---

### Task 3: Provider Abstractions and OpenAI Adapters

**Files:**
- Replace: `services/api/app/services/learning_asset_media.py`
- Test: `services/api/tests/test_learning_asset_media_provider.py`

- [ ] **Step 1: Write failing provider tests**

Create `services/api/tests/test_learning_asset_media_provider.py`:

```python
from __future__ import annotations

import base64
from pathlib import Path

import httpx
import pytest

from app.core.settings import get_settings
from app.models.contracts import LearningAsset
from app.services.learning_asset_media import (
    MediaProviderConfigurationError,
    OpenAIImageGenerationProvider,
    OpenAITTSProvider,
    build_media_provider_bundle,
)


class FakeTransport(httpx.BaseTransport):
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path.endswith("/images/generations") or request.url.path.endswith("/images/edits"):
            payload = {"data": [{"b64_json": base64.b64encode(b"image-bytes").decode("ascii")}]}
            return httpx.Response(200, json=payload, request=request)
        if request.url.path.endswith("/audio/speech"):
            return httpx.Response(200, content=b"audio-bytes", request=request)
        return httpx.Response(404, json={"error": "unexpected"}, request=request)


def test_build_real_media_provider_requires_openai_key(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("MEDIA_PROVIDER", "real")
    monkeypatch.setenv("MEDIA_IMAGE_PROVIDER", "openai")
    monkeypatch.setenv("MEDIA_TTS_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(MediaProviderConfigurationError) as exc:
        build_media_provider_bundle()

    assert "OPENAI_API_KEY" in str(exc.value)


def test_build_testing_media_provider_uses_mock(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("MEDIA_PROVIDER", "real")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    bundle = build_media_provider_bundle(public_base_url="http://testserver")

    assert bundle.mode == "mock"


def test_openai_image_generation_uses_generation_endpoint_without_reference(monkeypatch) -> None:
    transport = FakeTransport()
    client = httpx.Client(transport=transport)
    provider = OpenAIImageGenerationProvider(
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
        model="gpt-image-2",
        timeout_seconds=30,
        client=client,
        trust_env=False,
    )
    asset = LearningAsset(id="asset_queen", text="queen", kind="word", translation="女王")

    result = provider.generate(asset=asset, prompt="Create a colorful queen flashcard.", reference_image_path=None)

    assert result.payload == b"image-bytes"
    assert result.content_type == "image/png"
    assert transport.requests[0].url.path == "/v1/images/generations"
    assert transport.requests[0].headers["authorization"] == "Bearer sk-test"


def test_openai_image_generation_uses_edit_endpoint_with_reference(tmp_path: Path) -> None:
    reference = tmp_path / "reference.png"
    reference.write_bytes(b"reference-image")
    transport = FakeTransport()
    client = httpx.Client(transport=transport)
    provider = OpenAIImageGenerationProvider(
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
        model="gpt-image-2",
        timeout_seconds=30,
        client=client,
        trust_env=False,
    )
    asset = LearningAsset(id="asset_rabbit", text="A rabbit can hop fast.", kind="sentence")

    result = provider.generate(asset=asset, prompt="Create a colorful rabbit hopping scene.", reference_image_path=reference)

    assert result.payload == b"image-bytes"
    assert transport.requests[0].url.path == "/v1/images/edits"


def test_openai_tts_posts_speech_request() -> None:
    transport = FakeTransport()
    client = httpx.Client(transport=transport)
    provider = OpenAITTSProvider(
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini-tts",
        us_voice="coral",
        uk_voice="cedar",
        timeout_seconds=30,
        client=client,
        trust_env=False,
    )

    result = provider.synthesize(text="queen", accent="uk")

    assert result.payload == b"audio-bytes"
    assert result.content_type == "audio/mpeg"
    request = transport.requests[0]
    assert request.url.path == "/v1/audio/speech"
    assert request.headers["authorization"] == "Bearer sk-test"
    assert b"British English pronunciation" in request.content
    assert b"cedar" in request.content
```

- [ ] **Step 2: Run provider tests and verify failure**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_learning_asset_media_provider.py -q
```

Expected: fails because provider classes and factory do not exist.

- [ ] **Step 3: Replace media provider module with protocols and results**

Replace `services/api/app/services/learning_asset_media.py` with the implementation shaped below. Keep manifest validation behavior from the old module inside `HN014MockMediaProvider`.

```python
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Protocol

import httpx

from app.core.settings import get_settings
from app.models.contracts import LearningAsset, MediaGenerationStatus, SourceBoundingBox


@dataclass(frozen=True)
class GeneratedMedia:
    payload: bytes
    content_type: str
    extension: str


@dataclass(frozen=True)
class MediaProviderBundle:
    image_provider: "ImageGenerationProvider"
    tts_provider: "TTSProvider"
    mode: str


class ImageGenerationProvider(Protocol):
    def generate(
        self,
        *,
        asset: LearningAsset,
        prompt: str,
        reference_image_path: Optional[Path],
    ) -> GeneratedMedia:
        pass


class TTSProvider(Protocol):
    def synthesize(self, *, text: str, accent: str) -> GeneratedMedia:
        pass


class MediaProviderError(RuntimeError):
    pass


class MediaProviderConfigurationError(MediaProviderError):
    pass
```

- [ ] **Step 4: Implement OpenAI image and TTS classes**

Add the concrete classes to `services/api/app/services/learning_asset_media.py`:

```python
class OpenAIImageGenerationProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: int,
        client: Optional[httpx.Client] = None,
        trust_env: bool = False,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._client = client
        self.trust_env = trust_env

    def generate(
        self,
        *,
        asset: LearningAsset,
        prompt: str,
        reference_image_path: Optional[Path],
    ) -> GeneratedMedia:
        owns_client = self._client is None
        client = self._client or httpx.Client(timeout=self.timeout_seconds, trust_env=self.trust_env)
        try:
            if reference_image_path is not None:
                with reference_image_path.open("rb") as fp:
                    response = client.post(
                        f"{self.base_url}/images/edits",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        data={
                            "model": self.model,
                            "prompt": prompt,
                            "size": "1024x1024",
                        },
                        files={"image[]": (reference_image_path.name, fp, "image/png")},
                        timeout=self.timeout_seconds,
                    )
            else:
                response = client.post(
                    f"{self.base_url}/images/generations",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "size": "1024x1024",
                    },
                    timeout=self.timeout_seconds,
                )
            response.raise_for_status()
            payload = response.json()
            image_base64 = payload["data"][0]["b64_json"]
            return GeneratedMedia(
                payload=base64.b64decode(image_base64),
                content_type="image/png",
                extension=".png",
            )
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise MediaProviderError(f"图片生成失败：{exc}") from exc
        finally:
            if owns_client:
                client.close()


class OpenAITTSProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        us_voice: str,
        uk_voice: str,
        timeout_seconds: int,
        client: Optional[httpx.Client] = None,
        trust_env: bool = False,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.us_voice = us_voice
        self.uk_voice = uk_voice
        self.timeout_seconds = timeout_seconds
        self._client = client
        self.trust_env = trust_env

    def synthesize(self, *, text: str, accent: str) -> GeneratedMedia:
        owns_client = self._client is None
        client = self._client or httpx.Client(timeout=self.timeout_seconds, trust_env=self.trust_env)
        voice = self.uk_voice if accent == "uk" else self.us_voice
        accent_label = "British English pronunciation" if accent == "uk" else "American English pronunciation"
        try:
            response = client.post(
                f"{self.base_url}/audio/speech",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "voice": voice,
                    "input": text,
                    "instructions": f"Use clear {accent_label} for a young English learner. Speak naturally and do not add extra words.",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            return GeneratedMedia(
                payload=response.content,
                content_type="audio/mpeg",
                extension=".mp3",
            )
        except httpx.HTTPError as exc:
            raise MediaProviderError(f"TTS 生成失败：{exc}") from exc
        finally:
            if owns_client:
                client.close()
```

- [ ] **Step 5: Re-add mock provider under the new interface**

Add this adapter while preserving the old manifest parsing:

```python
class HN014MockMediaProvider:
    def __init__(self, public_base_url: str) -> None:
        self.public_base_url = public_base_url.rstrip("/")
        self.root = Path(__file__).resolve().parents[1] / "static" / "mock_media" / "hn014"
        payload = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        assets = payload.get("assets", [])
        if not isinstance(assets, list):
            raise ValueError("HN-014 mock media manifest must contain an assets list")
        for item in assets:
            _validate_manifest_item(item)
        self._by_text = {
            str(item.get("text", "")).strip().lower(): item
            for item in assets
            if str(item.get("text", "")).strip()
        }

    def apply(self, assets: list[LearningAsset]) -> list[LearningAsset]:
        updated: list[LearningAsset] = []
        for asset in assets:
            match = self._by_text.get(asset.text.strip().lower())
            if match is None:
                updated.append(
                    asset.model_copy(
                        update={
                            "generated_image_status": MediaGenerationStatus.failed,
                            "generated_image_error": "未找到匹配的 HN-014 mock 配图。",
                            "tts_us_status": MediaGenerationStatus.failed,
                            "tts_us_error": "未找到匹配的 HN-014 mock 美式音频。",
                            "tts_uk_status": MediaGenerationStatus.failed,
                            "tts_uk_error": "未找到匹配的 HN-014 mock 英式音频。",
                        }
                    )
                )
                continue
            image_path = str(match["image"])
            tts_us_path = str(match["tts_us"])
            tts_uk_path = str(match["tts_uk"])
            updated.append(
                asset.model_copy(
                    update={
                        "translation": asset.translation or match.get("translation", ""),
                        "kind": asset.kind or match.get("kind", "word"),
                        "source_page_index": int(match["source_page_index"]),
                        "source_bbox": asset.source_bbox or _source_bbox_from_manifest(match.get("source_bbox")),
                        "source_visual_description": asset.source_visual_description or match.get("source_visual_description", ""),
                        "generated_image_status": MediaGenerationStatus.ready,
                        "generated_image_url": self._url(image_path),
                        "generated_image_object_key": f"mock_media/hn014/{image_path}",
                        "generated_image_error": "",
                        "tts_us_status": MediaGenerationStatus.ready,
                        "tts_us_url": self._url(tts_us_path),
                        "tts_us_object_key": f"mock_media/hn014/{tts_us_path}",
                        "tts_us_error": "",
                        "tts_uk_status": MediaGenerationStatus.ready,
                        "tts_uk_url": self._url(tts_uk_path),
                        "tts_uk_object_key": f"mock_media/hn014/{tts_uk_path}",
                        "tts_uk_error": "",
                    }
                )
            )
        return updated

    def _url(self, relative_path: str) -> str:
        return f"{self.public_base_url}/mock-media/hn014/{relative_path}"
```

- [ ] **Step 6: Add provider factory**

Add:

```python
def build_media_provider_bundle(public_base_url: Optional[str] = None) -> MediaProviderBundle:
    settings = get_settings()
    if settings.app_env == "testing" or settings.media_provider == "mock":
        mock = HN014MockMediaProvider(public_base_url=public_base_url or settings.public_base_url)
        return MediaProviderBundle(image_provider=mock, tts_provider=mock, mode="mock")
    if settings.media_provider != "real":
        raise MediaProviderConfigurationError(f"Unsupported MEDIA_PROVIDER: {settings.media_provider}")
    if settings.media_image_provider != "openai":
        raise MediaProviderConfigurationError(f"Unsupported MEDIA_IMAGE_PROVIDER: {settings.media_image_provider}")
    if settings.media_tts_provider != "openai":
        raise MediaProviderConfigurationError(f"Unsupported MEDIA_TTS_PROVIDER: {settings.media_tts_provider}")
    if not settings.openai_api_key:
        raise MediaProviderConfigurationError("OPENAI_API_KEY is required when MEDIA_PROVIDER=real")
    return MediaProviderBundle(
        image_provider=OpenAIImageGenerationProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.media_image_model,
            timeout_seconds=settings.media_request_timeout_seconds,
            trust_env=settings.media_http_trust_env,
        ),
        tts_provider=OpenAITTSProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.media_tts_model,
            us_voice=settings.media_tts_us_voice,
            uk_voice=settings.media_tts_uk_voice,
            timeout_seconds=settings.media_request_timeout_seconds,
            trust_env=settings.media_http_trust_env,
        ),
        mode="real",
    )
```

For mock compatibility in Task 4, also add methods on `HN014MockMediaProvider`:

```python
    def generate(
        self,
        *,
        asset: LearningAsset,
        prompt: str,
        reference_image_path: Optional[Path],
    ) -> GeneratedMedia:
        match = self._by_text.get(asset.text.strip().lower())
        if match is None:
            raise MediaProviderError("未找到匹配的 HN-014 mock 配图。")
        return GeneratedMedia(
            payload=(self.root / str(match["image"])).read_bytes(),
            content_type="image/svg+xml",
            extension=".svg",
        )

    def synthesize(self, *, text: str, accent: str) -> GeneratedMedia:
        match = self._by_text.get(text.strip().lower())
        if match is None:
            raise MediaProviderError(f"未找到匹配的 HN-014 mock {accent} 音频。")
        key = "tts_uk" if accent == "uk" else "tts_us"
        return GeneratedMedia(
            payload=(self.root / str(match[key])).read_bytes(),
            content_type="audio/mp4",
            extension=".m4a",
        )
```

- [ ] **Step 7: Run provider tests**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_learning_asset_media_provider.py -q
```

Expected: pass.

- [ ] **Step 8: Commit**

```bash
git add services/api/app/services/learning_asset_media.py services/api/tests/test_learning_asset_media_provider.py
git commit -m "feat: add real media provider adapters"
```

---

### Task 4: Worker Media Generation and Independent Failure States

**Files:**
- Modify: `services/workers/workers_app/tasks.py`
- Test: `services/workers/tests/test_material_job_task.py`

- [ ] **Step 1: Add worker tests for real provider success and partial failure**

Append to `services/workers/tests/test_material_job_task.py`:

```python
def test_process_learning_asset_media_writes_generated_media_to_storage(monkeypatch) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _seed_media_material("material_real_media", "asset_queen", "queen")

    class FakeImageProvider:
        def generate(self, *, asset, prompt, reference_image_path):
            from app.services.learning_asset_media import GeneratedMedia
            return GeneratedMedia(payload=b"image-bytes", content_type="image/png", extension=".png")

    class FakeTTSProvider:
        def synthesize(self, *, text, accent):
            from app.services.learning_asset_media import GeneratedMedia
            return GeneratedMedia(payload=f"{accent}-audio".encode(), content_type="audio/mpeg", extension=".mp3")

    class FakeBundle:
        image_provider = FakeImageProvider()
        tts_provider = FakeTTSProvider()
        mode = "real"

    monkeypatch.setattr("workers_app.tasks.build_media_provider_bundle", lambda: FakeBundle())

    result = process_learning_asset_media("material_real_media")

    assert result == {"material_id": "material_real_media", "status": "ready"}
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, "material_real_media")
        assert material is not None
        asset = material.learning_assets[0]
        assert asset["generated_image_status"] == "ready"
        assert asset["generated_image_url"] == "http://testserver/uploads/generated/media/material_real_media/asset_queen/image.png"
        assert asset["tts_us_url"] == "http://testserver/uploads/generated/media/material_real_media/asset_queen/tts-us.mp3"
        assert asset["tts_uk_url"] == "http://testserver/uploads/generated/media/material_real_media/asset_queen/tts-uk.mp3"
        stored = db.query(StoredAssetModel).filter_by(owner_type="generated_media", owner_id="material_real_media").all()
        assert sorted(item.object_key for item in stored) == [
            "generated/media/material_real_media/asset_queen/image.png",
            "generated/media/material_real_media/asset_queen/tts-uk.mp3",
            "generated/media/material_real_media/asset_queen/tts-us.mp3",
        ]
        knowledge_pack = db.get(KnowledgePackModel, "knowledge_media_asset_queen")
        assert knowledge_pack is not None
        assert knowledge_pack.vocabulary_items[0]["image_url"].endswith("/image.png")
        assert knowledge_pack.vocabulary_items[0]["audio_url"].endswith("/tts-us.mp3")


def test_process_learning_asset_media_keeps_audio_when_image_fails(monkeypatch) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _seed_media_material("material_partial_media", "asset_duck", "duck")

    class FailingImageProvider:
        def generate(self, *, asset, prompt, reference_image_path):
            raise RuntimeError("image provider timeout")

    class FakeTTSProvider:
        def synthesize(self, *, text, accent):
            from app.services.learning_asset_media import GeneratedMedia
            return GeneratedMedia(payload=f"{accent}-audio".encode(), content_type="audio/mpeg", extension=".mp3")

    class FakeBundle:
        image_provider = FailingImageProvider()
        tts_provider = FakeTTSProvider()
        mode = "real"

    monkeypatch.setattr("workers_app.tasks.build_media_provider_bundle", lambda: FakeBundle())

    result = process_learning_asset_media("material_partial_media")

    assert result == {"material_id": "material_partial_media", "status": "partial"}
    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, "material_partial_media")
        assert material is not None
        asset = material.learning_assets[0]
        assert asset["generated_image_status"] == "failed"
        assert "图片生成失败" in asset["generated_image_error"]
        assert asset["tts_us_status"] == "ready"
        assert asset["tts_uk_status"] == "ready"
```

Add helper above the new tests:

```python
def _seed_media_material(material_id: str, asset_id: str, text: str) -> None:
    db = SessionLocal()
    try:
        parent = ParentAccountModel(
            id=f"parent_{material_id}",
            display_name="家长",
            wechat_union_id=f"wechat_union_{material_id}",
            wechat_open_id=f"wechat_open_{material_id}",
        )
        child = ChildProfileModel(
            id=f"child_{material_id}",
            parent_account_id=parent.id,
            name="Mia",
            age=6,
            level="starter",
            learning_goal="稳定复习",
            preferred_review_duration_minutes=10,
            parent_notes="",
        )
        material = CourseMaterialModel(
            id=material_id,
            child_id=child.id,
            teacher_name="Emma",
            lesson_date=date(2026, 5, 23),
            title="Generated Media",
            topic="Phonics",
            status=MaterialStatus.ready.value,
            uploaded_at=datetime.now(timezone.utc),
            learning_assets=[
                {
                    "id": asset_id,
                    "text": text,
                    "kind": "word",
                    "translation": "课堂词汇",
                    "pronunciation_text": text,
                    "primary_accent": "us",
                }
            ],
        )
        knowledge_pack = KnowledgePackModel(
            id=f"knowledge_media_{asset_id}",
            material_id=material.id,
            topic="Phonics",
            difficulty_band="repeat",
            lesson_summary="复习词汇。",
            review_recommendation="先听音再跟读。",
            vocabulary_items=[
                {
                    "id": f"word_{asset_id}",
                    "knowledge_pack_id": f"knowledge_media_{asset_id}",
                    "word": text,
                    "meaning_cn": "课堂词汇",
                    "image_url": "",
                    "audio_url": "",
                    "example_sentence": "",
                }
            ],
            sentence_patterns=[],
        )
        review_task = ReviewTaskModel(
            id=f"task_{asset_id}",
            child_id=child.id,
            material_id=material.id,
            task_type="flashcard",
            difficulty="easy",
            content_json={
                "asset_id": asset_id,
                "prompt": f"看图跟读：{text}",
                "word": text,
                "translation": "课堂词汇",
                "image_url": "",
                "audio_url": "",
            },
            due_date=datetime.now(timezone.utc),
            status="pending",
        )
        db.add_all([parent, child, material, knowledge_pack, review_task])
        db.commit()
    finally:
        db.close()
```

- [ ] **Step 2: Run worker tests and verify failure**

Run:

```bash
services/workers/.venv/bin/python -m pytest services/workers/tests/test_material_job_task.py -q
```

Expected: new tests fail because worker still uses `HN014MockMediaProvider.apply` directly and does not save generated bytes.

- [ ] **Step 3: Update imports in worker**

Modify `services/workers/workers_app/tasks.py` imports:

```python
import tempfile
```

Replace:

```python
from app.services.learning_asset_media import HN014MockMediaProvider
```

with:

```python
from app.services.learning_asset_media import MediaProviderError, build_media_provider_bundle
from app.services.media_reference import build_reference_image
```

- [ ] **Step 4: Add helper functions in worker**

Add below `_primary_accent_audio_url`:

```python
def _image_prompt(asset: LearningAsset) -> str:
    base = asset.image_prompt or asset.source_visual_description or asset.text
    return (
        "Create a colorful child-friendly English learning illustration. "
        f"Target text: {asset.text}. "
        f"Chinese meaning: {asset.translation}. "
        f"Worksheet context: {asset.source_visual_description}. "
        f"Image instruction: {base}. "
        "Keep the subject clear, simple, cheerful, and faithful to the worksheet context. "
        "Do not add watermarks or unrelated text."
    )


def _pronunciation_text(asset: LearningAsset) -> str:
    return (asset.pronunciation_text or asset.text).strip()


def _media_object_key(material_id: str, asset_id: str, name: str, extension: str) -> str:
    return f"generated/media/{material_id}/{asset_id}/{name}{extension}"


def _status_for_assets(assets: list[LearningAsset]) -> str:
    statuses: list[MediaGenerationStatus] = []
    for asset in assets:
        statuses.extend([asset.generated_image_status, asset.tts_us_status, asset.tts_uk_status])
    if all(status == MediaGenerationStatus.ready for status in statuses):
        return "ready"
    if any(status == MediaGenerationStatus.ready for status in statuses):
        return "partial"
    return "failed"
```

- [ ] **Step 5: Rewrite `process_learning_asset_media` generation block**

Inside `process_learning_asset_media`, keep existing DB loading, archived checks, processing status write, current accent merge, `_backfill_generated_media`, and commit pattern. Replace the provider call block with this structure:

```python
        storage = get_storage_service()
        source_assets = db.scalars(
            select(StoredAssetModel).where(
                StoredAssetModel.owner_type == "material",
                StoredAssetModel.owner_id == material.id,
            )
        ).all()
        bundle = build_media_provider_bundle()
        updated_assets: list[LearningAsset] = []
        with tempfile.TemporaryDirectory(prefix="learning-media-refs-") as temp_dir:
            reference_dir = Path(temp_dir)
            for asset in processing_assets:
                asset_updates = {}
                reference_image_path = build_reference_image(
                    asset=asset,
                    source_assets=list(source_assets),
                    work_dir=reference_dir,
                )
                try:
                    image = bundle.image_provider.generate(
                        asset=asset,
                        prompt=_image_prompt(asset),
                        reference_image_path=reference_image_path,
                    )
                    image_key = _media_object_key(material.id, asset.id, "image", image.extension)
                    stored_image = storage.save_bytes(
                        owner_type="generated_media",
                        owner_id=material.id,
                        object_key=image_key,
                        content_type=image.content_type,
                        payload=image.payload,
                    )
                    db.add(stored_image)
                    asset_updates.update(
                        {
                            "generated_image_status": MediaGenerationStatus.ready,
                            "generated_image_url": stored_image.url,
                            "generated_image_object_key": stored_image.object_key,
                            "generated_image_error": "",
                        }
                    )
                except Exception as exc:
                    asset_updates.update(
                        {
                            "generated_image_status": MediaGenerationStatus.failed,
                            "generated_image_error": f"图片生成失败：{exc}",
                        }
                    )

                for accent, status_field, url_field, key_field, error_field, file_name in [
                    ("us", "tts_us_status", "tts_us_url", "tts_us_object_key", "tts_us_error", "tts-us"),
                    ("uk", "tts_uk_status", "tts_uk_url", "tts_uk_object_key", "tts_uk_error", "tts-uk"),
                ]:
                    try:
                        audio = bundle.tts_provider.synthesize(text=_pronunciation_text(asset), accent=accent)
                        audio_key = _media_object_key(material.id, asset.id, file_name, audio.extension)
                        stored_audio = storage.save_bytes(
                            owner_type="generated_media",
                            owner_id=material.id,
                            object_key=audio_key,
                            content_type=audio.content_type,
                            payload=audio.payload,
                        )
                        db.add(stored_audio)
                        asset_updates.update(
                            {
                                status_field: MediaGenerationStatus.ready,
                                url_field: stored_audio.url,
                                key_field: stored_audio.object_key,
                                error_field: "",
                            }
                        )
                    except Exception as exc:
                        label = "美式发音" if accent == "us" else "英式发音"
                        asset_updates.update(
                            {
                                status_field: MediaGenerationStatus.failed,
                                error_field: f"{label}生成失败：{exc}",
                            }
                        )

                updated_assets.append(asset.model_copy(update=asset_updates))
        status_value = _status_for_assets(updated_assets)
```

- [ ] **Step 6: Preserve mock apply compatibility only if needed by old tests**

If old `test_process_learning_asset_media_fills_mock_urls` fails because object keys changed from `/mock-media/` to `/uploads/generated/`, update that test to assert the new generated storage URL for `APP_ENV=testing`. Keep one smaller provider-unit test for `HN014MockMediaProvider.apply` if old static URL compatibility still matters:

```python
def test_hn014_mock_provider_apply_keeps_static_manifest_urls() -> None:
    from app.services.learning_asset_media import HN014MockMediaProvider
    provider = HN014MockMediaProvider(public_base_url="http://testserver")
    asset = LearningAsset(id="asset_queen", text="queen", kind="word")

    updated = provider.apply([asset])[0]

    assert updated.generated_image_url == "http://testserver/mock-media/hn014/images/queen.svg"
    assert updated.tts_us_url == "http://testserver/mock-media/hn014/tts/us/queen.m4a"
```

- [ ] **Step 7: Run worker tests**

Run:

```bash
services/workers/.venv/bin/python -m pytest services/workers/tests/test_material_job_task.py -q
```

Expected: pass.

- [ ] **Step 8: Commit**

```bash
git add services/workers/workers_app/tasks.py services/workers/tests/test_material_job_task.py
git commit -m "feat: generate learning asset media in worker"
```

---

### Task 5: API Failure Backfill and Accent Guardrails

**Files:**
- Modify: `services/api/app/api/routes/material_jobs.py`
- Modify: `services/api/app/api/routes/materials.py`
- Test: `services/api/tests/test_material_failures.py`

- [ ] **Step 1: Add API tests for media errors and unavailable accent**

Append to `services/api/tests/test_material_failures.py`:

```python
def test_confirm_job_marks_media_enqueue_errors_on_learning_assets(api_client, monkeypatch) -> None:
    def fail_enqueue(material_id: str) -> None:
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr("app.api.routes.material_jobs.enqueue_learning_asset_media_job", fail_enqueue)
    headers, _ = auth_headers(api_client, auth_code="confirm-media-error-fields-parent")
    child_id = _create_child(api_client, headers)
    material_id, job_id = _create_material(api_client, headers, child_id)

    with SessionLocal() as db:
        job = db.get(MaterialParseJobModel, job_id)
        material = db.get(CourseMaterialModel, material_id)
        assert job is not None
        assert material is not None
        job.status = JobStatus.needs_review.value
        job.draft_title = "Qq Queen"
        job.draft_topic = "Phonics Qq"
        job.draft_vocabulary = ["queen"]
        job.draft_sentences = ["Find the queen."]
        job.draft_learning_assets = [
            {"id": "asset_queen", "text": "queen", "kind": "word", "translation": "女王", "primary_accent": "us"}
        ]
        material.status = MaterialStatus.needs_review.value
        db.add_all([job, material])
        db.commit()

    response = api_client.post(f"/v1/material-jobs/{job_id}/confirm", json={}, headers=headers)

    assert response.status_code == 200
    material_response = api_client.get(f"/v1/materials/{material_id}", headers=headers)
    asset = material_response.json()["material"]["learning_assets"][0]
    assert asset["generated_image_status"] == "failed"
    assert "媒体生成排队失败" in asset["generated_image_error"]
    assert "媒体生成排队失败" in asset["tts_us_error"]
    assert "媒体生成排队失败" in asset["tts_uk_error"]


def test_update_primary_accent_rejects_unavailable_audio(api_client) -> None:
    headers, _ = auth_headers(api_client, auth_code="primary-accent-unavailable-parent")
    child_id = _create_child(api_client, headers)
    material_id, _ = _create_material(api_client, headers, child_id)

    with SessionLocal() as db:
        material = db.get(CourseMaterialModel, material_id)
        assert material is not None
        material.status = MaterialStatus.ready.value
        material.learning_assets = [
            {
                "id": "asset_queen",
                "text": "queen",
                "kind": "word",
                "translation": "女王",
                "primary_accent": "us",
                "tts_us_status": "ready",
                "tts_us_url": "http://testserver/uploads/generated/media/material/asset/tts-us.mp3",
                "tts_uk_status": "failed",
                "tts_uk_error": "英式发音生成失败：provider timeout",
            }
        ]
        db.add(material)
        db.commit()

    response = api_client.patch(
        f"/v1/materials/{material_id}/learning-assets/asset_queen/primary-accent",
        json={"primary_accent": "uk"},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "英式发音暂不可用"
```

- [ ] **Step 2: Run API tests and verify failure**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_material_failures.py -q
```

Expected: new tests fail because enqueue failure does not write error fields and accent update does not reject unavailable audio.

- [ ] **Step 3: Update media enqueue failure helper**

Modify `_media_failed_learning_assets` in `services/api/app/api/routes/material_jobs.py`:

```python
def _media_failed_learning_assets(assets: list[LearningAsset]) -> list[dict]:
    return [
        asset.model_copy(
            update={
                "generated_image_status": MediaGenerationStatus.failed,
                "generated_image_error": "媒体生成排队失败，请稍后重试。",
                "tts_us_status": MediaGenerationStatus.failed,
                "tts_us_error": "媒体生成排队失败，请稍后重试。",
                "tts_uk_status": MediaGenerationStatus.failed,
                "tts_uk_error": "媒体生成排队失败，请稍后重试。",
            }
        ).model_dump(mode="json")
        for asset in assets
    ]
```

- [ ] **Step 4: Reject unavailable primary accent**

In `services/api/app/api/routes/materials.py`, find the primary accent update loop. Before setting `primary_accent`, add:

```python
        if payload.primary_accent == PrimaryAccent.uk and (
            asset.tts_uk_status != MediaGenerationStatus.ready or not asset.tts_uk_url
        ):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="英式发音暂不可用")
        if payload.primary_accent == PrimaryAccent.us and (
            asset.tts_us_status != MediaGenerationStatus.ready or not asset.tts_us_url
        ):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="美式发音暂不可用")
```

Confirm imports include:

```python
from app.models.contracts import MediaGenerationStatus
```

- [ ] **Step 5: Run API tests**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_material_failures.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add services/api/app/api/routes/material_jobs.py services/api/app/api/routes/materials.py services/api/tests/test_material_failures.py
git commit -m "feat: surface media generation failures"
```

---

### Task 6: Flutter Lesson Detail Media States

**Files:**
- Modify: `apps/mobile/lib/features/lessons/presentation/lesson_detail_screen.dart`
- Test: `apps/mobile/test/features/lessons/presentation/lesson_detail_media_test.dart`

- [ ] **Step 1: Write failing Flutter widget tests**

Create `apps/mobile/test/features/lessons/presentation/lesson_detail_media_test.dart`:

```dart
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:learning_english_contracts/contracts.dart';
import 'package:learning_english_mobile/features/lessons/presentation/lesson_detail_screen.dart';
import 'package:learning_english_mobile/features/materials/data/app_repository.dart';

void main() {
  testWidgets('lesson detail shows Chinese media failure reasons',
      (tester) async {
    final repository = _LessonMediaRepository(
      asset: const LearningAsset(
        id: 'asset_queen',
        text: 'queen',
        kind: 'word',
        translation: '女王',
        generatedImageStatus: 'failed',
        generatedImageError: '图片生成失败：provider timeout',
        ttsUsStatus: 'ready',
        ttsUsUrl: 'http://testserver/uploads/generated/media/material/asset/tts-us.mp3',
        ttsUkStatus: 'failed',
        ttsUkError: '英式发音生成失败：provider timeout',
        primaryAccent: 'us',
      ),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          appRepositoryProvider.overrideWithValue(repository),
        ],
        child: const MaterialApp(
          home: LessonDetailScreen(materialId: 'material_1'),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('图片生成失败：provider timeout'), findsOneWidget);
    expect(find.text('英式发音生成失败：provider timeout'), findsOneWidget);
  });

  testWidgets('lesson detail prevents switching to unavailable accent',
      (tester) async {
    final repository = _LessonMediaRepository(
      asset: const LearningAsset(
        id: 'asset_queen',
        text: 'queen',
        kind: 'word',
        translation: '女王',
        ttsUsStatus: 'ready',
        ttsUsUrl: 'http://testserver/uploads/generated/media/material/asset/tts-us.mp3',
        ttsUkStatus: 'failed',
        ttsUkError: '英式发音暂不可用',
        primaryAccent: 'us',
      ),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          appRepositoryProvider.overrideWithValue(repository),
        ],
        child: const MaterialApp(
          home: LessonDetailScreen(materialId: 'material_1'),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('英式'));
    await tester.pumpAndSettle();

    expect(repository.updatedAccent, isNull);
    expect(find.text('英式发音暂不可用'), findsOneWidget);
  });
}

class _LessonMediaRepository extends AppRepository {
  _LessonMediaRepository({required this.asset})
      : super(
          Dio(),
          accessToken: () => 'access-token',
          refreshSession: () async => false,
        );

  final LearningAsset asset;
  String? updatedAccent;

  @override
  Future<CourseMaterial> getMaterial(String materialId) async {
    return CourseMaterial(
      id: materialId,
      childId: 'child_1',
      parseJobId: 'job_1',
      teacherName: 'Emma',
      lessonDate: DateTime(2026, 5, 23),
      title: 'Qq Queen',
      topic: 'Phonics',
      status: MaterialStatus.ready,
      sourceImages: const <String>[],
      pdfUrl: '',
      ocrText: '',
      tags: const <String>[],
      learningAssets: <LearningAsset>[asset],
    );
  }

  @override
  Future<KnowledgePack> getKnowledgePack(String materialId) async {
    return const KnowledgePack(
      id: 'knowledge_1',
      materialId: 'material_1',
      topic: 'Phonics',
      difficultyBand: DifficultyBand.repeat,
      lessonSummary: '复习 queen。',
      reviewRecommendation: '先听音再跟读。',
      vocabularyItems: <VocabularyItem>[],
      sentencePatterns: <SentencePattern>[],
    );
  }

  @override
  Future<CourseMaterial> updateLearningAssetPrimaryAccent({
    required String materialId,
    required String assetId,
    required String primaryAccent,
  }) async {
    updatedAccent = primaryAccent;
    return getMaterial(materialId);
  }
}
```

- [ ] **Step 2: Run Flutter tests and verify failure**

Run:

```bash
cd apps/mobile && flutter test test/features/lessons/presentation/lesson_detail_media_test.dart
```

Expected: fails because UI does not show error text and still calls repository for unavailable UK audio.

- [ ] **Step 3: Add UI helpers**

In `apps/mobile/lib/features/lessons/presentation/lesson_detail_screen.dart`, add helpers near `_mediaStatusLabel`:

```dart
bool _accentAvailable(LearningAsset asset, String accent) {
  if (accent == 'uk') {
    return asset.ttsUkStatus == 'ready' && asset.ttsUkUrl.isNotEmpty;
  }
  return asset.ttsUsStatus == 'ready' && asset.ttsUsUrl.isNotEmpty;
}

String _accentUnavailableMessage(LearningAsset asset, String accent) {
  if (accent == 'uk') {
    return asset.ttsUkError.isNotEmpty ? asset.ttsUkError : '英式发音暂不可用';
  }
  return asset.ttsUsError.isNotEmpty ? asset.ttsUsError : '美式发音暂不可用';
}
```

- [ ] **Step 4: Update accent selection guard**

In `_LearningAssetCard._updatePrimaryAccent`, add before `setState`:

```dart
    if (!_accentAvailable(widget.asset, accent)) {
      setState(() {
        _accentError = _accentUnavailableMessage(widget.asset, accent);
      });
      return;
    }
```

- [ ] **Step 5: Display media error text**

Under the existing media status text, add:

```dart
                    if (asset.generatedImageStatus == 'failed' &&
                        asset.generatedImageError.isNotEmpty) ...<Widget>[
                      const SizedBox(height: AppSpacing.xxs),
                      Text(
                        asset.generatedImageError,
                        style: AppTextStyles.helper
                            .copyWith(color: AppColors.cocoaCoral),
                      ),
                    ],
                    if (asset.ttsUsStatus == 'failed' &&
                        asset.ttsUsError.isNotEmpty) ...<Widget>[
                      const SizedBox(height: AppSpacing.xxs),
                      Text(
                        asset.ttsUsError,
                        style: AppTextStyles.helper
                            .copyWith(color: AppColors.cocoaCoral),
                      ),
                    ],
                    if (asset.ttsUkStatus == 'failed' &&
                        asset.ttsUkError.isNotEmpty) ...<Widget>[
                      const SizedBox(height: AppSpacing.xxs),
                      Text(
                        asset.ttsUkError,
                        style: AppTextStyles.helper
                            .copyWith(color: AppColors.cocoaCoral),
                      ),
                    ],
```

- [ ] **Step 6: Run Flutter tests**

Run:

```bash
cd apps/mobile && flutter test test/features/lessons/presentation/lesson_detail_media_test.dart
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add apps/mobile/lib/features/lessons/presentation/lesson_detail_screen.dart apps/mobile/test/features/lessons/presentation/lesson_detail_media_test.dart
git commit -m "feat: show media generation errors in lesson detail"
```

---

### Task 7: Harness and Environment Documentation

**Files:**
- Modify: `infra/env/local.example.env`
- Modify: `docs/harness/upload-recognition-loop.md`
- Modify: `docs/harness/mvp-readiness-checklist.md`
- Modify: `docs/architecture/backend-architecture.md`
- Modify: `docs/architecture/overview.md`

- [ ] **Step 1: Update environment example**

Append to `infra/env/local.example.env`:

```dotenv
# Learning asset media provider.
# `mock` is deterministic for tests and local UI screenshots.
# `real` calls configured external providers and fails visibly if required
# keys/models are missing.
MEDIA_PROVIDER=mock
MEDIA_IMAGE_PROVIDER=openai
MEDIA_TTS_PROVIDER=openai
MEDIA_IMAGE_MODEL=gpt-image-2
MEDIA_TTS_MODEL=gpt-4o-mini-tts
MEDIA_TTS_US_VOICE=coral
MEDIA_TTS_UK_VOICE=cedar
MEDIA_REQUEST_TIMEOUT_SECONDS=180
MEDIA_HTTP_TRUST_ENV=false
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
```

- [ ] **Step 2: Add HN-016 to upload-recognition-loop**

Append after HN-015 in `docs/harness/upload-recognition-loop.md`:

```markdown
### HN-016：真实媒体生成 Provider

**目标：** 家长确认讲义后，后台用真实 provider 为每条学习资产生成彩色配图、美式 TTS 和英式 TTS，并保存到 storage。

**范围内：**
- `MEDIA_PROVIDER=real` 时使用真实外部 provider，不静默回退 mock。
- 图片、US TTS、UK TTS 独立生成和独立失败。
- 生成文件写入 storage 后回填 `material.learning_assets`、`KnowledgePack` 和 `ReviewTask`。
- 移动端课程详情展示生成中、已生成和失败原因。

**范围外：**
- 孩子录音评分。
- 家长编辑 prompt 或 voice。
- 历史 mock 媒体迁移。

**验收标准：**
- 至少一份 Qq/Rr 讲义确认后，`material.learning_assets` 含 `generated_image_url`、`tts_us_url`、`tts_uk_url`。
- storage 中存在对应图片和两份音频对象。
- 单项失败不会阻塞其他媒体成功。
- `MEDIA_PROVIDER=real` 缺少 `OPENAI_API_KEY` 时媒体状态为 `failed`，不展示 mock URL。
- 课程详情显示中文失败原因，不展示 provider 原始英文堆栈。

**Harness：**
- 自动化：`services/api/.venv/bin/python -m pytest services/api/tests/test_learning_asset_media_provider.py services/api/tests/test_storage_media_assets.py -q`
- 自动化：`services/workers/.venv/bin/python -m pytest services/workers/tests/test_material_job_task.py -q`
- 自动化：`cd apps/mobile && flutter test test/features/lessons/presentation/lesson_detail_media_test.dart`
- 人工：真机或模拟器确认课程后保存 material JSON、media job 日志和课程详情截图。

**证据位置：**
- `dist/harness/HN-016/`
```

- [ ] **Step 3: Update readiness checklist**

In `docs/harness/mvp-readiness-checklist.md`, add to current implementation status:

```markdown
- [ ] `HN-016` 真实媒体生成 Provider：待实现真实彩色配图、US TTS、UK TTS、storage 回填和课程详情失败态。
```

Add evidence directory:

```markdown
- HN-016 真实媒体 provider 证据：`dist/harness/HN-016/`
```

- [ ] **Step 4: Update architecture docs**

Replace `HN-014 Mock Media` references in `docs/architecture/overview.md` and `docs/architecture/backend-architecture.md` with:

```markdown
Learning Asset Media Provider（mock / OpenAI image / OpenAI TTS）
```

Add a limitation note:

```markdown
- HN-016 后，真实媒体 provider 可通过 `MEDIA_PROVIDER=real` 启用；本地测试默认仍使用 mock provider。
```

- [ ] **Step 5: Run doc diff check**

Run:

```bash
git diff --check
```

Expected: no whitespace errors.

- [ ] **Step 6: Commit**

```bash
git add infra/env/local.example.env docs/harness/upload-recognition-loop.md docs/harness/mvp-readiness-checklist.md docs/architecture/backend-architecture.md docs/architecture/overview.md
git commit -m "docs: add HN-016 media provider harness"
```

---

### Task 8: Full Verification and Evidence

**Files:**
- No source file changes required unless verification exposes regressions.
- Evidence: `dist/harness/HN-016/`

- [ ] **Step 1: Run API tests**

```bash
services/api/.venv/bin/python -m pytest services/api/tests -q
```

Expected: all API tests pass.

- [ ] **Step 2: Run worker tests**

```bash
services/workers/.venv/bin/python -m pytest services/workers/tests -q
```

Expected: all worker tests pass.

- [ ] **Step 3: Run Flutter tests and analyze**

```bash
cd apps/mobile && flutter test
cd apps/mobile && flutter analyze
```

Expected: all Flutter tests pass and analyze reports no issues.

- [ ] **Step 4: Run targeted real provider smoke when key is available**

Use this only when `OPENAI_API_KEY` is configured in the API/worker environment:

```bash
MEDIA_PROVIDER=real MEDIA_IMAGE_PROVIDER=openai MEDIA_TTS_PROVIDER=openai services/workers/.venv/bin/python -m pytest services/workers/tests/test_material_job_task.py::test_process_learning_asset_media_writes_generated_media_to_storage -q
```

Expected: the test still uses fakes and passes without network. For a real network smoke, create a temporary material through the app and inspect worker logs instead of adding network-dependent CI tests.

- [ ] **Step 5: Capture Harness evidence**

Create evidence directory:

```bash
mkdir -p dist/harness/HN-016
```

After confirming a material in simulator or real device, save JSON excerpts:

```bash
curl -s "$API_BASE_URL/materials/$MATERIAL_ID" -H "Authorization: Bearer $ACCESS_TOKEN" > dist/harness/HN-016/material-real-media.json
```

Save worker log excerpt:

```bash
docker compose logs worker --tail=300 > dist/harness/HN-016/media-worker.log
```

Capture course detail screenshot with existing harness command:

```bash
make harness-capture-ios-screen SCREEN=hn016-lesson-real-media
cp dist/harness/screens/hn016-lesson-real-media.png dist/harness/HN-016/lesson-real-media.png
```

- [ ] **Step 6: Final diff and status**

```bash
git status --short
git diff --check
```

Expected: only intended committed changes or ignored `dist/harness/` artifacts remain.

- [ ] **Step 7: Commit evidence docs if tracked docs changed during verification**

If only ignored `dist/harness/` files changed, do not commit them. If checklist evidence notes were edited, run:

```bash
git add docs/harness/mvp-readiness-checklist.md docs/harness/upload-recognition-loop.md
git commit -m "docs: record HN-016 verification"
```

---

## Self-Review

Spec coverage:

- 真实 provider：Task 3 和 Task 4。
- 配图参考讲义裁剪图：Task 2 和 Task 4。
- US/UK TTS：Task 3 和 Task 4。
- storage 保存与回填：Task 2、Task 4、Task 5。
- 独立失败状态：Task 4、Task 5、Task 6。
- mock 只用于测试/显式本地回归：Task 3。
- Harness：Task 7 和 Task 8。

Placeholder scan:

- Placeholder scan completed; no unresolved marker strings remain.
- No incomplete file paths.
- Commands include expected outcomes.

Type consistency:

- Python fields use `generated_image_error`, `tts_us_error`, `tts_uk_error`.
- Dart fields use `generatedImageError`, `ttsUsError`, `ttsUkError`.
- Worker object keys match `generated/media/{material_id}/{asset_id}/image.png`, `tts-us.mp3`, and `tts-uk.mp3`.
