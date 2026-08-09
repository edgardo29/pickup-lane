from __future__ import annotations

import hashlib
import logging
import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.observability.events import EventEnvelope
from backend.observability.redaction import redact_value

logger = logging.getLogger(__name__)

CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES = 5
CHAT_RATE_LIMIT_WINDOW_SECONDS = 60
CHAT_RATE_LIMIT_WINDOW = timedelta(seconds=CHAT_RATE_LIMIT_WINDOW_SECONDS)
CHAT_RATE_LIMIT_DETAIL = (
    "You can send up to 5 chat messages per minute. Try again shortly."
)
CHAT_RATE_LIMIT_ERROR_CODE = "API.RATE_LIMITED"
CHAT_RATE_LIMIT_ALGORITHM = "rolling_window"


def enforce_visible_text_chat_rate_limit(
    db: Session,
    *,
    limiter_category: str,
    message_model: Any,
    chat_id: uuid.UUID,
    sender_user_id: uuid.UUID,
    current_time: datetime,
    visible_status: str = "visible",
) -> None:
    """Serialize and enforce the approved visible-text chat rate policy."""

    now = ensure_aware_utc(current_time)
    try:
        _acquire_chat_rate_limit_lock(
            db,
            limiter_category=limiter_category,
            chat_id=chat_id,
            sender_user_id=sender_user_id,
        )
        recent_message_times = _recent_qualifying_message_times(
            db,
            message_model=message_model,
            chat_id=chat_id,
            sender_user_id=sender_user_id,
            current_time=now,
            visible_status=visible_status,
        )
    except SQLAlchemyError:
        _log_rate_limit_event(
            limiter_category=limiter_category,
            result="store_error",
            occurred_at=now,
            stable_error_code=None,
        )
        raise

    if len(recent_message_times) >= CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES:
        retry_after_seconds = retry_after_for_window(
            oldest_qualifying_message_at=recent_message_times[0],
            current_time=now,
        )
        _log_rate_limit_event(
            limiter_category=limiter_category,
            result="rejected",
            occurred_at=now,
            stable_error_code=CHAT_RATE_LIMIT_ERROR_CODE,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=CHAT_RATE_LIMIT_DETAIL,
            headers={"Retry-After": str(retry_after_seconds)},
        )

    _log_rate_limit_event(
        limiter_category=limiter_category,
        result="allowed",
        occurred_at=now,
        stable_error_code=None,
    )


def chat_rate_limit_lock_key(
    *,
    limiter_category: str,
    chat_id: uuid.UUID,
    sender_user_id: uuid.UUID,
) -> int:
    key_material = f"pickup-lane:{limiter_category}:{chat_id}:{sender_user_id}"
    digest = hashlib.blake2b(
        key_material.encode("utf-8"),
        digest_size=8,
        person=b"pl-chat-rate",
    ).digest()
    return int.from_bytes(digest, byteorder="big", signed=True)


def retry_after_for_window(
    *,
    oldest_qualifying_message_at: datetime,
    current_time: datetime,
) -> int:
    oldest_qualified_until = (
        ensure_aware_utc(oldest_qualifying_message_at) + CHAT_RATE_LIMIT_WINDOW
    )
    remaining_seconds = (
        oldest_qualified_until - ensure_aware_utc(current_time)
    ).total_seconds()
    return max(1, math.floor(remaining_seconds) + 1)


def ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _acquire_chat_rate_limit_lock(
    db: Session,
    *,
    limiter_category: str,
    chat_id: uuid.UUID,
    sender_user_id: uuid.UUID,
) -> None:
    db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {
            "lock_key": chat_rate_limit_lock_key(
                limiter_category=limiter_category,
                chat_id=chat_id,
                sender_user_id=sender_user_id,
            )
        },
    )


def _recent_qualifying_message_times(
    db: Session,
    *,
    message_model: Any,
    chat_id: uuid.UUID,
    sender_user_id: uuid.UUID,
    current_time: datetime,
    visible_status: str,
) -> list[datetime]:
    window_start = current_time - CHAT_RATE_LIMIT_WINDOW
    return list(
        db.scalars(
            select(message_model.created_at)
            .where(
                message_model.chat_id == chat_id,
                message_model.sender_user_id == sender_user_id,
                message_model.message_type == "text",
                message_model.visibility_status == visible_status,
                message_model.created_at >= window_start,
            )
            .order_by(message_model.created_at.asc(), message_model.id.asc())
            .limit(CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES)
        ).all()
    )


def _log_rate_limit_event(
    *,
    limiter_category: str,
    result: str,
    occurred_at: datetime,
    stable_error_code: str | None,
) -> None:
    envelope = EventEnvelope(
        event_name="chat.rate_limit",
        occurred_at=occurred_at,
        actor_kind="authenticated_user",
        operation="chat_rate_limit.check",
        resource_kind=limiter_category,
        result=result,
        stable_error_code=stable_error_code,
        labels={"outcome": result, "route_template": _route_template(limiter_category)},
    )
    logger.info(
        "Chat rate-limit check completed.",
        extra={"pickup_lane_event": redact_value(envelope.to_dict())},
    )


def _route_template(limiter_category: str) -> str:
    if limiter_category == "game_chat":
        return "/chat-messages"
    return "/need-a-sub/{sub_post_id}/chat/messages"
