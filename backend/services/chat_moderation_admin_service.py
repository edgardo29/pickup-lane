"""Admin chat moderation workflows scoped by owning feature routes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
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
    AdminChatModerationActionCreate,
    AdminChatModerationActionResultRead,
    AdminChatMessageListRead,
    AdminChatMessageRead,
    AdminChatSummaryRead,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_record_rules import (
    normalize_idempotency_key,
    normalize_optional_text,
)
from backend.services.auth_service import require_active_admin_user
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
VALID_REVIEW_VIEWS = {"needs_review", "removed", "all"}
DEFAULT_REVIEW_PAGE_SIZE = 20
MAX_REVIEW_PAGE_SIZE = 20


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


def build_initials(display_name: str) -> str:
    parts = [part for part in display_name.replace("@", " ").split() if part]
    initials = "".join(part[:1].upper() for part in parts[:2])
    return initials or "PL"


def serialize_detections(
    detections: list[GameChatMessageDetection | SubPostChatMessageDetection],
) -> list[AdminChatDetectionRead]:
    return [
        AdminChatDetectionRead(
            id=detection.id,
            category=detection.category,
            severity=detection.severity,
            rule_key=detection.rule_key,
            matched_preview=detection.matched_preview,
            created_at=detection.created_at,
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
    chat: GameChat,
    game: Game,
) -> AdminChatMessageRead:
    sender = db.get(User, message.sender_user_id) if message.sender_user_id else None
    sender_display_name = (
        get_user_display_name(sender, fallback="Deleted User")
        if sender is not None
        else "Deleted User"
    )
    return AdminChatMessageRead(
        id=message.id,
        chat_id=chat.id,
        sender_user_id=message.sender_user_id,
        sender_display_name=sender_display_name,
        sender_initials=build_initials(sender_display_name),
        message_type=message.message_type,
        message_body=message.message_body,
        visibility_status=message.visibility_status,
        review_status=message.review_status,
        created_at=message.created_at,
        updated_at=message.updated_at,
        reviewed_at=message.reviewed_at,
        reviewed_by_user_id=message.reviewed_by_user_id,
        removed_at=message.removed_at,
        removed_by_user_id=message.removed_by_user_id,
        removed_source=message.removed_source,
        restored_at=message.restored_at,
        restored_by_user_id=message.restored_by_user_id,
        detections=serialize_detections(
            get_game_message_detections(db, message.id)
        ),
    )


def serialize_need_a_sub_chat_message(
    db: Session,
    message: SubPostChatMessage,
    chat: SubPostChat,
    post: SubPost,
) -> AdminChatMessageRead:
    return AdminChatMessageRead(
        id=message.id,
        chat_id=chat.id,
        sender_user_id=message.sender_user_id,
        sender_display_name=message.sender_display_name_snapshot,
        sender_initials=message.sender_initials_snapshot,
        message_type=message.message_type,
        message_body=message.message_body,
        visibility_status=message.visibility_status,
        review_status=message.review_status,
        created_at=message.created_at,
        updated_at=message.updated_at,
        reviewed_at=message.reviewed_at,
        reviewed_by_user_id=message.reviewed_by_user_id,
        removed_at=message.removed_at,
        removed_by_user_id=message.removed_by_user_id,
        removed_source=message.removed_source,
        restored_at=message.restored_at,
        restored_by_user_id=message.restored_by_user_id,
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
        .join(GameChat, GameChat.id == ChatMessage.chat_id)
        .join(Game, Game.id == GameChat.game_id)
        .where(*game_message_filters(view, parent_id))
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [
        serialize_game_chat_message(db, message, chat, game)
        for message, chat, game in rows
    ]


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
        .join(SubPostChat, SubPostChat.id == SubPostChatMessage.chat_id)
        .join(SubPost, SubPost.id == SubPostChat.sub_post_id)
        .where(*sub_message_filters(view, parent_id))
        .order_by(SubPostChatMessage.created_at.desc(), SubPostChatMessage.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [
        serialize_need_a_sub_chat_message(db, message, chat, post)
        for message, chat, post in rows
    ]


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
) -> AdminChatMessageListRead:
    require_active_admin_user(viewer_user)
    normalized_view = normalize_review_view(view)
    page_offset = max(0, offset)
    page_limit = max(1, min(limit, MAX_REVIEW_PAGE_SIZE))
    total_count = count_game_chat_messages(
        db,
        view=normalized_view,
        parent_id=game_id,
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found.")
    chat = db.scalar(select(GameChat).where(GameChat.game_id == game.id))
    if chat is None:
        return AdminChatSummaryRead(
            chat_status="not_created",
        )
    return AdminChatSummaryRead(
        chat_id=chat.id,
        chat_status=chat.chat_status,
        message_count=chat.message_count,
        needs_review_count=chat.needs_review_count,
        removed_count=chat.removed_count,
        latest_message_id=chat.latest_message_id,
        latest_message_preview=chat.latest_message_preview,
        latest_message_at=chat.latest_message_at,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        closed_at=chat.closed_at,
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
        chat_id=chat.id,
        chat_status=chat.chat_status,
        message_count=chat.message_count,
        needs_review_count=chat.needs_review_count,
        removed_count=chat.removed_count,
        latest_message_id=chat.latest_message_id,
        latest_message_preview=chat.latest_message_preview,
        latest_message_at=chat.latest_message_at,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        closed_at=chat.closed_at,
    )


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


def serialize_action_message(
    db: Session,
    *,
    chat_scope: str,
    message: ChatMessage | SubPostChatMessage,
    chat: GameChat | SubPostChat,
    parent: Game | SubPost,
) -> AdminChatMessageRead:
    if chat_scope == CHAT_SCOPE_GAME:
        return serialize_game_chat_message(db, message, chat, parent)
    return serialize_need_a_sub_chat_message(db, message, chat, parent)


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
    if chat_scope == CHAT_SCOPE_GAME:
        return record_admin_action(
            db,
            admin_user_id=admin_user.id,
            action_type=action_type,
            target_user_id=message.sender_user_id,
            target_game_id=parent.id,
            target_message_id=message.id,
            reason=reason,
            metadata={
                "source": "chat_moderation",
                "before": before,
                "after": after,
            },
            idempotency_key=idempotency_key,
            created_at=created_at,
        )
    return record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type=action_type,
        target_user_id=message.sender_user_id,
        target_sub_post_id=parent.id,
        target_sub_chat_message_id=message.id,
        reason=reason,
        metadata={
            "source": "chat_moderation",
            "before": before,
            "after": after,
        },
        idempotency_key=idempotency_key,
        created_at=created_at,
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
        if normalized_scope == CHAT_SCOPE_GAME:
            message, chat, parent = get_game_message_context(
                db,
                message_id,
                lock_message=False,
            )
        else:
            message, chat, parent = get_sub_message_context(
                db,
                message_id,
                lock_message=False,
            )
        validate_message_parent(
            parent,
            expected_parent_id=parent_id,
            chat_scope=normalized_scope,
        )
        return AdminChatModerationActionResultRead(
            message=serialize_action_message(
                db,
                chat_scope=normalized_scope,
                message=message,
                chat=chat,
                parent=parent,
            ),
            audit_action_id=existing_action.id,
            idempotent_replay=True,
        )

    action_at = now_utc()
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
            if normalized_scope == CHAT_SCOPE_GAME:
                message, chat, parent = get_game_message_context(
                    db,
                    message_id,
                    lock_message=False,
                )
            else:
                message, chat, parent = get_sub_message_context(
                    db,
                    message_id,
                    lock_message=False,
                )
            validate_message_parent(
                parent,
                expected_parent_id=parent_id,
                chat_scope=normalized_scope,
            )
            return AdminChatModerationActionResultRead(
                message=serialize_action_message(
                    db,
                    chat_scope=normalized_scope,
                    message=message,
                    chat=chat,
                    parent=parent,
                ),
                audit_action_id=existing_action.id,
                idempotent_replay=True,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chat moderation action could not be saved.",
        ) from exc

    return AdminChatModerationActionResultRead(
        message=serialize_action_message(
            db,
            chat_scope=normalized_scope,
            message=message,
            chat=chat,
            parent=parent,
        ),
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
    )


def remove_game_chat_message(
    db: Session,
    *,
    game_id: uuid.UUID,
    message_id: uuid.UUID,
    admin_user: User,
    payload: AdminChatModerationActionCreate,
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
    )


def restore_game_chat_message(
    db: Session,
    *,
    game_id: uuid.UUID,
    message_id: uuid.UUID,
    admin_user: User,
    payload: AdminChatModerationActionCreate,
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
