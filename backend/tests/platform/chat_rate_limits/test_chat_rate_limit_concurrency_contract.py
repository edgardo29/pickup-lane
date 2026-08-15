from __future__ import annotations

import os
import threading
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import event, func, select

os.environ.setdefault("APP_ENV", "test")
if not os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (
        "postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/"
        "pickup_lane_test_db"
    )

from backend.models import ChatMessage, Game, GameChat, User, Venue
from backend.schemas.chat_message_schema import ChatMessageCreate
from backend.services import chat_rate_limit_service, game_chat_service

pytestmark = pytest.mark.suite_type("ordinary")

_BASE_TIME = datetime(2035, 4, 4, 12, 0, 0, tzinfo=timezone.utc)


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _user(index: int) -> User:
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-c3a-race-user-{index}-{uuid.uuid4()}",
        role="player",
        email=f"ws02-c3a-race-{index}-{uuid.uuid4()}@example.invalid",
        first_name="Race",
        last_name=f"User{index}",
        account_status="active",
        hosting_status="eligible",
    )


def _venue() -> Venue:
    return Venue(
        id=uuid.uuid4(),
        name="Race Gym",
        address_line_1="1 Lock Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        venue_status="approved",
        is_active=True,
    )


def _game(host: User, venue: Venue) -> Game:
    return Game(
        id=uuid.uuid4(),
        game_type="community",
        payment_collection_type="none",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title="C3A Race Game",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot=venue.address_line_1,
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        host_user_id=host.id,
        created_by_user_id=host.id,
        starts_at=_BASE_TIME,
        ends_at=_BASE_TIME + timedelta(hours=2),
        starts_on_local=_BASE_TIME.date(),
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


def _message(chat_id: uuid.UUID, sender_user_id: uuid.UUID, index: int) -> ChatMessage:
    created_at = datetime.now(timezone.utc) - timedelta(seconds=30 - index)
    return ChatMessage(
        id=uuid.UUID(int=index + 3001),
        chat_id=chat_id,
        sender_user_id=sender_user_id,
        message_type="text",
        message_body=f"race setup message {index}",
        visibility_status="visible",
        review_status="clear",
        created_at=created_at,
        updated_at=created_at,
    )


def _send(db, chat_id: uuid.UUID, sender: User, body: str) -> ChatMessage:
    return game_chat_service.create_chat_message_record(
        db,
        ChatMessageCreate(chat_id=chat_id, message_body=body),
        sender,
    )


def _visible_count(db, chat_id: uuid.UUID, sender_user_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(ChatMessage)
            .where(
                ChatMessage.chat_id == chat_id,
                ChatMessage.sender_user_id == sender_user_id,
                ChatMessage.message_type == "text",
                ChatMessage.visibility_status == "visible",
            )
        )
        or 0
    )


