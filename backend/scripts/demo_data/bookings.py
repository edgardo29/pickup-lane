from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models import Booking, Game, User
from backend.scripts.demo_data.games import DEMO_GAMES
from backend.scripts.demo_data.helpers import demo_uuid, now_utc, upsert_by_id
from backend.scripts.demo_data.users import PLAYER_KEYS


def seed_bookings(db: Session, users: dict[str, User], games: dict[str, Game]) -> dict[str, Booking]:
    seeded_bookings: dict[str, Booking] = {}
    timestamp = now_utc()

    for game_data in DEMO_GAMES:
        game = games[game_data["key"]]
        player_count = max(game_data["target_participants"] - 1, 0)

        for roster_index in range(player_count):
            player_key = PLAYER_KEYS[roster_index % len(PLAYER_KEYS)]
            buyer = users[player_key]
            booking_key = f"{game_data['key']}:{player_key}"
            booking_id = demo_uuid(f"booking:{booking_key}")
            subtotal_cents = game.price_per_player_cents

            seeded_bookings[booking_key] = upsert_by_id(
                db,
                Booking,
                booking_id,
                {
                    "game_id": game.id,
                    "buyer_user_id": buyer.id,
                    "booking_status": "confirmed",
                    "payment_status": "paid",
                    "participant_count": 1,
                    "subtotal_cents": subtotal_cents,
                    "platform_fee_cents": 0,
                    "discount_cents": 0,
                    "total_cents": subtotal_cents,
                    "currency": "USD",
                    "price_per_player_snapshot_cents": game.price_per_player_cents,
                    "platform_fee_snapshot_cents": 0,
                    "booked_at": timestamp,
                    "cancelled_at": None,
                    "cancelled_by_user_id": None,
                    "cancel_reason": None,
                    "expires_at": None,
                    "updated_at": timestamp,
                },
            )

    return seeded_bookings
