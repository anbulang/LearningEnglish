from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from app.core.db import SessionLocal
from app.core.settings import get_settings
from app.db.models import ChildProfileModel, ParentAccountModel, WeeklyReportModel
from app.services.shared.weekly_report import current_week_bounds
from conftest import configure_test_environment

configure_test_environment("learning-english-api-admin-outcomes-")


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _dashboard_reader(monkeypatch, token: str = "outcomes-reader-token") -> dict[str, str]:
    monkeypatch.setenv(
        "ADMIN_API_CREDENTIALS_JSON",
        json.dumps(
            [
                {
                    "id": "admin_outcomes_reader",
                    "display_name": "Outcomes Reader",
                    "email": "outcomes-reader@example.com",
                    "role": "Support Viewer",
                    "status": "active",
                    "permissions": ["admin.dashboard.read"],
                    "token_sha256": _token_hash(token),
                }
            ]
        ),
    )
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
    get_settings.cache_clear()
    return {"X-Admin-Token": token}


def _seed_tenant_with_weekly_reports(prefix: str) -> str:
    """One tenant, two children, reports across three ISO weeks (relative to now)."""
    tenant_id = f"tenant_{prefix}"
    now = datetime.now(timezone.utc)
    monday, _ = current_week_bounds()
    db = SessionLocal()
    try:
        db.add(
            ParentAccountModel(
                id=tenant_id, display_name=f"Tenant {prefix}", avatar_url="",
                phone_number=f"1390000{prefix[-4:]}", phone_verified_at=now,
                wechat_union_id=f"u_{tenant_id}", wechat_open_id=f"o_{tenant_id}",
                created_at=now, updated_at=now,
            )
        )
        for suffix, name in (("a", "Ivy"), ("b", "Leo")):
            db.add(
                ChildProfileModel(
                    id=f"child_{prefix}_{suffix}", parent_account_id=tenant_id, name=name,
                    avatar_url="", age=7, level="starter", learning_goal="phonics",
                    preferred_review_duration_minutes=10, parent_notes="",
                    created_at=now, updated_at=now,
                )
            )

        def _week(weeks_ago: int):
            start = monday - timedelta(days=7 * weeks_ago)
            return start, start + timedelta(days=6)

        # week -2: only child a active; week 0 (current): both active; week -1 left empty (gap)
        w2s, w2e = _week(2)
        w0s, w0e = _week(0)
        rows = [
            (f"rpt_{prefix}_a2", f"child_{prefix}_a", w2s, w2e, 1, 2, 1, ["dog"]),
            (f"rpt_{prefix}_a0", f"child_{prefix}_a", w0s, w0e, 3, 6, 2, ["cat"]),
            (f"rpt_{prefix}_b0", f"child_{prefix}_b", w0s, w0e, 2, 5, 1, ["cat", "sun"]),
        ]
        for rid, cid, ws, we, cs, rw, sa, weak in rows:
            db.add(
                WeeklyReportModel(
                    id=rid, child_id=cid, week_start=ws, week_end=we,
                    completed_sessions=cs, reviewed_words=rw, speaking_attempts=sa,
                    weak_items=weak, recommended_actions=[],
                )
            )
        db.commit()
    finally:
        db.close()
    return tenant_id


def test_learning_outcomes_aggregates_scope_by_week(api_client, monkeypatch) -> None:
    headers = _dashboard_reader(monkeypatch)
    tenant_id = _seed_tenant_with_weekly_reports("outc_agg")

    # scope to this tenant so assertions are deterministic in the shared test DB
    resp = api_client.get(
        f"/v1/admin/learning-outcomes?tenant_scope={tenant_id}&weeks=8", headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()

    points = body["points"]
    # consecutive weeks from earliest activity (-2) to current (0) = 3 points, oldest→newest
    assert len(points) == 3
    starts = [p["week_start"] for p in points]
    assert starts == sorted(starts)

    first, gap, latest = points
    assert first["completed_sessions"] == 1 and first["active_children"] == 1  # week -2, child a
    assert gap["completed_sessions"] == 0 and gap["active_children"] == 0  # week -1 zero-filled
    # current week: both children summed (3+2 sessions, 6+5 words, 2+1 attempts)
    assert latest["completed_sessions"] == 5
    assert latest["reviewed_words"] == 11
    assert latest["speaking_attempts"] == 3
    assert latest["active_children"] == 2
    assert latest["weak_item_count"] == 2  # distinct union {cat, sun}

    summary = body["summary"]
    assert summary["children_in_scope"] == 2
    assert summary["active_children_latest"] == 2
    assert summary["completed_sessions"] == 6  # 1 + 0 + 5 across the window
    assert set(summary["weak_items"]) == {"dog", "cat", "sun"}


def test_learning_outcomes_requires_admin_auth(api_client) -> None:
    resp = api_client.get("/v1/admin/learning-outcomes?tenant_scope=all")
    assert resp.status_code in (401, 403)


def test_learning_outcomes_unknown_scope_404(api_client, monkeypatch) -> None:
    headers = _dashboard_reader(monkeypatch, token="outcomes-reader-2")
    resp = api_client.get("/v1/admin/learning-outcomes?tenant_scope=nope", headers=headers)
    assert resp.status_code == 404


def test_learning_outcomes_empty_scope_returns_current_week_only(api_client, monkeypatch) -> None:
    headers = _dashboard_reader(monkeypatch, token="outcomes-reader-3")
    tenant_id = _seed_tenant_with_weekly_reports("outc_empty")
    # a different tenant with no reports → scoped query yields a single current-week zero point
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        db.add(
            ParentAccountModel(
                id="tenant_outc_none", display_name="Empty", avatar_url="",
                phone_number="13900001111", phone_verified_at=now,
                wechat_union_id="u_none", wechat_open_id="o_none",
                created_at=now, updated_at=now,
            )
        )
        db.commit()
    finally:
        db.close()

    resp = api_client.get(
        "/v1/admin/learning-outcomes?tenant_scope=tenant_outc_none", headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["points"]) == 1
    assert body["points"][0]["completed_sessions"] == 0
    assert body["summary"]["children_in_scope"] == 0