@pytest.mark.requirement("WS02-04C3A-R4")
@pytest.mark.requirement("WS02-04C3A-R6")
def test_same_sender_chat_family_concurrent_sends_serialize_on_postgresql_advisory_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.database import engine

    with _session() as db:
        sender = _user(1)
        venue = _venue()
        game = _game(sender, venue)
        chat = GameChat(id=uuid.uuid4(), game_id=game.id, chat_status="active")
        db.add_all([sender, venue])
        db.commit()
        db.add(game)
        db.commit()
        db.add(chat)
        db.commit()
        db.add_all(_message(chat.id, sender.id, index) for index in range(4))
        db.commit()
        sender_id = sender.id
        chat_id = chat.id

    release_a = threading.Event()
    a_paused_after_limiter = threading.Event()
    b_reached_lock = threading.Event()
    b_reached_lock_while_a_paused = threading.Event()
    lock_observations: list[tuple[str, object]] = []
    limiter_calls: list[tuple[str, dict[str, object]]] = []
    connection_ids: dict[str, int] = {}
    results: dict[str, tuple[object, ...]] = {}

    original_limiter = game_chat_service.enforce_visible_text_chat_rate_limit

    def observe_limiter(*args, **kwargs):
        limiter_calls.append((threading.current_thread().name, dict(kwargs)))
        return original_limiter(*args, **kwargs)

    monkeypatch.setattr(
        game_chat_service,
        "enforce_visible_text_chat_rate_limit",
        observe_limiter,
    )

    original_total_limit = game_chat_service.validate_total_message_limit

    def pause_request_a_after_limiter(db, chat_id_arg):
        if threading.current_thread().name == "request-a":
            a_paused_after_limiter.set()
            assert release_a.wait(timeout=5), "request A was not released"
        return original_total_limit(db, chat_id_arg)

    monkeypatch.setattr(
        game_chat_service,
        "validate_total_message_limit",
        pause_request_a_after_limiter,
    )

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        del cursor, context, executemany
        if "pg_advisory_xact_lock" not in statement:
            return
        thread_name = threading.current_thread().name
        lock_key = parameters.get("lock_key") if isinstance(parameters, dict) else parameters
        lock_observations.append((thread_name, lock_key))
        connection_ids.setdefault(thread_name, id(conn.connection))
        if thread_name == "request-b":
            if a_paused_after_limiter.is_set():
                b_reached_lock_while_a_paused.set()
            b_reached_lock.set()

    event.listen(engine, "before_cursor_execute", before_cursor_execute)

    def worker(label: str) -> None:
        try:
            with _session() as db:
                connection_ids.setdefault(threading.current_thread().name, id(db.connection().connection))
                message = _send(db, chat_id, sender, body=f"{label} race send")
                results[label] = ("created", message.id)
        except HTTPException as exc:
            results[label] = ("http", exc.status_code, dict(exc.headers or {}))
        except Exception as exc:  # pragma: no cover - surfaced in assertion below
            results[label] = ("error", repr(exc))

    try:
        thread_a = threading.Thread(target=worker, args=("A",), name="request-a")
        thread_b = threading.Thread(target=worker, args=("B",), name="request-b")
        thread_a.start()
        assert a_paused_after_limiter.wait(timeout=5), "request A did not pause after the real limiter"
        thread_b.start()
        assert b_reached_lock.wait(timeout=5), "request B did not reach the real advisory-lock SQL"
        assert b_reached_lock_while_a_paused.is_set()
        release_a.set()
        thread_a.join(timeout=5)
        thread_b.join(timeout=5)
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
        release_a.set()

    assert not thread_a.is_alive()
    assert not thread_b.is_alive()
    assert results["A"][0] == "created"
    assert results["B"][0] == "http"
    assert results["B"][1] == 429
    assert results["B"][2]["Retry-After"].isdigit()

    assert len(limiter_calls) == 2
    for _thread_name, call in limiter_calls:
        assert call["limiter_category"] == "game_chat"
        assert call["message_model"] is ChatMessage
        assert call["chat_id"] == chat_id
        assert call["sender_user_id"] == sender_id
    assert len(lock_observations) >= 2
    assert {thread_name for thread_name, _lock_key in lock_observations} >= {
        "request-a",
        "request-b",
    }
    assert len({lock_key for _thread_name, lock_key in lock_observations}) == 1
    assert connection_ids["request-a"] != connection_ids["request-b"]

    with _session() as db:
        assert _visible_count(db, chat_id, sender_id) == 5


@pytest.mark.requirement("WS02-04C3A-R4")
def test_advisory_key_layer_separates_sender_chat_and_family_identities() -> None:
    sender_id = uuid.UUID("00000000-0000-4000-8000-000000000101")
    other_sender_id = uuid.UUID("00000000-0000-4000-8000-000000000102")
    chat_id = uuid.UUID("00000000-0000-4000-8000-000000000201")
    other_chat_id = uuid.UUID("00000000-0000-4000-8000-000000000202")

    base = chat_rate_limit_service.chat_rate_limit_lock_key(
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
