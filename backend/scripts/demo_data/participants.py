from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models import Booking, Game, GameParticipant, User
from backend.scripts.demo_data.games import DEMO_GAMES, get_demo_game_host_key
from backend.scripts.demo_data.helpers import demo_uuid, now_utc, upsert_by_id
from backend.scripts.demo_data.users import PLAYER_KEYS

DEMO_WAITLIST_COUNT = 2


def seed_participants(
    db: Session,
    users: dict[str, User],
    games: dict[str, Game],
    bookings: dict[str, Booking],
) -> dict[str, GameParticipant]:
    seeded_participants: dict[str, GameParticipant] = {}
    timestamp = now_utc()

    for game_index, game_data in enumerate(DEMO_GAMES):
        game = games[game_data["key"]]
        host_key = get_demo_game_host_key(game_data, game_index)
        host = users[host_key]
        player_count = max(game_data["target_participants"] - 1, 0)
        host_participant_key = f"{game_data['key']}:{host_key}:host"

        seeded_participants[host_participant_key] = upsert_by_id(
            db,
            GameParticipant,
            demo_uuid(f"participant:{host_participant_key}"),
            {
                "game_id": game.id,
                "booking_id": None,
                "participant_type": "host",
                "user_id": host.id,
                "guest_name": None,
                "guest_email": None,
                "guest_phone": None,
                "display_name_snapshot": f"{host.first_name} {host.last_name}",
                "participant_status": "confirmed",
                "attendance_status": "unknown",
                "cancellation_type": "none",
                "price_cents": 0,
                "currency": "USD",
                "roster_order": 1,
                "joined_at": timestamp,
                "confirmed_at": timestamp,
                "cancelled_at": None,
                "checked_in_at": None,
                "marked_attendance_by_user_id": None,
                "attendance_decided_at": None,
                "attendance_notes": "Game day host.",
                "updated_at": timestamp,
            },
        )

        for roster_index in range(player_count):
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
                    "roster_order": roster_index + 2,
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

        for stale_roster_index in range(player_count, game_data["target_participants"]):
            stale_player_key = PLAYER_KEYS[stale_roster_index % len(PLAYER_KEYS)]
            stale_participant = db.get(
                GameParticipant,
                demo_uuid(f"participant:{game_data['key']}:{stale_player_key}"),
            )
            if stale_participant is not None:
                stale_participant.participant_status = "removed"
                stale_participant.cancelled_at = timestamp
                stale_participant.updated_at = timestamp

        for waitlist_index in range(DEMO_WAITLIST_COUNT):
            player_key = PLAYER_KEYS[
                (game_data["target_participants"] + waitlist_index) % len(PLAYER_KEYS)
            ]
            player = users[player_key]
            participant_key = f"{game_data['key']}:{player_key}:waitlist"
            participant_id = demo_uuid(f"participant:{participant_key}")

            seeded_participants[participant_key] = upsert_by_id(
                db,
                GameParticipant,
                participant_id,
                {
                    "game_id": game.id,
                    "booking_id": None,
                    "participant_type": "registered_user",
                    "user_id": player.id,
                    "guest_name": None,
                    "guest_email": None,
                    "guest_phone": None,
                    "display_name_snapshot": f"{player.first_name} {player.last_name}",
                    "participant_status": "waitlisted",
                    "attendance_status": "unknown",
                    "cancellation_type": "none",
                    "price_cents": game.price_per_player_cents,
                    "currency": "USD",
                    "roster_order": None,
                    "joined_at": timestamp,
                    "confirmed_at": None,
                    "cancelled_at": None,
                    "checked_in_at": None,
                    "marked_attendance_by_user_id": None,
                    "attendance_decided_at": None,
                    "attendance_notes": None,
                    "updated_at": timestamp,
                },
            )

    return seeded_participants
