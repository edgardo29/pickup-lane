import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import (
    AdminNeedASubChatModerationCreate,
    AdminNeedASubChatModerationResultRead,
    AdminNeedASubChatRead,
    AdminNeedASubPostDetailRead,
    AdminNeedASubPostListRead,
)
from backend.services.admin_need_a_sub_chat_service import (
    get_admin_need_a_sub_chat,
    moderate_admin_need_a_sub_chat_message,
)
from backend.services.admin_need_a_sub_service import (
    get_admin_need_a_sub_post_detail,
    list_admin_need_a_sub_posts,
)
from backend.services.admin_permission_service import (
    PERMISSION_NEED_A_SUB_MODERATE,
)
from backend.services.auth_service import require_admin_permission
from backend.services.need_a_sub_service import expire_due_posts_and_requests

router = APIRouter(prefix="/admin/need-a-sub", tags=["admin_need_a_sub"])

VALID_POST_STATUSES = {"active", "filled", "expired", "canceled", "removed"}


@router.get("", response_model=AdminNeedASubPostListRead)
def list_admin_need_a_sub_posts_route(
    query: str | None = Query(default=None),
    post_status: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_NEED_A_SUB_MODERATE)
    ),
) -> AdminNeedASubPostListRead:
    normalized_status = post_status.strip().lower() if post_status else None
    if normalized_status and normalized_status not in VALID_POST_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="post_status is not supported.",
        )
    expire_due_posts_and_requests(db)
    posts, total_count = list_admin_need_a_sub_posts(
        db,
        viewer_user=current_admin,
        query=query,
        post_status=normalized_status or None,
        offset=offset,
        limit=limit,
    )
    return AdminNeedASubPostListRead(
        posts=posts,
        total_count=total_count,
        offset=offset,
        limit=limit,
    )


@router.get("/{post_id}", response_model=AdminNeedASubPostDetailRead)
def get_admin_need_a_sub_post_route(
    post_id: uuid.UUID,
    request_offset: int = Query(default=0, ge=0),
    request_limit: int = Query(default=50, ge=1, le=100),
    audit_offset: int = Query(default=0, ge=0),
    audit_limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_NEED_A_SUB_MODERATE)
    ),
) -> AdminNeedASubPostDetailRead:
    expire_due_posts_and_requests(db)
    return get_admin_need_a_sub_post_detail(
        db,
        post_id=post_id,
        viewer_user=current_admin,
        request_offset=request_offset,
        request_limit=request_limit,
        audit_offset=audit_offset,
        audit_limit=audit_limit,
    )


@router.get("/{post_id}/chat", response_model=AdminNeedASubChatRead)
def get_admin_need_a_sub_chat_route(
    post_id: uuid.UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_NEED_A_SUB_MODERATE)
    ),
) -> AdminNeedASubChatRead:
    return get_admin_need_a_sub_chat(
        db,
        post_id=post_id,
        viewer_user=current_admin,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/{post_id}/chat/messages/{message_id}/hide",
    response_model=AdminNeedASubChatModerationResultRead,
)
def hide_admin_need_a_sub_chat_message_route(
    post_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: AdminNeedASubChatModerationCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_NEED_A_SUB_MODERATE)
    ),
) -> AdminNeedASubChatModerationResultRead:
    return moderate_admin_need_a_sub_chat_message(
        db,
        post_id=post_id,
        message_id=message_id,
        moderator_user=current_admin,
        payload=payload,
        moderation_action="hide",
    )


@router.post(
    "/{post_id}/chat/messages/{message_id}/remove",
    response_model=AdminNeedASubChatModerationResultRead,
)
def remove_admin_need_a_sub_chat_message_route(
    post_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: AdminNeedASubChatModerationCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_NEED_A_SUB_MODERATE)
    ),
) -> AdminNeedASubChatModerationResultRead:
    return moderate_admin_need_a_sub_chat_message(
        db,
        post_id=post_id,
        message_id=message_id,
        moderator_user=current_admin,
        payload=payload,
        moderation_action="remove",
    )
