import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import SubPostRequestStatusHistory, User
from backend.schemas import SubPostRequestStatusHistoryRead
from backend.services.auth_service import require_active_user
from backend.services.need_a_sub_lifecycle_service import (
    list_sub_post_request_status_history as list_sub_post_request_status_history_workflow,
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
    current_user: User = Depends(require_active_user),
) -> list[SubPostRequestStatusHistory]:
    return list_sub_post_request_status_history_workflow(db, request_id, current_user)
