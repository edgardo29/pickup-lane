from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models import Game, User, Venue
from backend.scripts.demo_data.helpers import demo_uuid, ends_at, now_utc, starts_at, upsert_by_id
from backend.scripts.demo_data.users import ADMIN_KEY, HOST_KEYS

DEMO_GAMES = [
    {
        "key": "intentional-7pm",
        "venue_key": "intentional-sports",
        "title": "Saturday Night 7v7",
        "game_type": "official",
        "day_offset": 0,
        "hour": 19,
        "minute": 0,
        "format_label": "7v7",
        "environment_type": "indoor",
        "total_spots": 16,
        "price_per_player_cents": 1200,
        "target_participants": 14,
    },
    {
        "key": "rauner-indoor-730pm",
        "venue_key": "rauner-ymca-indoor",
        "title": "Fast Indoor 5v5",
        "game_type": "official",
        "day_offset": 0,
        "hour": 19,
        "minute": 30,
        "format_label": "5v5",
        "environment_type": "indoor",
        "total_spots": 12,
        "price_per_player_cents": 1100,
        "target_participants": 4,
    },
    {
        "key": "skinner-745pm",
        "venue_key": "skinner-park",
        "title": "West Loop Pickup",
        "game_type": "official",
        "day_offset": 0,
        "hour": 19,
        "minute": 45,
        "format_label": "7v7",
        "environment_type": "outdoor",
        "total_spots": 14,
        "price_per_player_cents": 1200,
        "target_participants": 6,
    },
    {
        "key": "skyline-755pm",
        "venue_key": "skyline-pitch",
        "title": "Skyline Lights",
        "game_type": "official",
        "day_offset": 0,
        "hour": 19,
        "minute": 55,
        "format_label": "5v5",
        "environment_type": "outdoor",
        "total_spots": 10,
        "price_per_player_cents": 1000,
        "target_participants": 3,
    },
    {
        "key": "harrison-8pm",
        "venue_key": "harrison-park",
        "title": "Pilsen 7v7",
        "game_type": "official",
        "day_offset": 0,
        "hour": 20,
        "minute": 0,
        "format_label": "7v7",
        "environment_type": "outdoor",
        "total_spots": 12,
        "price_per_player_cents": 900,
        "target_participants": 5,
    },
    {
        "key": "livingston-830pm",
        "venue_key": "livingston-park",
        "title": "Uptown Under Lights",
        "game_type": "official",
        "day_offset": 0,
        "hour": 20,
        "minute": 30,
        "format_label": "7v7",
        "environment_type": "outdoor",
        "total_spots": 16,
        "price_per_player_cents": 1200,
        "target_participants": 8,
    },
    {
        "key": "british-school-845pm",
        "venue_key": "british-international-school-of-chicago-south-loop",
        "title": "South Loop Indoor",
        "game_type": "official",
        "day_offset": 0,
        "hour": 20,
        "minute": 45,
        "format_label": "5v5",
        "environment_type": "indoor",
        "total_spots": 10,
        "price_per_player_cents": 1000,
        "target_participants": 2,
    },
    {
        "key": "rauner-outdoor-915pm",
        "venue_key": "rauner-ymca-outdoor",
        "title": "Community Run 7v7",
        "game_type": "community",
        "host_key": "host-marcus",
        "day_offset": 0,
        "hour": 21,
        "minute": 15,
        "format_label": "7v7",
        "environment_type": "outdoor",
        "total_spots": 12,
        "price_per_player_cents": 1100,
        "target_participants": 6,
    },
    {
        "key": "skyline-community-945pm",
        "venue_key": "skyline-pitch",
        "title": "Late Night Community 5s",
        "game_type": "community",
        "host_key": "host-sofia",
        "day_offset": 0,
        "hour": 21,
        "minute": 45,
        "format_label": "5v5",
        "environment_type": "outdoor",
        "total_spots": 10,
        "price_per_player_cents": 1000,
        "target_participants": 3,
    },
    {
        "key": "intentional-sunday-6pm",
        "venue_key": "intentional-sports",
        "title": "Sunday Indoor 5v5",
        "game_type": "official",
        "day_offset": 1,
        "hour": 18,
        "minute": 0,
        "format_label": "5v5",
        "environment_type": "indoor",
        "total_spots": 12,
        "price_per_player_cents": 1200,
        "target_participants": 7,
    },
    {
        "key": "skinner-sunday-7pm",
        "venue_key": "skinner-park",
        "title": "Sunday West Loop 7s",
        "game_type": "official",
        "day_offset": 1,
        "hour": 19,
        "minute": 0,
        "format_label": "7v7",
        "environment_type": "outdoor",
        "total_spots": 14,
        "price_per_player_cents": 1100,
        "target_participants": 9,
    },
]

