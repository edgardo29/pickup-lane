from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from backend.tests.support.auth import run_as_temporary_admin
from backend.tests.support.factories import unique_suffix


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
        "policy_mode": "official_standard",
    }
    payload.update(overrides)
    if "total_spots" in overrides and "format_label" not in overrides:
        total_spots = int(payload["total_spots"])
        if total_spots < 10:
            side_size = max(3, total_spots // 2)
            payload["format_label"] = f"{side_size}v{side_size}"

    if (
        payload["game_type"] == "community"
        and "payment_collection_type" not in overrides
    ):
        payload["payment_collection_type"] = "external_host"

    response = run_as_temporary_admin(
        client,
        lambda: client.post("/games", json=payload),
    )

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
    if (
        payload["booking_status"] == "pending_payment"
        and payload.get("expires_at") is None
    ):
        payload["expires_at"] = (
            datetime.now(UTC) + timedelta(minutes=2)
        ).isoformat()

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
        "image_url": (
            f"https://example.com/images/ci-game-image-{unique_suffix()}.jpg"
        ),
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
