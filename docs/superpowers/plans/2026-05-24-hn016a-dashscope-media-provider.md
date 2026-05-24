# HN-016A DashScope Media Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 HN-016 增加 DashScope / 百炼国内媒体 provider，使课程确认后可通过 DashScope 生成彩色配图、US TTS 和 UK TTS，并继续写入现有 storage 与学习资产回填链路。

**Architecture:** 保留现有 `MediaProviderBundle`、worker 和移动端合同；只新增 DashScope image / TTS adapter、配置项、provider factory 分支和 Harness 文档。DashScope 返回的临时 URL 必须由 adapter 立即下载成 bytes，worker 继续通过 `_save_generated_media_asset()` 写入 storage。

**Tech Stack:** Python 3.12, FastAPI service modules, Celery worker, SQLAlchemy models, `httpx`, pytest, Flutter existing media UI tests, DashScope HTTP API.

---

## File Structure

- Modify: `services/api/app/core/settings.py`
  - 增加 DashScope base URL、DashScope image edit model、DashScope polling 配置。
- Modify: `services/api/app/services/learning_asset_media.py`
  - 新增 `DashScopeImageGenerationProvider`、`DashScopeTTSProvider` 和 DashScope 任务轮询 / 下载 helper。
  - 扩展 `build_media_provider_bundle()`，允许 image 和 TTS 分别选择 `openai` 或 `dashscope`。
- Modify: `services/api/tests/test_learning_asset_media_provider.py`
  - 增加 DashScope image / TTS adapter、factory 和配置失败测试。
- Modify: `services/workers/tests/test_material_job_task.py`
  - 增加 DashScope 配置失败不覆盖 ready media、错误脱敏和 existing worker storage 链路回归。
- Modify: `infra/env/local.example.env`
  - 增加 DashScope provider 示例配置。
- Modify: `docs/harness/upload-recognition-loop.md`
  - 增加 HN-016A 需求、验收标准和证据目录。
- Modify: `docs/harness/mvp-readiness-checklist.md`
  - 增加 HN-016A readiness 子项和 `dist/harness/HN-016A/` 证据路径。

Implementation note: do not split provider classes into a new module in this iteration. `learning_asset_media.py` already owns the provider abstraction and OpenAI adapters; adding DashScope there keeps imports and tests focused.

## Task 1: Settings and Environment Contract

**Files:**
- Modify: `services/api/app/core/settings.py`
- Modify: `services/api/tests/test_learning_asset_media_provider.py`

- [ ] **Step 1: Write the failing settings test**

Append these tests to `services/api/tests/test_learning_asset_media_provider.py` after `test_testing_environment_explicit_real_with_whitespace_requires_openai_api_key`:

```python
def test_media_settings_include_dashscope_provider_config(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_media_env(monkeypatch)
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://dashscope.test/api/v1")
    monkeypatch.setenv("MEDIA_IMAGE_EDIT_MODEL", "wanx2.1-imageedit-test")
    monkeypatch.setenv("MEDIA_PROVIDER_POLL_INTERVAL_SECONDS", "3")
    monkeypatch.setenv("MEDIA_PROVIDER_MAX_POLL_SECONDS", "33")

    settings = get_settings()

    assert settings.dashscope_base_url == "https://dashscope.test/api/v1"
    assert settings.media_image_edit_model == "wanx2.1-imageedit-test"
    assert settings.media_provider_poll_interval_seconds == 3
    assert settings.media_provider_max_poll_seconds == 33
```

Also update `_clear_media_env()` in the same file to delete:

```python
"MEDIA_IMAGE_EDIT_MODEL",
"MEDIA_PROVIDER_POLL_INTERVAL_SECONDS",
"MEDIA_PROVIDER_MAX_POLL_SECONDS",
"DASHSCOPE_API_KEY",
"DASHSCOPE_BASE_URL",
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_learning_asset_media_provider.py::test_media_settings_include_dashscope_provider_config -q
```

Expected:

```text
FAILED with "AttributeError: 'Settings' object has no attribute 'dashscope_base_url'"
```

- [ ] **Step 3: Add settings fields**

Modify `Settings` in `services/api/app/core/settings.py` by adding fields after `media_image_model`, after `media_http_trust_env`, and after `dashscope_api_key`:

```python
    media_image_edit_model: str
    media_provider_poll_interval_seconds: int
    media_provider_max_poll_seconds: int
    dashscope_base_url: str
```

Modify `get_settings()` with these values:

```python
        media_image_model=os.getenv("MEDIA_IMAGE_MODEL", "gpt-image-2"),
        media_image_edit_model=os.getenv("MEDIA_IMAGE_EDIT_MODEL", "wanx2.1-imageedit"),
        media_tts_model=os.getenv("MEDIA_TTS_MODEL", "gpt-4o-mini-tts"),
        media_tts_us_voice=os.getenv("MEDIA_TTS_US_VOICE", "coral"),
        media_tts_uk_voice=os.getenv("MEDIA_TTS_UK_VOICE", "cedar"),
        media_request_timeout_seconds=int(os.getenv("MEDIA_REQUEST_TIMEOUT_SECONDS", "180")),
        media_http_trust_env=os.getenv("MEDIA_HTTP_TRUST_ENV", "false").lower() == "true",
        media_provider_poll_interval_seconds=int(os.getenv("MEDIA_PROVIDER_POLL_INTERVAL_SECONDS", "10")),
        media_provider_max_poll_seconds=int(os.getenv("MEDIA_PROVIDER_MAX_POLL_SECONDS", "180")),
        dashscope_base_url=os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/api/v1"),
```