DEFAULT_GAME_DETAILS = {
    "description": (
        "Fast-paced pickup soccer with balanced teams, clear communication, "
        "and a welcoming competitive level."
    ),
    "arrival_notes": "Arrive 10 minutes early and check in with the host near the field entrance.",
    "parking_notes": "Street parking is limited near kickoff, so give yourself a little extra time.",
    "custom_rules_text": None,
    "custom_cancellation_text": None,
    "game_notes": "Bring a white and a dark shirt.",
    "minimum_age": 18,
}

GAME_DETAILS_BY_KEY = {
    "intentional-7pm": {
        "description": (
            "Competitive indoor 7v7 with quick rotations and high tempo play. "
            "All skill levels are welcome, but expect a steady pace."
        ),
        "arrival_notes": "Enter through the main entrance and meet the host beside the indoor field.",
    },
    "skinner-park": {
        "description": "Outdoor West Loop pickup with organized teams and a friendly competitive pace.",
        "arrival_notes": "Meet near the field gate closest to Adams St.",
        "parking_notes": "Street parking is usually easiest on nearby side streets.",
    },
    "rauner-outdoor-915pm": {
        "description": "Community-hosted outdoor 7v7 for players who want a relaxed late game.",
        "custom_rules_text": "Bring a light and dark shirt. Host will confirm final teams.",
        "custom_cancellation_text": "Cancel at least 12 hours before kickoff so the host can refill your spot.",
    },
    "skyline-community-945pm": {
        "description": "Late night community 5v5 with a casual pace and smaller teams.",
        "custom_rules_text": "Keep subs moving and call your own fouls.",
        "custom_cancellation_text": "Cancel at least 12 hours before kickoff so the host can refill your spot.",
    },
}


def get_demo_game_host_key(game_data: dict, game_index: int) -> str:
    return game_data.get("host_key") or HOST_KEYS[game_index % len(HOST_KEYS)]


def seed_games(db: Session, users: dict[str, User], venues: dict[str, Venue]) -> dict[str, Game]:
    seeded_games: dict[str, Game] = {}
    timestamp = now_utc()
    admin = users[ADMIN_KEY]

    for game_index, game_data in enumerate(DEMO_GAMES):
        venue = venues[game_data["venue_key"]]
        game_start = starts_at(game_data["day_offset"], game_data["hour"], game_data["minute"])
        game_id = demo_uuid(f"game:{game_data['key']}")
        is_community = game_data["game_type"] == "community"
        host = users[get_demo_game_host_key(game_data, game_index)]
        details = DEFAULT_GAME_DETAILS | GAME_DETAILS_BY_KEY.get(game_data["key"], {})

        seeded_games[game_data["key"]] = upsert_by_id(
            db,
            Game,
            game_id,
            {
                "game_type": game_data["game_type"],
                "publish_status": "published",
                "game_status": "scheduled",
                "title": game_data["title"],
                "description": details["description"],
                "venue_id": venue.id,
                "venue_name_snapshot": venue.name,
                "address_snapshot": venue.address_line_1,
                "city_snapshot": venue.city,
                "state_snapshot": venue.state,
                "neighborhood_snapshot": venue.neighborhood,
                "host_user_id": host.id,
                "created_by_user_id": host.id if is_community else admin.id,
                "starts_at": game_start,
                "ends_at": ends_at(game_start),
                "timezone": "America/Chicago",
                "sport_type": "soccer",
                "format_label": game_data["format_label"],
                "environment_type": game_data["environment_type"],
                "total_spots": game_data["total_spots"],
                "price_per_player_cents": game_data["price_per_player_cents"],
                "currency": "USD",
                "minimum_age": details["minimum_age"],
                "allow_guests": True,
                "max_guests_per_booking": 2,
                "waitlist_enabled": True,
                "is_chat_enabled": True,
                "policy_mode": "custom_hosted" if is_community else "official_standard",
                "custom_rules_text": details["custom_rules_text"],
                "custom_cancellation_text": details["custom_cancellation_text"],
                "game_notes": details["game_notes"],
                "arrival_notes": details["arrival_notes"],
                "parking_notes": details["parking_notes"],
                "published_at": timestamp,
                "cancelled_at": None,
                "cancelled_by_user_id": None,
                "cancel_reason": None,
                "completed_at": None,
                "completed_by_user_id": None,
                "deleted_at": None,
                "updated_at": timestamp,
            },
        )

    return seeded_games
