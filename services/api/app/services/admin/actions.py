from __future__ import annotations

from typing import Literal, TypedDict

ActionStatus = Literal["success", "noop", "failed", "unavailable"]


class AdminActionResult(TypedDict):
    action: str
    status: ActionStatus
    resource_type: str
    resource_id: str
    tenant_id: str
    message: str


def build_action_result(
    *,
    action: str,
    status: ActionStatus,
    resource_type: str,
    resource_id: str,
    tenant_id: str,
    message: str,
) -> AdminActionResult:
    return {
        "action": action,
        "status": status,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "tenant_id": tenant_id,
        "message": message,
    }