The existing `dashscope_api_key` and `qwen_model` fields remain. Do not rename `dashscope_api_key`.

- [ ] **Step 4: Keep provider factory unchanged**

Do not add DashScope providers or factory branches in Task 1. Keep implementation scoped to settings so this task can commit passing tests without introducing unsupported provider classes.

- [ ] **Step 5: Run full provider test file**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_learning_asset_media_provider.py -q
```

Expected after Task 1 only:

```text
all existing provider tests pass
```

- [ ] **Step 6: Commit**

```bash
git add services/api/app/core/settings.py services/api/tests/test_learning_asset_media_provider.py
git commit -m "test: cover DashScope media provider settings"
```

## Task 2: DashScope Image Provider

**Files:**
- Modify: `services/api/app/services/learning_asset_media.py`
- Modify: `services/api/tests/test_learning_asset_media_provider.py`

- [ ] **Step 1: Add imports for DashScope image provider tests**

Modify the provider import block in `services/api/tests/test_learning_asset_media_provider.py`:

```python
from app.services.learning_asset_media import (
    DashScopeImageGenerationProvider,
    MediaProviderBundle,
    MediaProviderConfigurationError,
    MediaProviderError,
    OpenAIImageGenerationProvider,
    OpenAITTSProvider,
    build_media_provider_bundle,
)
```

- [ ] **Step 2: Write failing no-reference image generation test**

Append after `test_openai_image_generation_wraps_network_errors`:

```python
def test_dashscope_image_generation_without_reference_polls_and_downloads_result() -> None:
    image_payload = b"dashscope-image"

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://dashscope.test/api/v1/services/aigc/image-generation/generation":
            assert request.headers["authorization"] == "Bearer sk-dashscope"
            assert request.headers["x-dashscope-async"] == "enable"
            body = json.loads(request.content)
            assert body["model"] == "wan2.6-image"
            assert body["input"]["messages"][0]["content"] == [{"text": "Draw a colorful queen flashcard."}]
            assert body["parameters"]["watermark"] is False
            assert body["parameters"]["n"] == 1
            return httpx.Response(200, json={"output": {"task_id": "task_image_1", "task_status": "PENDING"}})
        if str(request.url) == "https://dashscope.test/api/v1/tasks/task_image_1":
            return httpx.Response(
                200,
                json={
                    "output": {
                        "task_status": "SUCCEEDED",
                        "choices": [
                            {
                                "message": {
                                    "content": [
                                        {"type": "image", "image": "https://result.test/image.png?Expires=1"}
                                    ]
                                }
                            }
                        ],
                    }
                },
            )
        if str(request.url) == "https://result.test/image.png?Expires=1":
            return httpx.Response(200, content=image_payload)
        return httpx.Response(404, text=str(request.url))

    provider = DashScopeImageGenerationProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="wan2.6-image",
        edit_model="wanx2.1-imageedit",
        client=httpx.Client(transport=FakeTransport(handler)),
        sleep=lambda seconds: None,
    )

    media = provider.generate(
        asset=LearningAsset(id="asset_queen", text="queen", kind="word"),
        prompt="Draw a colorful queen flashcard.",
        reference_image_path=None,
    )

    assert media.payload == image_payload
    assert media.content_type == "image/png"
    assert media.extension == ".png"
```

- [ ] **Step 3: Run no-reference test to verify failure**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_learning_asset_media_provider.py::test_dashscope_image_generation_without_reference_polls_and_downloads_result -q
```

Expected:

```text
ImportError: cannot import name 'DashScopeImageGenerationProvider'
```

- [ ] **Step 4: Implement DashScope image provider skeleton and polling**

In `services/api/app/services/learning_asset_media.py`, add imports:

```python
import time
from collections.abc import Callable
```

Add this class after `OpenAIImageGenerationProvider`:

