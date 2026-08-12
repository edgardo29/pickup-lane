from datetime import UTC, datetime, timedelta
from uuid import UUID
from uuid import uuid4

from fastapi.testclient import TestClient

GAME_CREATE_REQUEST_FIELDS = {
    "allow_guests",
    "custom_rules_text",
    "description",
    "ends_at",
    "environment_type",
    "format_label",
    "game_player_group",
    "game_type",
    "game_notes",
    "host_user_id",
    "is_chat_enabled",
    "max_guests_per_booking",
    "parking_notes",
    "price_per_player_cents",
    "skill_level",
    "starts_at",
    "timezone",
    "title",
    "total_spots",
    "venue_id",
    "waitlist_enabled",
}


def unique_suffix() -> str:
    # Generate unique values for fields with database uniqueness constraints
    # such as email, phone, auth_user_id, and Stripe payment method IDs.
    return uuid4().hex


def create_user(client: TestClient, **overrides: object) -> dict:
    # User scaffolding routes are admin-only. This helper creates setup rows
    # directly so tests for auth/admin routes do not need to bootstrap through
    # the route they are validating.
    del client
    from backend.database import SessionLocal
    from backend.models import User
    from backend.schemas import UserCreate, UserRead

    suffix = unique_suffix()
    payload = {
        "auth_user_id": f"firebase-{suffix}",
        "email": f"user-{suffix}@example.com",
        "phone": f"+1555{suffix[:7]}",
        "first_name": "Test",
        "last_name": "User",
        "date_of_birth": "1995-01-01",
        "home_city": "Chicago",
        "home_state": "IL",
    }
    payload.update(overrides)
    user_payload = UserCreate.model_validate(payload)

    with SessionLocal() as db:
        db_user = User(id=uuid4(), **user_payload.model_dump())
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        return UserRead.model_validate(db_user).model_dump(mode="json")


def set_user_role(user_id: str, role: str) -> None:
    # Some internal roles are server-managed and cannot be set through the
    # public user API, so tests adjust them directly only when validating
    # admin-only behavior.
    from backend.database import SessionLocal
    from backend.models import User

    with SessionLocal() as db:
        db_user = db.get(User, UUID(user_id))
        assert db_user is not None
        db_user.role = role
        db.commit()


def set_user_account_status(user_id: str, account_status: str) -> None:
    from backend.database import SessionLocal
    from backend.models import User

    with SessionLocal() as db:
        db_user = db.get(User, UUID(user_id))
        assert db_user is not None
        db_user.account_status = account_status
        db.commit()


def set_user_hosting_status(user_id: str, hosting_status: str) -> None:
    from backend.database import SessionLocal
    from backend.models import User

    with SessionLocal() as db:
        db_user = db.get(User, UUID(user_id))
        assert db_user is not None
        db_user.hosting_status = hosting_status
        db.commit()


def soft_delete_user(user_id: str) -> None:
    from datetime import UTC, datetime

    from backend.database import SessionLocal
    from backend.models import User

    with SessionLocal() as db:
        db_user = db.get(User, UUID(user_id))
        assert db_user is not None
        db_user.account_status = "deleted"
        db_user.deleted_at = datetime.now(UTC)
        db.commit()


def mark_user_email_verified(user_id: str) -> None:
    from datetime import UTC, datetime

    from backend.database import SessionLocal
    from backend.models import User

    with SessionLocal() as db:
        db_user = db.get(User, UUID(user_id))
        assert db_user is not None
        db_user.email_verified_at = datetime.now(UTC)
        if db_user.hosting_status == "not_eligible":
            db_user.hosting_status = "eligible"
        db.commit()


def authenticate_as(user_id: str, target_app=None) -> None:
    from backend.database import SessionLocal
    from backend.main import app
    from backend.models import User
    from backend.services.auth_service import (
        VerifiedFirebaseIdentity,
        get_current_app_user,
        get_verified_firebase_identity,
        require_verified_user,
    )

    app_with_overrides = target_app or app

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

    app_with_overrides.dependency_overrides[get_current_app_user] = override_current_user
    app_with_overrides.dependency_overrides[get_verified_firebase_identity] = (
        override_firebase_identity
    )
    app_with_overrides.dependency_overrides[require_verified_user] = override_current_user


