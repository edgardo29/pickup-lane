from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

os.environ.setdefault("APP_ENV", "test")
if not os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (
        "postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/"
        "pickup_lane_test_db"
    )

from backend.models import ChatMessage, Game, GameChat, User, Venue
from backend.services import chat_rate_limit_service

pytestmark = pytest.mark.suite_type("ordinary")

_BASE_TIME = datetime(2035, 4, 1, 12, 0, 0, tzinfo=timezone.utc)


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _user(index: int) -> User:
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-c3a-service-user-{index}-{uuid.uuid4()}",
        role="player",
        email=f"ws02-c3a-service-{index}-{uuid.uuid4()}@example.invalid",
        first_name="Rate",
        last_name=f"User{index}",
        account_status="active",
        hosting_status="eligible",
    )


def _venue() -> Venue:
    return Venue(
        id=uuid.uuid4(),
        name="Rate Limit Gym",
        address_line_1="1 Window Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        venue_status="approved",
        is_active=True,
    )


def _game(host: User, venue: Venue, index: int) -> Game:
    return Game(
        id=uuid.uuid4(),
        game_type="community",
        payment_collection_type="none",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title=f"Rate Limit Game {index}",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot=venue.address_line_1,
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        host_user_id=host.id,
        created_by_user_id=host.id,
        starts_at=_BASE_TIME + timedelta(days=index),
        ends_at=_BASE_TIME + timedelta(days=index, hours=2),
        starts_on_local=(_BASE_TIME + timedelta(days=index)).date(),
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


def _chat(game: Game) -> GameChat:
    return GameChat(id=uuid.uuid4(), game_id=game.id, chat_status="active")


def _context(db):
    sender = _user(1)
    other_sender = _user(2)
    venue = _venue()
    game = _game(sender, venue, 1)
    other_game = _game(sender, venue, 2)
    chat = _chat(game)
    other_chat = _chat(other_game)
    db.add_all([sender, other_sender, venue])
    db.commit()
    db.add_all([game, other_game])
    db.commit()
    db.add_all([chat, other_chat])
    db.commit()
    return sender, other_sender, chat, other_chat


def _message(
    *,
    chat_id: uuid.UUID,
    sender_user_id: uuid.UUID,
    created_at: datetime,
    index: int,
    message_type: str = "text",
    visibility_status: str = "visible",
) -> ChatMessage:
    removed_at = created_at if visibility_status == "removed" else None
    removed_source = "admin" if visibility_status == "removed" else None
    return ChatMessage(
        id=uuid.UUID(int=index + 1),
        chat_id=chat_id,
        sender_user_id=sender_user_id,
        message_type=message_type,
        message_body=f"service message {index}",
        visibility_status=visibility_status,
        review_status="clear",
        removed_at=removed_at,
        removed_source=removed_source,
        created_at=created_at,
        updated_at=created_at,
    )


def _event_payloads(caplog: pytest.LogCaptureFixture) -> list[dict[str, object]]:
    return [
        record.pickup_lane_event
        for record in caplog.records
        if hasattr(record, "pickup_lane_event")
    ]


def _assert_safe_event_payload(event: dict[str, object], *, result: str) -> None:
    serialized = json.dumps(event, sort_keys=True)
    assert event["event_name"] == "chat.rate_limit"
    assert event["actor_kind"] == "authenticated_user"
    assert event["operation"] == "chat_rate_limit.check"
    assert event["result"] == result
    assert event["resource_kind"] in {"game_chat", "need_a_sub_chat"}
    labels = event["labels"]
    assert labels == {
        "outcome": result,
        "route_template": (
            "/chat-messages"
            if event["resource_kind"] == "game_chat"
            else "/need-a-sub/{sub_post_id}/chat/messages"
        ),
    }
    for forbidden in (
        "user_id",
        "chat_id",
        "game_id",
        "example.invalid",
        "message body",
        "token",
        "provider",
        "SELECT",
        "synthetic-store-secret",
        "00000000-",
    ):
        assert forbidden not in serialized


@pytest.mark.requirement("WS02-04C3A-R1")
@pytest.mark.requirement("WS02-04C3A-R3")
def test_approved_constants_and_retry_after_boundaries() -> None:
    assert chat_rate_limit_service.CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES == 5
    assert chat_rate_limit_service.CHAT_RATE_LIMIT_WINDOW_SECONDS == 60
    assert chat_rate_limit_service.CHAT_RATE_LIMIT_ERROR_CODE == "API.RATE_LIMITED"
    assert chat_rate_limit_service.CHAT_RATE_LIMIT_ALGORITHM == "rolling_window"

    assert (
        chat_rate_limit_service.retry_after_for_window(
            oldest_qualifying_message_at=_BASE_TIME - timedelta(seconds=60),
            current_time=_BASE_TIME,
        )
        == 1
    )
    assert (
        chat_rate_limit_service.retry_after_for_window(
            oldest_qualifying_message_at=_BASE_TIME - timedelta(seconds=59, milliseconds=200),
            current_time=_BASE_TIME,
        )
        == 1
    )
    assert (
        chat_rate_limit_service.retry_after_for_window(
            oldest_qualifying_message_at=_BASE_TIME - timedelta(seconds=45, milliseconds=400),
            current_time=_BASE_TIME,
        )
        == 15
    )


@pytest.mark.requirement("WS02-04C3A-R2")
@pytest.mark.requirement("WS02-04C3A-R4")
def test_lock_key_uses_deterministic_sender_chat_and_family_identity() -> None:
    sender_id = uuid.UUID("00000000-0000-4000-8000-000000000001")
    other_sender_id = uuid.UUID("00000000-0000-4000-8000-000000000002")
    chat_id = uuid.UUID("00000000-0000-4000-8000-000000000010")
    other_chat_id = uuid.UUID("00000000-0000-4000-8000-000000000011")

    base = chat_rate_limit_service.chat_rate_limit_lock_key(
        limiter_category="game_chat",
        chat_id=chat_id,
        sender_user_id=sender_id,
    )

    assert base == chat_rate_limit_service.chat_rate_limit_lock_key(
        limiter_category="game_chat",
        chat_id=chat_id,
        sender_user_id=sender_id,
    )
    assert base != chat_rate_limit_service.chat_rate_limit_lock_key(
        limiter_category="game_chat",
        chat_id=chat_id,
        sender_user_id=other_sender_id,
    )
    assert base != chat_rate_limit_service.chat_rate_limit_lock_key(
        limiter_category="game_chat",
        chat_id=other_chat_id,
        sender_user_id=sender_id,
    )
    assert base != chat_rate_limit_service.chat_rate_limit_lock_key(
        limiter_category="need_a_sub_chat",
        chat_id=chat_id,
        sender_user_id=sender_id,
    )


@pytest.mark.requirement("WS02-04C3A-R1")
@pytest.mark.requirement("WS02-04C3A-R2")
@pytest.mark.requirement("WS02-04C3A-R3")
def test_rolling_window_uses_committed_visible_text_rows_and_inclusive_boundary() -> None:
    with _session() as db:
        sender, other_sender, chat, other_chat = _context(db)
        allowed_times = [
            _BASE_TIME - timedelta(seconds=55),
            _BASE_TIME - timedelta(seconds=40),
            _BASE_TIME - timedelta(seconds=20),
            _BASE_TIME - timedelta(seconds=1),
        ]
        db.add_all(
            _message(
                chat_id=chat.id,
                sender_user_id=sender.id,
                created_at=created_at,
                index=index,
            )
            for index, created_at in enumerate(allowed_times)
        )
        db.commit()

        chat_rate_limit_service.enforce_visible_text_chat_rate_limit(
            db,
            limiter_category="game_chat",
            message_model=ChatMessage,
            chat_id=chat.id,
            sender_user_id=sender.id,
            current_time=_BASE_TIME,
        )

        exact_boundary = _BASE_TIME - timedelta(seconds=60)
        db.add(
            _message(
                chat_id=chat.id,
                sender_user_id=sender.id,
                created_at=exact_boundary,
                index=10,
            )
        )
        db.add(
            _message(
                chat_id=chat.id,
                sender_user_id=sender.id,
                created_at=_BASE_TIME - timedelta(seconds=61),
                index=11,
            )
        )
        db.add(
            _message(
                chat_id=chat.id,
                sender_user_id=other_sender.id,
                created_at=_BASE_TIME - timedelta(seconds=10),
                index=12,
            )
        )
        db.add(
            _message(
                chat_id=other_chat.id,
                sender_user_id=sender.id,
                created_at=_BASE_TIME - timedelta(seconds=10),
                index=13,
            )
        )
        db.add(
            _message(
                chat_id=chat.id,
                sender_user_id=sender.id,
                created_at=_BASE_TIME - timedelta(seconds=10),
                index=14,
                visibility_status="removed",
            )
        )
        db.add(
            _message(
                chat_id=chat.id,
                sender_user_id=sender.id,
                created_at=_BASE_TIME - timedelta(seconds=10),
                index=15,
                message_type="system",
            )
        )
        db.commit()

        recent = chat_rate_limit_service._recent_qualifying_message_times(
            db,
            message_model=ChatMessage,
            chat_id=chat.id,
            sender_user_id=sender.id,
            current_time=_BASE_TIME,
            visible_status="visible",
        )

        assert recent == [exact_boundary, *allowed_times]
        with pytest.raises(HTTPException) as exc_info:
            chat_rate_limit_service.enforce_visible_text_chat_rate_limit(
                db,
                limiter_category="game_chat",
                message_model=ChatMessage,
                chat_id=chat.id,
                sender_user_id=sender.id,
                current_time=_BASE_TIME,
            )

        assert exc_info.value.status_code == 429
        assert exc_info.value.detail == chat_rate_limit_service.CHAT_RATE_LIMIT_DETAIL
        assert exc_info.value.headers == {"Retry-After": "1"}


@pytest.mark.requirement("WS02-04C3A-R6")
@pytest.mark.requirement("WS02-04C3A-R10")
def test_advisory_lock_failure_fails_closed_without_fake_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail_lock(*args, **kwargs) -> None:
        del args, kwargs
        raise SQLAlchemyError("synthetic-store-secret SELECT raw_lock_failure")

    monkeypatch.setattr(chat_rate_limit_service, "_acquire_chat_rate_limit_lock", fail_lock)

    with _session() as db, caplog.at_level(
        logging.INFO,
        logger="backend.services.chat_rate_limit_service",
    ):
        with pytest.raises(SQLAlchemyError):
            chat_rate_limit_service.enforce_visible_text_chat_rate_limit(
                db,
                limiter_category="game_chat",
                message_model=ChatMessage,
                chat_id=uuid.uuid4(),
                sender_user_id=uuid.uuid4(),
                current_time=_BASE_TIME,
            )

    events = _event_payloads(caplog)
    assert [event["result"] for event in events] == ["store_error"]
    assert "stable_error_code" not in events[0]
    _assert_safe_event_payload(events[0], result="store_error")


@pytest.mark.requirement("WS02-04C3A-R6")
@pytest.mark.requirement("WS02-04C3A-R10")
def test_rolling_window_read_failure_fails_closed_without_fake_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail_read(*args, **kwargs) -> list[datetime]:
        del args, kwargs
        raise SQLAlchemyError("synthetic-store-secret SELECT raw_read_failure")

    monkeypatch.setattr(chat_rate_limit_service, "_recent_qualifying_message_times", fail_read)

    with _session() as db, caplog.at_level(
        logging.INFO,
        logger="backend.services.chat_rate_limit_service",
    ):
        with pytest.raises(SQLAlchemyError):
            chat_rate_limit_service.enforce_visible_text_chat_rate_limit(
                db,
                limiter_category="game_chat",
                message_model=ChatMessage,
                chat_id=uuid.uuid4(),
                sender_user_id=uuid.uuid4(),
                current_time=_BASE_TIME,
            )

    events = _event_payloads(caplog)
    assert [event["result"] for event in events] == ["store_error"]
    assert "stable_error_code" not in events[0]
    _assert_safe_event_payload(events[0], result="store_error")


@pytest.mark.requirement("WS02-04C3A-R10")
def test_allowed_rejected_and_store_error_telemetry_are_bounded(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with _session() as db:
        sender, _other_sender, chat, _other_chat = _context(db)
        db.add_all(
            _message(
                chat_id=chat.id,
                sender_user_id=sender.id,
                created_at=_BASE_TIME - timedelta(seconds=index + 1),
                index=index + 20,
            )
            for index in range(5)
        )
        db.commit()

        with caplog.at_level(
            logging.INFO,
            logger="backend.services.chat_rate_limit_service",
        ):
            chat_rate_limit_service.enforce_visible_text_chat_rate_limit(
                db,
                limiter_category="need_a_sub_chat",
                message_model=ChatMessage,
                chat_id=uuid.uuid4(),
                sender_user_id=uuid.uuid4(),
                current_time=_BASE_TIME,
            )

            with pytest.raises(HTTPException):
                chat_rate_limit_service.enforce_visible_text_chat_rate_limit(
                    db,
                    limiter_category="game_chat",
                    message_model=ChatMessage,
                    chat_id=chat.id,
                    sender_user_id=sender.id,
                    current_time=_BASE_TIME,
                )

            def fail_lock(*args, **kwargs) -> None:
                del args, kwargs
                raise SQLAlchemyError("synthetic-store-secret raw telemetry text")

            monkeypatch.setattr(
                chat_rate_limit_service,
                "_acquire_chat_rate_limit_lock",
                fail_lock,
            )
            with pytest.raises(SQLAlchemyError):
                chat_rate_limit_service.enforce_visible_text_chat_rate_limit(
                    db,
                    limiter_category="game_chat",
                    message_model=ChatMessage,
                    chat_id=uuid.uuid4(),
                    sender_user_id=uuid.uuid4(),
                    current_time=_BASE_TIME,
                )

    events = _event_payloads(caplog)
    assert [event["result"] for event in events] == ["allowed", "rejected", "store_error"]
    assert events[1]["stable_error_code"] == "API.RATE_LIMITED"
    assert "stable_error_code" not in events[0]
    assert "stable_error_code" not in events[2]
    for event in events:
        _assert_safe_event_payload(event, result=str(event["result"]))