```python
class DashScopeImageGenerationProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        edit_model: str,
        timeout_seconds: int = 180,
        trust_env: bool = False,
        poll_interval_seconds: int = 10,
        max_poll_seconds: int = 180,
        client: Optional[httpx.Client] = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.edit_model = edit_model
        self.poll_interval_seconds = poll_interval_seconds
        self.max_poll_seconds = max_poll_seconds
        self._client = client or httpx.Client(timeout=timeout_seconds, trust_env=trust_env)
        self._owns_client = client is None
        self._sleep = sleep

    def generate(
        self,
        asset: LearningAsset,
        prompt: str,
        reference_image_path: Optional[Path],
    ) -> GeneratedMedia:
        del asset
        content: list[dict[str, str]] = [{"text": prompt}]
        if reference_image_path is not None:
            content.append({"image": _image_data_url(reference_image_path)})
        task_id = self._create_image_task(content)
        image_url = self._poll_image_result(task_id)
        payload = self._download_result(image_url, "DashScope image result download failed")
        return GeneratedMedia(payload=payload, content_type="image/png", extension=".png")

    def _create_image_task(self, content: list[dict[str, str]]) -> str:
        try:
            response = self._client.post(
                f"{self.base_url}/services/aigc/image-generation/generation",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "X-DashScope-Async": "enable",
                },
                json={
                    "model": self.model,
                    "input": {"messages": [{"role": "user", "content": content}]},
                    "parameters": {
                        "prompt_extend": True,
                        "watermark": False,
                        "n": 1,
                        "size": "1280*1280",
                        "enable_interleave": len(content) > 1,
                    },
                },
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise MediaProviderError("DashScope image task creation failed") from exc
        except ValueError as exc:
            raise MediaProviderError("DashScope image task creation failed") from exc
        task_id = payload.get("output", {}).get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            raise MediaProviderError("DashScope image task response missing output.task_id")
        return task_id

    def _poll_image_result(self, task_id: str) -> str:
        elapsed = 0
        while elapsed <= self.max_poll_seconds:
            try:
                response = self._client.get(
                    f"{self.base_url}/tasks/{task_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPError as exc:
                raise MediaProviderError("DashScope image task polling failed") from exc
            except ValueError as exc:
                raise MediaProviderError("DashScope image task polling failed") from exc

            output = payload.get("output", {})
            status = str(output.get("task_status", "")).upper()
            if status == "SUCCEEDED":
                return _dashscope_first_image_url(output)
            if status in {"FAILED", "CANCELED", "UNKNOWN"}:
                raise MediaProviderError("DashScope image task failed")
            self._sleep(self.poll_interval_seconds)
            elapsed += self.poll_interval_seconds
        raise MediaProviderError("DashScope image task polling timed out")

    def _download_result(self, url: str, error_message: str) -> bytes:
        try:
            response = self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise MediaProviderError(error_message) from exc
        return response.content

    def close(self) -> None:
        if self._owns_client:
            self._client.close()
```

Add helper functions near `_source_bbox_from_manifest()`:

```python
def _image_data_url(path: Path) -> str:
    payload = path.read_bytes()
    image_b64 = base64.b64encode(payload).decode("ascii")
    return f"data:image/png;base64,{image_b64}"


def _dashscope_first_image_url(output: dict[str, Any]) -> str:
    choices = output.get("choices")
    if not isinstance(choices, list):
        raise MediaProviderError("DashScope image result missing output.choices")
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("image"), str) and item["image"].strip():
                return item["image"]
    raise MediaProviderError("DashScope image result missing generated image URL")
```

- [ ] **Step 5: Run no-reference test to verify pass**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_learning_asset_media_provider.py::test_dashscope_image_generation_without_reference_polls_and_downloads_result -q
```

Expected:

```text
1 passed
```

- [ ] **Step 6: Write failing reference-image test**

Append this test after the no-reference DashScope image test:

```python
def test_dashscope_image_generation_with_reference_sends_data_url(tmp_path: Path) -> None:
    reference_path = tmp_path / "reference.png"
    reference_path.write_bytes(b"reference-bytes")

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://dashscope.test/api/v1/services/aigc/image-generation/generation":
            body = json.loads(request.content)
            content = body["input"]["messages"][0]["content"]
            assert content[0] == {"text": "Color the worksheet crop."}
            assert content[1]["image"] == "data:image/png;base64,cmVmZXJlbmNlLWJ5dGVz"
            assert body["parameters"]["enable_interleave"] is True
            return httpx.Response(200, json={"output": {"task_id": "task_reference"}})
        if str(request.url) == "https://dashscope.test/api/v1/tasks/task_reference":
            return httpx.Response(
                200,
                json={
                    "output": {
                        "task_status": "SUCCEEDED",
                        "choices": [
                            {"message": {"content": [{"type": "image", "image": "https://result.test/reference.png"}]}}
                        ],
                    }
                },
            )
        if str(request.url) == "https://result.test/reference.png":
            return httpx.Response(200, content=b"reference-result")
        return httpx.Response(404, text=str(request.url))

    provider = DashScopeImageGenerationProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="wan2.6-image",
        edit_model="wanx2.1-imageedit",
        client=httpx.Client(transport=FakeTransport(handler)),
        sleep=lambda seconds: None,
    )

    media = provider.generate(
        asset=LearningAsset(id="asset_1", text="queen", kind="word"),
        prompt="Color the worksheet crop.",
        reference_image_path=reference_path,
    )

    assert media.payload == b"reference-result"
```

- [ ] **Step 7: Run reference-image test**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_learning_asset_media_provider.py::test_dashscope_image_generation_with_reference_sends_data_url -q
```

Expected:

```text
1 passed
```

- [ ] **Step 8: Add image failure tests**

Append these tests:

```python
def test_dashscope_image_generation_fails_when_task_fails() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/services/aigc/image-generation/generation"):
            return httpx.Response(200, json={"output": {"task_id": "task_failed"}})
        if str(request.url).endswith("/tasks/task_failed"):
            return httpx.Response(200, json={"output": {"task_status": "FAILED"}})
        return httpx.Response(404)

    provider = DashScopeImageGenerationProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="wan2.6-image",
        edit_model="wanx2.1-imageedit",
        client=httpx.Client(transport=FakeTransport(handler)),
        sleep=lambda seconds: None,
    )

    with pytest.raises(MediaProviderError, match="DashScope image task failed"):
        provider.generate(LearningAsset(id="asset_1", text="queen", kind="word"), "Draw queen.", None)


def test_dashscope_image_generation_fails_when_polling_times_out() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/services/aigc/image-generation/generation"):
            return httpx.Response(200, json={"output": {"task_id": "task_slow"}})
        if str(request.url).endswith("/tasks/task_slow"):
            return httpx.Response(200, json={"output": {"task_status": "RUNNING"}})
        return httpx.Response(404)

    provider = DashScopeImageGenerationProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="wan2.6-image",
        edit_model="wanx2.1-imageedit",
        poll_interval_seconds=10,
        max_poll_seconds=0,
        client=httpx.Client(transport=FakeTransport(handler)),
        sleep=lambda seconds: None,
    )

    with pytest.raises(MediaProviderError, match="DashScope image task polling timed out"):
        provider.generate(LearningAsset(id="asset_1", text="queen", kind="word"), "Draw queen.", None)
```