def run_as_temporary_admin(client: TestClient, request_fn):
    from backend.services.auth_service import (
        get_current_app_user,
        get_verified_firebase_identity,
        require_verified_user,
    )

    app_with_overrides = client.app
    had_previous_override = get_current_app_user in app_with_overrides.dependency_overrides
    previous_override = app_with_overrides.dependency_overrides.get(get_current_app_user)
    had_previous_identity_override = (
        get_verified_firebase_identity in app_with_overrides.dependency_overrides
    )
    previous_identity_override = app_with_overrides.dependency_overrides.get(
        get_verified_firebase_identity
    )
    had_previous_verified_override = (
        require_verified_user in app_with_overrides.dependency_overrides
    )
    previous_verified_override = app_with_overrides.dependency_overrides.get(
        require_verified_user
    )
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    authenticate_as(admin["id"], target_app=app_with_overrides)

    try:
        return request_fn()
    finally:
        if had_previous_override and previous_override is not None:
            app_with_overrides.dependency_overrides[get_current_app_user] = (
                previous_override
            )
        else:
            app_with_overrides.dependency_overrides.pop(get_current_app_user, None)
        if had_previous_identity_override and previous_identity_override is not None:
            app_with_overrides.dependency_overrides[get_verified_firebase_identity] = (
                previous_identity_override
            )
        else:
            app_with_overrides.dependency_overrides.pop(get_verified_firebase_identity, None)
        if had_previous_verified_override and previous_verified_override is not None:
            app_with_overrides.dependency_overrides[require_verified_user] = (
                previous_verified_override
            )
        else:
            app_with_overrides.dependency_overrides.pop(require_verified_user, None)


def get_money_as_admin(client: TestClient, path: str):
    return run_as_temporary_admin(client, lambda: client.get(path))


def get_roster_as_admin(client: TestClient, path: str):
    return run_as_temporary_admin(client, lambda: client.get(path))


def create_user_settings(client: TestClient, user_id: str, **overrides: object) -> dict:
    del client
    from backend.database import SessionLocal
    from backend.schemas import UserSettingsCreate, UserSettingsRead
    from backend.services.user_settings_service import create_user_settings_workflow

    payload = {
        "user_id": user_id,
        "selected_city": "Chicago",
        "selected_state": "IL",
    }
    payload.update(overrides)

    with SessionLocal() as db:
        user_settings = create_user_settings_workflow(
            db,
            UserSettingsCreate.model_validate(payload),
        )
        return UserSettingsRead.model_validate(user_settings).model_dump(mode="json")


def create_user_payment_method(
    client: TestClient, user_id: str, **overrides: object
) -> dict:
    from datetime import UTC, datetime

    from backend.database import SessionLocal
    from backend.models import User, UserPaymentMethod

    suffix = unique_suffix()
    defaults = {
        "stripe_customer_id": f"cus_{suffix}",
        "stripe_payment_method_id": f"pm_{suffix}",
        "card_fingerprint": f"fp_{suffix}",
        "card_brand": "visa",
        "card_last4": "4242",
        "exp_month": 12,
        "exp_year": 2030,
        "method_status": "active",
        "is_default": True,
        "detached_at": None,
    }
    defaults.update(overrides)

    with SessionLocal() as db:
        db_user = db.get(User, UUID(user_id))
        assert db_user is not None
        payment_method_id = uuid4()
        db_user.stripe_customer_id = str(defaults["stripe_customer_id"])
        payment_method = UserPaymentMethod(
            id=payment_method_id,
            user_id=UUID(user_id),
            stripe_customer_id=str(defaults["stripe_customer_id"]),
            stripe_payment_method_id=str(defaults["stripe_payment_method_id"]),
            card_fingerprint=str(defaults["card_fingerprint"]),
            card_brand=str(defaults["card_brand"]),
            card_last4=str(defaults["card_last4"]),
            exp_month=int(defaults["exp_month"]),
            exp_year=int(defaults["exp_year"]),
            method_status=str(defaults["method_status"]),
            is_default=bool(defaults["is_default"]),
            detached_at=defaults["detached_at"],
            updated_at=datetime.now(UTC),
        )
        db.add(db_user)
        db.add(payment_method)
        db.commit()

    return {
        "id": str(payment_method_id),
        "user_id": user_id,
        **defaults,
        "created_at": None,
        "updated_at": None,
    }


