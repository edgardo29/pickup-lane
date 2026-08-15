from __future__ import annotations

import inspect
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

os.environ.setdefault("APP_ENV", "test")
if not os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (
        "postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/"
        "pickup_lane_test_db"
    )

from backend.models import (
    AdminContentModerationFinding,
    Notification,
    SubPost,
    SubPostChat,
    SubPostChatMessage,
    SubPostChatMessageDetection,
    SubPostChatRead,
    User,
)
from backend.schemas.sub_post_chat_message_schema import SubPostChatMessageCreate
from backend.services import chat_rate_limit_service, sub_post_chat_service

pytestmark = pytest.mark.suite_type("ordinary")

_BASE_TIME = datetime(2035, 4, 3, 12, 0, 0, tzinfo=timezone.utc)


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _user(index: int) -> User:
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-c3a-sub-user-{index}-{uuid.uuid4()}",
        role="player",
        email=f"ws02-c3a-sub-{index}-{uuid.uuid4()}@example.invalid",
        first_name="Sub",
        last_name=f"User{index}",
        account_status="active",
        hosting_status="eligible",
    )


def _sub_post(owner: User, index: int) -> SubPost:
    starts_at = _BASE_TIME + timedelta(days=index)
    return SubPost(
        id=uuid.uuid4(),
        owner_user_id=owner.id,
        post_status="active",
        public_visibility_status="visible",
        sport_type="soccer",
        format_label="5v5",
        environment_type="indoor",
        skill_level="any",
        game_player_group="coed",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=2),
        starts_on_local=starts_at.date(),
        timezone="UTC",
        location_name=f"Sub Field {index}",
        address_line_1="1 Sub Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        subs_needed=1,
        price_due_at_venue_cents=0,
        currency="USD",
        expires_at=starts_at - timedelta(hours=1),
    )


def _chat(post: SubPost) -> SubPostChat:
    return SubPostChat(id=uuid.uuid4(), sub_post_id=post.id, chat_status="active")


def _context(db):
    owner = _user(1)
    outsider = _user(2)
    post = _sub_post(owner, 1)
    other_post = _sub_post(owner, 2)
    chat = _chat(post)
    other_chat = _chat(other_post)
    db.add_all([owner, outsider])
    db.commit()
    db.add_all([post, other_post])
    db.commit()
    db.add_all([chat, other_chat])
    db.commit()
    return owner, outsider, post, chat, other_chat


def _message(
    *,
    chat_id: uuid.UUID,
    sender_user_id: uuid.UUID,
    index: int,
    seconds_ago: int = 10,
    visibility_status: str = "visible",
) -> SubPostChatMessage:
    created_at = datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)
    removed_at = created_at if visibility_status == "removed" else None
    removed_source = "admin" if visibility_status == "removed" else None
    return SubPostChatMessage(
        id=uuid.UUID(int=index + 1001),
        chat_id=chat_id,
        sender_user_id=sender_user_id,
        sender_display_name_snapshot="Sub User",
        sender_initials_snapshot="SU",
        message_type="text",
        message_body=f"sub rate message {index}",
        visibility_status=visibility_status,
        review_status="clear",
        removed_at=removed_at,
        removed_source=removed_source,
        created_at=created_at,
        updated_at=created_at,
    )


def _send(
    db,
    *,
    post_id: uuid.UUID,
    chat_id: uuid.UUID,
    sender: User,
    body: str = "new sub message",
) -> dict:
    return sub_post_chat_service.create_sub_post_chat_message_workflow(
        db,
        post_id,
        SubPostChatMessageCreate(chat_id=chat_id, message_body=body),
        sender,
    )


def _count(db, model, *where) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(*where)) or 0)


def _side_effect_snapshot(db, chat: SubPostChat) -> dict[str, object]:
    db.refresh(chat)
    return {
        "messages": _count(db, SubPostChatMessage, SubPostChatMessage.chat_id == chat.id),
        "notifications": _count(db, Notification, Notification.related_sub_post_chat_id == chat.id),
        "reads": _count(db, SubPostChatRead, SubPostChatRead.chat_id == chat.id),
        "detections": _count(db, SubPostChatMessageDetection),
        "findings": _count(db, AdminContentModerationFinding),
        "message_count": chat.message_count,
        "removed_count": chat.removed_count,
        "latest_message_id": chat.latest_message_id,
        "latest_message_at": chat.latest_message_at,
    }