- [ ] **Step 9: Run DashScope image tests**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_learning_asset_media_provider.py -k dashscope_image -q
```

Expected:

```text
4 passed
```

- [ ] **Step 10: Commit**

```bash
git add services/api/app/services/learning_asset_media.py services/api/tests/test_learning_asset_media_provider.py
git commit -m "feat: add DashScope image media provider"
```

## Task 3: DashScope TTS Provider

**Files:**
- Modify: `services/api/app/services/learning_asset_media.py`
- Modify: `services/api/tests/test_learning_asset_media_provider.py`

- [ ] **Step 1: Add DashScope TTS import in tests**

Modify the provider import block in `services/api/tests/test_learning_asset_media_provider.py`:

```python
from app.services.learning_asset_media import (
    DashScopeImageGenerationProvider,
    DashScopeTTSProvider,
    MediaProviderBundle,
    MediaProviderConfigurationError,
    MediaProviderError,
    OpenAIImageGenerationProvider,
    OpenAITTSProvider,
    build_media_provider_bundle,
)
```

- [ ] **Step 2: Write failing TTS success test**

Append after `test_openai_tts_synthesize_wraps_http_failures`:

```python
def test_dashscope_tts_synthesize_uses_cosyvoice_and_downloads_audio() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://dashscope.test/api/v1/services/audio/tts/SpeechSynthesizer":
            assert request.headers["authorization"] == "Bearer sk-dashscope"
            body = json.loads(request.content)
            assert body == {
                "model": "cosyvoice-v3-flash",
                "input": {
                    "text": "A rabbit can hop fast.",
                    "voice": "uk-voice",
                    "format": "mp3",
                    "language_hints": ["en"],
                },
            }
            return httpx.Response(
                200,
                json={"output": {"finish_reason": "stop", "audio": {"url": "https://result.test/audio.mp3"}}},
            )
        if str(request.url) == "https://result.test/audio.mp3":
            return httpx.Response(200, content=b"mp3-bytes")
        return httpx.Response(404, text=str(request.url))

    provider = DashScopeTTSProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="cosyvoice-v3-flash",
        us_voice="us-voice",
        uk_voice="uk-voice",
        client=httpx.Client(transport=FakeTransport(handler)),
    )

    media = provider.synthesize("A rabbit can hop fast.", "uk")

    assert media.payload == b"mp3-bytes"
    assert media.content_type == "audio/mpeg"
    assert media.extension == ".mp3"
```

- [ ] **Step 3: Run TTS success test to verify failure**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_learning_asset_media_provider.py::test_dashscope_tts_synthesize_uses_cosyvoice_and_downloads_audio -q
```

Expected:

```text
ImportError: cannot import name 'DashScopeTTSProvider'
```

- [ ] **Step 4: Implement DashScope TTS provider**

Add this class after `OpenAITTSProvider`:

```python
class DashScopeTTSProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        us_voice: str,
        uk_voice: str,
        timeout_seconds: int = 180,
        trust_env: bool = False,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.us_voice = us_voice
        self.uk_voice = uk_voice
        self._client = client or httpx.Client(timeout=timeout_seconds, trust_env=trust_env)
        self._owns_client = client is None

    def synthesize(self, text: str, accent: str) -> GeneratedMedia:
        accent_key = accent.strip().lower()
        if accent_key not in {"us", "uk"}:
            raise MediaProviderError(f"Unsupported TTS accent: {accent}")
        voice = self.uk_voice if accent_key == "uk" else self.us_voice
        if not voice.strip():
            raise MediaProviderError("DashScope TTS voice is not configured")
        try:
            response = self._client.post(
                f"{self.base_url}/services/audio/tts/SpeechSynthesizer",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": {
                        "text": text,
                        "voice": voice,
                        "format": "mp3",
                        "language_hints": ["en"],
                    },
                },
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise MediaProviderError("DashScope TTS generation failed") from exc
        except ValueError as exc:
            raise MediaProviderError("DashScope TTS generation failed") from exc
        audio_url = payload.get("output", {}).get("audio", {}).get("url")
        if not isinstance(audio_url, str) or not audio_url.strip():
            raise MediaProviderError("DashScope TTS response missing output.audio.url")
        try:
            audio_response = self._client.get(audio_url)
            audio_response.raise_for_status()
        except httpx.HTTPError as exc:
            raise MediaProviderError("DashScope TTS audio download failed") from exc
        return GeneratedMedia(payload=audio_response.content, content_type="audio/mpeg", extension=".mp3")

    def close(self) -> None:
        if self._owns_client:
            self._client.close()
```

