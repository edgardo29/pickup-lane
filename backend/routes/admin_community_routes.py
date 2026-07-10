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
    AdminCommunityGameDetailRead,
    AdminCommunityGameHidePaymentTextCreate,
    AdminCommunityGameHidePaymentTextResultRead,
    AdminCommunityGameListRead,
    AdminCommunityGameReviewFlagCreate,
    AdminCommunityGameReviewFlagResultRead,
)
from backend.services.admin_community_service import (
    flag_admin_community_game_for_review,
    get_admin_community_game_detail,
    get_community_game_or_404,
    hide_admin_community_game_payment_text,
    list_admin_community_games,
)
from backend.services.admin_permission_service import (
    PERMISSION_COMMUNITY_GAMES_FLAG,
    PERMISSION_COMMUNITY_GAMES_HIDE_UNSAFE_CONTENT,
    PERMISSION_COMMUNITY_GAMES_READ,
    PERMISSION_CONTENT_MODERATE,
    require_user_admin_permission,
)
from backend.services.auth_service import require_admin_permission
from backend.services.chat_moderation_admin_service import (
    get_admin_game_chat_summary,
    list_admin_game_chat_messages,
    mark_game_chat_message_reviewed,
    remove_game_chat_message,
    restore_game_chat_message,
)

router = APIRouter(prefix="/admin/community-games", tags=["admin_community_games"])

VALID_GAME_LIST_VIEWS = {
    "active",
    "full",
    "completed",
    "cancelled",
    "expired",
    "removed",
}
VALID_PUBLISH_STATUS_FILTERS = {"draft", "published", "archived"}


def validate_optional_filter(
    value: str | None,
    *,
    allowed_values: set[str],
    field_name: str,
) -> str | None:
    if value is None:
        return None

    normalized = value.strip().lower()
    if not normalized:
        return None

    if normalized not in allowed_values:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is not supported.",
        )
    return normalized


@router.get("", response_model=AdminCommunityGameListRead)
def list_admin_community_games_route(
    query: str | None = Query(default=None),
    view: str = Query(default="active"),
    publish_status: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=2000),
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_COMMUNITY_GAMES_READ)
    ),
) -> AdminCommunityGameListRead:
    normalized_view = view.strip().lower()
    if normalized_view not in VALID_GAME_LIST_VIEWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="view is not supported.",
        )

    games, total_count, next_cursor, has_more = list_admin_community_games(
        db,
        viewer_user=current_admin,
        query=query,
        view=normalized_view,
        publish_status=validate_optional_filter(
            publish_status,
            allowed_values=VALID_PUBLISH_STATUS_FILTERS,
            field_name="publish_status",
        ),
        offset=offset,
        limit=limit,
        cursor=cursor,
    )
    return AdminCommunityGameListRead(
        games=games,
        total_count=total_count,
        offset=offset,
        limit=limit,
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get("/{game_id}", response_model=AdminCommunityGameDetailRead)
def get_admin_community_game_route(
    game_id: uuid.UUID,
    support_flag_offset: int = Query(default=0, ge=0),
    support_flag_limit: int = Query(default=50, ge=1, le=100),
    audit_offset: int = Query(default=0, ge=0),
    audit_limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_COMMUNITY_GAMES_READ)
    ),
) -> AdminCommunityGameDetailRead:
    return get_admin_community_game_detail(
        db,
        game_id=game_id,
        viewer_user=current_admin,
        support_flag_offset=support_flag_offset,
        support_flag_limit=support_flag_limit,
        audit_offset=audit_offset,
        audit_limit=audit_limit,
    )


@router.get("/{game_id}/chat/summary", response_model=AdminChatSummaryRead)
def get_admin_community_game_chat_summary_route(
    game_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_CONTENT_MODERATE)
    ),
) -> AdminChatSummaryRead:
    require_user_admin_permission(current_admin, PERMISSION_COMMUNITY_GAMES_READ)
    get_community_game_or_404(db, game_id)
    return get_admin_game_chat_summary(
        db,
        game_id=game_id,
        viewer_user=current_admin,
    )


@router.get("/{game_id}/chat/messages", response_model=AdminChatMessageListRead)
def list_admin_community_game_chat_messages_route(
    game_id: uuid.UUID,
    view: str = Query(default="needs_review"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=20),
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_CONTENT_MODERATE)
    ),
) -> AdminChatMessageListRead:
    require_user_admin_permission(current_admin, PERMISSION_COMMUNITY_GAMES_READ)
    get_community_game_or_404(db, game_id)
    return list_admin_game_chat_messages(
        db,
        game_id=game_id,
        viewer_user=current_admin,
        view=view,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/{game_id}/chat/messages/{message_id}/review",
    response_model=AdminChatModerationActionResultRead,
    status_code=status.HTTP_200_OK,
)
def mark_admin_community_game_chat_message_reviewed_route(
    game_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: AdminChatModerationActionCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_CONTENT_MODERATE)
    ),
) -> AdminChatModerationActionResultRead:
    require_user_admin_permission(current_admin, PERMISSION_COMMUNITY_GAMES_READ)
    get_community_game_or_404(db, game_id)
    return mark_game_chat_message_reviewed(
        db,
        game_id=game_id,
        message_id=message_id,
        admin_user=current_admin,
        payload=payload,
    )


@router.post(
    "/{game_id}/chat/messages/{message_id}/remove",
    response_model=AdminChatModerationActionResultRead,
    status_code=status.HTTP_200_OK,
)
def remove_admin_community_game_chat_message_route(
    game_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: AdminChatModerationActionCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_CONTENT_MODERATE)
    ),
) -> AdminChatModerationActionResultRead:
    require_user_admin_permission(current_admin, PERMISSION_COMMUNITY_GAMES_READ)
    get_community_game_or_404(db, game_id)
    return remove_game_chat_message(
        db,
        game_id=game_id,
        message_id=message_id,
        admin_user=current_admin,
        payload=payload,
    )


@router.post(
    "/{game_id}/chat/messages/{message_id}/restore",
    response_model=AdminChatModerationActionResultRead,
    status_code=status.HTTP_200_OK,
)
def restore_admin_community_game_chat_message_route(
    game_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: AdminChatModerationActionCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_CONTENT_MODERATE)
    ),
) -> AdminChatModerationActionResultRead:
    require_user_admin_permission(current_admin, PERMISSION_COMMUNITY_GAMES_READ)
    get_community_game_or_404(db, game_id)
    return restore_game_chat_message(
        db,
        game_id=game_id,
        message_id=message_id,
        admin_user=current_admin,
        payload=payload,
    )


@router.post(
    "/{game_id}/hide-payment-text",
    response_model=AdminCommunityGameHidePaymentTextResultRead,
)
def hide_admin_community_game_payment_text_route(
    game_id: uuid.UUID,
    payload: AdminCommunityGameHidePaymentTextCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_COMMUNITY_GAMES_HIDE_UNSAFE_CONTENT)
    ),
) -> AdminCommunityGameHidePaymentTextResultRead:
    return hide_admin_community_game_payment_text(
        db,
        game_id=game_id,
        admin_user=current_admin,
        payload=payload,
    )


@router.post(
    "/{game_id}/flag-for-review",
    response_model=AdminCommunityGameReviewFlagResultRead,
)
def flag_admin_community_game_for_review_route(
    game_id: uuid.UUID,
    payload: AdminCommunityGameReviewFlagCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_COMMUNITY_GAMES_FLAG)
    ),
) -> AdminCommunityGameReviewFlagResultRead:
    return flag_admin_community_game_for_review(
        db,
        game_id=game_id,
        admin_user=current_admin,
        payload=payload,
    )
