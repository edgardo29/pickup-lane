from datetime import UTC, datetime, timedelta
from uuid import UUID
from uuid import uuid4

from fastapi.testclient import TestClient


def unique_suffix() -> str:
    # Generate unique values for fields with database uniqueness constraints
    # such as email, phone, auth_user_id, and provider payment method IDs.
    return uuid4().hex


def create_user(client: TestClient, **overrides: object) -> dict:
    # Helpers create real rows through the API instead of inserting directly,
    # so setup data exercises the same validation as normal requests.
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

    response = client.post("/users", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


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


def authenticate_as(user_id: str) -> None:
    from backend.database import SessionLocal
    from backend.main import app
    from backend.models import User
    from backend.routes.auth_routes import get_current_app_user

    def override_current_user() -> User:
        with SessionLocal() as db:
            db_user = db.get(User, UUID(user_id))
            assert db_user is not None
            return db_user

    app.dependency_overrides[get_current_app_user] = override_current_user


def create_user_settings(client: TestClient, user_id: str, **overrides: object) -> dict:
    payload = {
        "user_id": user_id,
        "selected_city": "Chicago",
        "selected_state": "IL",
    }
    payload.update(overrides)

    response = client.post("/user-settings", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_user_payment_method(
    client: TestClient, user_id: str, **overrides: object
) -> dict:
    payload = {
        "user_id": user_id,
        "provider_payment_method_id": f"pm_{unique_suffix()}",
        "card_brand": "visa",
        "card_last4": "4242",
        "exp_month": 12,
        "exp_year": 2030,
        "is_default": True,
        "is_active": True,
    }
    payload.update(overrides)

    response = client.post("/user-payment-methods", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_venue(client: TestClient, user_id: str, **overrides: object) -> dict:
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

    response = client.post("/venues", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_game(
    client: TestClient, user_id: str, venue: dict, **overrides: object
) -> dict:
    starts_at = datetime.now(UTC) + timedelta(days=7)
    ends_at = starts_at + timedelta(hours=1)
    payload = {
        "game_type": "official",
        "payment_collection_type": "in_app",
        "publish_status": "published",
        "game_status": "scheduled",
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
        "policy_mode": "official_standard",
    }
    payload.update(overrides)
    if (
        payload["game_type"] == "community"
        and "payment_collection_type" not in overrides
    ):
        payload["payment_collection_type"] = "external_host"

    response = client.post("/games", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def build_sub_post_payload(**overrides: object) -> dict:
    starts_at = datetime.now(UTC) + timedelta(days=7)
    ends_at = starts_at + timedelta(hours=2)
    payload = {
        "sport_type": "soccer",
        "format_label": "7v7",
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


def create_booking(client: TestClient, user_id: str, game_id: str) -> dict:
    response = client.post(
        "/bookings",
        json={
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
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_game_participant(
    client: TestClient,
    user_id: str,
    game_id: str,
    booking_id: str | None = None,
    **overrides: object,
) -> dict:
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

    response = client.post("/game-participants", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_waitlist_entry(
    client: TestClient, user_id: str, game_id: str, **overrides: object
) -> dict:
    payload = {
        "game_id": game_id,
        "user_id": user_id,
        "party_size": 1,
        "position": 1,
    }
    payload.update(overrides)

    response = client.post("/waitlist-entries", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


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
        "failure_reason": None,
        "metadata": {"source": "ci"},
    }
    payload.update(overrides)

    response = client.post("/payments", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


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

    response = client.post("/refunds", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_game_chat(client: TestClient, game_id: str, **overrides: object) -> dict:
    payload = {
        "game_id": game_id,
        "chat_status": "active",
    }
    payload.update(overrides)

    response = client.post("/game-chats", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


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
        "message_type": "text",
        "message_body": "CI chat message",
        "is_pinned": False,
        "moderation_status": "visible",
    }
    if sender_user_id is not None:
        payload["sender_user_id"] = sender_user_id
    payload.update(overrides)

    response = client.post("/chat-messages", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_notification(
    client: TestClient,
    user_id: str,
    **overrides: object,
) -> dict:
    payload = {
        "user_id": user_id,
        "notification_type": "admin_notice",
        "title": "CI notification",
        "body": "CI notification body",
        "is_read": False,
    }
    payload.update(overrides)

    response = client.post("/notifications", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_game_status_history(
    client: TestClient,
    game_id: str,
    **overrides: object,
) -> dict:
    payload = {
        "game_id": game_id,
        "old_publish_status": "draft",
        "new_publish_status": "published",
        "old_game_status": "scheduled",
        "new_game_status": "scheduled",
        "change_source": "admin",
        "change_reason": "CI status history row",
    }
    payload.update(overrides)

    response = client.post("/game-status-history", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_booking_status_history(
    client: TestClient,
    booking_id: str,
    **overrides: object,
) -> dict:
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

    response = client.post("/booking-status-history", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_participant_status_history(
    client: TestClient,
    participant_id: str,
    **overrides: object,
) -> dict:
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

    response = client.post("/participant-status-history", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_user_stats(
    client: TestClient,
    user_id: str,
    **overrides: object,
) -> dict:
    payload = {
        "user_id": user_id,
        "games_played_count": 3,
        "games_hosted_completed_count": 1,
        "no_show_count": 0,
        "late_cancel_count": 1,
        "host_cancel_count": 0,
    }
    payload.update(overrides)

    response = client.post("/user-stats", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_admin_action(
    client: TestClient,
    admin_user_id: str,
    **overrides: object,
) -> dict:
    payload = {
        "admin_user_id": admin_user_id,
        "action_type": "suspend_user",
        "reason": "CI admin action row",
        "metadata": {"source": "ci"},
    }
    payload.update(overrides)

    response = client.post("/admin-actions", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


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

    response = client.post("/payment-events", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_policy_document(
    client: TestClient,
    **overrides: object,
) -> dict:
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

    response = client.post("/policy-documents", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_policy_acceptance(
    client: TestClient,
    user_id: str,
    policy_document_id: str,
    **overrides: object,
) -> dict:
    payload = {
        "user_id": user_id,
        "policy_document_id": policy_document_id,
        "ip_address": "127.0.0.1",
        "user_agent": "CI policy acceptance test",
    }
    payload.update(overrides)

    response = client.post("/policy-acceptances", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_booking_policy_acceptance(
    client: TestClient,
    booking_id: str,
    policy_document_id: str,
    **overrides: object,
) -> dict:
    payload = {
        "booking_id": booking_id,
        "policy_document_id": policy_document_id,
    }
    payload.update(overrides)

    response = client.post("/booking-policy-acceptances", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_venue_approval_request(
    client: TestClient,
    submitted_by_user_id: str,
    **overrides: object,
) -> dict:
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

    response = client.post("/venue-approval-requests", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_game_image(
    client: TestClient,
    game_id: str,
    uploaded_by_user_id: str | None = None,
    **overrides: object,
) -> dict:
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

    response = client.post("/game-images", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


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

    response = client.post("/community-game-details", json=payload)

    assert response.status_code == 201, response.text
    return response.json()


def create_host_publish_fee(
    client: TestClient,
    game_id: str,
    host_user_id: str,
    **overrides: object,
) -> dict:
    payload = {
        "game_id": game_id,
        "host_user_id": host_user_id,
        "amount_cents": 0,
        "currency": "USD",
        "fee_status": "waived",
        "waiver_reason": "first_game_free",
    }
    payload.update(overrides)

    response = client.post("/host-publish-fees", json=payload)

    assert response.status_code == 201, response.text
    return response.json()