- [ ] **Step 5: Run TTS success test to verify pass**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_learning_asset_media_provider.py::test_dashscope_tts_synthesize_uses_cosyvoice_and_downloads_audio -q
```

Expected:

```text
1 passed
```

- [ ] **Step 6: Add TTS failure tests**

Append these tests:

```python
def test_dashscope_tts_synthesize_rejects_unknown_accent() -> None:
    provider = DashScopeTTSProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="cosyvoice-v3-flash",
        us_voice="us-voice",
        uk_voice="uk-voice",
        client=httpx.Client(transport=FakeTransport(lambda request: httpx.Response(200, content=b"unused"))),
    )

    with pytest.raises(MediaProviderError, match="Unsupported TTS accent"):
        provider.synthesize("queen", "au")


def test_dashscope_tts_synthesize_requires_voice() -> None:
    provider = DashScopeTTSProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="cosyvoice-v3-flash",
        us_voice="",
        uk_voice="uk-voice",
        client=httpx.Client(transport=FakeTransport(lambda request: httpx.Response(200, content=b"unused"))),
    )

    with pytest.raises(MediaProviderError, match="DashScope TTS voice is not configured"):
        provider.synthesize("queen", "us")


def test_dashscope_tts_synthesize_fails_without_audio_url() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"output": {"finish_reason": "stop", "audio": {}}})

    provider = DashScopeTTSProvider(
        api_key="sk-dashscope",
        base_url="https://dashscope.test/api/v1",
        model="cosyvoice-v3-flash",
        us_voice="us-voice",
        uk_voice="uk-voice",
        client=httpx.Client(transport=FakeTransport(handler)),
    )

    with pytest.raises(MediaProviderError, match="DashScope TTS response missing output.audio.url"):
        provider.synthesize("queen", "us")
```

- [ ] **Step 7: Run DashScope TTS tests**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_learning_asset_media_provider.py -k dashscope_tts -q
```

Expected:

```text
4 passed
```

- [ ] **Step 8: Commit**

```bash
git add services/api/app/services/learning_asset_media.py services/api/tests/test_learning_asset_media_provider.py
git commit -m "feat: add DashScope TTS media provider"
```

## Task 4: Provider Factory Integration

**Files:**
- Modify: `services/api/app/services/learning_asset_media.py`
- Modify: `services/api/tests/test_learning_asset_media_provider.py`

- [ ] **Step 1: Update factory tests to expect DashScope providers**

The tests from Task 1 should now pass once the factory is implemented. Add a mixed-provider test:

```python
def test_real_bundle_supports_openai_image_and_dashscope_tts(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_media_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("MEDIA_PROVIDER", "real")
    monkeypatch.setenv("MEDIA_IMAGE_PROVIDER", "openai")
    monkeypatch.setenv("MEDIA_TTS_PROVIDER", "dashscope")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-dashscope")
    monkeypatch.setenv("MEDIA_TTS_US_VOICE", "us-voice")
    monkeypatch.setenv("MEDIA_TTS_UK_VOICE", "uk-voice")

    bundle = build_media_provider_bundle(public_base_url="http://testserver")

    assert bundle.mode == "real"
    assert bundle.image_provider.__class__.__name__ == "OpenAIImageGenerationProvider"
    assert bundle.tts_provider.__class__.__name__ == "DashScopeTTSProvider"
    bundle.close()
```

- [ ] **Step 2: Run factory tests to verify failure**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_learning_asset_media_provider.py -k "bundle and dashscope" -q
```

Expected:

```text
FAILED with "Unsupported MEDIA_IMAGE_PROVIDER: dashscope"
```

- [ ] **Step 3: Implement factory helpers**

Replace the provider construction section in `build_media_provider_bundle()` with helper-based code:

```python
    if media_provider != "real":
        raise MediaProviderConfigurationError(f"Unsupported MEDIA_PROVIDER: {settings.media_provider}")

    image_provider = _build_image_provider(settings)
    tts_provider = _build_tts_provider(settings)
    return MediaProviderBundle(image_provider=image_provider, tts_provider=tts_provider, mode="real")
```

Add helpers below `build_media_provider_bundle()`:

```python
def _build_image_provider(settings) -> ImageGenerationProvider:
    provider = settings.media_image_provider.strip().lower()
    if provider == "openai":
        if not settings.openai_api_key:
            raise MediaProviderConfigurationError("OPENAI_API_KEY is required when MEDIA_IMAGE_PROVIDER=openai")
        return OpenAIImageGenerationProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.media_image_model,
            timeout_seconds=settings.media_request_timeout_seconds,
            trust_env=settings.media_http_trust_env,
        )
    if provider == "dashscope":
        if not settings.dashscope_api_key:
            raise MediaProviderConfigurationError("DASHSCOPE_API_KEY is required when MEDIA_IMAGE_PROVIDER=dashscope")
        return DashScopeImageGenerationProvider(
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
            model=settings.media_image_model,
            edit_model=settings.media_image_edit_model,
            timeout_seconds=settings.media_request_timeout_seconds,
            trust_env=settings.media_http_trust_env,
            poll_interval_seconds=settings.media_provider_poll_interval_seconds,
            max_poll_seconds=settings.media_provider_max_poll_seconds,
        )
    raise MediaProviderConfigurationError(f"Unsupported MEDIA_IMAGE_PROVIDER: {settings.media_image_provider}")


