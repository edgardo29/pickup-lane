from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from backend.models import Booking, ChatMessage, Game, GameParticipant, Notification, User
from backend.scripts.demo_data.helpers import demo_uuid, now_utc, upsert_by_id
from backend.scripts.demo_data.users import CURRENT_USER_KEY


def seed_notifications(
    db: Session,
    users: dict[str, User],
    games: dict[str, Game],
    bookings: dict[str, Booking],
    participants: dict[str, GameParticipant],
) -> dict[str, Notification]:
    current_user = users[CURRENT_USER_KEY]
    timestamp = now_utc()
    seeded_notifications: dict[str, Notification] = {}

    notification_data = [
        {
            "key": "policy-update",
            "age": timedelta(hours=2),
            "notification_type": "admin_notice",
            "title": "Pickup Lane Updates",
            "body": "New cancellation policy is now live. Tap to learn more.",
            "is_read": False,
        },
        {
            "key": "support-reply",
            "age": timedelta(hours=5),
            "notification_type": "admin_notice",
            "title": "Support",
            "body": "We received your request and will get back to you shortly.",
            "is_read": False,
        },
        {
            "key": "booking-confirmed",
            "age": timedelta(days=1),
            "notification_type": "booking_confirmed",
            "title": "Booking Update",
            "body": "Your spot for Thursday Indoor 7v7 has been confirmed.",
            "related_game_key": "my-upcoming-confirmed",
            "related_booking_key": f"my-upcoming-confirmed:{CURRENT_USER_KEY}",
            "related_participant_key": f"my-upcoming-confirmed:{CURRENT_USER_KEY}",
            "is_read": False,
        },
        {
            "key": "account-security",
            "age": timedelta(days=2),
            "notification_type": "admin_notice",
            "title": "Account Security",
            "body": "We noticed a new login to your account from a new device.",
            "is_read": True,
        },
        {
            "key": "waitlist-joined",
            "age": timedelta(hours=8),
            "notification_type": "waitlist_joined",
            "title": "Waitlist Update",
            "body": "You are on the waitlist for Skyline Community 7s.",
            "related_game_key": "my-upcoming-waitlist",
            "related_participant_key": f"my-upcoming-waitlist:{CURRENT_USER_KEY}",
            "is_read": True,
        },
        {
            "key": "game-time-update",
            "age": timedelta(hours=12),
            "notification_type": "game_updated",
            "title": "Game Update",
            "body": "Alex's Community Run has updated game notes.",
            "related_game_key": "my-hosted-upcoming",
            "is_read": True,
        },
        {
            "key": "host-message",
            "age": timedelta(minutes=58),
            "notification_type": "chat_message",
            "title": "Marcus Reed",
            "body": "Give yourself a few extra minutes for parking.",
            "related_game_key": "my-upcoming-confirmed",
            "related_message_key": "my-upcoming-confirmed:3",
            "is_read": False,
        },
        {
            "key": "player-message",
            "age": timedelta(hours=3),
            "notification_type": "chat_message",
            "title": "Player12 Demo",
            "body": "I can bring one. See everyone soon.",
            "related_game_key": "my-hosted-upcoming",
            "related_message_key": "my-hosted-upcoming:5",
            "is_read": True,
        },
        {
            "key": "cancelled-game",
            "age": timedelta(days=3),
            "notification_type": "game_cancelled",
            "title": "Game Cancelled",
            "body": "Saturday Showdown was cancelled by the host.",
            "related_game_key": "my-past-cancelled",
            "is_read": True,
        },
    ]

    for item in notification_data:
        created_at = timestamp - item["age"]
        is_read = item["is_read"]
        game_key = item.get("related_game_key")
        booking_key = item.get("related_booking_key")
        participant_key = item.get("related_participant_key")
        message_key = item.get("related_message_key")

        seeded_notifications[item["key"]] = upsert_by_id(
            db,
            Notification,
            demo_uuid(f"notification:{CURRENT_USER_KEY}:{item['key']}"),
            {
                "user_id": current_user.id,
                "notification_type": item["notification_type"],
                "title": item["title"],
                "body": item["body"],
                "related_game_id": games[game_key].id if game_key else None,
                "related_booking_id": bookings[booking_key].id if booking_key else None,
                "related_participant_id": (
                    participants[participant_key].id if participant_key else None
                ),
                "related_message_id": (
                    db.get(ChatMessage, demo_uuid(f"chat-message:{message_key}")).id
                    if message_key
                    else None
                ),
                "is_read": is_read,
                "read_at": created_at + timedelta(minutes=2) if is_read else None,
                "created_at": created_at,
            },
        )

    return seeded_notifications
