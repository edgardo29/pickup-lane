from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from backend.database import SessionLocal
from backend.models import (
    ChatMessage,
    Notification,
    SubPostChatMessage,
    SubPostPosition,
    SubPostRequest,
    User,
)
from backend.observability.correlation import CORRELATION_ID_HEADER
from backend.schemas.chat_message_schema import ChatMessageCreate
from backend.services.auth_service import (
    VerifiedFirebaseIdentity,
    get_current_app_user,
    get_optional_current_app_user,
    get_verified_firebase_identity,
    require_verified_user,
)
import backend.services.chat_rate_limit_service as chat_rate_limit_service
from backend.services.chat_rate_limit_service import (
    CHAT_RATE_LIMIT_DETAIL,
    CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES,
    CHAT_RATE_LIMIT_WINDOW_SECONDS,
    chat_rate_limit_lock_key,
    retry_after_for_window,
)
from backend.services.game_chat_service import (
    MAX_CHAT_MESSAGE_LENGTH,
    create_chat_message_record,
)
from backend.tests.helpers import build_sub_post_payload
from backend.tests.support.auth import set_user_role
from backend.tests.support.factories import create_user


ALLOWED_ORIGIN = "http://localhost:5173"


@pytest.fixture(autouse=True)
def clear_client_dependency_overrides(client: TestClient):
    client.app.dependency_overrides.clear()
    yield
    client.app.dependency_overrides.clear()


def authenticate_client_as(client: TestClient, user_id: str) -> None:
    def override_current_user() -> User:
        with SessionLocal() as db:
            db_user = db.get(User, UUID(user_id))
            assert db_user is not None
            return db_user

    def override_firebase_identity() -> VerifiedFirebaseIdentity:
        with SessionLocal() as db:
            db_user = db.get(User, UUID(user_id))
            assert db_user is not None
            return VerifiedFirebaseIdentity(
                auth_user_id=db_user.auth_user_id,
                email=db_user.email,
                email_verified=True,
            )

    client.app.dependency_overrides[get_current_app_user] = override_current_user
    client.app.dependency_overrides[get_optional_current_app_user] = override_current_user
    client.app.dependency_overrides[get_verified_firebase_identity] = (
        override_firebase_identity
    )
    client.app.dependency_overrides[require_verified_user] = override_current_user


def run_client_as_user(client: TestClient, user_id: str, request_fn):
    previous_overrides = dict(client.app.dependency_overrides)
    authenticate_client_as(client, user_id)
    try:
        return request_fn()
    finally:
        client.app.dependency_overrides.clear()
        client.app.dependency_overrides.update(previous_overrides)


def create_admin_user(client: TestClient) -> dict:
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    return admin


def create_venue(client: TestClient, admin_user_id: str) -> dict:
    del client
    from backend.schemas import VenueCreate, VenueRead
    from backend.services.venue_service import create_venue_record

    payload = {
        "address_line_1": "123 Rate Limit Ave",
        "approved_by_user_id": admin_user_id,
        "city": "Chicago",
        "country_code": "US",
        "created_by_user_id": admin_user_id,
        "is_active": True,
        "name": "Rate Limit Field",
        "postal_code": "60601",
        "state": "IL",
        "venue_status": "approved",
    }
    with SessionLocal() as db:
        venue = create_venue_record(db, VenueCreate.model_validate(payload))
        return VenueRead.model_validate(venue).model_dump(mode="json")


def create_game(client: TestClient, admin_user_id: str, venue: dict) -> dict:
    starts_at = datetime.now(UTC) + timedelta(days=7)
    payload = {
        "allow_guests": True,
        "ends_at": (starts_at + timedelta(hours=1)).isoformat(),
        "environment_type": "indoor",
        "format_label": "5v5",
        "game_type": "official",
        "is_chat_enabled": True,
        "max_guests_per_booking": 2,
        "price_per_player_cents": 1200,
        "starts_at": starts_at.isoformat(),
        "timezone": "America/Chicago",
        "title": "Rate Limit Match",
        "total_spots": 10,
        "venue_id": venue["id"],
        "waitlist_enabled": True,
    }
    response = run_client_as_user(
        client,
        admin_user_id,
        lambda: client.post("/games", json=payload),
    )
    assert response.status_code == status.HTTP_201_CREATED, response.text
    return response.json()


