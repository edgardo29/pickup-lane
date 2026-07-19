import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import (
    AdminChatMessageListRead,
    AdminChatModerationActionCreate,
    AdminChatModerationActionResultRead,
    AdminChatSummaryRead,
    AdminNeedASubEnforcementActionCreate,
    AdminNeedASubEnforcementActionResultRead,
    AdminNeedASubPostDetailRead,
    AdminNeedASubPostListRead,
    AdminNeedASubRequestDetailRead,
)
from backend.services.admin_need_a_sub_service import (
    get_admin_need_a_sub_request_detail,
    get_admin_need_a_sub_post_detail,
    get_admin_need_a_sub_post_or_404,
    list_admin_need_a_sub_posts,
)
from backend.services.need_a_sub_enforcement_service import (
    hide_need_a_sub_post,
    remove_need_a_sub_post_by_admin,
    restore_need_a_sub_post,
)
from backend.services.auth_service import require_active_admin
from backend.services.chat_moderation_admin_service import (
    get_admin_need_a_sub_chat_summary,
    list_admin_need_a_sub_chat_messages,
    mark_need_a_sub_chat_message_reviewed,
    remove_need_a_sub_chat_message,
    restore_need_a_sub_chat_message,
)

VALID_NEED_A_SUB_LIST_VIEWS = {
    "active",
    "full",
    "completed",
    "cancelled",
    "expired",
    "removed",
}

router = APIRouter(prefix="/admin/need-a-sub", tags=["admin_need_a_sub"])


@router.get("", response_model=AdminNeedASubPostListRead)
def list_admin_need_a_sub_posts_route(
    query: str | None = Query(default=None),
    view: str = Query(default="active"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=2000),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminNeedASubPostListRead:
    normalized_view = view.strip().lower()
    if normalized_view not in VALID_NEED_A_SUB_LIST_VIEWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="view is not supported.",
        )
    posts, total_count, next_cursor, has_more = list_admin_need_a_sub_posts(
        db,
        viewer_user=current_admin,
        query=query,
        view=normalized_view,
        offset=offset,
        limit=limit,
        cursor=cursor,
    )
    return AdminNeedASubPostListRead(
        posts=posts,
        total_count=total_count,
        offset=offset,
        limit=limit,
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get("/requests/{request_id}", response_model=AdminNeedASubRequestDetailRead)
def get_admin_need_a_sub_request_route(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminNeedASubRequestDetailRead:
    return get_admin_need_a_sub_request_detail(
        db,
        request_id=request_id,
        viewer_user=current_admin,
    )


@router.get("/{post_id}", response_model=AdminNeedASubPostDetailRead)
def get_admin_need_a_sub_post_route(
    post_id: uuid.UUID,
    request_offset: int = Query(default=0, ge=0),
    request_limit: int = Query(default=50, ge=1, le=100),
    audit_offset: int = Query(default=0, ge=0),
    audit_limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminNeedASubPostDetailRead:
    return get_admin_need_a_sub_post_detail(
        db,
        post_id=post_id,
        viewer_user=current_admin,
        request_offset=request_offset,
        request_limit=request_limit,
        audit_offset=audit_offset,
        audit_limit=audit_limit,
    )


@router.post(
    "/{post_id}/hide",
    response_model=AdminNeedASubEnforcementActionResultRead,
)
def hide_admin_need_a_sub_post_route(
    post_id: uuid.UUID,
    payload: AdminNeedASubEnforcementActionCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminNeedASubEnforcementActionResultRead:
    return hide_need_a_sub_post(
        db,
        post_id=post_id,
        admin_user=current_admin,
        payload=payload,
    )


@router.post(
    "/{post_id}/restore",
    response_model=AdminNeedASubEnforcementActionResultRead,
)
def restore_admin_need_a_sub_post_route(
    post_id: uuid.UUID,
    payload: AdminNeedASubEnforcementActionCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminNeedASubEnforcementActionResultRead:
    return restore_need_a_sub_post(
        db,
        post_id=post_id,
        admin_user=current_admin,
        payload=payload,
    )


@router.post(
    "/{post_id}/remove",
    response_model=AdminNeedASubEnforcementActionResultRead,
)
def remove_admin_need_a_sub_post_route(
    post_id: uuid.UUID,
    payload: AdminNeedASubEnforcementActionCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminNeedASubEnforcementActionResultRead:
    return remove_need_a_sub_post_by_admin(
        db,
        post_id=post_id,
        admin_user=current_admin,
        payload=payload,
    )


@router.get("/{post_id}/chat/summary", response_model=AdminChatSummaryRead)
def get_admin_need_a_sub_chat_summary_route(
    post_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminChatSummaryRead:
    return get_admin_need_a_sub_chat_summary(
        db,
        post_id=post_id,
        viewer_user=current_admin,
    )


@router.get("/{post_id}/chat/messages", response_model=AdminChatMessageListRead)
def list_admin_need_a_sub_chat_messages_route(
    post_id: uuid.UUID,
    view: str = Query(default="needs_review"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=20),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminChatMessageListRead:
    get_admin_need_a_sub_post_or_404(db, post_id)
    return list_admin_need_a_sub_chat_messages(
        db,
        post_id=post_id,
        viewer_user=current_admin,
        view=view,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/{post_id}/chat/messages/{message_id}/review",
    response_model=AdminChatModerationActionResultRead,
    status_code=status.HTTP_200_OK,
)
def mark_admin_need_a_sub_chat_message_reviewed_route(
    post_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: AdminChatModerationActionCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminChatModerationActionResultRead:
    get_admin_need_a_sub_post_or_404(db, post_id)
    return mark_need_a_sub_chat_message_reviewed(
        db,
        post_id=post_id,
        message_id=message_id,
        admin_user=current_admin,
        payload=payload,
    )


@router.post(
    "/{post_id}/chat/messages/{message_id}/remove",
    response_model=AdminChatModerationActionResultRead,
    status_code=status.HTTP_200_OK,
)
def remove_admin_need_a_sub_chat_message_route(
    post_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: AdminChatModerationActionCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminChatModerationActionResultRead:
    get_admin_need_a_sub_post_or_404(db, post_id)
    return remove_need_a_sub_chat_message(
        db,
        post_id=post_id,
        message_id=message_id,
        admin_user=current_admin,
        payload=payload,
    )


@router.post(
    "/{post_id}/chat/messages/{message_id}/restore",
    response_model=AdminChatModerationActionResultRead,
    status_code=status.HTTP_200_OK,
)
def restore_admin_need_a_sub_chat_message_route(
    post_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: AdminChatModerationActionCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminChatModerationActionResultRead:
    get_admin_need_a_sub_post_or_404(db, post_id)
    return restore_need_a_sub_chat_message(
        db,
        post_id=post_id,
        message_id=message_id,
        admin_user=current_admin,
        payload=payload,
    )
