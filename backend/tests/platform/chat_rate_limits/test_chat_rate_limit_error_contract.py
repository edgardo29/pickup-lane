from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from starlette.exceptions import HTTPException as StarletteHTTPException

os.environ.setdefault("APP_ENV", "test")
if not os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (
        "postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/"
        "pickup_lane_test_db"
    )

from backend.models import ChatMessage, Game, GameChat, User, Venue
from backend.observability.http_errors import handle_http_exception
from backend.services.auth_service import require_verified_user

pytestmark = pytest.mark.suite_type("ordinary")

_BASE_TIME = datetime(2035, 4, 5, 12, 0, 0, tzinfo=timezone.utc)
_ALLOWED_ORIGIN = "http://localhost:5173"
_VALID_REQUEST_ID = "123e4567-e89b-42d3-a456-426614174010"


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _user(index: int) -> User:
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-c3a-error-user-{index}-{uuid.uuid4()}",
        role="player",
        email=f"ws02-c3a-error-{index}-{uuid.uuid4()}@example.invalid",
        first_name="Error",
        last_name=f"User{index}",
        account_status="active",
        hosting_status="eligible",
    )


def _venue() -> Venue:
    return Venue(
        id=uuid.uuid4(),
        name="Error Gym",
        address_line_1="1 Error Way",
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
        title="C3A Error Game",
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
        id=uuid.UUID(int=index + 5001),
        chat_id=chat_id,
        sender_user_id=sender_user_id,
        message_type="text",
        message_body=f"error setup message {index}",
        visibility_status="visible",
        review_status="clear",
        created_at=created_at,
        updated_at=created_at,
    )


def _rate_limited_context() -> tuple[User, uuid.UUID]:
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
        db.add_all(_message(chat.id, sender.id, index) for index in range(5))
        db.commit()
        sender_id = sender.id
        chat_id = chat.id

    return (
        User(
            id=sender_id,
            auth_user_id="detached-c3a-error-user",
            role="player",
            email="detached-c3a-error@example.invalid",
            first_name="Error",
            last_name="User",
            account_status="active",
            hosting_status="eligible",
        ),
        chat_id,
    )


def _assert_canonical_uuidv4(value: str) -> None:
    parsed = uuid.UUID(value)
    assert parsed.version == 4
    assert str(parsed) == value


def _normalized_http_exception(
    status_code: int,
    *,
    detail: Any = "Synthetic safe detail.",
    headers: Mapping[str, str] | None = None,
) -> tuple[int, dict[str, Any], Mapping[str, str]]:
    response = asyncio.run(
        handle_http_exception(
            None,  # type: ignore[arg-type]
            StarletteHTTPException(
                status_code=status_code,
                detail=detail,
                headers=headers,
            ),
        )
    )
    return response.status_code, json.loads(response.body), response.headers


@pytest.mark.requirement("WS02-04C3A-R7")
def test_real_chat_rate_limit_rejection_uses_safe_429_contract(client: TestClient) -> None:
    sender, chat_id = _rate_limited_context()
    client.app.dependency_overrides[require_verified_user] = lambda: sender

    response = client.post(
        "/chat-messages",
        headers={
            "Host": "testserver",
            "Origin": _ALLOWED_ORIGIN,
            "X-Request-ID": _VALID_REQUEST_ID,
        },
        json={
            "chat_id": str(chat_id),
            "message_body": "blocked by real C3A limiter",
        },
    )

    payload = response.json()
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert payload["code"] == "API.RATE_LIMITED"
    assert payload["message"] == "You can send up to 5 chat messages per minute. Try again shortly."
    assert payload["detail"] == "You can send up to 5 chat messages per minute. Try again shortly."
    assert payload["correlation_id"] == _VALID_REQUEST_ID
    assert response.headers["X-Request-ID"] == _VALID_REQUEST_ID
    assert response.headers["Retry-After"].isdigit()
    assert int(response.headers["Retry-After"]) >= 1
    assert response.headers["Access-Control-Allow-Origin"] == _ALLOWED_ORIGIN
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] == "private, no-store"

    with _session() as db:
        assert int(
            db.scalar(
                select(func.count())
                .select_from(ChatMessage)
                .where(ChatMessage.chat_id == chat_id)
            )
            or 0
        ) == 5


@pytest.mark.requirement("WS02-04C3A-R7")
def test_c3a_retry_after_allowance_does_not_make_unrelated_headers_public() -> None:
    response_status, payload, headers = _normalized_http_exception(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Synthetic service unavailable.",
        headers={"Retry-After": "7", "X-Internal": "secret"},
    )

    assert response_status == status.HTTP_503_SERVICE_UNAVAILABLE
    assert payload["code"] == "API.SERVICE_UNAVAILABLE"
    _assert_canonical_uuidv4(payload["correlation_id"])
    assert "Retry-After" not in headers
    assert "X-Internal" not in headers
