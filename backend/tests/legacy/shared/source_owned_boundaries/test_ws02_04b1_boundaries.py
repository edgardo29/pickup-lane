from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest
from sqlalchemy import func, select

from backend.database import SessionLocal
from backend.models import (
    ChatMessage,
    Notification,
    PlatformNotice,
    PlatformNoticeRecipient,
    SubPost,
    SubPostChatMessage,
    SubPostPosition,
    SubPostRequest,
    User,
    UserPaymentMethod,
    VenueImage,
)
from backend.observability.request_body_limits import (
    DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES,
)
from backend.schemas.sub_post_schema import MAX_SUB_POST_POSITION_ROWS, SubPostCreate
from backend.services.game_chat_service import (
    MAX_CHAT_MESSAGE_LENGTH,
    MAX_CHAT_MESSAGES_PER_PAGE,
    MAX_CHAT_MESSAGES_TOTAL,
)
from backend.services.need_a_sub_post_service import (
    SUB_POST_CARD_DEFAULT_LIMIT,
    SUB_POST_CARD_MAX_LIMIT,
)
from backend.services.need_a_sub_rules import MAX_WAITLIST_REQUESTS_PER_POST
from backend.services.payment_method_service import MAX_ACTIVE_PAYMENT_METHODS
from backend.services.platform_notice_service import MAX_SELECTED_PLATFORM_NOTICE_USERS
from backend.services.auth_service import (
    VerifiedFirebaseIdentity,
    get_current_app_user,
    get_optional_current_app_user,
    get_verified_firebase_identity,
    require_verified_user,
)
from backend.services.stripe_service import (
    StripePaymentMethodCardResult,
    StripeSetupIntentResult,
)
from backend.services.sub_post_chat_service import (
    MAX_SUB_CHAT_MESSAGE_LENGTH,
    MAX_SUB_CHAT_MESSAGES_PER_PAGE,
    MAX_SUB_CHAT_MESSAGES_TOTAL,
)
from backend.tests.helpers import (
    build_sub_post_payload,
    create_user_payment_method,
    set_user_account_status,
)
from backend.tests.support.auth import set_user_role
from backend.tests.support.factories import create_user, unique_suffix


APPROVED_IMAGE_SIZE_BYTES = 8 * 1024 * 1024
APPROVED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})


@pytest.fixture(autouse=True)
def clear_client_dependency_overrides(client: TestClient):
    client.app.dependency_overrides.clear()
    yield
    client.app.dependency_overrides.clear()


def model_count(model) -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(model)) or 0


def create_admin_user(client: TestClient) -> dict:
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    return admin


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
                authenticated_at=datetime.now(UTC),
            )

    client.app.dependency_overrides[get_current_app_user] = override_current_user
    client.app.dependency_overrides[get_optional_current_app_user] = override_current_user
    client.app.dependency_overrides[get_verified_firebase_identity] = (
        override_firebase_identity
    )
    client.app.dependency_overrides[require_verified_user] = override_current_user


def run_client_as_user(client: TestClient, user_id: str, request_fn):
    overrides = client.app.dependency_overrides
    previous_current = overrides.get(get_current_app_user)
    previous_optional = overrides.get(get_optional_current_app_user)
    previous_identity = overrides.get(get_verified_firebase_identity)
    previous_verified = overrides.get(require_verified_user)
    had_current = get_current_app_user in overrides
    had_optional = get_optional_current_app_user in overrides
    had_identity = get_verified_firebase_identity in overrides
    had_verified = require_verified_user in overrides

    authenticate_client_as(client, user_id)
    try:
        return request_fn()
    finally:
        if had_current:
            overrides[get_current_app_user] = previous_current
        else:
            overrides.pop(get_current_app_user, None)
        if had_optional:
            overrides[get_optional_current_app_user] = previous_optional
        else:
            overrides.pop(get_optional_current_app_user, None)
        if had_identity:
            overrides[get_verified_firebase_identity] = previous_identity
        else:
            overrides.pop(get_verified_firebase_identity, None)
        if had_verified:
            overrides[require_verified_user] = previous_verified
        else:
            overrides.pop(require_verified_user, None)


