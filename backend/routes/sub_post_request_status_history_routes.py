import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import SubPostRequestStatusHistory, User
from backend.routes.auth_routes import get_current_app_user, is_admin_or_moderator
from backend.schemas import SubPostRequestStatusHistoryRead
from backend.services.need_a_sub_service import (
    get_sub_post_or_404,
    get_sub_post_request_or_404,
)

router = APIRouter(
    prefix="/need-a-sub/requests/{request_id}/status-history",
    tags=["need_a_sub_request_status_history"],
)


@router.get(
    "",
    response_model=list[SubPostRequestStatusHistoryRead],
    status_code=status.HTTP_200_OK,
)
def list_need_a_sub_request_status_history(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> list[SubPostRequestStatusHistory]:
    sub_request = get_sub_post_request_or_404(db, request_id)
    sub_post = get_sub_post_or_404(db, sub_request.sub_post_id)
    can_view = (
        sub_request.requester_user_id == current_user.id
        or sub_post.owner_user_id == current_user.id
        or is_admin_or_moderator(current_user)
    )

    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot view this request history.",
        )

    return list(
        db.scalars(
            select(SubPostRequestStatusHistory)
            .where(SubPostRequestStatusHistory.sub_post_request_id == request_id)
            .order_by(SubPostRequestStatusHistory.created_at.asc())
        ).all()
    )