def _build_tts_provider(settings) -> TTSProvider:
    provider = settings.media_tts_provider.strip().lower()
    if provider == "openai":
        if not settings.openai_api_key:
            raise MediaProviderConfigurationError("OPENAI_API_KEY is required when MEDIA_TTS_PROVIDER=openai")
        return OpenAITTSProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.media_tts_model,
            us_voice=settings.media_tts_us_voice,
            uk_voice=settings.media_tts_uk_voice,
            timeout_seconds=settings.media_request_timeout_seconds,
            trust_env=settings.media_http_trust_env,
        )
    if provider == "dashscope":
        if not settings.dashscope_api_key:
            raise MediaProviderConfigurationError("DASHSCOPE_API_KEY is required when MEDIA_TTS_PROVIDER=dashscope")
        return DashScopeTTSProvider(
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
            model=settings.media_tts_model,
            us_voice=settings.media_tts_us_voice,
            uk_voice=settings.media_tts_uk_voice,
            timeout_seconds=settings.media_request_timeout_seconds,
            trust_env=settings.media_http_trust_env,
        )
    raise MediaProviderConfigurationError(f"Unsupported MEDIA_TTS_PROVIDER: {settings.media_tts_provider}")
```

- [ ] **Step 4: Run factory tests**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_learning_asset_media_provider.py -k "bundle" -q
```

Expected:

```text
7 passed
```

The exact count may be higher if more bundle tests already exist. Any failure must be investigated.

- [ ] **Step 5: Run provider test file**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests/test_learning_asset_media_provider.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add services/api/app/core/settings.py services/api/app/services/learning_asset_media.py services/api/tests/test_learning_asset_media_provider.py
git commit -m "feat: wire DashScope media provider factory"
```

## Task 5: Worker Regression Coverage

**Files:**
- Modify: `services/workers/tests/test_material_job_task.py`

- [ ] **Step 1: Add fake DashScope-style bundle regression test**

Append near existing `test_process_learning_asset_media_generates_and_stores_provider_media`:

```python
def test_process_learning_asset_media_stores_dashscope_style_media(monkeypatch) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    _seed_media_material("material_dashscope_media", "asset_rabbit", "rabbit")

    class FakeDashScopeImageProvider:
        def generate(self, asset, prompt, reference_image_path):
            assert asset.id == "asset_rabbit"
            assert "rabbit" in prompt
            return GeneratedMedia(b"dashscope-image", "image/png", ".png")

    class FakeDashScopeTTSProvider:
        def synthesize(self, text, accent):
            assert text == "rabbit"
            assert accent in {"us", "uk"}
            return GeneratedMedia(f"dashscope-{accent}".encode(), "audio/mpeg", ".mp3")

    class FakeBundle:
        mode = "real"
        image_provider = FakeDashScopeImageProvider()
        tts_provider = FakeDashScopeTTSProvider()

        def close(self) -> None:
            pass

    monkeypatch.setattr("workers_app.tasks.build_media_provider_bundle", lambda: FakeBundle())

    result = process_learning_asset_media("material_dashscope_media")

    assert result["status"] == "ready"
    db = SessionLocal()
    try:
        material = db.get(CourseMaterialModel, "material_dashscope_media")
        assert material is not None
        asset = material.learning_assets[0]
        assert asset["generated_image_url"].endswith("/generated/media/material_dashscope_media/asset_rabbit/image.png")
        assert asset["tts_us_url"].endswith("/generated/media/material_dashscope_media/asset_rabbit/tts-us.mp3")
        assert asset["tts_uk_url"].endswith("/generated/media/material_dashscope_media/asset_rabbit/tts-uk.mp3")
        stored_assets = db.scalars(
            select(StoredAssetModel).where(StoredAssetModel.owner_type == "generated_media")
        ).all()
        assert len(stored_assets) == 3
    finally:
        db.close()
```

- [ ] **Step 2: Run worker test to verify it passes with existing worker**

Run:

```bash
services/workers/.venv/bin/python -m pytest services/workers/tests/test_material_job_task.py::test_process_learning_asset_media_stores_dashscope_style_media -q
```

Expected:

```text
1 passed
```

This test should pass without production worker changes. If it fails, fix only the worker regression exposed by the test.

- [ ] **Step 3: Add configuration failure sanitization regression for DashScope**

Append near existing provider configuration failure tests:

```python
def test_process_learning_asset_media_sanitizes_dashscope_configuration_failure(monkeypatch) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    _seed_media_material("material_dashscope_config_failure", "asset_queen", "queen")

    def fail_bundle():
        raise MediaProviderConfigurationError("DASHSCOPE_API_KEY is required: sk-secret")

    monkeypatch.setattr("workers_app.tasks.build_media_provider_bundle", fail_bundle)

    result = process_learning_asset_media("material_dashscope_config_failure")

    assert result["status"] == "failed"
    db = SessionLocal()
    try:
        material = db.get(CourseMaterialModel, "material_dashscope_config_failure")
        assert material is not None
        asset = material.learning_assets[0]
        assert asset["generated_image_status"] == "failed"
        assert asset["tts_us_status"] == "failed"
        assert asset["tts_uk_status"] == "failed"
        assert "媒体生成配置失败" in asset["generated_image_error"]
        assert "sk-secret" not in asset["generated_image_error"]
        assert "DASHSCOPE_API_KEY" not in asset["generated_image_error"]
    finally:
        db.close()
