import os
import tempfile

_TEST_ROOT = tempfile.mkdtemp(prefix="learning-english-api-errors-")
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_ROOT}/test.db"
os.environ["LOCAL_STORAGE_PATH"] = f"{_TEST_ROOT}/uploads"
os.environ["PUBLIC_BASE_URL"] = "http://testserver"
os.environ["JWT_SECRET"] = "learning-english-test-secret-at-least-32-bytes"

from fastapi.testclient import TestClient

from app.main import app
from test_vertical_slice import _auth_headers


def test_error_contracts_are_explicit() -> None:
    with TestClient(app) as client:
        unauthorized = client.get("/v1/me")
        assert unauthorized.status_code == 401
        assert unauthorized.json()["detail"] == "Missing access token"

        headers, _ = _auth_headers(client)

        missing_material = client.get("/v1/materials/material_missing", headers=headers)
        assert missing_material.status_code == 404
        assert missing_material.json()["detail"] == "Material not found"

        invalid_child = client.post(
            "/v1/children",
            json={"name": "NoAge"},
            headers=headers,
        )
        assert invalid_child.status_code == 422
        assert "Field required" in invalid_child.json()["detail"]
