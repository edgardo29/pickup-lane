"""Admin chat moderation workflows scoped by owning feature routes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, load_only

from backend.models import (
    AdminAction,
    AdminTargetNotice,
    ChatMessage,
    Game,
    GameChat,
    GameChatMessageDetection,
    SubPost,
    SubPostChat,
    SubPostChatMessage,
    SubPostChatMessageDetection,
    User,
)
from backend.schemas.admin_chat_moderation_schema import (
    AdminChatDetectionRead,
    AdminChatMessageContentRead,
    AdminChatMessageListRead,
    AdminChatMessageRead,
    AdminChatModerationActionCreate,
    AdminChatModerationActionResultRead,
    AdminChatSummaryRead,
)
from backend.services.admin_action_service import (
    integrity_error_matches_constraint,
    record_admin_action,
    record_sensitive_admin_read,
)
from backend.services.admin_record_rules import (
    normalize_idempotency_key,
    normalize_optional_text,
)
from backend.services.admin_target_notice_service import create_admin_target_notice
from backend.services.auth_service import require_active_admin_user
from backend.services.chat_moderation_service import build_safe_message_preview
from backend.services.game_chat_service import (
    reconcile_game_chat_notifications_after_moderation,
    refresh_game_chat_summary,
)
from backend.services.sub_post_chat_service import (
    reconcile_sub_chat_notifications_after_moderation,
    refresh_sub_post_chat_summary,
)
from backend.services.user_service import get_user_display_name

CHAT_SCOPE_GAME = "game"
CHAT_SCOPE_NEED_A_SUB = "need_a_sub"
VALID_CHAT_SCOPES = {CHAT_SCOPE_GAME, CHAT_SCOPE_NEED_A_SUB}
VALID_GAME_CHAT_PARENT_TYPES = {"official", "community"}
TERMINAL_GAME_CHAT_RESTORATION_STATUSES = {"cancelled", "removed"}
TERMINAL_SUB_CHAT_RESTORATION_STATUSES = {"cancelled", "removed"}
VALID_REVIEW_VIEWS = {"needs_review", "removed", "all"}
DEFAULT_REVIEW_PAGE_SIZE = 20
MAX_REVIEW_PAGE_SIZE = 20
CHAT_NOTICE_COPY = {
    (CHAT_SCOPE_GAME, "remove_chat_message"): (
        "game_chat_message_removed",
        "Game chat message removed",
        (
            "A message you posted in a game chat was removed for safety or "
            "policy reasons. Contact support if you believe this was a mistake."
        ),
    ),
    (CHAT_SCOPE_GAME, "restore_chat_message"): (
        "game_chat_message_restored",
        "Game chat message restored",
        "A message you posted in a game chat was restored and is visible again.",
    ),
    (CHAT_SCOPE_NEED_A_SUB, "remove_chat_message"): (
        "need_sub_chat_message_removed",
        "Need a Sub chat message removed",
        (
            "A message you posted in a Need a Sub chat was removed for safety "
            "or policy reasons. Contact support if you believe this was a mistake."
        ),
    ),
    (CHAT_SCOPE_NEED_A_SUB, "restore_chat_message"): (
        "need_sub_chat_message_restored",
        "Need a Sub chat message restored",
        (
            "A message you posted in a Need a Sub chat was restored and is "
            "visible again."
        ),
    ),
}
CHAT_IDEMPOTENCY_CONSTRAINTS = {
    (CHAT_SCOPE_GAME, "mark_chat_message_reviewed"): (
        "uq_admin_actions_mark_reviewed_chat_message_idempotency"
    ),
    (CHAT_SCOPE_GAME, "remove_chat_message"): (
        "uq_admin_actions_remove_chat_message_idempotency"
    ),
    (CHAT_SCOPE_GAME, "restore_chat_message"): (
        "uq_admin_actions_restore_chat_message_idempotency"
    ),
    (CHAT_SCOPE_NEED_A_SUB, "mark_chat_message_reviewed"): (
        "uq_admin_actions_mark_reviewed_sub_chat_message_idempotency"
    ),
    (CHAT_SCOPE_NEED_A_SUB, "remove_chat_message"): (
        "uq_admin_actions_remove_sub_chat_message_idempotency"
    ),
    (CHAT_SCOPE_NEED_A_SUB, "restore_chat_message"): (
        "uq_admin_actions_restore_sub_chat_message_idempotency"
    ),
}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def normalize_chat_scope(chat_scope: str) -> str:
    normalized = chat_scope.strip().lower()
    if normalized not in VALID_CHAT_SCOPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chat_scope must be 'game' or 'need_a_sub'.",
        )
    return normalized


def normalize_review_view(view: str) -> str:
    normalized = view.strip().lower()
    if normalized not in VALID_REVIEW_VIEWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="view must be 'needs_review', 'removed', or 'all'.",
        )
    return normalized


def normalize_action_payload(
    payload: AdminChatModerationActionCreate,
    *,
    require_reason: bool,
) -> tuple[str | None, str]:
    reason = normalize_optional_text(payload.reason, "reason")
    if require_reason and reason is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reason is required.",
        )
    idempotency_key = normalize_idempotency_key(payload.idempotency_key)
    if idempotency_key is None or len(idempotency_key) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="idempotency_key must be at least 8 characters.",
        )
    return reason, idempotency_key


def serialize_detections(
    detections: list[GameChatMessageDetection | SubPostChatMessageDetection],
) -> list[AdminChatDetectionRead]:
    return [
        AdminChatDetectionRead(
            category=detection.category,
            severity=detection.severity,
        )
        for detection in detections
    ]


def get_game_message_detections(
    db: Session,
    message_id: uuid.UUID,
) -> list[GameChatMessageDetection]:
    return list(
        db.scalars(
            select(GameChatMessageDetection)
            .where(GameChatMessageDetection.message_id == message_id)
            .order_by(GameChatMessageDetection.created_at.asc())
        ).all()
    )


def get_sub_message_detections(
    db: Session,
    message_id: uuid.UUID,
) -> list[SubPostChatMessageDetection]:
    return list(
        db.scalars(
            select(SubPostChatMessageDetection)
            .where(SubPostChatMessageDetection.message_id == message_id)
            .order_by(SubPostChatMessageDetection.created_at.asc())
        ).all()
    )


def serialize_game_chat_message(
    db: Session,
    message: ChatMessage,
) -> AdminChatMessageRead:
    sender = db.get(User, message.sender_user_id) if message.sender_user_id else None
    sender_display_name = (
        get_user_display_name(sender, fallback="Deleted User")
        if sender is not None
        else "Deleted User"
    )
    return AdminChatMessageRead(
        id=message.id,
        sender_display_name=sender_display_name,
        message_excerpt=build_safe_message_preview(message.message_body),
        visibility_status=message.visibility_status,
        review_status=message.review_status,
        created_at=message.created_at,
        removed_source=message.removed_source,
        detections=serialize_detections(get_game_message_detections(db, message.id)),
    )


def serialize_need_a_sub_chat_message(
    db: Session,
    message: SubPostChatMessage,
) -> AdminChatMessageRead:
    return AdminChatMessageRead(
        id=message.id,
        sender_display_name=message.sender_display_name_snapshot,
        message_excerpt=build_safe_message_preview(message.message_body),
        visibility_status=message.visibility_status,
        review_status=message.review_status,
        created_at=message.created_at,
        removed_source=message.removed_source,
        detections=serialize_detections(get_sub_message_detections(db, message.id)),
    )


def game_message_filters(
    view: str,
    parent_id: uuid.UUID | None,
) -> list[object]:
    filters: list[object] = []
    if parent_id is not None:
        filters.append(GameChat.game_id == parent_id)
    if view == "needs_review":
        filters.append(ChatMessage.review_status == "needs_review")
    elif view == "removed":
        filters.append(ChatMessage.visibility_status == "removed")
    return filters


def sub_message_filters(
    view: str,
    parent_id: uuid.UUID | None,
) -> list[object]:
    filters: list[object] = []
    if parent_id is not None:
        filters.append(SubPostChat.sub_post_id == parent_id)
    if view == "needs_review":
        filters.append(SubPostChatMessage.review_status == "needs_review")
    elif view == "removed":
        filters.append(SubPostChatMessage.visibility_status == "removed")
    return filters


def count_game_chat_messages(
    db: Session,
    *,
    view: str,
    parent_id: uuid.UUID | None,
) -> int:
    statement = (
        select(func.count())
        .select_from(ChatMessage)
        .join(GameChat, GameChat.id == ChatMessage.chat_id)
        .where(*game_message_filters(view, parent_id))
    )
    return db.scalar(statement) or 0


def count_need_a_sub_chat_messages(
    db: Session,
    *,
    view: str,
    parent_id: uuid.UUID | None,
) -> int:
    statement = (
        select(func.count())
        .select_from(SubPostChatMessage)
        .join(SubPostChat, SubPostChat.id == SubPostChatMessage.chat_id)
        .where(*sub_message_filters(view, parent_id))
    )
    return db.scalar(statement) or 0


def list_game_chat_messages(
    db: Session,
    *,
    view: str,
    parent_id: uuid.UUID | None,
    offset: int,
    limit: int,
) -> list[AdminChatMessageRead]:
    rows = db.execute(
        select(ChatMessage, GameChat, Game)
        .options(
            load_only(
                ChatMessage.id,
                ChatMessage.sender_user_id,
                ChatMessage.message_body,
                ChatMessage.visibility_status,
                ChatMessage.review_status,
                ChatMessage.created_at,
                ChatMessage.removed_source,
            )
        )
        .join(GameChat, GameChat.id == ChatMessage.chat_id)
        .join(Game, Game.id == GameChat.game_id)
        .where(*game_message_filters(view, parent_id))
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [serialize_game_chat_message(db, message) for message, _, _ in rows]


def list_need_a_sub_chat_messages(
    db: Session,
    *,
    view: str,
    parent_id: uuid.UUID | None,
    offset: int,
    limit: int,
) -> list[AdminChatMessageRead]:
    rows = db.execute(
        select(SubPostChatMessage, SubPostChat, SubPost)
        .options(
            load_only(
                SubPostChatMessage.id,
                SubPostChatMessage.sender_display_name_snapshot,
                SubPostChatMessage.message_body,
                SubPostChatMessage.visibility_status,
                SubPostChatMessage.review_status,
                SubPostChatMessage.created_at,
                SubPostChatMessage.removed_source,
            )
        )
        .join(SubPostChat, SubPostChat.id == SubPostChatMessage.chat_id)
        .join(SubPost, SubPost.id == SubPostChat.sub_post_id)
        .where(*sub_message_filters(view, parent_id))
        .order_by(SubPostChatMessage.created_at.desc(), SubPostChatMessage.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [serialize_need_a_sub_chat_message(db, message) for message, _, _ in rows]


def game_chat_page_has_messages(
    db: Session,
    *,
    view: str,
    parent_id: uuid.UUID,
    offset: int,
    limit: int,
) -> bool:
    return db.scalar(
        select(ChatMessage.id)
        .join(GameChat, GameChat.id == ChatMessage.chat_id)
        .where(*game_message_filters(view, parent_id))
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .offset(offset)
        .limit(limit)
    ) is not None


def need_a_sub_chat_page_has_messages(
    db: Session,
    *,
    view: str,
    parent_id: uuid.UUID,
    offset: int,
    limit: int,
) -> bool:
    return db.scalar(
        select(SubPostChatMessage.id)
        .join(SubPostChat, SubPostChat.id == SubPostChatMessage.chat_id)
        .where(*sub_message_filters(view, parent_id))
        .order_by(SubPostChatMessage.created_at.desc(), SubPostChatMessage.id.desc())
        .offset(offset)
        .limit(limit)
    ) is not None


def build_message_list_response(
    *,
    messages: list[AdminChatMessageRead],
    total_count: int,
    offset: int,
    limit: int,
) -> AdminChatMessageListRead:
    page_offset = max(0, offset)
    page_limit = max(1, min(limit, MAX_REVIEW_PAGE_SIZE))
    return AdminChatMessageListRead(
        messages=messages,
        total_count=total_count,
        offset=page_offset,
        limit=page_limit,
    )


def list_admin_game_chat_messages(
    db: Session,
    *,
    viewer_user: User,
    game_id: uuid.UUID,
    view: str = "needs_review",
    offset: int = 0,
    limit: int = DEFAULT_REVIEW_PAGE_SIZE,
    expected_game_type: str,
) -> AdminChatMessageListRead:
    require_active_admin_user(viewer_user)
    game_identity = db.execute(
        select(Game.id, Game.game_type, Game.deleted_at).where(Game.id == game_id)
    ).one_or_none()
    if (
        game_identity is None
        or game_identity.game_type != expected_game_type
        or game_identity.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )
    normalized_view = normalize_review_view(view)
    page_offset = max(0, offset)
    page_limit = max(1, min(limit, MAX_REVIEW_PAGE_SIZE))
    total_count = count_game_chat_messages(
        db,
        view=normalized_view,
        parent_id=game_id,
    )
    if not game_chat_page_has_messages(
        db,
        view=normalized_view,
        parent_id=game_id,
        offset=page_offset,
        limit=page_limit,
    ):
        return build_message_list_response(
            messages=[],
            total_count=total_count,
            offset=page_offset,
            limit=page_limit,
        )
    record_sensitive_admin_read(
        authenticated_admin_id=viewer_user.id,
        action_type="read_game_chat_moderation",
        target_game_id=game_id,
        reason=None,
        metadata=None,
    )
    messages = list_game_chat_messages(
        db,
        view=normalized_view,
        parent_id=game_id,
        offset=page_offset,
        limit=page_limit,
    )
    return build_message_list_response(
        messages=messages,
        total_count=total_count,
        offset=page_offset,
        limit=page_limit,
    )


def list_admin_need_a_sub_chat_messages(
    db: Session,
    *,
    viewer_user: User,
    post_id: uuid.UUID,
    view: str = "needs_review",
    offset: int = 0,
    limit: int = DEFAULT_REVIEW_PAGE_SIZE,
) -> AdminChatMessageListRead:
    require_active_admin_user(viewer_user)
    normalized_view = normalize_review_view(view)
    page_offset = max(0, offset)
    page_limit = max(1, min(limit, MAX_REVIEW_PAGE_SIZE))
    total_count = count_need_a_sub_chat_messages(
        db,
        view=normalized_view,
        parent_id=post_id,
    )
    if not need_a_sub_chat_page_has_messages(
        db,
        view=normalized_view,
        parent_id=post_id,
        offset=page_offset,
        limit=page_limit,
    ):
        return build_message_list_response(
            messages=[],
            total_count=total_count,
            offset=page_offset,
            limit=page_limit,
        )
    record_sensitive_admin_read(
        authenticated_admin_id=viewer_user.id,
        action_type="read_need_sub_chat_moderation",
        target_sub_post_id=post_id,
        reason=None,
        metadata=None,
    )
    messages = list_need_a_sub_chat_messages(
        db,
        view=normalized_view,
        parent_id=post_id,
        offset=page_offset,
        limit=page_limit,
    )
    return build_message_list_response(
        messages=messages,
        total_count=total_count,
        offset=page_offset,
        limit=page_limit,
    )


def get_admin_game_chat_summary(
    db: Session,
    *,
    game_id: uuid.UUID,
    viewer_user: User,
) -> AdminChatSummaryRead:
    require_active_admin_user(viewer_user)
    game = db.get(Game, game_id)
    if game is None or game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found."
        )
    chat = db.scalar(select(GameChat).where(GameChat.game_id == game.id))
    if chat is None:
        return AdminChatSummaryRead(
            chat_status="not_created",
        )
    return AdminChatSummaryRead(
        chat_status=chat.chat_status,
        message_count=chat.message_count,
        needs_review_count=chat.needs_review_count,
        removed_count=chat.removed_count,
    )


def get_admin_need_a_sub_chat_summary(
    db: Session,
    *,
    post_id: uuid.UUID,
    viewer_user: User,
) -> AdminChatSummaryRead:
    require_active_admin_user(viewer_user)
    post = db.get(SubPost, post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub post not found.",
        )
    chat = db.scalar(select(SubPostChat).where(SubPostChat.sub_post_id == post.id))
    if chat is None:
        return AdminChatSummaryRead(
            chat_status="not_created",
        )
    return AdminChatSummaryRead(
        chat_status=chat.chat_status,
        message_count=chat.message_count,
        needs_review_count=chat.needs_review_count,
        removed_count=chat.removed_count,
    )


def reveal_admin_game_chat_message_content(
    db: Session,
    *,
    viewer_user: User,
    game_id: uuid.UUID,
    message_id: uuid.UUID,
    expected_game_type: str,
) -> AdminChatMessageContentRead:
    require_active_admin_user(viewer_user)
    identity = db.execute(
        select(ChatMessage.id)
        .join(GameChat, GameChat.id == ChatMessage.chat_id)
        .join(Game, Game.id == GameChat.game_id)
        .where(
            ChatMessage.id == message_id,
            GameChat.game_id == game_id,
            Game.game_type == expected_game_type,
            Game.deleted_at.is_(None),
        )
    ).one_or_none()
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat message not found.",
        )

    record_sensitive_admin_read(
        authenticated_admin_id=viewer_user.id,
        action_type="reveal_game_chat_message_content",
        target_game_id=game_id,
        target_message_id=message_id,
        reason=None,
        metadata=None,
    )
    message = db.execute(
        select(ChatMessage.id, ChatMessage.message_body)
        .join(GameChat, GameChat.id == ChatMessage.chat_id)
        .join(Game, Game.id == GameChat.game_id)
        .where(
            ChatMessage.id == message_id,
            GameChat.game_id == game_id,
            Game.game_type == expected_game_type,
            Game.deleted_at.is_(None),
        )
    ).one_or_none()
    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat message not found.",
        )
    return AdminChatMessageContentRead(id=message.id, message_body=message.message_body)


def reveal_admin_need_a_sub_chat_message_content(
    db: Session,
    *,
    viewer_user: User,
    post_id: uuid.UUID,
    message_id: uuid.UUID,
) -> AdminChatMessageContentRead:
    require_active_admin_user(viewer_user)
    identity = db.execute(
        select(SubPostChatMessage.id)
        .join(SubPostChat, SubPostChat.id == SubPostChatMessage.chat_id)
        .join(SubPost, SubPost.id == SubPostChat.sub_post_id)
        .where(
            SubPostChatMessage.id == message_id,
            SubPostChat.sub_post_id == post_id,
        )
    ).one_or_none()
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub chat message not found.",
        )

    record_sensitive_admin_read(
        authenticated_admin_id=viewer_user.id,
        action_type="reveal_need_sub_chat_message_content",
        target_sub_post_id=post_id,
        target_sub_chat_message_id=message_id,
        reason=None,
        metadata=None,
    )
    message = db.execute(
        select(SubPostChatMessage.id, SubPostChatMessage.message_body)
        .join(SubPostChat, SubPostChat.id == SubPostChatMessage.chat_id)
        .join(SubPost, SubPost.id == SubPostChat.sub_post_id)
        .where(
            SubPostChatMessage.id == message_id,
            SubPostChat.sub_post_id == post_id,
        )
    ).one_or_none()
    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub chat message not found.",
        )
    return AdminChatMessageContentRead(id=message.id, message_body=message.message_body)


def get_existing_chat_moderation_action(
    db: Session,
    *,
    action_type: str,
    admin_user_id: uuid.UUID,
    chat_scope: str,
    message_id: uuid.UUID,
    idempotency_key: str,
) -> AdminAction | None:
    target_column = (
        AdminAction.target_message_id
        if chat_scope == CHAT_SCOPE_GAME
        else AdminAction.target_sub_chat_message_id
    )
    return db.scalar(
        select(AdminAction)
        .where(
            AdminAction.action_type == action_type,
            AdminAction.admin_user_id == admin_user_id,
            target_column == message_id,
            AdminAction.idempotency_key == idempotency_key,
        )
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
        .limit(1)
    )


def validate_existing_action(
    action: AdminAction,
    *,
    expected_reason: str | None,
) -> None:
    if action.reason != expected_reason:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="idempotency_key was already used for a different chat review action.",
        )


def get_chat_notices_for_action(
    db: Session,
    action_id: uuid.UUID,
) -> list[AdminTargetNotice]:
    return list(
        db.scalars(
            select(AdminTargetNotice)
            .where(AdminTargetNotice.admin_action_id == action_id)
            .order_by(AdminTargetNotice.created_at.asc(), AdminTargetNotice.id.asc())
        ).all()
    )


def validate_chat_replay_communication(
    db: Session,
    action: AdminAction,
) -> None:
    if action.action_type == "mark_chat_message_reviewed":
        return
    notices = get_chat_notices_for_action(db, action.id)
    suppression_reason = (action.metadata_ or {}).get("notice_suppression_reason")
    if suppression_reason == "recipient_unavailable":
        valid = action.target_user_id is None and not notices
    else:
        valid = suppression_reason is None and len(notices) == 1
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The prior chat moderation result is incomplete.",
        )


def get_game_message_context(
    db: Session,
    message_id: uuid.UUID,
    *,
    lock_message: bool,
) -> tuple[ChatMessage, GameChat, Game]:
    statement = (
        select(ChatMessage, GameChat, Game)
        .join(GameChat, GameChat.id == ChatMessage.chat_id)
        .join(Game, Game.id == GameChat.game_id)
        .where(ChatMessage.id == message_id)
    )
    if lock_message:
        statement = statement.with_for_update(of=ChatMessage)
    row = db.execute(statement).one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat message not found.",
        )
    message, chat, game = row
    return message, chat, game


def get_sub_message_context(
    db: Session,
    message_id: uuid.UUID,
    *,
    lock_message: bool,
) -> tuple[SubPostChatMessage, SubPostChat, SubPost]:
    statement = (
        select(SubPostChatMessage, SubPostChat, SubPost)
        .join(SubPostChat, SubPostChat.id == SubPostChatMessage.chat_id)
        .join(SubPost, SubPost.id == SubPostChat.sub_post_id)
        .where(SubPostChatMessage.id == message_id)
    )
    if lock_message:
        statement = statement.with_for_update(of=SubPostChatMessage)
    row = db.execute(statement).one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub chat message not found.",
        )
    message, chat, post = row
    return message, chat, post


def record_chat_moderation_action(
    db: Session,
    *,
    action_type: str,
    chat_scope: str,
    message: ChatMessage | SubPostChatMessage,
    chat: GameChat | SubPostChat,
    parent: Game | SubPost,
    admin_user: User,
    reason: str | None,
    idempotency_key: str,
    created_at: datetime,
    before: dict[str, object],
    after: dict[str, object],
) -> AdminAction:
    metadata = {
        "source": "chat_moderation",
        "before": before,
        "after": after,
    }
    if (
        action_type in {"remove_chat_message", "restore_chat_message"}
        and message.sender_user_id is None
    ):
        metadata["notice_suppression_reason"] = "recipient_unavailable"
    if chat_scope == CHAT_SCOPE_GAME:
        return record_admin_action(
            db,
            admin_user_id=admin_user.id,
            action_type=action_type,
            outcome="succeeded",
            target_user_id=message.sender_user_id,
            target_game_id=parent.id,
            target_message_id=message.id,
            reason=reason,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )
    return record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type=action_type,
        outcome="succeeded",
        target_user_id=message.sender_user_id,
        target_sub_post_id=parent.id,
        target_sub_chat_message_id=message.id,
        reason=reason,
        metadata=metadata,
        idempotency_key=idempotency_key,
    )


def apply_chat_action(
    *,
    action_type: str,
    message: ChatMessage | SubPostChatMessage,
    admin_user: User,
    reason: str | None,
    action_at: datetime,
) -> tuple[dict[str, object], dict[str, object]]:
    before = {
        "visibility_status": message.visibility_status,
        "review_status": message.review_status,
    }
    if action_type == "mark_chat_message_reviewed":
        if message.review_status != "needs_review":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only messages needing review can be marked reviewed.",
            )
        message.review_status = "reviewed"
        message.reviewed_at = action_at
        message.reviewed_by_user_id = admin_user.id
    elif action_type == "remove_chat_message":
        if message.visibility_status == "removed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This chat message is already removed.",
            )
        message.visibility_status = "removed"
        message.review_status = "reviewed"
        message.reviewed_at = action_at
        message.reviewed_by_user_id = admin_user.id
        message.removed_at = action_at
        message.removed_by_user_id = admin_user.id
        message.removed_source = "admin"
        message.removed_reason = reason
    elif action_type == "restore_chat_message":
        if message.visibility_status != "removed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only removed chat messages can be restored.",
            )
        if message.removed_source != "admin":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only messages removed by an admin can be restored.",
            )
        message.visibility_status = "visible"
        message.review_status = "reviewed"
        message.reviewed_at = action_at
        message.reviewed_by_user_id = admin_user.id
        message.restored_at = action_at
        message.restored_by_user_id = admin_user.id
        message.restored_reason = reason
    else:
        raise ValueError("Unsupported chat moderation action.")
    message.updated_at = action_at
    after = {
        "visibility_status": message.visibility_status,
        "review_status": message.review_status,
    }
    return before, after


def create_chat_enforcement_notice(
    db: Session,
    *,
    action_type: str,
    chat_scope: str,
    message: ChatMessage | SubPostChatMessage,
    parent: Game | SubPost,
    admin_user: User,
    audit_action: AdminAction,
) -> AdminTargetNotice | None:
    copy = CHAT_NOTICE_COPY.get((chat_scope, action_type))
    if copy is None or message.sender_user_id is None:
        return None
    notice_type, title, body = copy
    return create_admin_target_notice(
        db,
        notice_type=notice_type,
        title=title,
        body=body,
        recipient_user_id=message.sender_user_id,
        target_user_id=message.sender_user_id,
        target_game_id=parent.id if chat_scope == CHAT_SCOPE_GAME else None,
        target_sub_post_id=(parent.id if chat_scope == CHAT_SCOPE_NEED_A_SUB else None),
        admin_action=audit_action,
        created_by_user_id=admin_user.id,
    )


def build_chat_action_replay(
    db: Session,
    *,
    action: AdminAction,
    chat_scope: str,
    parent_id: uuid.UUID,
    message_id: uuid.UUID,
) -> AdminChatModerationActionResultRead:
    if chat_scope == CHAT_SCOPE_GAME:
        message, _chat, parent = get_game_message_context(
            db,
            message_id,
            lock_message=False,
        )
    else:
        message, _chat, parent = get_sub_message_context(
            db,
            message_id,
            lock_message=False,
        )
    validate_message_parent(
        parent,
        expected_parent_id=parent_id,
        chat_scope=chat_scope,
    )
    validate_chat_replay_communication(db, action)
    return AdminChatModerationActionResultRead(
        message_id=message.id,
        audit_action_id=action.id,
        idempotent_replay=True,
    )


def validate_message_parent(
    parent: Game | SubPost,
    *,
    expected_parent_id: uuid.UUID,
    chat_scope: str,
) -> None:
    if parent.id == expected_parent_id:
        return

    detail = (
        "Chat message not found for this game."
        if chat_scope == CHAT_SCOPE_GAME
        else "Need a Sub chat message not found for this post."
    )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def lock_chat_action_parent(
    db: Session,
    *,
    chat_scope: str,
    parent_id: uuid.UUID,
    action_type: str,
    expected_game_type: str | None,
) -> Game | SubPost:
    if chat_scope == CHAT_SCOPE_GAME:
        if expected_game_type not in VALID_GAME_CHAT_PARENT_TYPES:
            raise ValueError("expected_game_type is required for game chat actions.")
        parent = db.scalar(
            select(Game)
            .where(Game.id == parent_id)
            .execution_options(populate_existing=True)
            .with_for_update()
        )
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found.",
            )
        if parent.deleted_at is not None or parent.game_type != expected_game_type:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Game is no longer available for this chat action.",
            )
        if (
            action_type == "restore_chat_message"
            and parent.game_status in TERMINAL_GAME_CHAT_RESTORATION_STATUSES
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Chat messages cannot be restored for this game.",
            )
        return parent

    parent = db.scalar(
        select(SubPost)
        .where(SubPost.id == parent_id)
        .execution_options(populate_existing=True)
        .with_for_update()
    )
    if parent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub post not found.",
        )
    if (
        action_type == "restore_chat_message"
        and parent.post_status in TERMINAL_SUB_CHAT_RESTORATION_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chat messages cannot be restored for this Need a Sub post.",
        )
    return parent


def run_chat_moderation_action(
    db: Session,
    *,
    chat_scope: str,
    parent_id: uuid.UUID,
    message_id: uuid.UUID,
    admin_user: User,
    payload: AdminChatModerationActionCreate,
    action_type: str,
    require_reason: bool,
    expected_game_type: str | None = None,
) -> AdminChatModerationActionResultRead:
    require_active_admin_user(admin_user)
    normalized_scope = normalize_chat_scope(chat_scope)
    reason, idempotency_key = normalize_action_payload(
        payload,
        require_reason=require_reason,
    )
    existing_action = get_existing_chat_moderation_action(
        db,
        action_type=action_type,
        admin_user_id=admin_user.id,
        chat_scope=normalized_scope,
        message_id=message_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        validate_existing_action(existing_action, expected_reason=reason)
        return build_chat_action_replay(
            db,
            action=existing_action,
            chat_scope=normalized_scope,
            parent_id=parent_id,
            message_id=message_id,
        )

    lock_chat_action_parent(
        db,
        chat_scope=normalized_scope,
        parent_id=parent_id,
        action_type=action_type,
        expected_game_type=expected_game_type,
    )
    if normalized_scope == CHAT_SCOPE_GAME:
        message, chat, parent = get_game_message_context(
            db,
            message_id,
            lock_message=True,
        )
    else:
        message, chat, parent = get_sub_message_context(
            db,
            message_id,
            lock_message=True,
        )
    validate_message_parent(
        parent,
        expected_parent_id=parent_id,
        chat_scope=normalized_scope,
    )
    existing_action = get_existing_chat_moderation_action(
        db,
        action_type=action_type,
        admin_user_id=admin_user.id,
        chat_scope=normalized_scope,
        message_id=message_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        validate_existing_action(existing_action, expected_reason=reason)
        return build_chat_action_replay(
            db,
            action=existing_action,
            chat_scope=normalized_scope,
            parent_id=parent_id,
            message_id=message_id,
        )

    action_at = now_utc()
    before, after = apply_chat_action(
        action_type=action_type,
        message=message,
        admin_user=admin_user,
        reason=reason,
        action_at=action_at,
    )
    audit_action = record_chat_moderation_action(
        db,
        action_type=action_type,
        chat_scope=normalized_scope,
        message=message,
        chat=chat,
        parent=parent,
        admin_user=admin_user,
        reason=reason,
        idempotency_key=idempotency_key,
        created_at=action_at,
        before=before,
        after=after,
    )
    try:
        create_chat_enforcement_notice(
            db,
            action_type=action_type,
            chat_scope=normalized_scope,
            message=message,
            parent=parent,
            admin_user=admin_user,
            audit_action=audit_action,
        )
        db.add(message)
        db.flush()
        if normalized_scope == CHAT_SCOPE_GAME:
            refresh_game_chat_summary(db, chat)
            reconcile_game_chat_notifications_after_moderation(
                db,
                db_chat=chat,
                moderated_at=action_at,
            )
        else:
            refresh_sub_post_chat_summary(db, chat)
            reconcile_sub_chat_notifications_after_moderation(
                db,
                db_chat=chat,
                moderated_at=action_at,
            )
        db.flush()
        db.commit()
        db.refresh(message)
        db.refresh(audit_action)
    except IntegrityError as exc:
        db.rollback()
        existing_action = None
        expected_constraint = CHAT_IDEMPOTENCY_CONSTRAINTS[
            (normalized_scope, action_type)
        ]
        if integrity_error_matches_constraint(exc, expected_constraint):
            existing_action = get_existing_chat_moderation_action(
                db,
                action_type=action_type,
                admin_user_id=admin_user.id,
                chat_scope=normalized_scope,
                message_id=message_id,
                idempotency_key=idempotency_key,
            )
        if existing_action is not None:
            validate_existing_action(existing_action, expected_reason=reason)
            return build_chat_action_replay(
                db,
                action=existing_action,
                chat_scope=normalized_scope,
                parent_id=parent_id,
                message_id=message_id,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chat moderation action could not be saved.",
        ) from exc
    except Exception:
        db.rollback()
        raise

    return AdminChatModerationActionResultRead(
        message_id=message.id,
        audit_action_id=audit_action.id,
        idempotent_replay=False,
    )


def mark_game_chat_message_reviewed(
    db: Session,
    *,
    game_id: uuid.UUID,
    message_id: uuid.UUID,
    admin_user: User,
    payload: AdminChatModerationActionCreate,
    expected_game_type: str,
) -> AdminChatModerationActionResultRead:
    return run_chat_moderation_action(
        db,
        chat_scope=CHAT_SCOPE_GAME,
        parent_id=game_id,
        message_id=message_id,
        admin_user=admin_user,
        payload=payload,
        action_type="mark_chat_message_reviewed",
        require_reason=False,
        expected_game_type=expected_game_type,
    )


def remove_game_chat_message(
    db: Session,
    *,
    game_id: uuid.UUID,
    message_id: uuid.UUID,
    admin_user: User,
    payload: AdminChatModerationActionCreate,
    expected_game_type: str,
) -> AdminChatModerationActionResultRead:
    return run_chat_moderation_action(
        db,
        chat_scope=CHAT_SCOPE_GAME,
        parent_id=game_id,
        message_id=message_id,
        admin_user=admin_user,
        payload=payload,
        action_type="remove_chat_message",
        require_reason=True,
        expected_game_type=expected_game_type,
    )


def restore_game_chat_message(
    db: Session,
    *,
    game_id: uuid.UUID,
    message_id: uuid.UUID,
    admin_user: User,
    payload: AdminChatModerationActionCreate,
    expected_game_type: str,
) -> AdminChatModerationActionResultRead:
    return run_chat_moderation_action(
        db,
        chat_scope=CHAT_SCOPE_GAME,
        parent_id=game_id,
        message_id=message_id,
        admin_user=admin_user,
        payload=payload,
        action_type="restore_chat_message",
        require_reason=True,
        expected_game_type=expected_game_type,
    )


def mark_need_a_sub_chat_message_reviewed(
    db: Session,
    *,
    post_id: uuid.UUID,
    message_id: uuid.UUID,
    admin_user: User,
    payload: AdminChatModerationActionCreate,
) -> AdminChatModerationActionResultRead:
    return run_chat_moderation_action(
        db,
        chat_scope=CHAT_SCOPE_NEED_A_SUB,
        parent_id=post_id,
        message_id=message_id,
        admin_user=admin_user,
        payload=payload,
        action_type="mark_chat_message_reviewed",
        require_reason=False,
    )


def remove_need_a_sub_chat_message(
    db: Session,
    *,
    post_id: uuid.UUID,
    message_id: uuid.UUID,
    admin_user: User,
    payload: AdminChatModerationActionCreate,
) -> AdminChatModerationActionResultRead:
    return run_chat_moderation_action(
        db,
        chat_scope=CHAT_SCOPE_NEED_A_SUB,
        parent_id=post_id,
        message_id=message_id,
        admin_user=admin_user,
        payload=payload,
        action_type="remove_chat_message",
        require_reason=True,
    )


def restore_need_a_sub_chat_message(
    db: Session,
    *,
    post_id: uuid.UUID,
    message_id: uuid.UUID,
    admin_user: User,
    payload: AdminChatModerationActionCreate,
) -> AdminChatModerationActionResultRead:
    return run_chat_moderation_action(
        db,
        chat_scope=CHAT_SCOPE_NEED_A_SUB,
        parent_id=post_id,
        message_id=message_id,
        admin_user=admin_user,
        payload=payload,
        action_type="restore_chat_message",
        require_reason=True,
    )
