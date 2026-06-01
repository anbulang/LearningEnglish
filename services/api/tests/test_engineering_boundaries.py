from __future__ import annotations

from pathlib import Path

from app.main import app


API_ROOT = Path(__file__).resolve().parents[1] / "app" / "api"
SERVICES_ROOT = Path(__file__).resolve().parents[1] / "app" / "services"


def test_api_routes_are_grouped_by_product_boundary() -> None:
    assert (API_ROOT / "parent").is_dir()
    assert (API_ROOT / "admin").is_dir()
    assert not (API_ROOT / "routes").exists()


def test_services_are_grouped_by_runtime_boundary() -> None:
    assert (SERVICES_ROOT / "parent").is_dir()
    assert (SERVICES_ROOT / "admin").is_dir()
    assert (SERVICES_ROOT / "shared").is_dir()
    assert not list(SERVICES_ROOT.glob("admin_*.py"))


def test_public_api_paths_stay_stable_after_package_split() -> None:
    openapi = app.openapi()
    paths = set(openapi["paths"])

    parent_paths = {
        "/v1/auth/wechat/login",
        "/v1/auth/phone/request-otp",
        "/v1/auth/phone/bind",
        "/v1/me",
        "/v1/children",
        "/v1/materials",
        "/v1/reports/weekly",
    }
    admin_paths = {
        "/v1/admin/dashboard",
        "/v1/admin/operations",
        "/v1/admin/access",
        "/v1/admin/audit-events",
        "/v1/admin/impersonation-sessions",
    }

    assert parent_paths.issubset(paths)
    assert admin_paths.issubset(paths)