def create_game_participant(
    client: TestClient,
    admin_user_id: str,
    user_id: str,
    game_id: str,
) -> dict:
    del client, admin_user_id
    from backend.schemas import GameParticipantCreate, GameParticipantRead
    from backend.services.game_participant_service import (
        create_game_participant_workflow,
    )

    payload = {
        "attendance_status": "unknown",
        "booking_id": None,
        "cancellation_type": "none",
        "currency": "USD",
        "display_name_snapshot": "Rate Limit User",
        "game_id": game_id,
        "participant_status": "confirmed",
        "participant_type": "registered_user",
        "price_cents": 1200,
        "roster_order": 1,
        "user_id": user_id,
    }
    with SessionLocal() as db:
        participant = create_game_participant_workflow(
            db,
            GameParticipantCreate.model_validate(payload),
        )
        return GameParticipantRead.model_validate(participant).model_dump(mode="json")


def create_game_chat(client: TestClient, admin_user_id: str, game_id: str) -> dict:
    del client
    from backend.schemas import GameChatCreate, GameChatRead
    from backend.services.game_chat_service import create_game_chat_record

    with SessionLocal() as db:
        admin_user = db.get(User, UUID(admin_user_id))
        assert admin_user is not None
        chat = create_game_chat_record(
            db,
            GameChatCreate.model_validate(
                {"chat_status": "active", "game_id": game_id},
            ),
            admin_user,
        )
        return GameChatRead.model_validate(chat).model_dump(mode="json")


def create_game_chat_fixture(client: TestClient) -> tuple[dict, dict, dict]:
    admin = create_admin_user(client)
    player = create_user(client)
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    create_game_participant(client, admin["id"], player["id"], game["id"])
    chat = create_game_chat(client, admin["id"], game["id"])
    return admin, player, chat


def create_second_game_chat_for_player(
    client: TestClient,
    admin_user_id: str,
    player_user_id: str,
) -> dict:
    venue = create_venue(client, admin_user_id)
    game = create_game(client, admin_user_id, venue)
    create_game_participant(client, admin_user_id, player_user_id, game["id"])
    return create_game_chat(client, admin_user_id, game["id"])


def create_sub_post(
    client: TestClient,
    owner_user_id: str,
    **overrides: object,
) -> dict:
    response = run_client_as_user(
        client,
        owner_user_id,
        lambda: client.post(
            "/need-a-sub/posts",
            json=build_sub_post_payload(**overrides),
        ),
    )
    assert response.status_code == status.HTTP_201_CREATED, response.text
    return response.json()


