import os
import sys
import tempfile
from pathlib import Path


_TEST_ROOT = tempfile.mkdtemp(prefix="learning-english-worker-reserved-test-")
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_ROOT}/worker.db"
os.environ["LOCAL_STORAGE_PATH"] = f"{_TEST_ROOT}/uploads"
os.environ["PUBLIC_BASE_URL"] = "http://testserver"
os.environ["JWT_SECRET"] = "learning-english-worker-test-secret-at-least-32-bytes"
os.environ["AI_PROVIDER"] = "stub"

API_ROOT = Path(__file__).resolve().parents[2] / "api"
if str(API_ROOT) not in sys.path:
    sys.path.append(str(API_ROOT))
WORKERS_ROOT = Path(__file__).resolve().parents[1]
if str(WORKERS_ROOT) not in sys.path:
    sys.path.append(str(WORKERS_ROOT))

from workers_app import tasks
from workers_app.celery_app import celery_app


# 任务名 -> (函数, 占位返回 status)。锁定预留任务的当前契约,
# 任何"看似要实现"的改动都应同时更新这里,避免占位被误当成真实链路。
RESERVED_TASKS = {
    "materials.enhance_images": (tasks.enhance_images, "enhanced"),
    "materials.run_ocr": (tasks.run_ocr, "ocr_complete"),
    "knowledge.parse_material": (tasks.parse_material, "parsed"),
    "review.generate_tasks": (tasks.generate_review_tasks, "review_tasks_generated"),
    "speaking.generate_tts": (tasks.generate_tts, "tts_generated"),
}


def test_reserved_tasks_are_registered_under_expected_names() -> None:
    for name, (task, _status) in RESERVED_TASKS.items():
        assert task.name == name
        assert name in celery_app.tasks


def test_reserved_tasks_return_placeholder_status_only() -> None:
    for _name, (task, status) in RESERVED_TASKS.items():
        result = task.run("material-123")
        assert result == {"material_id": "material-123", "status": status}


def test_reserved_tasks_have_not_implemented_docstring() -> None:
    # docstring 是这些任务"预留、未实现"的可执行说明;移除即意味着有人开始实现它。
    for _name, (task, _status) in RESERVED_TASKS.items():
        assert task.__doc__ is not None
        assert "未实现" in task.__doc__
