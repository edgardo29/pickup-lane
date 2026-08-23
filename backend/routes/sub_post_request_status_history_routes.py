import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import SubPostRequestStatusHistory, User
from backend.schemas import SubPostRequestStatusHistoryRead
from backend.services.auth_service import require_active_user
from backend.services.need_a_sub_lifecycle_service import (
    list_sub_post_request_status_history as list_sub_post_request_status_history_workflow,
)
from backend.services.query_pagination import (
    DEFAULT_COLLECTION_LIMIT,
    MAX_COLLECTION_LIMIT,
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
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_COLLECTION_LIMIT, ge=1, le=MAX_COLLECTION_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> list[SubPostRequestStatusHistory]:
    return list_sub_post_request_status_history_workflow(
        db,
        request_id,
        current_user,
        limit=limit,
        offset=offset,
    )
