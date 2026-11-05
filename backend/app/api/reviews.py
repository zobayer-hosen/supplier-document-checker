from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.batch import DashboardSummary
from app.schemas.evaluation import PendingReviewItem
from app.services import results_service, review_service

router = APIRouter(tags=["reviews and dashboard"])


@router.get("/reviews/pending", response_model=list[PendingReviewItem])
def pending_reviews(session: Session = Depends(get_db)):
    """Documents that need a person and do not have a completed review yet."""
    return review_service.list_pending_reviews(session)


@router.get("/dashboard", response_model=DashboardSummary)
def dashboard(session: Session = Depends(get_db)):
    """Totals for the dashboard page."""
    return results_service.dashboard_summary(session)