@pytest.mark.requirement("WS02-04C3A-R1")
@pytest.mark.requirement("WS02-04C3A-R2")
def test_need_a_sub_send_uses_shared_need_a_sub_limiter_and_allows_until_fifth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[dict[str, object]] = []
    original = sub_post_chat_service.enforce_visible_text_chat_rate_limit

    def observe(*args, **kwargs):
        seen.append(dict(kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(sub_post_chat_service, "enforce_visible_text_chat_rate_limit", observe)

    with _session() as db:
        owner, _outsider, post, chat, _other_chat = _context(db)
        for index in range(4):
            db.add(_message(chat_id=chat.id, sender_user_id=owner.id, index=index))
        db.commit()

        created = _send(
            db,
            post_id=post.id,
            chat_id=chat.id,
            sender=owner,
            body="permitted fifth sub message",
        )

        assert created["chat_id"] == chat.id
        assert created["sender_user_id"] == owner.id
        assert _count(
            db,
            SubPostChatMessage,
            SubPostChatMessage.chat_id == chat.id,
            SubPostChatMessage.sender_user_id == owner.id,
            SubPostChatMessage.visibility_status == "visible",
        ) == 5
        assert seen[-1]["limiter_category"] == "need_a_sub_chat"
        assert seen[-1]["message_model"] is SubPostChatMessage
        assert seen[-1]["chat_id"] == chat.id
        assert seen[-1]["sender_user_id"] == owner.id


@pytest.mark.requirement("WS02-04C3A-R1")
@pytest.mark.requirement("WS02-04C3A-R2")
@pytest.mark.requirement("WS02-04C3A-R6")
def test_need_a_sub_sixth_message_rejects_without_send_side_effects() -> None:
    with _session() as db:
        owner, outsider, post, chat, other_chat = _context(db)
        for index in range(5):
            db.add(_message(chat_id=chat.id, sender_user_id=owner.id, index=index))
        for index in range(5, 10):
            db.add(_message(chat_id=chat.id, sender_user_id=outsider.id, index=index))
            db.add(_message(chat_id=other_chat.id, sender_user_id=owner.id, index=index + 10))
        db.commit()
        sub_post_chat_service.refresh_sub_post_chat_summary(db, chat)
        db.commit()
        before = _side_effect_snapshot(db, chat)

        with pytest.raises(HTTPException) as exc_info:
            _send(
                db,
                post_id=post.id,
                chat_id=chat.id,
                sender=owner,
                body="blocked sixth sub message",
            )

        assert exc_info.value.status_code == 429
        assert exc_info.value.headers["Retry-After"].isdigit()
        db.rollback()
        assert _side_effect_snapshot(db, chat) == before


@pytest.mark.requirement("WS02-04C3A-R5")
def test_need_a_sub_auth_ownership_and_payload_checks_precede_limiter_disclosure() -> None:
    with _session() as db:
        owner, outsider, post, chat, other_chat = _context(db)
        for index in range(5):
            db.add(_message(chat_id=chat.id, sender_user_id=outsider.id, index=index))
        db.commit()

        with pytest.raises(HTTPException) as outsider_exc:
            _send(
                db,
                post_id=post.id,
                chat_id=chat.id,
                sender=outsider,
                body="outsider should not learn count",
            )
        assert outsider_exc.value.status_code == 403
        assert "rate" not in str(outsider_exc.value.detail).lower()

        with pytest.raises(HTTPException) as mismatch_exc:
            _send(
                db,
                post_id=post.id,
                chat_id=other_chat.id,
                sender=owner,
                body="wrong chat should not learn count",
            )
        assert mismatch_exc.value.status_code == 400
        assert "match" in str(mismatch_exc.value.detail).lower()
        assert "rate" not in str(mismatch_exc.value.detail).lower()


@pytest.mark.requirement("WS02-04C3A-R6")
def test_need_a_sub_limiter_store_failure_precedes_send_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_lock(*args, **kwargs) -> None:
        del args, kwargs
        raise SQLAlchemyError("synthetic need-a-sub limiter store failure")

    monkeypatch.setattr(chat_rate_limit_service, "_acquire_chat_rate_limit_lock", fail_lock)

    with _session() as db:
        owner, _outsider, post, chat, _other_chat = _context(db)
        before = _side_effect_snapshot(db, chat)

        with pytest.raises(SQLAlchemyError):
            _send(
                db,
                post_id=post.id,
                chat_id=chat.id,
                sender=owner,
                body="store failure sub message",
            )

        db.rollback()
        assert _side_effect_snapshot(db, chat) == before


@pytest.mark.requirement("WS02-04C3A-R8")
def test_need_a_sub_visibility_restoration_and_text_only_schema_boundaries() -> None:
    with _session() as db:
        owner, _outsider, post, chat, _other_chat = _context(db)
        removed = _message(
            chat_id=chat.id,
            sender_user_id=owner.id,
            index=1,
            visibility_status="removed",
        )
        db.add(removed)
        db.commit()

        _send(
            db,
            post_id=post.id,
            chat_id=chat.id,
            sender=owner,
            body="removed row does not count",
        )
        assert _count(db, SubPostChatMessage, SubPostChatMessage.chat_id == chat.id) == 2

        original_created_at = removed.created_at
        removed.visibility_status = "visible"
        removed.removed_at = None
        removed.removed_source = None
        removed.restored_at = datetime.now(timezone.utc)
        removed.restored_by_user_id = owner.id
        db.add(removed)
        db.commit()

        for index in range(4, 8):
            db.add(_message(chat_id=chat.id, sender_user_id=owner.id, index=index))
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            _send(
                db,
                post_id=post.id,
                chat_id=chat.id,
                sender=owner,
                body="restored sub row counts again",
            )

        assert exc_info.value.status_code == 429
        restored = db.get(SubPostChatMessage, removed.id)
        assert restored is not None
        assert restored.created_at == original_created_at
        assert _count(db, SubPostChatMessage, SubPostChatMessage.chat_id == chat.id) == 6

    message_type_constraints = [
        constraint.sqltext.text
        for constraint in SubPostChatMessage.__table__.constraints
        if constraint.name == "ck_sub_post_chat_messages_message_type"
    ]
    assert message_type_constraints == ["message_type IN ('text')"]


@pytest.mark.requirement("WS02-04C3A-R1")
@pytest.mark.requirement("WS02-04C3A-R8")
def test_need_a_sub_rate_limiter_remains_before_b1_total_history_cap() -> None:
    source = inspect.getsource(sub_post_chat_service.create_sub_post_chat_message_workflow)

    assert source.index("validate_sender_rate_limit") < source.index("validate_total_message_limit")
    assert sub_post_chat_service.MAX_SUB_CHAT_MESSAGES_PER_MINUTE == 5
    assert sub_post_chat_service.MAX_SUB_CHAT_MESSAGES_TOTAL == 200