def ensure_sub_post_chat(client: TestClient, owner_user_id: str, sub_post_id: str) -> dict:
    response = run_client_as_user(
        client,
        owner_user_id,
        lambda: client.post(f"/need-a-sub/posts/{sub_post_id}/chat", json={}),
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    return response.json()


def create_sub_post_chat_fixture(client: TestClient) -> tuple[dict, dict, dict]:
    owner = create_user(client)
    sub_post = create_sub_post(client, owner["id"])
    chat = ensure_sub_post_chat(client, owner["id"], sub_post["id"])
    return owner, sub_post, chat


def create_confirmed_sub_request(sub_post_id: str, requester_user_id: str) -> None:
    current_time = datetime.now(UTC)
    with SessionLocal() as db:
        position = db.scalar(
            select(SubPostPosition)
            .where(SubPostPosition.sub_post_id == UUID(sub_post_id))
            .order_by(SubPostPosition.sort_order.asc(), SubPostPosition.id.asc())
        )
        assert position is not None
        db.add(
            SubPostRequest(
                id=uuid4(),
                sub_post_id=UUID(sub_post_id),
                sub_post_position_id=position.id,
                requester_user_id=UUID(requester_user_id),
                request_status="confirmed",
                confirmed_at=current_time,
            )
        )
        db.commit()


def post_game_chat_message(
    client: TestClient,
    *,
    chat_id: str,
    message_body: str,
    include_origin: bool = False,
):
    headers = {"Origin": ALLOWED_ORIGIN} if include_origin else None
    return client.post(
        "/chat-messages",
        json={"chat_id": chat_id, "message_body": message_body},
        headers=headers,
    )


def post_sub_chat_message(
    client: TestClient,
    *,
    sub_post_id: str,
    chat_id: str,
    message_body: str,
    include_origin: bool = False,
):
    headers = {"Origin": ALLOWED_ORIGIN} if include_origin else None
    return client.post(
        f"/need-a-sub/posts/{sub_post_id}/chat/messages",
        json={"chat_id": chat_id, "message_body": message_body},
        headers=headers,
    )


def visible_text_count(model, *, chat_id: str, sender_user_id: str | None = None) -> int:
    statement = (
        select(func.count())
        .select_from(model)
        .where(
            model.chat_id == UUID(chat_id),
            model.message_type == "text",
            model.visibility_status == "visible",
        )
    )
    if sender_user_id is not None:
        statement = statement.where(model.sender_user_id == UUID(sender_user_id))

    with SessionLocal() as db:
        return db.scalar(statement) or 0


def notification_count() -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(Notification)) or 0


def seed_game_chat_messages(
    *,
    chat_id: str,
    sender_user_id: str,
    count: int,
    created_at: datetime,
    visibility_status: str = "visible",
    message_type: str = "text",
    start_index: int = 0,
) -> None:
    with SessionLocal() as db:
        for index in range(start_index, start_index + count):
            db.add(
                ChatMessage(
                    id=uuid4(),
                    chat_id=UUID(chat_id),
                    sender_user_id=UUID(sender_user_id),
                    message_type=message_type,
                    message_body=f"seeded game message {index}",
                    visibility_status=visibility_status,
                    review_status="clear",
                    is_pinned=False,
                    removed_at=(
                        created_at if visibility_status == "removed" else None
                    ),
                    removed_source=(
                        "system" if visibility_status == "removed" else None
                    ),
                    created_at=created_at + timedelta(milliseconds=index),
                    updated_at=created_at + timedelta(milliseconds=index),
                )
            )
        db.commit()


def seed_sub_chat_messages(
    *,
    chat_id: str,
    sender_user_id: str,
    count: int,
    created_at: datetime,
    visibility_status: str = "visible",
    start_index: int = 0,
) -> None:
    with SessionLocal() as db:
        for index in range(start_index, start_index + count):
            db.add(
                SubPostChatMessage(
                    id=uuid4(),
                    chat_id=UUID(chat_id),
                    sender_user_id=UUID(sender_user_id),
                    sender_display_name_snapshot="Rate Limit User",
                    sender_initials_snapshot="RL",
                    message_type="text",
                    message_body=f"seeded need a sub message {index}",
                    visibility_status=visibility_status,
                    review_status="clear",
                    removed_at=(
                        created_at if visibility_status == "removed" else None
                    ),
                    removed_source=(
                        "system" if visibility_status == "removed" else None
                    ),
                    created_at=created_at + timedelta(milliseconds=index),
                    updated_at=created_at + timedelta(milliseconds=index),
                )
            )
        db.commit()