def mock_checkout_payment_method_verification(
    monkeypatch,
    payment_method: dict,
    **overrides: object,
) -> None:
    from backend.services.stripe_service import StripePaymentMethodCardResult

    values = {
        "id": payment_method["stripe_payment_method_id"],
        "customer_id": payment_method["stripe_customer_id"],
        "card_fingerprint": payment_method["card_fingerprint"],
        "card_brand": payment_method["card_brand"],
        "card_last4": payment_method["card_last4"],
        "exp_month": payment_method["exp_month"],
        "exp_year": payment_method["exp_year"],
    }
    values.update(overrides)

    def fake_retrieve_payment_method(stripe_payment_method_id):
        return StripePaymentMethodCardResult(
            id=str(stripe_payment_method_id),
            customer_id=str(values["customer_id"]),
            card_fingerprint=str(values["card_fingerprint"]),
            card_brand=str(values["card_brand"]),
            card_last4=str(values["card_last4"]),
            exp_month=int(values["exp_month"]),
            exp_year=int(values["exp_year"]),
        )

    monkeypatch.setattr(
        "backend.services.payment_method_service.retrieve_payment_method",
        fake_retrieve_payment_method,
    )


def create_venue(client: TestClient, user_id: str, **overrides: object) -> dict:
    del client
    from backend.database import SessionLocal
    from backend.schemas import VenueCreate, VenueRead
    from backend.services.venue_service import create_venue_record

    payload = {
        "name": "CI Test Field",
        "address_line_1": "123 Test Ave",
        "city": "Chicago",
        "state": "IL",
        "postal_code": "60601",
        "country_code": "US",
        "venue_status": "approved",
        "created_by_user_id": user_id,
        "approved_by_user_id": user_id,
        "is_active": True,
    }
    payload.update(overrides)

    with SessionLocal() as db:
        venue = create_venue_record(db, VenueCreate.model_validate(payload))
        return VenueRead.model_validate(venue).model_dump(mode="json")


