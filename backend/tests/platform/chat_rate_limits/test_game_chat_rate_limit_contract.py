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
    pytest.skip(
        "DATABASE_URL is required for backend integration tests.",
        allow_module_level=True,
    )

from backend.models import (
    AdminContentModerationFinding,
    ChatMessage,
    Game,
    GameChat,
    GameChatMessageDetection,
    GameChatRead,
    GameParticipant,
    Notification,
    User,
    Venue,
)
from backend.schemas.chat_message_schema import ChatMessageCreate
from backend.services import chat_rate_limit_service, game_chat_service

pytestmark = pytest.mark.suite_type("ordinary")

_BASE_TIME = datetime(2035, 4, 2, 12, 0, 0, tzinfo=timezone.utc)


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _user(index: int, *, role: str = "player") -> User:
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-c3a-game-user-{index}-{uuid.uuid4()}",
        role=role,
        email=f"ws02-c3a-game-{index}-{uuid.uuid4()}@example.invalid",
        first_name="Game",
        last_name=f"User{index}",
        account_status="active",
        hosting_status="eligible",
    )


def _venue() -> Venue:
    return Venue(
        id=uuid.uuid4(),
        name="Game Rate Gym",
        address_line_1="1 Game Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        venue_status="approved",
        is_active=True,
    )


def _game(host: User, venue: Venue, index: int) -> Game:
    starts_at = _BASE_TIME + timedelta(days=index)
    return Game(
        id=uuid.uuid4(),
        game_type="community",
        payment_collection_type="none",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title=f"C3A Game {index}",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot=venue.address_line_1,
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        host_user_id=host.id,
        created_by_user_id=host.id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=2),
        starts_on_local=starts_at.date(),
        timezone="UTC",
        sport_type="soccer",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="indoor",
        total_spots=10,
        price_per_player_cents=0,
        currency="USD",
        policy_mode="custom_hosted",
        published_at=_BASE_TIME - timedelta(days=1),
    )


def _participant(game: Game, user: User, index: int) -> GameParticipant:
    return GameParticipant(
        id=uuid.uuid4(),
        game_id=game.id,
        participant_type="registered_user",
        user_id=user.id,
        display_name_snapshot=f"{user.first_name} {user.last_name}",
        participant_status="confirmed",
        attendance_status="unknown",
        cancellation_type="none",
        price_cents=0,
        currency="USD",
        roster_order=index,
        confirmed_at=_BASE_TIME,
    )


def _chat(game: Game) -> GameChat:
    return GameChat(id=uuid.uuid4(), game_id=game.id, chat_status="active")


def _context(db, *, with_recipient: bool = True):
    sender = _user(1)
    recipient = _user(2)
    outsider = _user(3)
    venue = _venue()
    game = _game(sender, venue, 1)
    other_game = _game(sender, venue, 2)
    chat = _chat(game)
    other_chat = _chat(other_game)
    db.add_all([sender, recipient, outsider, venue])
    db.commit()
    db.add_all([game, other_game])
    db.commit()
    if with_recipient:
        db.add(_participant(game, recipient, 1))
        db.commit()
    db.add_all([chat, other_chat])
    db.commit()
    return sender, recipient, outsider, chat, other_chat


def _message(
    *,
    chat_id: uuid.UUID,
    sender_user_id: uuid.UUID | None,
    index: int,
    seconds_ago: int = 10,
    message_type: str = "text",
    visibility_status: str = "visible",
) -> ChatMessage:
    created_at = datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)
    removed_at = created_at if visibility_status == "removed" else None
    removed_source = "admin" if visibility_status == "removed" else None
    return ChatMessage(
        id=uuid.UUID(int=index + 101),
        chat_id=chat_id,
        sender_user_id=sender_user_id,
        message_type=message_type,
        message_body=f"game rate message {index}",
        visibility_status=visibility_status,
        review_status="clear",
        removed_at=removed_at,
        removed_source=removed_source,
        created_at=created_at,
        updated_at=created_at,
    )


def _send(db, chat_id: uuid.UUID, sender: User, body: str = "new game message") -> ChatMessage:
    return game_chat_service.create_chat_message_record(
        db,
        ChatMessageCreate(chat_id=chat_id, message_body=body),
        sender,
    )


def _count(db, model, *where) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(*where)) or 0)


def _side_effect_snapshot(db, chat: GameChat) -> dict[str, object]:
    db.refresh(chat)
    return {
        "messages": _count(db, ChatMessage, ChatMessage.chat_id == chat.id),
        "notifications": _count(db, Notification, Notification.related_chat_id == chat.id),
        "reads": _count(db, GameChatRead, GameChatRead.chat_id == chat.id),
        "detections": _count(db, GameChatMessageDetection),
        "findings": _count(db, AdminContentModerationFinding),
        "message_count": chat.message_count,
        "removed_count": chat.removed_count,
        "latest_message_id": chat.latest_message_id,
        "latest_message_at": chat.latest_message_at,
    }