def assert_rate_limited_response(response, *, sender_id: str, chat_id: str) -> None:
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS, response.text
    body = response.json()
    assert body["code"] == "API.RATE_LIMITED"
    assert body["detail"] == CHAT_RATE_LIMIT_DETAIL
    assert body["message"] == CHAT_RATE_LIMIT_DETAIL
    assert body["correlation_id"] == response.headers[CORRELATION_ID_HEADER]
    assert response.headers["Retry-After"].isdigit()
    assert 1 <= int(response.headers["Retry-After"]) <= CHAT_RATE_LIMIT_WINDOW_SECONDS
    assert response.headers["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] == "private, no-store"
    assert sender_id not in response.text
    assert chat_id not in response.text
    assert "seeded" not in response.text
    assert "SQL" not in response.text


def test_game_chat_accepts_first_five_and_rejects_sixth_without_mutation(
    client: TestClient,
):
    _admin, player, chat = create_game_chat_fixture(client)
    authenticate_client_as(client, player["id"])

    for index in range(CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES):
        response = post_game_chat_message(
            client,
            chat_id=chat["id"],
            message_body=f"allowed game message {index}",
        )
        assert response.status_code == status.HTTP_201_CREATED, response.text

    before_message_count = visible_text_count(
        ChatMessage,
        chat_id=chat["id"],
        sender_user_id=player["id"],
    )
    before_notification_count = notification_count()
    limited_response = post_game_chat_message(
        client,
        chat_id=chat["id"],
        message_body="game message rejected by rate limit",
        include_origin=True,
    )

    assert_rate_limited_response(
        limited_response,
        sender_id=player["id"],
        chat_id=chat["id"],
    )
    assert visible_text_count(
        ChatMessage,
        chat_id=chat["id"],
        sender_user_id=player["id"],
    ) == before_message_count
    assert notification_count() == before_notification_count


def test_game_chat_reopens_after_window_and_ignores_non_counting_messages(
    client: TestClient,
):
    _admin, player, chat = create_game_chat_fixture(client)
    authenticate_client_as(client, player["id"])
    old_time = datetime.now(UTC) - timedelta(seconds=70)
    recent_time = datetime.now(UTC) - timedelta(seconds=10)
    seed_game_chat_messages(
        chat_id=chat["id"],
        sender_user_id=player["id"],
        count=CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES,
        created_at=old_time,
    )
    accepted_after_window = post_game_chat_message(
        client,
        chat_id=chat["id"],
        message_body="eligible after oldest exits window",
    )

    assert accepted_after_window.status_code == status.HTTP_201_CREATED

    seed_game_chat_messages(
        chat_id=chat["id"],
        sender_user_id=player["id"],
        count=CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES,
        created_at=recent_time,
        visibility_status="removed",
        start_index=20,
    )
    seed_game_chat_messages(
        chat_id=chat["id"],
        sender_user_id=player["id"],
        count=CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES,
        created_at=recent_time,
        message_type="system",
        start_index=40,
    )
    accepted_with_non_counting_messages = post_game_chat_message(
        client,
        chat_id=chat["id"],
        message_body="non counting states and types ignored",
    )

    assert accepted_with_non_counting_messages.status_code == status.HTTP_201_CREATED


def test_game_chat_rate_limit_is_sender_and_chat_scoped(client: TestClient):
    admin, player, chat = create_game_chat_fixture(client)
    other_player = create_user(client)
    create_game_participant(client, admin["id"], other_player["id"], chat["game_id"])
    second_chat = create_second_game_chat_for_player(client, admin["id"], player["id"])
    recent_time = datetime.now(UTC) - timedelta(seconds=10)
    seed_game_chat_messages(
        chat_id=chat["id"],
        sender_user_id=other_player["id"],
        count=CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES,
        created_at=recent_time,
    )
    seed_game_chat_messages(
        chat_id=second_chat["id"],
        sender_user_id=player["id"],
        count=CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES,
        created_at=recent_time,
        start_index=20,
    )
    authenticate_client_as(client, player["id"])

    response = post_game_chat_message(
        client,
        chat_id=chat["id"],
        message_body="sender and chat scoped game message",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.text


def test_game_chat_concurrent_cross_session_sends_cannot_exceed_limit(
    client: TestClient,
):
    _admin, player, chat = create_game_chat_fixture(client)
    seed_game_chat_messages(
        chat_id=chat["id"],
        sender_user_id=player["id"],
        count=CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES - 1,
        created_at=datetime.now(UTC) - timedelta(seconds=10),
    )
    start_barrier = Barrier(2)

    def send_message(index: int) -> int:
        with SessionLocal() as db:
            db_user = db.get(User, UUID(player["id"]))
            assert db_user is not None
            start_barrier.wait(timeout=5)
            try:
                create_chat_message_record(
                    db,
                    ChatMessageCreate.model_validate(
                        {
                            "chat_id": chat["id"],
                            "message_body": f"concurrent game message {index}",
                        }
                    ),
                    db_user,
                )
            except HTTPException as exc:
                db.rollback()
                return exc.status_code
            return status.HTTP_201_CREATED

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(send_message, (1, 2)))

    assert sorted(results) == [
        status.HTTP_201_CREATED,
        status.HTTP_429_TOO_MANY_REQUESTS,
    ]
    assert visible_text_count(
        ChatMessage,
        chat_id=chat["id"],
        sender_user_id=player["id"],
    ) == CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES


def test_game_chat_limiter_check_failure_does_not_insert_or_raise_429(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    _admin, player, chat = create_game_chat_fixture(client)
    before_count = visible_text_count(
        ChatMessage,
        chat_id=chat["id"],
        sender_user_id=player["id"],
    )

    def fail_lock(*_args, **_kwargs):
        raise SQLAlchemyError("synthetic limiter store failure")

    monkeypatch.setattr(
        chat_rate_limit_service,
        "_acquire_chat_rate_limit_lock",
        fail_lock,
    )
    with SessionLocal() as db:
        db_user = db.get(User, UUID(player["id"]))
        assert db_user is not None
        with pytest.raises(SQLAlchemyError):
            create_chat_message_record(
                db,
                ChatMessageCreate.model_validate(
                    {
                        "chat_id": chat["id"],
                        "message_body": "should not be inserted",
                    }
                ),
                db_user,
            )
        db.rollback()

    assert visible_text_count(
        ChatMessage,
        chat_id=chat["id"],
        sender_user_id=player["id"],
    ) == before_count


def test_need_a_sub_chat_accepts_first_five_and_rejects_sixth_without_mutation(
    client: TestClient,
):
    owner, _sub_post, chat = create_sub_post_chat_fixture(client)
    authenticate_client_as(client, owner["id"])

    for index in range(CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES):
        response = post_sub_chat_message(
            client,
            sub_post_id=chat["sub_post_id"],
            chat_id=chat["id"],
            message_body=f"allowed need a sub message {index}",
        )
        assert response.status_code == status.HTTP_201_CREATED, response.text

    before_message_count = visible_text_count(
        SubPostChatMessage,
        chat_id=chat["id"],
        sender_user_id=owner["id"],
    )
    before_notification_count = notification_count()
    limited_response = post_sub_chat_message(
        client,
        sub_post_id=chat["sub_post_id"],
        chat_id=chat["id"],
        message_body="need a sub message rejected by rate limit",
        include_origin=True,
    )

    assert_rate_limited_response(
        limited_response,
        sender_id=owner["id"],
        chat_id=chat["id"],
    )
    assert visible_text_count(
        SubPostChatMessage,
        chat_id=chat["id"],
        sender_user_id=owner["id"],
    ) == before_message_count
    assert notification_count() == before_notification_count


def test_need_a_sub_chat_reopens_after_window_and_ignores_removed_messages(
    client: TestClient,
):
    owner, _sub_post, chat = create_sub_post_chat_fixture(client)
    authenticate_client_as(client, owner["id"])
    old_time = datetime.now(UTC) - timedelta(seconds=70)
    recent_time = datetime.now(UTC) - timedelta(seconds=10)
    seed_sub_chat_messages(
        chat_id=chat["id"],
        sender_user_id=owner["id"],
        count=CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES,
        created_at=old_time,
    )
    accepted_after_window = post_sub_chat_message(
        client,
        sub_post_id=chat["sub_post_id"],
        chat_id=chat["id"],
        message_body="need a sub eligible after window",
    )

    assert accepted_after_window.status_code == status.HTTP_201_CREATED

    seed_sub_chat_messages(
        chat_id=chat["id"],
        sender_user_id=owner["id"],
        count=CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES,
        created_at=recent_time,
        visibility_status="removed",
        start_index=20,
    )
    accepted_with_removed_messages = post_sub_chat_message(
        client,
        sub_post_id=chat["sub_post_id"],
        chat_id=chat["id"],
        message_body="need a sub removed messages ignored",
    )

    assert accepted_with_removed_messages.status_code == status.HTTP_201_CREATED


def test_need_a_sub_rate_limit_is_sender_and_chat_scoped(client: TestClient):
    owner, sub_post, chat = create_sub_post_chat_fixture(client)
    other_player = create_user(client)
    create_confirmed_sub_request(sub_post["id"], other_player["id"])
    second_starts_at = datetime.now(UTC).replace(
        hour=18,
        minute=0,
        second=0,
        microsecond=0,
    ) + timedelta(days=8)
    second_sub_post = create_sub_post(
        client,
        owner["id"],
        starts_at=second_starts_at.isoformat(),
        ends_at=(second_starts_at + timedelta(hours=2)).isoformat(),
    )
    second_chat = ensure_sub_post_chat(client, owner["id"], second_sub_post["id"])
    recent_time = datetime.now(UTC) - timedelta(seconds=10)
    seed_sub_chat_messages(
        chat_id=chat["id"],
        sender_user_id=other_player["id"],
        count=CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES,
        created_at=recent_time,
    )
    seed_sub_chat_messages(
        chat_id=second_chat["id"],
        sender_user_id=owner["id"],
        count=CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES,
        created_at=recent_time,
        start_index=20,
    )
    authenticate_client_as(client, owner["id"])

    response = post_sub_chat_message(
        client,
        sub_post_id=chat["sub_post_id"],
        chat_id=chat["id"],
        message_body="sender and chat scoped need a sub message",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.text


def test_lock_identity_and_retry_after_are_deterministic_and_safely_scoped():
    chat_id = uuid4()
    sender_id = uuid4()

    assert chat_rate_limit_lock_key(
        limiter_category="game_chat",
        chat_id=chat_id,
        sender_user_id=sender_id,
    ) == chat_rate_limit_lock_key(
        limiter_category="game_chat",
        chat_id=chat_id,
        sender_user_id=sender_id,
    )
    assert chat_rate_limit_lock_key(
        limiter_category="game_chat",
        chat_id=chat_id,
        sender_user_id=sender_id,
    ) != chat_rate_limit_lock_key(
        limiter_category="game_chat",
        chat_id=uuid4(),
        sender_user_id=sender_id,
    )
    assert chat_rate_limit_lock_key(
        limiter_category="game_chat",
        chat_id=chat_id,
        sender_user_id=sender_id,
    ) != chat_rate_limit_lock_key(
        limiter_category="need_a_sub_chat",
        chat_id=chat_id,
        sender_user_id=sender_id,
    )
    current_time = datetime(2026, 8, 9, 12, 0, 0, 500000, tzinfo=UTC)

    assert retry_after_for_window(
        oldest_qualifying_message_at=current_time - timedelta(seconds=59),
        current_time=current_time,
    ) == 2


def test_chat_message_length_contract_remains_three_hundred_characters(
    client: TestClient,
):
    _admin, player, chat = create_game_chat_fixture(client)
    authenticate_client_as(client, player["id"])
    exact_response = post_game_chat_message(
        client,
        chat_id=chat["id"],
        message_body="G" * MAX_CHAT_MESSAGE_LENGTH,
    )
    long_response = post_game_chat_message(
        client,
        chat_id=chat["id"],
        message_body="G" * (MAX_CHAT_MESSAGE_LENGTH + 1),
    )

    assert exact_response.status_code == status.HTTP_201_CREATED
    assert long_response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