def create_game(
    client: TestClient, user_id: str, venue: dict, **overrides: object
) -> dict:
    starts_at = datetime.now(UTC) + timedelta(days=7)
    ends_at = starts_at + timedelta(hours=1)
    payload = {
        "game_type": "official",
        "payment_collection_type": "in_app",
        "publish_status": "published",
        "game_status": "active",
        "title": "CI Test Match",
        "venue_id": venue["id"],
        "venue_name_snapshot": venue["name"],
        "address_snapshot": venue["address_line_1"],
        "city_snapshot": venue["city"],
        "state_snapshot": venue["state"],
        "created_by_user_id": user_id,
        "starts_at": starts_at.isoformat(),
        "ends_at": ends_at.isoformat(),
        "timezone": "America/Chicago",
        "sport_type": "soccer",
        "format_label": "5v5",
        "environment_type": "indoor",
        "total_spots": 10,
        "price_per_player_cents": 1200,
        "currency": "USD",
        "allow_guests": True,
        "max_guests_per_booking": 2,
        "waitlist_enabled": True,
        "is_chat_enabled": True,
    }
    request_overrides = {
        key: value for key, value in overrides.items() if key in GAME_CREATE_REQUEST_FIELDS
    }
    seeded_overrides = {
        key: value for key, value in overrides.items() if key not in GAME_CREATE_REQUEST_FIELDS
    }
    payload.update(request_overrides)
    if "total_spots" in overrides and "format_label" not in overrides:
        total_spots = int(payload["total_spots"])
        if total_spots < 10:
            side_size = max(3, total_spots // 2)
            payload["format_label"] = f"{side_size}v{side_size}"
    payload = {key: value for key, value in payload.items() if key in GAME_CREATE_REQUEST_FIELDS}

    response = run_as_temporary_admin(
        client,
        lambda: client.post("/games", json=payload),
    )

    assert response.status_code == 201, response.text
    game = response.json()
    seeded_overrides.setdefault("created_by_user_id", user_id)
    return apply_seeded_game_overrides(game["id"], seeded_overrides)


def apply_seeded_game_overrides(game_id: str, overrides: dict[str, object]) -> dict:
    if not overrides:
        return {}

    from backend.database import SessionLocal
    from backend.models import Game
    from backend.schemas import GameRead

    now = datetime.now(UTC)
    with SessionLocal() as db:
        db_game = db.get(Game, UUID(game_id))
        assert db_game is not None

        for field_name, value in overrides.items():
            assert hasattr(db_game, field_name), field_name
            setattr(db_game, field_name, value)

        if db_game.publish_status == "published" and db_game.published_at is None:
            db_game.published_at = now
        if db_game.publish_status != "published":
            db_game.published_at = None

        if db_game.game_status == "cancelled":
            db_game.cancelled_at = db_game.cancelled_at or now
            db_game.cancellation_source = db_game.cancellation_source or "host"
            db_game.completed_at = None
            db_game.completed_by_user_id = None
        elif db_game.game_status == "completed":
            db_game.completed_at = db_game.completed_at or now
            db_game.cancelled_at = None
            db_game.cancelled_by_user_id = None
            db_game.cancellation_source = None
            db_game.cancel_reason = None
        else:
            db_game.cancelled_at = None
            db_game.cancelled_by_user_id = None
            db_game.cancellation_source = None
            db_game.cancel_reason = None
            db_game.completed_at = None
            db_game.completed_by_user_id = None

        db.commit()
        db.refresh(db_game)
        return GameRead.model_validate(db_game).model_dump(mode="json")


def build_sub_post_payload(**overrides: object) -> dict:
    starts_at = (
        datetime.now(UTC)
        .replace(hour=18, minute=0, second=0, microsecond=0)
        + timedelta(days=7)
    )
    ends_at = starts_at + timedelta(hours=2)
    payload = {
        "sport_type": "soccer",
        "format_label": "7v7",
        "environment_type": "outdoor",
        "skill_level": "intermediate",
        "game_player_group": "coed",
        "team_name": "CI FC",
        "starts_at": starts_at.isoformat(),
        "ends_at": ends_at.isoformat(),
        "timezone": "America/Chicago",
        "location_name": "CI Test Field",
        "address_line_1": "123 Test Ave",
        "city": "Chicago",
        "state": "IL",
        "postal_code": "60601",
        "country_code": "US",
        "neighborhood": "Loop",
        "subs_needed": 2,
        "price_due_at_venue_cents": 0,
        "currency": "USD",
        "payment_note": None,
        "notes": "Bring a light and dark shirt.",
        "positions": [
            {
                "position_label": "field_player",
                "player_group": "men",
                "spots_needed": 1,
                "sort_order": 0,
            },
            {
                "position_label": "field_player",
                "player_group": "women",
                "spots_needed": 1,
                "sort_order": 1,
            },
        ],
    }
    payload.update(overrides)
    return payload


def create_sub_post(client: TestClient, owner_user_id: str, **overrides: object) -> dict:
    authenticate_as(owner_user_id)
    response = client.post("/need-a-sub/posts", json=build_sub_post_payload(**overrides))

    assert response.status_code == 201, response.text
    return response.json()


def create_booking(
    client: TestClient, user_id: str, game_id: str, **overrides: object
) -> dict:
    del client
    from backend.database import SessionLocal
    from backend.schemas import BookingCreate, BookingRead
    from backend.services.booking_service import create_booking_workflow

    payload = {
        "game_id": game_id,
        "buyer_user_id": user_id,
        "booking_status": "confirmed",
        "payment_status": "paid",
        "participant_count": 1,
        "subtotal_cents": 1200,
        "platform_fee_cents": 100,
        "discount_cents": 0,
        "total_cents": 1300,
        "currency": "USD",
        "price_per_player_snapshot_cents": 1200,
        "platform_fee_snapshot_cents": 100,
    }
    payload.update(overrides)
    if payload["booking_status"] == "pending_payment" and payload.get("expires_at") is None:
        payload["expires_at"] = (datetime.now(UTC) + timedelta(minutes=2)).isoformat()

    with SessionLocal() as db:
        booking = create_booking_workflow(db, BookingCreate.model_validate(payload))
        return BookingRead.model_validate(booking).model_dump(mode="json")


def create_game_participant(
    client: TestClient,
    user_id: str | None,
    game_id: str,
    booking_id: str | None = None,
    **overrides: object,
) -> dict:
    del client
    from backend.database import SessionLocal
    from backend.schemas import GameParticipantCreate, GameParticipantRead
    from backend.services.game_participant_service import (
        create_game_participant_workflow,
    )

    payload = {
        "game_id": game_id,
        "booking_id": booking_id,
        "participant_type": "registered_user",
        "user_id": user_id,
        "display_name_snapshot": "Test User",
        "participant_status": "confirmed",
        "attendance_status": "unknown",
        "cancellation_type": "none",
        "price_cents": 1200,
        "currency": "USD",
        "roster_order": 1,
    }
    payload.update(overrides)

    with SessionLocal() as db:
        participant = create_game_participant_workflow(
            db,
            GameParticipantCreate.model_validate(payload),
        )
        return GameParticipantRead.model_validate(participant).model_dump(mode="json")


def create_waitlist_entry(
    client: TestClient, user_id: str, game_id: str, **overrides: object
) -> dict:
    del client
    from backend.database import SessionLocal
    from backend.schemas import WaitlistEntryCreate, WaitlistEntryRead
    from backend.services.waitlist_entry_service import create_waitlist_entry_workflow

    payload = {
        "game_id": game_id,
        "user_id": user_id,
        "party_size": 1,
        "position": 1,
    }
    payload.update(overrides)

    with SessionLocal() as db:
        waitlist_entry = create_waitlist_entry_workflow(
            db,
            WaitlistEntryCreate.model_validate(payload),
        )
        return WaitlistEntryRead.model_validate(waitlist_entry).model_dump(mode="json")


def create_payment(
    client: TestClient,
    payer_user_id: str,
    booking_id: str | None = None,
    game_id: str | None = None,
    **overrides: object,
) -> dict:
    # Payment helper keeps Stripe-like identifiers unique so repeated tests
    # do not trip database uniqueness constraints.
    suffix = unique_suffix()
    payload = {
        "payer_user_id": payer_user_id,
        "booking_id": booking_id,
        "game_id": game_id,
        "payment_type": "booking",
        "provider": "stripe",
        "provider_payment_intent_id": f"pi_{suffix}",
        "provider_charge_id": None,
        "idempotency_key": f"payment-{suffix}",
        "amount_cents": 1300,
        "currency": "USD",
        "payment_status": "processing",
        "metadata": {"source": "ci"},
    }
    payload.update(overrides)

    from backend.database import SessionLocal
    from backend.models import User
    from backend.schemas import PaymentCreate, PaymentRead
    from backend.services.payment_service import create_payment_record

    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    with SessionLocal() as db:
        admin_user = db.get(User, UUID(admin["id"]))
        assert admin_user is not None
        payment = create_payment_record(
            db,
            admin_user=admin_user,
            payload=PaymentCreate.model_validate(payload),
        )
        return PaymentRead.model_validate(payment).model_dump(mode="json")


def create_refund(
    client: TestClient,
    payment_id: str,
    booking_id: str | None = None,
    participant_id: str | None = None,
    **overrides: object,
) -> dict:
    payload = {
        "payment_id": payment_id,
        "booking_id": booking_id,
        "participant_id": participant_id,
        "provider_refund_id": f"re_{unique_suffix()}",
        "amount_cents": 500,
        "currency": "USD",
        "refund_reason": "player_cancelled",
        "refund_status": "pending",
    }
    payload.update(overrides)

    from backend.database import SessionLocal
    from backend.models import User
    from backend.schemas import RefundCreate, RefundRead
    from backend.services.refund_service import create_refund_record

    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    with SessionLocal() as db:
        admin_user = db.get(User, UUID(admin["id"]))
        assert admin_user is not None
        refund = create_refund_record(
            db,
            admin_user=admin_user,
            payload=RefundCreate.model_validate(payload),
        )
        return RefundRead.model_validate(refund).model_dump(mode="json")


def create_game_chat(client: TestClient, game_id: str, **overrides: object) -> dict:
    from backend.database import SessionLocal
    from backend.models import User
    from backend.schemas import GameChatCreate, GameChatRead
    from backend.services.game_chat_service import create_game_chat_record

    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    payload = {
        "game_id": game_id,
        "chat_status": "active",
    }
    payload.update(overrides)

    with SessionLocal() as db:
        admin_user = db.get(User, UUID(admin["id"]))
        assert admin_user is not None
        game_chat = create_game_chat_record(
            db,
            GameChatCreate.model_validate(payload),
            admin_user,
        )
        return GameChatRead.model_validate(game_chat).model_dump(mode="json")


def create_chat_message(
    client: TestClient,
    chat_id: str,
    sender_user_id: str | None = None,
    **overrides: object,
) -> dict:
    if sender_user_id is not None:
        authenticate_as(sender_user_id)

    payload = {
        "chat_id": chat_id,
        "message_body": "CI chat message",
    }
    payload.update(overrides)

    response = client.post("/chat-messages", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_notification(
    client: TestClient,
    user_id: str,
    **overrides: object,
) -> dict:
    from backend.database import SessionLocal
    from backend.models import User
    from backend.schemas import NotificationCreate, NotificationRead
    from backend.services.notification_service import create_notification_workflow

    authenticate_as(user_id)
    payload = {
        "user_id": user_id,
        "notification_type": "admin_enforcement_notice",
        "notification_category": "app",
        "notification_domain": "admin",
        "source_type": "pickup_lane",
        "title": "CI notification",
        "subject_label": "Pickup Lane",
        "summary": "Pickup Lane posted an update.",
        "body": "CI notification body",
        "event_at": datetime.now(UTC).isoformat(),
        "actor_user_id": None,
        "is_read": False,
    }
    payload.update(overrides)

    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    notification_payload = NotificationCreate.model_validate(payload)

    with SessionLocal() as db:
        admin_user = db.get(User, UUID(admin["id"]))
        assert admin_user is not None
        result = create_notification_workflow(db, notification_payload, admin_user)

    return NotificationRead.model_validate(result).model_dump(mode="json")


def create_game_status_history(
    client: TestClient,
    game_id: str,
    **overrides: object,
) -> dict:
    del client
    from backend.database import SessionLocal
    from backend.schemas import GameStatusHistoryCreate, GameStatusHistoryRead
    from backend.services.status_history_service import create_game_status_history_record

    payload = {
        "game_id": game_id,
        "old_publish_status": "draft",
        "new_publish_status": "published",
        "old_game_status": "active",
        "new_game_status": "active",
        "change_source": "admin",
        "change_reason": "CI status history row",
    }
    payload.update(overrides)

    with SessionLocal() as db:
        history = create_game_status_history_record(
            db,
            GameStatusHistoryCreate.model_validate(payload),
        )
        return GameStatusHistoryRead.model_validate(history).model_dump(mode="json")


def create_booking_status_history(
    client: TestClient,
    booking_id: str,
    **overrides: object,
) -> dict:
    del client
    from backend.database import SessionLocal
    from backend.schemas import (
        BookingStatusHistoryCreate,
        BookingStatusHistoryRead,
    )
    from backend.services.status_history_service import (
        create_booking_status_history_record,
    )

    payload = {
        "booking_id": booking_id,
        "old_booking_status": "pending_payment",
        "new_booking_status": "confirmed",
        "old_payment_status": "processing",
        "new_payment_status": "paid",
        "change_source": "payment_webhook",
        "change_reason": "CI booking status history row",
    }
    payload.update(overrides)

    with SessionLocal() as db:
        history = create_booking_status_history_record(
            db,
            BookingStatusHistoryCreate.model_validate(payload),
        )
        return BookingStatusHistoryRead.model_validate(history).model_dump(mode="json")


def create_participant_status_history(
    client: TestClient,
    participant_id: str,
    **overrides: object,
) -> dict:
    del client
    from backend.database import SessionLocal
    from backend.schemas import (
        ParticipantStatusHistoryCreate,
        ParticipantStatusHistoryRead,
    )
    from backend.services.status_history_service import (
        create_participant_status_history_record,
    )

    payload = {
        "participant_id": participant_id,
        "old_participant_status": "pending_payment",
        "new_participant_status": "confirmed",
        "old_attendance_status": "unknown",
        "new_attendance_status": "attended",
        "change_source": "admin",
        "change_reason": "CI participant status history row",
    }
    payload.update(overrides)

    with SessionLocal() as db:
        history = create_participant_status_history_record(
            db,
            ParticipantStatusHistoryCreate.model_validate(payload),
        )
        return ParticipantStatusHistoryRead.model_validate(history).model_dump(
            mode="json"
        )


def create_user_stats(
    client: TestClient,
    user_id: str,
    **overrides: object,
) -> dict:
    del client
    from backend.database import SessionLocal
    from backend.schemas import UserStatsCreate, UserStatsRead
    from backend.services.user_stats_service import create_user_stats_workflow

    payload = {
        "user_id": user_id,
        "games_played_count": 3,
        "games_hosted_completed_count": 1,
        "no_show_count": 0,
        "late_cancel_count": 1,
        "host_cancel_count": 0,
    }
    payload.update(overrides)

    with SessionLocal() as db:
        user_stats = create_user_stats_workflow(
            db,
            UserStatsCreate.model_validate(payload),
        )
        return UserStatsRead.model_validate(user_stats).model_dump(mode="json")


def create_admin_action(
    client: TestClient,
    admin_user_id: str,
    **overrides: object,
) -> dict:
    del client
    from backend.database import SessionLocal
    from backend.models import User
    from backend.schemas import AdminActionCreate
    from backend.services.admin_action_service import (
        create_admin_action as create_admin_action_record,
        serialize_admin_action_reads,
    )

    payload = {
        "action_type": "suspend_user",
        "reason": "CI admin action row",
        "metadata": {"source": "ci"},
    }
    payload.update(overrides)

    with SessionLocal() as db:
        admin_user = db.get(User, UUID(admin_user_id))
        assert admin_user is not None
        admin_action = create_admin_action_record(
            db,
            admin_user=admin_user,
            payload=AdminActionCreate.model_validate(payload),
        )
        return serialize_admin_action_reads(db, [admin_action])[0].model_dump(
            mode="json"
        )


def create_payment_event(
    client: TestClient,
    **overrides: object,
) -> dict:
    payload = {
        "payment_id": None,
        "provider": "stripe",
        "provider_event_id": f"evt_{unique_suffix()}",
        "event_type": "payment_intent.succeeded",
        "raw_payload": {
            "type": "payment_intent.succeeded",
            "source": "ci",
        },
        "processing_status": "pending",
    }
    payload.update(overrides)

    del client
    from backend.database import SessionLocal
    from backend.schemas import PaymentEventCreate, PaymentEventRead
    from backend.services.payment_event_service import create_payment_event_record

    with SessionLocal() as db:
        payment_event = create_payment_event_record(
            db,
            PaymentEventCreate.model_validate(payload),
        )
        return PaymentEventRead.model_validate(payment_event).model_dump(mode="json")


def create_policy_document(
    client: TestClient,
    **overrides: object,
) -> dict:
    del client
    from backend.database import SessionLocal
    from backend.schemas import PolicyDocumentCreate, PolicyDocumentRead
    from backend.services.policy_document_service import (
        create_policy_document_record,
    )

    payload = {
        "policy_type": "privacy_policy",
        "version": f"v-{unique_suffix()[:8]}",
        "title": "CI Privacy Policy",
        "content_url": None,
        "content_text": "CI policy document content.",
        "effective_at": datetime.now(UTC).isoformat(),
        "is_active": True,
    }
    payload.update(overrides)

    with SessionLocal() as db:
        policy_document = create_policy_document_record(
            db,
            PolicyDocumentCreate.model_validate(payload),
        )
        return PolicyDocumentRead.model_validate(policy_document).model_dump(
            mode="json"
        )


def create_policy_acceptance(
    client: TestClient,
    user_id: str,
    policy_document_id: str,
    **overrides: object,
) -> dict:
    del client
    from backend.database import SessionLocal
    from backend.schemas import PolicyAcceptanceCreate, PolicyAcceptanceRead
    from backend.services.policy_acceptance_service import (
        create_policy_acceptance_record,
    )

    payload = {
        "user_id": user_id,
        "policy_document_id": policy_document_id,
        "ip_address": "127.0.0.1",
        "user_agent": "CI policy acceptance test",
    }
    payload.update(overrides)

    with SessionLocal() as db:
        policy_acceptance = create_policy_acceptance_record(
            db,
            PolicyAcceptanceCreate.model_validate(payload),
        )
        return PolicyAcceptanceRead.model_validate(policy_acceptance).model_dump(
            mode="json"
        )


def create_booking_policy_acceptance(
    client: TestClient,
    booking_id: str,
    policy_document_id: str,
    **overrides: object,
) -> dict:
    del client
    from backend.database import SessionLocal
    from backend.schemas import (
        BookingPolicyAcceptanceCreate,
        BookingPolicyAcceptanceRead,
    )
    from backend.services.booking_policy_acceptance_service import (
        create_booking_policy_acceptance_record,
    )

    payload = {
        "booking_id": booking_id,
        "policy_document_id": policy_document_id,
    }
    payload.update(overrides)

    with SessionLocal() as db:
        acceptance = create_booking_policy_acceptance_record(
            db,
            BookingPolicyAcceptanceCreate.model_validate(payload),
        )
        return BookingPolicyAcceptanceRead.model_validate(acceptance).model_dump(
            mode="json"
        )


def create_venue_approval_request(
    client: TestClient,
    submitted_by_user_id: str,
    **overrides: object,
) -> dict:
    del client
    from backend.database import SessionLocal
    from backend.schemas import (
        VenueApprovalRequestCreate,
        VenueApprovalRequestRead,
    )
    from backend.services.venue_approval_request_service import (
        create_venue_approval_request_record,
    )

    payload = {
        "submitted_by_user_id": submitted_by_user_id,
        "requested_name": "CI Requested Soccer Field",
        "requested_address_line_1": "999 CI Requested Field Ave",
        "requested_city": "Chicago",
        "requested_state": "IL",
        "requested_postal_code": "60601",
        "requested_country_code": "US",
    }
    payload.update(overrides)

    with SessionLocal() as db:
        approval_request = create_venue_approval_request_record(
            db,
            VenueApprovalRequestCreate.model_validate(payload),
        )
        return VenueApprovalRequestRead.model_validate(approval_request).model_dump(
            mode="json"
        )


def create_game_image(
    client: TestClient,
    game_id: str,
    uploaded_by_user_id: str | None = None,
    **overrides: object,
) -> dict:
    del client
    from backend.database import SessionLocal
    from backend.schemas import GameImageCreate, GameImageRead
    from backend.services.game_image_service import create_game_image_record

    payload = {
        "game_id": game_id,
        "uploaded_by_user_id": uploaded_by_user_id,
        "image_url": f"https://example.com/images/ci-game-image-{unique_suffix()}.jpg",
        "image_role": "gallery",
        "image_status": "active",
        "is_primary": False,
        "sort_order": 0,
    }
    payload.update(overrides)

    with SessionLocal() as db:
        game_image = create_game_image_record(
            db,
            GameImageCreate.model_validate(payload),
        )
        return GameImageRead.model_validate(game_image).model_dump(mode="json")


def create_community_game_detail(
    client: TestClient,
    game_id: str,
    **overrides: object,
) -> dict:
    payload = {
        "game_id": game_id,
        "payment_methods_snapshot": [{"type": "venmo", "value": "@pickup-host"}],
        "payment_instructions_snapshot": "Pay the host before kickoff.",
    }
    payload.update(overrides)

    def request():
        response = client.post("/community-game-details", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return run_as_temporary_admin(client, request)


def create_host_publish_fee(
    client: TestClient,
    game_id: str,
    host_user_id: str,
    **overrides: object,
) -> dict:
    del client
    from backend.database import SessionLocal
    from backend.schemas import HostPublishFeeCreate, HostPublishFeeRead
    from backend.services.host_publish_fee_service import create_host_publish_fee_record

    payload = {
        "game_id": game_id,
        "host_user_id": host_user_id,
        "amount_cents": 0,
        "currency": "USD",
        "fee_status": "waived",
        "waiver_reason": "first_game_free",
    }
    payload.update(overrides)

    with SessionLocal() as db:
        host_publish_fee = create_host_publish_fee_record(
            db,
            HostPublishFeeCreate.model_validate(payload),
        )
        return HostPublishFeeRead.model_validate(host_publish_fee).model_dump(
            mode="json"
        )