@pytest.mark.requirement("WS02-04C3A-R1")
@pytest.mark.requirement("WS02-04C3A-R2")
def test_game_chat_send_uses_shared_game_chat_limiter_and_allows_until_fifth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[dict[str, object]] = []
    original = game_chat_service.enforce_visible_text_chat_rate_limit

    def observe(*args, **kwargs):
        seen.append(dict(kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(game_chat_service, "enforce_visible_text_chat_rate_limit", observe)

    with _session() as db:
        sender, _recipient, _outsider, chat, _other_chat = _context(db)
        for index in range(4):
            db.add(_message(chat_id=chat.id, sender_user_id=sender.id, index=index))
        db.commit()

        created = _send(db, chat.id, sender, body="permitted fifth game message")

        assert created.chat_id == chat.id
        assert created.sender_user_id == sender.id
        assert _count(
            db,
            ChatMessage,
            ChatMessage.chat_id == chat.id,
            ChatMessage.sender_user_id == sender.id,
            ChatMessage.visibility_status == "visible",
        ) == 5
        assert seen[-1]["limiter_category"] == "game_chat"
        assert seen[-1]["message_model"] is ChatMessage
        assert seen[-1]["chat_id"] == chat.id
        assert seen[-1]["sender_user_id"] == sender.id


@pytest.mark.requirement("WS02-04C3A-R1")
@pytest.mark.requirement("WS02-04C3A-R2")
@pytest.mark.requirement("WS02-04C3A-R6")
def test_game_chat_sixth_message_rejects_without_send_side_effects() -> None:
    with _session() as db:
        sender, other_sender, _outsider, chat, other_chat = _context(db)
        for index in range(5):
            db.add(_message(chat_id=chat.id, sender_user_id=sender.id, index=index))
        for index in range(5, 10):
            db.add(_message(chat_id=chat.id, sender_user_id=other_sender.id, index=index))
            db.add(_message(chat_id=other_chat.id, sender_user_id=sender.id, index=index + 10))
        db.commit()
        game_chat_service.refresh_game_chat_summary(db, chat)
        db.commit()
        before = _side_effect_snapshot(db, chat)

        with pytest.raises(HTTPException) as exc_info:
            _send(db, chat.id, sender, body="blocked sixth game message")

        assert exc_info.value.status_code == 429
        assert exc_info.value.headers["Retry-After"].isdigit()
        db.rollback()
        assert _side_effect_snapshot(db, chat) == before


@pytest.mark.requirement("WS02-04C3A-R5")
def test_game_chat_authorization_happens_before_limiter_disclosure() -> None:
    with _session() as db:
        sender, _recipient, outsider, chat, _other_chat = _context(db)
        for index in range(5):
            db.add(_message(chat_id=chat.id, sender_user_id=outsider.id, index=index))
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            _send(db, chat.id, outsider, body="outsider should not learn count")

        assert exc_info.value.status_code == 403
        assert "chat" in str(exc_info.value.detail).lower()
        assert exc_info.value.headers is None
        assert "rate" not in str(exc_info.value.detail).lower()
        assert _count(db, ChatMessage, ChatMessage.chat_id == chat.id) == 5


@pytest.mark.requirement("WS02-04C3A-R6")
def test_game_chat_limiter_store_failure_precedes_send_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_lock(*args, **kwargs) -> None:
        del args, kwargs
        raise SQLAlchemyError("synthetic game-chat limiter store failure")

    monkeypatch.setattr(chat_rate_limit_service, "_acquire_chat_rate_limit_lock", fail_lock)

    with _session() as db:
        sender, _recipient, _outsider, chat, _other_chat = _context(db)
        before = _side_effect_snapshot(db, chat)

        with pytest.raises(SQLAlchemyError):
            _send(db, chat.id, sender, body="store failure game message")

        db.rollback()
        assert _side_effect_snapshot(db, chat) == before


@pytest.mark.requirement("WS02-04C3A-R8")
def test_game_chat_visibility_restoration_and_non_text_boundaries() -> None:
    with _session() as db:
        sender, _recipient, _outsider, chat, _other_chat = _context(db)
        removed = _message(
            chat_id=chat.id,
            sender_user_id=sender.id,
            index=1,
            visibility_status="removed",
        )
        system = _message(
            chat_id=chat.id,
            sender_user_id=sender.id,
            index=2,
            message_type="system",
        )
        pinned = _message(
            chat_id=chat.id,
            sender_user_id=sender.id,
            index=3,
            message_type="pinned_update",
        )
        db.add_all([removed, system, pinned])
        db.commit()

        _send(db, chat.id, sender, body="removed and non-text do not count")
        assert _count(db, ChatMessage, ChatMessage.chat_id == chat.id) == 4

        original_created_at = removed.created_at
        removed.visibility_status = "visible"
        removed.removed_at = None
        removed.removed_source = None
        removed.restored_at = datetime.now(timezone.utc)
        removed.restored_by_user_id = sender.id
        db.add(removed)
        db.commit()

        for index in range(4, 8):
            db.add(_message(chat_id=chat.id, sender_user_id=sender.id, index=index))
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            _send(db, chat.id, sender, body="restored row counts again")

        assert exc_info.value.status_code == 429
        restored = db.get(ChatMessage, removed.id)
        assert restored is not None
        assert restored.created_at == original_created_at
        assert _count(db, ChatMessage, ChatMessage.chat_id == chat.id) == 8


@pytest.mark.requirement("WS02-04C3A-R1")
@pytest.mark.requirement("WS02-04C3A-R8")
def test_game_chat_rate_limiter_remains_before_b1_total_history_cap() -> None:
    source = inspect.getsource(game_chat_service.create_chat_message_record)

    assert source.index("validate_sender_rate_limit") < source.index("validate_total_message_limit")
    assert game_chat_service.MAX_CHAT_MESSAGES_PER_MINUTE == 5
    assert game_chat_service.MAX_CHAT_MESSAGES_TOTAL == 200
