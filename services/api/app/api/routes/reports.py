from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_store
from app.models.contracts import WeeklyReportResponse
from app.repositories.in_memory import InMemoryStore

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/weekly", response_model=WeeklyReportResponse)
def get_weekly_report(
    child_id: str,
    store: InMemoryStore = Depends(get_store),
) -> WeeklyReportResponse:
    report = store.weekly_reports.get(child_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return WeeklyReportResponse(report=report)