```

- [ ] **Step 4: Run focused worker tests**

Run:

```bash
services/workers/.venv/bin/python -m pytest services/workers/tests/test_material_job_task.py -k "dashscope or bundle_configuration or preserves_ready_media" -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Run full worker tests**

Run:

```bash
services/workers/.venv/bin/python -m pytest services/workers/tests -q
```

Expected: all worker tests pass.

- [ ] **Step 6: Commit**

```bash
git add services/workers/tests/test_material_job_task.py
git commit -m "test: cover DashScope media worker behavior"
```

## Task 6: Documentation and Env Examples

**Files:**
- Modify: `infra/env/local.example.env`
- Modify: `docs/harness/upload-recognition-loop.md`
- Modify: `docs/harness/mvp-readiness-checklist.md`
- Modify: `docs/project/2026-05-23-status-and-todo.md`

- [ ] **Step 1: Update env example**

In `infra/env/local.example.env`, under existing media provider settings, add:

```dotenv
# DashScope / Model Studio media provider.
# Use with MEDIA_PROVIDER=real, MEDIA_IMAGE_PROVIDER=dashscope,
# and MEDIA_TTS_PROVIDER=dashscope.
DASHSCOPE_API_KEY=
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/api/v1
MEDIA_IMAGE_EDIT_MODEL=wanx2.1-imageedit
MEDIA_PROVIDER_POLL_INTERVAL_SECONDS=10
MEDIA_PROVIDER_MAX_POLL_SECONDS=180
```

Keep `OPENAI_API_KEY=` and OpenAI defaults. Do not replace them.

- [ ] **Step 2: Update upload recognition harness doc**

In `docs/harness/upload-recognition-loop.md`, after HN-016, add:

```markdown
### HN-016A：DashScope 国内媒体 Provider

**目标：** 在 HN-016 的媒体 provider 抽象上增加 DashScope / 百炼支持，使国内环境可以通过 `MEDIA_IMAGE_PROVIDER=dashscope` 和 `MEDIA_TTS_PROVIDER=dashscope` 生成彩色配图、US TTS 和 UK TTS。

**范围内：**
- DashScope 万相图片生成或参考图生成。
- DashScope CosyVoice 非流式 TTS。
- provider 临时 URL 下载并转存到现有 storage。
- 保留 OpenAI provider、mock provider 和现有移动端合同。

**范围外：**
- 不做 OpenAI / DashScope 自动降级。
- 不做孩子录音上传或发音评分。
- 不把 provider 临时 URL 作为长期资源 URL。

**验收标准：**
- `MEDIA_PROVIDER=real`、`MEDIA_IMAGE_PROVIDER=dashscope`、`MEDIA_TTS_PROVIDER=dashscope` 时，worker 可以完成图片、US TTS、UK TTS 生成和 storage 回填。
- DashScope 配置缺失、任务失败、轮询超时或结果下载失败时，媒体通道进入 `failed`，课程详情显示中文失败态。
- 已经 `ready` 的媒体不会被配置失败重试覆盖。

**证据位置：**
- `dist/harness/HN-016A/`
```

- [ ] **Step 3: Update MVP readiness checklist**

In `docs/harness/mvp-readiness-checklist.md`, near HN-016 status, add:

```markdown
- [ ] `HN-016A` DashScope 国内媒体 Provider：待补齐 DashScope 图片、US TTS、UK TTS、storage 回填和课程详情证据。
```

In the evidence list, add:

```markdown
- HN-016A DashScope 国内媒体 provider 证据：`dist/harness/HN-016A/`
```

- [ ] **Step 4: Update project status doc**

In `docs/project/2026-05-23-status-and-todo.md`, update HN-016 wording from “未开始 / 当前仍使用 mock” to current main reality:

```markdown
| `HN-016` 真实媒体 Provider | 已合入主线，readiness 待证据 | OpenAI provider 已接入，DashScope 国内 provider 进入 HN-016A |
```

Under P1 content loop, replace the HN-016 item with:

```markdown
- [ ] `HN-016` / `HN-016A`：补齐真实 provider 证据；HN-016 已支持 OpenAI，HN-016A 增加 DashScope 国内图片和 TTS provider。
```

- [ ] **Step 5: Run doc checks**

Run:

```bash
rg -n "HN-016.*未开始|当前仍使用 `HN014MockMediaProvider`|待实现真实彩色配图" docs/project docs/harness
git diff --check
```

Expected:

```text
no stale HN-016 lines in docs/project or docs/harness
git diff --check exits 0
```

- [ ] **Step 6: Commit**

```bash
git add infra/env/local.example.env docs/harness/upload-recognition-loop.md docs/harness/mvp-readiness-checklist.md docs/project/2026-05-23-status-and-todo.md
git commit -m "docs: add HN-016A DashScope media harness"
```

## Task 7: Full Verification and Optional Real DashScope Evidence

**Files:**
- No committed code changes required unless evidence docs are updated.
- Evidence output: `dist/harness/HN-016A/` is local artifact and remains untracked.

