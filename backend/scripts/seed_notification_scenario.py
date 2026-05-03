from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import (
    Booking,
    ChatMessage,
    Game,
    GameChat,
    GameParticipant,
    User,
    Venue,
)

DEV_IDS = {
    "notification_user_id": UUID("24242424-2424-4242-8242-242424242424"),
    "notification_admin_id": UUID("25252525-2525-4252-8252-252525252525"),
    "notification_venue_id": UUID("26262626-2626-4262-8262-262626262626"),
    "notification_game_id": UUID("27272727-2727-4272-8272-272727272727"),
    "notification_booking_id": UUID("28282828-2828-4282-8282-282828282828"),
    "notification_participant_id": UUID("29292929-2929-4292-8292-292929292929"),
    "notification_chat_id": UUID("30303030-3030-4303-8303-303030303030"),
    "notification_message_id": UUID("31313131-3131-4313-8313-313131313131"),
}


def upsert_by_id(
    db: Session,
    model: type,
    record_id: UUID,
    values: dict[str, Any],
    lookup_filters: dict[str, Any] | None = None,
) -> Any:
    record = db.get(model, record_id)

    if record is None and lookup_filters:
        statement = select(model)
        for field_name, field_value in lookup_filters.items():
            statement = statement.where(getattr(model, field_name) == field_value)
        record = db.scalars(statement).first()

    if record is None:
        record = model(id=record_id)
        db.add(record)

    for field_name, field_value in values.items():
        setattr(record, field_name, field_value)

    return record


def seed_notification_scenario() -> dict[str, UUID]:
    now = datetime.now(UTC)
    starts_at = now + timedelta(days=7)
    ends_at = starts_at + timedelta(hours=1)

    with SessionLocal() as db:
        user = upsert_by_id(
            db,
            User,
            DEV_IDS["notification_user_id"],
            {
                "auth_user_id": "dev-notification-user",
                "role": "player",
                "email": "dev-notification-user@pickuplane.local",
                "phone": "+15550000008",
                "first_name": "Dev",
                "last_name": "NotificationUser",
                "date_of_birth": date(1995, 1, 1),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "not_eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-notification-user"},
        )
        admin = upsert_by_id(
            db,
            User,
            DEV_IDS["notification_admin_id"],
            {
                "auth_user_id": "dev-notification-admin",
                "role": "admin",
                "email": "dev-notification-admin@pickuplane.local",
                "phone": "+15550000009",
                "first_name": "Dev",
                "last_name": "NotificationAdmin",
                "date_of_birth": date(1990, 3, 15),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-notification-admin"},
        )
        db.flush()

        venue = upsert_by_id(
            db,
            Venue,
            DEV_IDS["notification_venue_id"],
            {
                "name": "Dev Notification Field",
                "address_line_1": "321 Notification Ave",
                "city": "Chicago",
                "state": "IL",
                "postal_code": "60601",
                "country_code": "US",
                "venue_status": "approved",
                "created_by_user_id": admin.id,
                "approved_by_user_id": admin.id,
                "approved_at": now,
                "is_active": True,
                "deleted_at": None,
                "updated_at": now,
            },
        )
        db.flush()

        game = upsert_by_id(
            db,
            Game,
            DEV_IDS["notification_game_id"],
            {
                "game_type": "official",
                "publish_status": "published",
                "game_status": "scheduled",
                "title": "Dev Game Ready For Notifications",
                "venue_id": venue.id,
                "venue_name_snapshot": venue.name,
                "address_snapshot": venue.address_line_1,
                "city_snapshot": venue.city,
                "state_snapshot": venue.state,
                "host_user_id": None,
                "created_by_user_id": admin.id,
                "starts_at": starts_at,
                "ends_at": ends_at,
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
                "published_at": now,
                "cancelled_at": None,
                "completed_at": None,
                "deleted_at": None,
                "updated_at": now,
            },
        )
        db.flush()

        booking = upsert_by_id(
            db,
            Booking,
            DEV_IDS["notification_booking_id"],
            {
                "game_id": game.id,
                "buyer_user_id": user.id,
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
                "booked_at": now,
                "cancelled_at": None,
                "cancelled_by_user_id": None,
                "cancel_reason": None,
                "expires_at": None,
                "updated_at": now,
            },
        )
        db.flush()

        participant = upsert_by_id(
            db,
            GameParticipant,
            DEV_IDS["notification_participant_id"],
            {
                "game_id": game.id,
                "booking_id": booking.id,
                "participant_type": "registered_user",
                "user_id": user.id,
                "guest_name": None,
                "guest_email": None,
                "guest_phone": None,
                "display_name_snapshot": "Dev NotificationUser",
                "participant_status": "confirmed",
                "attendance_status": "unknown",
                "cancellation_type": "none",
                "price_cents": 1200,
                "currency": "USD",
                "roster_order": 1,
                "confirmed_at": now,
                "cancelled_at": None,
                "checked_in_at": None,
                "marked_attendance_by_user_id": None,
                "attendance_decided_at": None,
                "attendance_notes": None,
                "updated_at": now,
            },
            lookup_filters={"game_id": game.id, "user_id": user.id},
        )
        db.flush()

        game_chat = upsert_by_id(
            db,
            GameChat,
            DEV_IDS["notification_chat_id"],
            {
                "game_id": game.id,
                "chat_status": "active",
                "locked_at": None,
                "updated_at": now,
            },
            lookup_filters={"game_id": game.id},
        )
        db.flush()

        chat_message = upsert_by_id(
            db,
            ChatMessage,
            DEV_IDS["notification_message_id"],
            {
                "chat_id": game_chat.id,
                "sender_user_id": admin.id,
                "message_type": "pinned_update",
                "message_body": "Bring both light and dark shirts.",
                "is_pinned": True,
                "pinned_at": now,
                "pinned_by_user_id": admin.id,
                "moderation_status": "visible",
                "edited_at": None,
                "deleted_at": None,
                "deleted_by_user_id": None,
                "updated_at": now,
            },
        )

        db.commit()

        return {
            "notification_user_id": user.id,
            "notification_admin_id": admin.id,
            "notification_venue_id": venue.id,
            "notification_game_id": game.id,
            "notification_booking_id": booking.id,
            "notification_participant_id": participant.id,
            "notification_chat_id": game_chat.id,
            "notification_message_id": chat_message.id,
        }


def main() -> None:
    ids = seed_notification_scenario()

    print("Notification scenario data ready.")
    print("")
    print("Use these IDs in Postman:")
    for label, value in ids.items():
        print(f"{label}: {value}")
    print("")
    print("POST /notifications body:")
    print("{")
    print(f'  "user_id": "{ids["notification_user_id"]}",')
    print('  "notification_type": "chat_message",')
    print('  "title": "New pinned update",')
    print('  "body": "Bring both light and dark shirts.",')
    print(f'  "related_game_id": "{ids["notification_game_id"]}",')
    print(f'  "related_message_id": "{ids["notification_message_id"]}",')
    print('  "is_read": false')
    print("}")


if __name__ == "__main__":
    main()
