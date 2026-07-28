import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas.inbox_schema import (
    InboxCountsRead,
    InboxGlobalSeenUpdate,
    InboxItemRead,
    InboxListRead,
)
from backend.services.auth_service import require_active_user
from backend.services.inbox_service import (
    get_inbox_counts,
    list_app_updates,
    list_game_activity,
    mark_global_platform_notices_seen,
    mark_selected_platform_notice_read,
)

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.get(
    "/app-updates",
    response_model=InboxListRead,
    status_code=status.HTTP_200_OK,
)
def list_app_updates_route(
    cursor: str | None = None,
    filter: str = Query(default="all"),
    limit: int = Query(default=30, ge=1, le=50),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> InboxListRead:
    return list_app_updates(
        db,
        cursor=cursor,
        filter_mode=filter,
        limit=limit,
        user=current_user,
    )


@router.put(
    "/app-updates/global-seen",
    response_model=InboxCountsRead,
    status_code=status.HTTP_200_OK,
)
def mark_global_platform_notices_seen_route(
    payload: InboxGlobalSeenUpdate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> InboxCountsRead:
    return mark_global_platform_notices_seen(
        db,
        seen_token=payload.seen_token,
        user=current_user,
    )


@router.put(
    "/app-updates/platform-notices/{notice_id}/read",
    response_model=InboxItemRead,
    status_code=status.HTTP_200_OK,
)
def mark_selected_platform_notice_read_route(
    notice_id: uuid.UUID,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> InboxItemRead:
    return mark_selected_platform_notice_read(
        db,
        notice_id=notice_id,
        user=current_user,
    )


@router.get(
    "/game-activity",
    response_model=InboxListRead,
    status_code=status.HTTP_200_OK,
)
def list_game_activity_route(
    cursor: str | None = None,
    filter: str = Query(default="all"),
    limit: int = Query(default=30, ge=1, le=50),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> InboxListRead:
    return list_game_activity(
        db,
        cursor=cursor,
        filter_mode=filter,
        limit=limit,
        user=current_user,
    )


@router.get("/counts", response_model=InboxCountsRead, status_code=status.HTTP_200_OK)
def get_inbox_counts_route(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> InboxCountsRead:
    return get_inbox_counts(db, user=current_user)