- [ ] **Step 1: Run API tests**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests -q
```

Expected: all API tests pass.

- [ ] **Step 2: Run worker tests**

Run:

```bash
services/workers/.venv/bin/python -m pytest services/workers/tests -q
```

Expected: all worker tests pass.

- [ ] **Step 3: Run Flutter tests**

Run:

```bash
cd apps/mobile && flutter test
```

Expected: all Flutter tests pass. If sandbox blocks Flutter SDK cache writes with `engine.stamp: Operation not permitted`, rerun with approved sandbox escalation.

- [ ] **Step 4: Run Flutter analyze**

Run:

```bash
cd apps/mobile && flutter analyze
```

Expected:

```text
No issues found!
```

- [ ] **Step 5: Run optional real DashScope smoke only if key is configured**

If `DASHSCOPE_API_KEY` is available in the shell or env file, run a focused manual smoke with one confirmed material. Use local API/worker env:

```bash
MEDIA_PROVIDER=real \
MEDIA_IMAGE_PROVIDER=dashscope \
MEDIA_TTS_PROVIDER=dashscope \
MEDIA_IMAGE_MODEL=wan2.6-image \
MEDIA_TTS_MODEL=cosyvoice-v3-flash \
MEDIA_TTS_US_VOICE="$MEDIA_TTS_US_VOICE" \
MEDIA_TTS_UK_VOICE="$MEDIA_TTS_UK_VOICE" \
DASHSCOPE_API_KEY="$DASHSCOPE_API_KEY" \
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/api/v1 \
services/workers/.venv/bin/python -m pytest services/workers/tests/test_material_job_task.py -k dashscope -q
```

This command is not a substitute for a real material smoke; it validates the selected test slice under DashScope env. Real material evidence requires running API/worker and confirming a material through the app or API.

- [ ] **Step 6: Save real evidence when a DashScope key is available**

Create evidence directory:

```bash
mkdir -p dist/harness/HN-016A
```

Save a sanitized config summary:

```bash
cat > dist/harness/HN-016A/provider-config.json <<'JSON'
{
  "media_provider": "real",
  "media_image_provider": "dashscope",
  "media_tts_provider": "dashscope",
  "media_image_model": "wan2.6-image",
  "media_tts_model": "cosyvoice-v3-flash",
  "dashscope_base_url": "https://dashscope.aliyuncs.com/api/v1",
  "note": "DASHSCOPE_API_KEY is intentionally omitted."
}
JSON
```

After confirming a material, save material JSON:

```bash
curl -s "$API_BASE_URL/materials/$MATERIAL_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  > dist/harness/HN-016A/material-dashscope-media.json
```

Save worker log:

```bash
docker compose logs worker --tail=300 > dist/harness/HN-016A/media-worker.log
```

Do not commit `dist/harness/HN-016A/*` unless the repo convention changes. Mention the local evidence path in final verification notes.

- [ ] **Step 7: Commit only if docs changed during verification**

If Task 7 only creates `dist/` artifacts, do not commit. If checklist status is changed because real evidence was completed, commit:

```bash
git add docs/harness/mvp-readiness-checklist.md docs/harness/upload-recognition-loop.md docs/project/2026-05-23-status-and-todo.md
git commit -m "docs: record HN-016A DashScope verification"
```

## Task 8: Final Review and PR

**Files:**
- No required file changes.

- [ ] **Step 1: Inspect branch diff**

Run:

```bash
git status --short --branch
git diff --stat main..HEAD
```

Expected:

```text
working tree clean
diff limited to provider settings/adapters/tests/docs
```

- [ ] **Step 2: Request final code review**

Use `superpowers:requesting-code-review` or a fresh review subagent if executing with `subagent-driven-development`. Ask the reviewer to focus on:

- DashScope task polling and timeout behavior.
- Temporary URL download and storage boundaries.
- Provider error sanitization.
- OpenAI and mock provider regression risk.
- `MEDIA_PROVIDER=real` with mixed `openai` / `dashscope` combinations.

- [ ] **Step 3: Fix review findings with TDD**

For every blocking review issue:

1. Add or update a failing test in `services/api/tests/test_learning_asset_media_provider.py` or `services/workers/tests/test_material_job_task.py`.
2. Run the focused test and confirm it fails for the reported reason.
3. Implement the minimal fix.
4. Run focused tests and full impacted suite.
5. Commit with a `fix:` message.

- [ ] **Step 4: Final verification**

Run:

```bash
services/api/.venv/bin/python -m pytest services/api/tests -q
services/workers/.venv/bin/python -m pytest services/workers/tests -q
cd apps/mobile && flutter test
cd apps/mobile && flutter analyze
git diff --check main...HEAD
```

Expected: all checks pass.

- [ ] **Step 5: Finish branch**

Use `superpowers:finishing-a-development-branch`.

Recommended PR title:

```text
HN-016A DashScope 国内媒体 Provider
```

Recommended PR summary:

```markdown
## Summary
- 新增 DashScope image / CosyVoice TTS 媒体 provider，保留 OpenAI 与 mock provider。
- 支持 DashScope 异步图片任务轮询、临时 URL 下载和 storage 回填。
- 更新 HN-016A Harness、readiness checklist 和 env 示例。

## Test Plan
- `services/api/.venv/bin/python -m pytest services/api/tests -q`
- `services/workers/.venv/bin/python -m pytest services/workers/tests -q`
- `cd apps/mobile && flutter test`
- `cd apps/mobile && flutter analyze`
```
