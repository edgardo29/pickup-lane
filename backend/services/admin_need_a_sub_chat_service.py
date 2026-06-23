"""Admin inspection and moderation for scoped Need a Sub chat."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import AdminAction, SubPost, SubPostChat, SubPostChatMessage, User
from backend.schemas.admin_need_a_sub_schema import (
    AdminNeedASubChatMessageRead,
    AdminNeedASubChatModerationCreate,
    AdminNeedASubChatModerationResultRead,
    AdminNeedASubChatRead,
)
from backend.services.admin_action_service import (
    normalize_idempotency_key,
    normalize_optional_text,
    record_admin_action,
)
from backend.services.admin_need_a_sub_service import (
    get_admin_need_a_sub_post_or_404,
)
from backend.services.admin_permission_service import (
    PERMISSION_CONTENT_MODERATE,
    require_user_admin_permission,
)
from backend.services.sub_post_chat_service import (
    reconcile_sub_chat_notifications_after_moderation,
    sub_chat_closes_at,
)

CHAT_MODERATION_ACTIONS = {
    "hide": ("hide_chat_message", "hidden_by_admin"),
    "remove": ("remove_chat_message", "removed_by_admin"),
}


def serialize_chat_message(
    message: SubPostChatMessage,
) -> AdminNeedASubChatMessageRead:
    return AdminNeedASubChatMessageRead(
        id=message.id,
        sender_user_id=message.sender_user_id,
        sender_display_name_snapshot=message.sender_display_name_snapshot,
        sender_initials_snapshot=message.sender_initials_snapshot,
        message_body=message.message_body,
        moderation_status=message.moderation_status,
        created_at=message.created_at,
        updated_at=message.updated_at,
        edited_at=message.edited_at,
        deleted_at=message.deleted_at,
        deleted_by_user_id=message.deleted_by_user_id,
    )


def get_effective_chat_lifecycle(
    post: SubPost,
    chat: SubPostChat,
) -> tuple[str, datetime | None]:
    if chat.chat_status != "active":
        return chat.chat_status, chat.closed_at
    if post.post_status == "canceled":
        return "closed", post.canceled_at
    if post.post_status == "removed":
        return "closed", post.removed_at

    closes_at = sub_chat_closes_at(post)
    if datetime.now(timezone.utc) >= closes_at:
        return "closed", closes_at
    return chat.chat_status, chat.closed_at


def get_admin_need_a_sub_chat(
    db: Session,
    *,
    post_id: uuid.UUID,
    viewer_user: User,
    offset: int = 0,
    limit: int = 50,
) -> AdminNeedASubChatRead:
    require_user_admin_permission(viewer_user, PERMISSION_CONTENT_MODERATE)
    post = get_admin_need_a_sub_post_or_404(db, post_id)
    page_offset = max(0, offset)
    page_limit = max(1, min(limit, 100))
    chat = db.scalar(select(SubPostChat).where(SubPostChat.sub_post_id == post.id))
    if chat is None:
        return AdminNeedASubChatRead(
            post_id=post.id,
            chat_status="not_created",
            offset=page_offset,
            limit=page_limit,
        )

    total_message_count = (
        db.scalar(
            select(func.count())
            .select_from(SubPostChatMessage)
            .where(SubPostChatMessage.chat_id == chat.id)
        )
        or 0
    )
    messages = list(
        db.scalars(
            select(SubPostChatMessage)
            .where(SubPostChatMessage.chat_id == chat.id)
            .order_by(
                SubPostChatMessage.created_at.desc(),
                SubPostChatMessage.id.desc(),
            )
            .offset(page_offset)
            .limit(page_limit)
        ).all()
    )
    effective_status, effective_closed_at = get_effective_chat_lifecycle(post, chat)

    return AdminNeedASubChatRead(
        post_id=post.id,
        chat_id=chat.id,
        chat_status=effective_status,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        closed_at=effective_closed_at,
        total_message_count=total_message_count,
        offset=page_offset,
        limit=page_limit,
        messages=[serialize_chat_message(message) for message in reversed(messages)],
    )


def normalize_chat_moderation_request(
    payload: AdminNeedASubChatModerationCreate,
) -> tuple[str, str]:
    reason = normalize_optional_text(payload.reason, "reason")
    if reason is None:
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


def get_existing_chat_moderation_action(
    db: Session,
    *,
    action_type: str,
    moderator_user_id: uuid.UUID,
    message_id: uuid.UUID,
    idempotency_key: str,
) -> AdminAction | None:
    return db.scalar(
        select(AdminAction)
        .where(
            AdminAction.action_type == action_type,
            AdminAction.admin_user_id == moderator_user_id,
            AdminAction.target_sub_chat_message_id == message_id,
            AdminAction.idempotency_key == idempotency_key,
        )
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
        .limit(1)
    )


def validate_existing_chat_moderation_action(
    action: AdminAction,
    *,
    expected_reason: str,
) -> None:
    if action.reason != expected_reason:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "idempotency_key was already used for a different "
                "Need a Sub chat moderation request."
            ),
        )


def get_chat_and_message_or_404(
    db: Session,
    *,
    post: SubPost,
    message_id: uuid.UUID,
    lock_message: bool = False,
) -> tuple[SubPostChat, SubPostChatMessage]:
    chat = db.scalar(select(SubPostChat).where(SubPostChat.sub_post_id == post.id))
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub chat not found.",
        )

    statement = select(SubPostChatMessage).where(
        SubPostChatMessage.id == message_id,
        SubPostChatMessage.chat_id == chat.id,
    )
    if lock_message:
        statement = statement.with_for_update()
    message = db.scalar(statement)
    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub chat message not found.",
        )
    return chat, message


def build_chat_moderation_result(
    *,
    post: SubPost,
    chat: SubPostChat,
    message: SubPostChatMessage,
    audit_action: AdminAction,
    idempotent_replay: bool,
) -> AdminNeedASubChatModerationResultRead:
    return AdminNeedASubChatModerationResultRead(
        post_id=post.id,
        chat_id=chat.id,
        message=serialize_chat_message(message),
        audit_action_id=audit_action.id,
        idempotent_replay=idempotent_replay,
    )


def moderate_admin_need_a_sub_chat_message(
    db: Session,
    *,
    post_id: uuid.UUID,
    message_id: uuid.UUID,
    moderator_user: User,
    payload: AdminNeedASubChatModerationCreate,
    moderation_action: str,
) -> AdminNeedASubChatModerationResultRead:
    require_user_admin_permission(moderator_user, PERMISSION_CONTENT_MODERATE)
    action_config = CHAT_MODERATION_ACTIONS.get(moderation_action)
    if action_config is None:
        raise ValueError("Unsupported Need a Sub chat moderation action.")

    reason, idempotency_key = normalize_chat_moderation_request(payload)
    action_type, new_status = action_config
    existing_action = get_existing_chat_moderation_action(
        db,
        action_type=action_type,
        moderator_user_id=moderator_user.id,
        message_id=message_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        validate_existing_chat_moderation_action(
            existing_action,
            expected_reason=reason,
        )
        post = get_admin_need_a_sub_post_or_404(db, post_id)
        chat, message = get_chat_and_message_or_404(
            db,
            post=post,
            message_id=message_id,
        )
        return build_chat_moderation_result(
            post=post,
            chat=chat,
            message=message,
            audit_action=existing_action,
            idempotent_replay=True,
        )

    post = db.scalar(
        select(SubPost).where(SubPost.id == post_id).with_for_update()
    )
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub post not found.",
        )
    chat, message = get_chat_and_message_or_404(
        db,
        post=post,
        message_id=message_id,
        lock_message=True,
    )

    existing_action = get_existing_chat_moderation_action(
        db,
        action_type=action_type,
        moderator_user_id=moderator_user.id,
        message_id=message_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        validate_existing_chat_moderation_action(
            existing_action,
            expected_reason=reason,
        )
        return build_chat_moderation_result(
            post=post,
            chat=chat,
            message=message,
            audit_action=existing_action,
            idempotent_replay=True,
        )

    if moderation_action == "hide" and message.moderation_status not in {
        "visible",
        "flagged",
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only visible or flagged messages can be hidden.",
        )
    if moderation_action == "remove" and message.moderation_status in {
        "removed_by_admin",
        "deleted_by_sender",
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This message is already removed or deleted.",
        )

    old_status = message.moderation_status
    moderated_at = datetime.now(timezone.utc)
    message.moderation_status = new_status
    message.deleted_at = moderated_at
    message.deleted_by_user_id = moderator_user.id
    message.updated_at = moderated_at
    audit_action = record_admin_action(
        db,
        admin_user_id=moderator_user.id,
        action_type=action_type,
        target_user_id=message.sender_user_id,
        target_sub_post_id=post.id,
        target_sub_chat_message_id=message.id,
        reason=reason,
        metadata={
            "source": "admin_need_a_sub_chat",
            "before": {
                "moderation_status": old_status,
                "content_length": len(message.message_body),
            },
            "after": {
                "moderation_status": new_status,
                "content_length": len(message.message_body),
            },
        },
        idempotency_key=idempotency_key,
        created_at=moderated_at,
    )
    try:
        db.add(message)
        db.flush()
        reconcile_sub_chat_notifications_after_moderation(
            db,
            db_chat=chat,
            moderated_at=moderated_at,
        )
        db.commit()
        db.refresh(message)
        db.refresh(audit_action)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        existing_action = get_existing_chat_moderation_action(
            db,
            action_type=action_type,
            moderator_user_id=moderator_user.id,
            message_id=message_id,
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            validate_existing_chat_moderation_action(
                existing_action,
                expected_reason=reason,
            )
            post = get_admin_need_a_sub_post_or_404(db, post_id)
            chat, message = get_chat_and_message_or_404(
                db,
                post=post,
                message_id=message_id,
            )
            return build_chat_moderation_result(
                post=post,
                chat=chat,
                message=message,
                audit_action=existing_action,
                idempotent_replay=True,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Need a Sub chat message could not be moderated.",
        ) from exc

    return build_chat_moderation_result(
        post=post,
        chat=chat,
        message=message,
        audit_action=audit_action,
        idempotent_replay=False,
    )
