from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models import Booking, Game, GameParticipant, User
from backend.scripts.demo_data.games import DEMO_GAMES
from backend.scripts.demo_data.helpers import demo_uuid, now_utc, upsert_by_id
from backend.scripts.demo_data.users import PLAYER_KEYS


def seed_participants(
    db: Session,
    users: dict[str, User],
    games: dict[str, Game],
    bookings: dict[str, Booking],
) -> dict[str, GameParticipant]:
    seeded_participants: dict[str, GameParticipant] = {}
    timestamp = now_utc()

    for game_data in DEMO_GAMES:
        game = games[game_data["key"]]

        for roster_index in range(game_data["target_participants"]):
            player_key = PLAYER_KEYS[roster_index % len(PLAYER_KEYS)]
            player = users[player_key]
            booking_key = f"{game_data['key']}:{player_key}"
            participant_key = f"{game_data['key']}:{player_key}"
            participant_id = demo_uuid(f"participant:{participant_key}")

            seeded_participants[participant_key] = upsert_by_id(
                db,
                GameParticipant,
                participant_id,
                {
                    "game_id": game.id,
                    "booking_id": bookings[booking_key].id,
                    "participant_type": "registered_user",
                    "user_id": player.id,
                    "guest_name": None,
                    "guest_email": None,
                    "guest_phone": None,
                    "display_name_snapshot": f"{player.first_name} {player.last_name}",
                    "participant_status": "confirmed",
                    "attendance_status": "unknown",
                    "cancellation_type": "none",
                    "price_cents": game.price_per_player_cents,
                    "currency": "USD",
                    "roster_order": roster_index + 1,
                    "joined_at": timestamp,
                    "confirmed_at": timestamp,
                    "cancelled_at": None,
                    "checked_in_at": None,
                    "marked_attendance_by_user_id": None,
                    "attendance_decided_at": None,
                    "attendance_notes": None,
                    "updated_at": timestamp,
                },
            )

    return seeded_participants