def create_venue_via_api(client: TestClient, admin_user_id: str) -> dict:
    del client
    from backend.schemas import VenueCreate, VenueRead
    from backend.services.venue_service import create_venue_record

    payload = {
        "address_line_1": "123 Boundary Ave",
        "approved_by_user_id": admin_user_id,
        "city": "Chicago",
        "country_code": "US",
        "created_by_user_id": admin_user_id,
        "is_active": True,
        "name": "Boundary Field",
        "postal_code": "60601",
        "state": "IL",
        "venue_status": "approved",
    }
    with SessionLocal() as db:
        venue = create_venue_record(db, VenueCreate.model_validate(payload))
        return VenueRead.model_validate(venue).model_dump(mode="json")


def create_game_via_api(client: TestClient, admin_user_id: str, venue: dict) -> dict:
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
        "title": "Boundary Match",
        "total_spots": 10,
        "venue_id": venue["id"],
        "waitlist_enabled": True,
    }
    response = run_client_as_user(
        client,
        admin_user_id,
        lambda: client.post("/games", json=payload),
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_game_participant_via_api(
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
        "display_name_snapshot": "Boundary User",
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


def create_game_chat_via_api(
    client: TestClient,
    admin_user_id: str,
    game_id: str,
) -> dict:
    del client
    from backend.schemas import GameChatCreate, GameChatRead
    from backend.services.game_chat_service import create_game_chat_record

    with SessionLocal() as db:
        admin_user = db.get(User, UUID(admin_user_id))
        assert admin_user is not None
        game_chat = create_game_chat_record(
            db,
            GameChatCreate.model_validate(
                {"chat_status": "active", "game_id": game_id},
            ),
            admin_user,
        )
        return GameChatRead.model_validate(game_chat).model_dump(mode="json")


def create_sub_post_via_api(
    client: TestClient,
    owner_user_id: str,
    **overrides: object,
) -> dict:
    authenticate_client_as(client, owner_user_id)
    response = client.post(
        "/need-a-sub/posts",
        json=build_sub_post_payload(**overrides),
    )
    assert response.status_code == 201, response.text
    return response.json()


def bulk_create_active_users(count: int) -> list[str]:
    user_ids: list[str] = []
    with SessionLocal() as db:
        for index in range(count):
            suffix = unique_suffix()
            user_id = uuid4()
            db.add(
                User(
                    id=user_id,
                    auth_user_id=f"firebase-boundary-{suffix}",
                    email=f"boundary-{suffix}@example.com",
                    phone=f"+1555{suffix[:7]}",
                    first_name="Boundary",
                    last_name=f"User {index}",
                    date_of_birth=date(1995, 1, 1),
                    home_city="Chicago",
                    home_state="IL",
                )
            )
            user_ids.append(str(user_id))
        db.commit()
    return user_ids


def platform_notice_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "audience_type": "all_eligible_users",
        "idempotency_key": f"platform-notice-{unique_suffix()}",
        "message": "Pickup Lane source-owned boundary notice.",
        "selected_user_ids": [],
        "title": "Boundary notice",
    }
    payload.update(overrides)
    return payload


def assert_stable_error(response, *, status_code: int) -> dict:
    assert response.status_code == status_code, response.text
    body = response.json()
    assert "code" in body
    assert "message" in body
    assert "correlation_id" in body
    return body


def create_single_position_sub_post(client: TestClient, owner_user_id: str) -> dict:
    return create_sub_post_via_api(
        client,
        owner_user_id,
        subs_needed=1,
        positions=[
            {
                "position_label": "field_player",
                "player_group": "men",
                "spots_needed": 1,
                "sort_order": 0,
            }
        ],
    )


def get_first_sub_post_position_id(sub_post_id: str) -> str:
    with SessionLocal() as db:
        position = db.scalar(
            select(SubPostPosition)
            .where(SubPostPosition.sub_post_id == UUID(sub_post_id))
            .order_by(SubPostPosition.sort_order.asc(), SubPostPosition.id.asc())
        )
        assert position is not None
        return str(position.id)


def create_game_chat_fixture(client: TestClient) -> tuple[dict, dict]:
    admin = create_admin_user(client)
    player = create_user(client)
    venue = create_venue_via_api(client, admin["id"])
    game = create_game_via_api(client, admin["id"], venue)
    create_game_participant_via_api(client, admin["id"], player["id"], game["id"])
    chat = create_game_chat_via_api(client, admin["id"], game["id"])
    return player, chat


def create_sub_post_chat_fixture(client: TestClient) -> tuple[dict, dict, dict]:
    owner = create_user(client)
    sub_post = create_single_position_sub_post(client, owner["id"])
    authenticate_client_as(client, owner["id"])
    response = client.post(f"/need-a-sub/posts/{sub_post['id']}/chat", json={})
    assert response.status_code == 200, response.text
    return owner, sub_post, response.json()


def seed_game_chat_messages(
    *,
    chat_id: str,
    sender_user_id: str,
    count: int,
    start_index: int = 0,
) -> None:
    base_time = datetime.now(UTC) - timedelta(hours=2)
    with SessionLocal() as db:
        for index in range(start_index, start_index + count):
            db.add(
                ChatMessage(
                    id=uuid4(),
                    chat_id=UUID(chat_id),
                    sender_user_id=UUID(sender_user_id),
                    message_type="text",
                    message_body=f"game history message {index}",
                    visibility_status="visible",
                    review_status="clear",
                    is_pinned=False,
                    created_at=base_time + timedelta(seconds=index),
                    updated_at=base_time + timedelta(seconds=index),
                )
            )
        db.commit()


def seed_sub_chat_messages(
    *,
    chat_id: str,
    sender_user_id: str,
    count: int,
    start_index: int = 0,
) -> None:
    base_time = datetime.now(UTC) - timedelta(hours=2)
    with SessionLocal() as db:
        for index in range(start_index, start_index + count):
            db.add(
                SubPostChatMessage(
                    id=uuid4(),
                    chat_id=UUID(chat_id),
                    sender_user_id=UUID(sender_user_id),
                    sender_display_name_snapshot="Boundary User",
                    sender_initials_snapshot="BU",
                    message_type="text",
                    message_body=f"need a sub history message {index}",
                    visibility_status="visible",
                    review_status="clear",
                    created_at=base_time + timedelta(seconds=index),
                    updated_at=base_time + timedelta(seconds=index),
                )
            )
        db.commit()


def mock_saved_card_sync(
    monkeypatch: pytest.MonkeyPatch,
    *,
    customer_id: str,
    fingerprint: str,
    payment_method_id: str,
    detached: list[str] | None = None,
) -> None:
    def fake_retrieve_setup_intent(setup_intent_id):
        return StripeSetupIntentResult(
            id=setup_intent_id,
            client_secret=None,
            status="succeeded",
            customer_id=customer_id,
            payment_method_id=payment_method_id,
        )

    def fake_retrieve_payment_method(stripe_payment_method_id):
        return StripePaymentMethodCardResult(
            id=str(stripe_payment_method_id),
            customer_id=customer_id,
            card_fingerprint=fingerprint,
            card_brand="visa",
            card_last4="4242",
            exp_month=12,
            exp_year=2030,
        )

    monkeypatch.setattr(
        "backend.services.payment_method_service.retrieve_setup_intent",
        fake_retrieve_setup_intent,
    )
    monkeypatch.setattr(
        "backend.services.payment_method_service.retrieve_payment_method",
        fake_retrieve_payment_method,
    )
    monkeypatch.setattr(
        "backend.services.payment_method_service.set_customer_default_payment_method",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "backend.services.payment_method_service.detach_payment_method",
        lambda stripe_payment_method_id: None,
    )
    monkeypatch.setattr(
        "backend.services.payment_method_service.detach_unpersisted_payment_method",
        (
            lambda stripe_payment_method_id: detached.append(
                str(stripe_payment_method_id)
            )
        )
        if detached is not None
        else (lambda stripe_payment_method_id: None),
    )


def active_saved_card_count(user_id: str) -> int:
    with SessionLocal() as db:
        return db.scalar(
            select(func.count())
            .select_from(UserPaymentMethod)
            .where(
                UserPaymentMethod.user_id == UUID(user_id),
                UserPaymentMethod.method_status == "active",
            )
        ) or 0


def fake_r2_storage(
    monkeypatch: pytest.MonkeyPatch,
    *,
    object_size: int | None = None,
    content_type: str | None = None,
) -> None:
    monkeypatch.setattr(
        "backend.services.venue_image_service.get_r2_storage_config",
        lambda: SimpleNamespace(
            account_id="boundary-account",
            allowed_image_types=APPROVED_IMAGE_TYPES,
            bucket_name="boundary-bucket",
            max_image_bytes=APPROVED_IMAGE_SIZE_BYTES,
        ),
    )
    monkeypatch.setattr(
        "backend.services.venue_image_service.create_object_read_url",
        lambda object_key: f"/media/{object_key}",
    )
    monkeypatch.setattr(
        "backend.services.venue_image_service.create_object_upload_url",
        lambda **kwargs: SimpleNamespace(
            upload_url="/uploads/venue-image",
            upload_headers={"Content-Type": kwargs["content_type"]},
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        ),
    )
    monkeypatch.setattr(
        "backend.services.venue_image_service.get_object_properties",
        lambda object_key: SimpleNamespace(
            content_type=content_type or "image/jpeg",
            size_bytes=(
                object_size
                if object_size is not None
                else APPROVED_IMAGE_SIZE_BYTES
            ),
            etag="boundary-etag",
        ),
    )


def test_platform_notice_selected_audience_accepts_500_and_keeps_recipient_paging(
    client: TestClient,
):
    admin = create_admin_user(client)
    selected_user_ids = bulk_create_active_users(MAX_SELECTED_PLATFORM_NOTICE_USERS)
    authenticate_client_as(client, admin["id"])
    payload = platform_notice_payload(
        audience_type="selected_users",
        selected_user_ids=selected_user_ids,
    )
    compact_payload_size = len(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )

    assert compact_payload_size < DEFAULT_PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES

    response = client.post(
        "/admin/platform-notices",
        json=payload,
    )

    assert response.status_code == 201, response.text
    notice = response.json()["notice"]
    assert notice["selected_recipient_count"] == MAX_SELECTED_PLATFORM_NOTICE_USERS
    assert model_count(PlatformNotice) == 1
    assert model_count(PlatformNoticeRecipient) == MAX_SELECTED_PLATFORM_NOTICE_USERS
    assert model_count(Notification) == 0

    default_page_response = client.get(
        f"/admin/platform-notices/{notice['id']}/recipients"
    )
    max_page_response = client.get(
        f"/admin/platform-notices/{notice['id']}/recipients",
        params={"limit": 100},
    )
    too_large_page_response = client.get(
        f"/admin/platform-notices/{notice['id']}/recipients",
        params={"limit": 101},
    )

    assert default_page_response.status_code == 200, default_page_response.text
    default_page = default_page_response.json()
    assert len(default_page["recipients"]) == 50
    assert default_page["limit"] == 50
    assert default_page["has_more"] is True
    assert max_page_response.status_code == 200, max_page_response.text
    max_page = max_page_response.json()
    assert len(max_page["recipients"]) == 100
    assert max_page["limit"] == 100
    assert max_page["has_more"] is True
    assert_stable_error(too_large_page_response, status_code=422)


def test_platform_notice_selected_audience_rejects_501_before_mutation(
    client: TestClient,
):
    admin = create_admin_user(client)
    selected_user_ids = [
        str(uuid4()) for _ in range(MAX_SELECTED_PLATFORM_NOTICE_USERS + 1)
    ]
    authenticate_client_as(client, admin["id"])

    response = client.post(
        "/admin/platform-notices",
        json=platform_notice_payload(
            audience_type="selected_users",
            selected_user_ids=selected_user_ids,
        ),
    )

    body = assert_stable_error(response, status_code=400)
    assert str(MAX_SELECTED_PLATFORM_NOTICE_USERS) in response.text
    assert "selected_user_ids" in response.text
    assert body["message"]
    assert model_count(PlatformNotice) == 0
    assert model_count(PlatformNoticeRecipient) == 0
    assert model_count(Notification) == 0


def test_platform_notice_selected_audience_dedupes_and_rejects_ineligible_users(
    client: TestClient,
):
    admin = create_admin_user(client)
    recipient = create_user(client)
    ineligible_user = create_user(client)
    set_user_account_status(ineligible_user["id"], "suspended")
    authenticate_client_as(client, admin["id"])

    duplicate_response = client.post(
        "/admin/platform-notices",
        json=platform_notice_payload(
            audience_type="selected_users",
            selected_user_ids=[recipient["id"]]
            * (MAX_SELECTED_PLATFORM_NOTICE_USERS + 1),
        ),
    )

    assert duplicate_response.status_code == 201, duplicate_response.text
    assert duplicate_response.json()["notice"]["selected_recipient_count"] == 1
    assert model_count(PlatformNoticeRecipient) == 1

    ineligible_response = client.post(
        "/admin/platform-notices",
        json=platform_notice_payload(
            audience_type="selected_users",
            selected_user_ids=[ineligible_user["id"]],
        ),
    )

    assert_stable_error(ineligible_response, status_code=422)
    assert "selected_user_ineligible" in ineligible_response.text
    assert model_count(PlatformNotice) == 1
    assert model_count(PlatformNoticeRecipient) == 1


def test_platform_notice_field_history_and_cancellation_limits(client: TestClient):
    admin = create_admin_user(client)
    authenticate_client_as(client, admin["id"])

    exact_response = client.post(
        "/admin/platform-notices",
        json=platform_notice_payload(
            title="T" * 150,
            message="M" * 4000,
        ),
    )
    assert exact_response.status_code == 201, exact_response.text

    long_title_response = client.post(
        "/admin/platform-notices",
        json=platform_notice_payload(title="T" * 151),
    )
    long_message_response = client.post(
        "/admin/platform-notices",
        json=platform_notice_payload(message="M" * 4001),
    )
    exact_search_response = client.get(
        "/admin/platform-notices",
        params={"search": "a" * 200},
    )
    long_search_response = client.get(
        "/admin/platform-notices",
        params={"search": "a" * 201},
    )
    exact_history_limit_response = client.get(
        "/admin/platform-notices",
        params={"limit": 30},
    )
    long_history_limit_response = client.get(
        "/admin/platform-notices",
        params={"limit": 31},
    )

    assert_stable_error(long_title_response, status_code=422)
    assert_stable_error(long_message_response, status_code=422)
    assert exact_search_response.status_code == 200, exact_search_response.text
    assert_stable_error(long_search_response, status_code=422)
    assert exact_history_limit_response.status_code == 200
    assert_stable_error(long_history_limit_response, status_code=422)

    cancel_notice = client.post(
        "/admin/platform-notices",
        json=platform_notice_payload(title="Cancellation boundary"),
    ).json()["notice"]
    exact_cancel_response = client.post(
        f"/admin/platform-notices/{cancel_notice['id']}/cancel",
        json={"cancellation_reason": "R" * 1000},
    )
    assert exact_cancel_response.status_code == 200, exact_cancel_response.text

    second_notice = client.post(
        "/admin/platform-notices",
        json=platform_notice_payload(title="Long cancellation boundary"),
    ).json()["notice"]
    long_cancel_response = client.post(
        f"/admin/platform-notices/{second_notice['id']}/cancel",
        json={"cancellation_reason": "R" * 1001},
    )
    assert_stable_error(long_cancel_response, status_code=422)


def test_need_a_sub_public_cards_use_approved_pagination_boundaries(
    client: TestClient,
):
    starts_on = (datetime.now(UTC) + timedelta(days=7)).date().isoformat()

    default_response = client.get(
        "/need-a-sub/posts/cards",
        params={"starts_on": starts_on},
    )
    max_response = client.get(
        "/need-a-sub/posts/cards",
        params={"starts_on": starts_on, "limit": SUB_POST_CARD_MAX_LIMIT},
    )
    capped_response = client.get(
        "/need-a-sub/posts/cards",
        params={"starts_on": starts_on, "limit": 500},
    )
    rejected_min_response = client.get(
        "/need-a-sub/posts/cards",
        params={"starts_on": starts_on, "limit": 0},
    )
    invalid_cursor_response = client.get(
        "/need-a-sub/posts/cards",
        params={"starts_on": starts_on, "cursor": "x" * 2000},
    )
    oversized_cursor_response = client.get(
        "/need-a-sub/posts/cards",
        params={"starts_on": starts_on, "cursor": "x" * 2001},
    )

    assert default_response.status_code == 200, default_response.text
    assert default_response.json()["limit"] == SUB_POST_CARD_DEFAULT_LIMIT
    assert max_response.status_code == 200, max_response.text
    assert max_response.json()["limit"] == SUB_POST_CARD_MAX_LIMIT
    assert capped_response.status_code == 200, capped_response.text
    assert capped_response.json()["limit"] == SUB_POST_CARD_MAX_LIMIT
    assert_stable_error(rejected_min_response, status_code=422)
    assert_stable_error(invalid_cursor_response, status_code=400)
    assert_stable_error(oversized_cursor_response, status_code=422)


def test_need_a_sub_position_schema_and_total_substitute_boundaries(
    client: TestClient,
):
    six_positions_payload = build_sub_post_payload(
        subs_needed=6,
        positions=[
            {
                "position_label": "field_player",
                "player_group": "men",
                "spots_needed": 1,
                "sort_order": index,
            }
            for index in range(MAX_SUB_POST_POSITION_ROWS)
        ],
    )
    SubPostCreate.model_validate(six_positions_payload)

    with pytest.raises(ValidationError):
        SubPostCreate.model_validate(
            build_sub_post_payload(
                subs_needed=7,
                positions=[
                    {
                        "position_label": "field_player",
                        "player_group": "men",
                        "spots_needed": 1,
                        "sort_order": index,
                    }
                    for index in range(MAX_SUB_POST_POSITION_ROWS + 1)
                ],
            )
        )

    owner = create_user(client)
    accepted_response = client.post(
        "/need-a-sub/posts",
        json=build_sub_post_payload(
            subs_needed=11,
            positions=[
                {
                    "position_label": "field_player",
                    "player_group": "men",
                    "spots_needed": 6,
                    "sort_order": 0,
                },
                {
                    "position_label": "field_player",
                    "player_group": "women",
                    "spots_needed": 5,
                    "sort_order": 1,
                },
            ],
        ),
    )
    assert accepted_response.status_code == 401

    authenticate_client_as(client, owner["id"])
    accepted_response = client.post(
        "/need-a-sub/posts",
        json=build_sub_post_payload(
            subs_needed=11,
            positions=[
                {
                    "position_label": "field_player",
                    "player_group": "men",
                    "spots_needed": 6,
                    "sort_order": 0,
                },
                {
                    "position_label": "field_player",
                    "player_group": "women",
                    "spots_needed": 5,
                    "sort_order": 1,
                },
            ],
        ),
    )
    assert accepted_response.status_code == 201, accepted_response.text
    assert accepted_response.json()["subs_needed"] == 11

    rejected_response = client.post(
        "/need-a-sub/posts",
        json=build_sub_post_payload(
            subs_needed=12,
            positions=[
                {
                    "position_label": "field_player",
                    "player_group": "men",
                    "spots_needed": 6,
                    "sort_order": 0,
                },
                {
                    "position_label": "field_player",
                    "player_group": "women",
                    "spots_needed": 6,
                    "sort_order": 1,
                },
            ],
        ),
    )
    duplicate_response = client.post(
        "/need-a-sub/posts",
        json=build_sub_post_payload(
            starts_at=(datetime.now(UTC) + timedelta(days=8)).isoformat(),
            ends_at=(datetime.now(UTC) + timedelta(days=8, hours=2)).isoformat(),
            positions=[
                {
                    "position_label": "field_player",
                    "player_group": "men",
                    "spots_needed": 1,
                    "sort_order": 0,
                },
                {
                    "position_label": "field_player",
                    "player_group": "men",
                    "spots_needed": 1,
                    "sort_order": 1,
                },
            ],
        ),
    )

    assert_stable_error(rejected_response, status_code=422)
    assert_stable_error(duplicate_response, status_code=400)
    assert "unique" in duplicate_response.text


def test_need_a_sub_waitlist_rejects_twenty_sixth_waitlisted_request(
    client: TestClient,
):
    owner = create_user(client)
    sub_post = create_single_position_sub_post(client, owner["id"])
    position_id = get_first_sub_post_position_id(sub_post["id"])

    requesters = [
        create_user(client) for _ in range(MAX_WAITLIST_REQUESTS_PER_POST + 2)
    ]
    responses = []
    for requester in requesters:
        authenticate_client_as(client, requester["id"])
        responses.append(
            client.post(
                f"/need-a-sub/posts/{sub_post['id']}/requests",
                json={"sub_post_position_id": position_id},
            )
        )

    assert responses[0].status_code == 201, responses[0].text
    for response in responses[1:-1]:
        assert response.status_code == 201, response.text
        assert response.json()["request_status"] == "sub_waitlist"
    assert_stable_error(responses[-1], status_code=400)
    assert "waitlist is full" in responses[-1].text

    with SessionLocal() as db:
        waitlist_count = db.scalar(
            select(func.count())
            .select_from(SubPostRequest)
            .where(
                SubPostRequest.sub_post_id == UUID(sub_post["id"]),
                SubPostRequest.request_status == "sub_waitlist",
            )
        )
        assert waitlist_count == MAX_WAITLIST_REQUESTS_PER_POST


def test_saved_cards_allow_five_active_cards_and_reject_sixth_before_db_row(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    user = create_user(client)
    customer_id = f"customer-boundary-{unique_suffix()}"
    for index in range(MAX_ACTIVE_PAYMENT_METHODS - 1):
        create_user_payment_method(
            client,
            user["id"],
            stripe_customer_id=customer_id,
            stripe_payment_method_id=f"payment-method-boundary-{index}-{unique_suffix()}",
            card_fingerprint=f"fingerprint-boundary-{index}-{unique_suffix()}",
            is_default=index == 0,
        )
    create_user_payment_method(
        client,
        user["id"],
        stripe_customer_id=customer_id,
        stripe_payment_method_id=f"detached-boundary-{unique_suffix()}",
        card_fingerprint=f"detached-fingerprint-{unique_suffix()}",
        method_status="detached",
        is_default=False,
        detached_at=datetime.now(UTC),
    )

    mock_saved_card_sync(
        monkeypatch,
        customer_id=customer_id,
        fingerprint=f"fingerprint-boundary-fifth-{unique_suffix()}",
        payment_method_id=f"payment-method-boundary-fifth-{unique_suffix()}",
    )
    authenticate_client_as(client, user["id"])
    fifth_response = client.post(
        "/user-payment-methods/sync",
        json={"setup_intent_id": "setup-intent-boundary-fifth"},
    )

    assert fifth_response.status_code == 201, fifth_response.text
    assert active_saved_card_count(user["id"]) == MAX_ACTIVE_PAYMENT_METHODS

    detached_calls: list[str] = []
    rejected_fingerprint = f"fingerprint-boundary-sixth-{unique_suffix()}"
    mock_saved_card_sync(
        monkeypatch,
        customer_id=customer_id,
        fingerprint=rejected_fingerprint,
        payment_method_id=f"payment-method-boundary-sixth-{unique_suffix()}",
        detached=detached_calls,
    )
    sixth_response = client.post(
        "/user-payment-methods/sync",
        json={"setup_intent_id": "setup-intent-boundary-sixth"},
    )

    assert_stable_error(sixth_response, status_code=400)
    assert str(MAX_ACTIVE_PAYMENT_METHODS) in sixth_response.text
    assert detached_calls
    assert active_saved_card_count(user["id"]) == MAX_ACTIVE_PAYMENT_METHODS
    with SessionLocal() as db:
        rejected_row = db.scalar(
            select(UserPaymentMethod).where(
                UserPaymentMethod.card_fingerprint == rejected_fingerprint
            )
        )
        assert rejected_row is None


def test_game_chat_boundaries_enforce_body_page_and_history_caps(
    client: TestClient,
):
    player, chat = create_game_chat_fixture(client)
    authenticate_client_as(client, player["id"])

    exact_response = client.post(
        "/chat-messages",
        json={"chat_id": chat["id"], "message_body": "G" * MAX_CHAT_MESSAGE_LENGTH},
    )
    long_response = client.post(
        "/chat-messages",
        json={
            "chat_id": chat["id"],
            "message_body": "G" * (MAX_CHAT_MESSAGE_LENGTH + 1),
        },
    )

    assert exact_response.status_code == 201, exact_response.text
    assert_stable_error(long_response, status_code=422)

    seed_game_chat_messages(
        chat_id=chat["id"],
        sender_user_id=player["id"],
        count=MAX_CHAT_MESSAGES_TOTAL - 1,
        start_index=1,
    )
    page_response = client.get(
        "/chat-messages",
        params={"chat_id": chat["id"], "limit": 500},
    )
    history_response = client.post(
        "/chat-messages",
        json={"chat_id": chat["id"], "message_body": "after history cap"},
    )

    assert page_response.status_code == 200, page_response.text
    assert len(page_response.json()) == MAX_CHAT_MESSAGES_PER_PAGE
    assert_stable_error(history_response, status_code=400)
    assert "message limit" in history_response.text
    assert model_count(ChatMessage) == MAX_CHAT_MESSAGES_TOTAL


def test_need_a_sub_chat_boundaries_enforce_body_page_and_history_caps(
    client: TestClient,
):
    owner, _sub_post, chat = create_sub_post_chat_fixture(client)
    authenticate_client_as(client, owner["id"])

    exact_response = client.post(
        f"/need-a-sub/posts/{chat['sub_post_id']}/chat/messages",
        json={"chat_id": chat["id"], "message_body": "S" * MAX_SUB_CHAT_MESSAGE_LENGTH},
    )
    long_response = client.post(
        f"/need-a-sub/posts/{chat['sub_post_id']}/chat/messages",
        json={
            "chat_id": chat["id"],
            "message_body": "S" * (MAX_SUB_CHAT_MESSAGE_LENGTH + 1),
        },
    )

    assert exact_response.status_code == 201, exact_response.text
    assert_stable_error(long_response, status_code=422)

    seed_sub_chat_messages(
        chat_id=chat["id"],
        sender_user_id=owner["id"],
        count=MAX_SUB_CHAT_MESSAGES_TOTAL - 1,
        start_index=1,
    )
    page_response = client.get(
        f"/need-a-sub/posts/{chat['sub_post_id']}/chat/messages",
        params={"limit": 500},
    )
    history_response = client.post(
        f"/need-a-sub/posts/{chat['sub_post_id']}/chat/messages",
        json={"chat_id": chat["id"], "message_body": "after history cap"},
    )

    assert page_response.status_code == 200, page_response.text
    assert len(page_response.json()) == MAX_SUB_CHAT_MESSAGES_PER_PAGE
    assert_stable_error(history_response, status_code=400)
    assert "message limit" in history_response.text
    assert model_count(SubPostChatMessage) == MAX_SUB_CHAT_MESSAGES_TOTAL


def test_venue_image_upload_boundaries_validate_declared_size_and_type(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    fake_r2_storage(monkeypatch)
    admin = create_admin_user(client)
    venue = create_venue_via_api(client, admin["id"])
    authenticate_client_as(client, admin["id"])

    exact_response = client.post(
        f"/admin/venues/{venue['id']}/images/upload-url",
        json={
            "file_name": "boundary.jpg",
            "content_type": "image/jpeg",
            "size_bytes": APPROVED_IMAGE_SIZE_BYTES,
            "image_role": "card",
            "is_primary": True,
        },
    )
    unsupported_type_response = client.post(
        f"/admin/venues/{venue['id']}/images/upload-url",
        json={
            "file_name": "boundary.gif",
            "content_type": "image/gif",
            "size_bytes": 1024,
            "image_role": "gallery",
        },
    )

    upload_authorization_called = False

    def fail_if_upload_authorized(**kwargs):
        nonlocal upload_authorization_called
        upload_authorization_called = True
        raise AssertionError("oversized image should not receive upload authorization")

    monkeypatch.setattr(
        "backend.services.venue_image_service.create_object_upload_url",
        fail_if_upload_authorized,
    )
    oversized_response = client.post(
        f"/admin/venues/{venue['id']}/images/upload-url",
        json={
            "file_name": "boundary-large.jpg",
            "content_type": "image/jpeg",
            "size_bytes": APPROVED_IMAGE_SIZE_BYTES + 1,
            "image_role": "gallery",
        },
    )

    assert exact_response.status_code == 201, exact_response.text
    assert exact_response.json()["image"]["size_bytes"] == APPROVED_IMAGE_SIZE_BYTES
    assert_stable_error(unsupported_type_response, status_code=400)
    assert_stable_error(oversized_response, status_code=400)
    assert upload_authorization_called is False
    assert model_count(VenueImage) == 1


def test_venue_image_completion_rejects_stored_object_mismatches(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    fake_r2_storage(monkeypatch)
    admin = create_admin_user(client)
    venue = create_venue_via_api(client, admin["id"])
    authenticate_client_as(client, admin["id"])
    upload_response = client.post(
        f"/admin/venues/{venue['id']}/images/upload-url",
        json={
            "file_name": "boundary.jpg",
            "content_type": "image/jpeg",
            "size_bytes": APPROVED_IMAGE_SIZE_BYTES,
            "image_role": "card",
            "is_primary": True,
        },
    )
    assert upload_response.status_code == 201, upload_response.text
    image_id = upload_response.json()["image"]["id"]

    fake_r2_storage(monkeypatch, object_size=APPROVED_IMAGE_SIZE_BYTES - 1)
    size_mismatch_response = client.post(f"/admin/venue-images/{image_id}/complete")
    assert_stable_error(size_mismatch_response, status_code=400)

    fake_r2_storage(monkeypatch, content_type="image/png")
    type_mismatch_response = client.post(f"/admin/venue-images/{image_id}/complete")
    assert_stable_error(type_mismatch_response, status_code=400)

    with SessionLocal() as db:
        venue_image = db.get(VenueImage, UUID(image_id))
        assert venue_image is not None
        assert venue_image.image_status == "pending_upload"
        assert venue_image.upload_completed_at is None
