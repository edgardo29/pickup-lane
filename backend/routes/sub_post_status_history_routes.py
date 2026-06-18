import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import SubPostStatusHistory, User
from backend.schemas import SubPostStatusHistoryRead
from backend.services.admin_permission_service import (
    PERMISSION_NEED_A_SUB_MODERATE,
    user_has_admin_permission,
)
from backend.services.auth_service import require_active_user
from backend.services.need_a_sub_service import get_sub_post_or_404

router = APIRouter(
    prefix="/need-a-sub/posts/{sub_post_id}/status-history",
    tags=["need_a_sub_post_status_history"],
)


@router.get(
    "",
    response_model=list[SubPostStatusHistoryRead],
    status_code=status.HTTP_200_OK,
)
def list_need_a_sub_post_status_history(
    sub_post_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> list[SubPostStatusHistory]:
    sub_post = get_sub_post_or_404(db, sub_post_id)

    if (
        sub_post.owner_user_id != current_user.id
        and not user_has_admin_permission(current_user, PERMISSION_NEED_A_SUB_MODERATE)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot view this post history.",
        )

    return list(
        db.scalars(
            select(SubPostStatusHistory)
            .where(SubPostStatusHistory.sub_post_id == sub_post_id)
            .order_by(SubPostStatusHistory.created_at.asc())
        ).all()
    )
