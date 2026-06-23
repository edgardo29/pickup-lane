import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import SubPostStatusHistory, User
from backend.schemas import SubPostStatusHistoryRead
from backend.services.auth_service import require_active_user
from backend.services.need_a_sub_lifecycle_service import (
    list_sub_post_status_history as list_sub_post_status_history_workflow,
)

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
    return list_sub_post_status_history_workflow(db, sub_post_id, current_user)
