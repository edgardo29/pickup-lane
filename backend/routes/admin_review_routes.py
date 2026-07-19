import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import (
    AdminReviewCaseActionResultRead,
    AdminReviewCaseDetailRead,
    AdminReviewCaseListRead,
    AdminReviewCaseNoteCreate,
    AdminReviewCaseNoteResultRead,
    AdminReviewCaseClose,
)
from backend.services.admin_review_service import (
    add_review_case_note,
    get_review_case_detail,
    list_review_cases,
    close_review_case,
)
from backend.services.auth_service import require_active_admin

router = APIRouter(prefix="/admin/review-cases", tags=["admin_review_cases"])


@router.get("", response_model=AdminReviewCaseListRead)
def list_admin_review_cases_route(
    case_status: str | None = Query(default=None),
    case_category: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=24, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=2000),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminReviewCaseListRead:
    return list_review_cases(
        db,
        viewer_user=current_admin,
        case_status=case_status,
        case_category=case_category,
        target_type=target_type,
        offset=offset,
        limit=limit,
        cursor=cursor,
    )


@router.get("/{review_case_id}", response_model=AdminReviewCaseDetailRead)
def get_admin_review_case_route(
    review_case_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminReviewCaseDetailRead:
    return get_review_case_detail(
        db,
        review_case_id=review_case_id,
        viewer_user=current_admin,
    )


@router.post("/{review_case_id}/notes", response_model=AdminReviewCaseNoteResultRead)
def add_admin_review_case_note_route(
    review_case_id: uuid.UUID,
    payload: AdminReviewCaseNoteCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminReviewCaseNoteResultRead:
    return add_review_case_note(
        db,
        review_case_id=review_case_id,
        admin_user=current_admin,
        payload=payload,
    )


@router.post("/{review_case_id}/close", response_model=AdminReviewCaseActionResultRead)
def close_admin_review_case_route(
    review_case_id: uuid.UUID,
    payload: AdminReviewCaseClose,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminReviewCaseActionResultRead:
    return close_review_case(
        db,
        review_case_id=review_case_id,
        admin_user=current_admin,
        payload=payload,
    )
