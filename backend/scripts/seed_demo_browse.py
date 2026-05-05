from __future__ import annotations

from sqlalchemy import select

from backend.database import SessionLocal
from backend.models import Game
from backend.scripts.demo_data.bookings import seed_bookings
from backend.scripts.demo_data.chats import MESSAGES_PER_CHAT, seed_game_chats
from backend.scripts.demo_data.games import DEMO_GAMES, seed_games
from backend.scripts.demo_data.images import seed_game_images
from backend.scripts.demo_data.participants import seed_participants
from backend.scripts.demo_data.users import seed_users
from backend.scripts.demo_data.venues import seed_venues


def seed_demo_browse() -> None:
    with SessionLocal() as db:
        users = seed_users(db)
        db.flush()
        venues = seed_venues(db, users)
        db.flush()
        games = seed_games(db, users, venues)
        db.flush()
        seed_game_images(db, games)
        db.flush()
        chats = seed_game_chats(db, users, games)
        db.flush()
        bookings = seed_bookings(db, users, games)
        db.flush()
        seed_participants(db, users, games, bookings)
        archive_old_scenario_games(db, allowed_game_ids={game.id for game in games.values()})
        db.commit()

    print("Browse demo data ready.")
    print(f"Seeded {len(DEMO_GAMES)} games with images, bookings, and participants.")
    print(f"Seeded {len(chats)} game chats and {len(chats) * MESSAGES_PER_CHAT} chat messages.")


def archive_old_scenario_games(db, allowed_game_ids: set) -> None:
    scenario_games = db.scalars(
        select(Game).where(
            Game.deleted_at.is_(None),
            Game.id.not_in(allowed_game_ids),
            Game.publish_status == "published",
        )
    ).all()

    for game in scenario_games:
        if game.title.startswith("Dev ") or game.venue_name_snapshot.startswith("Dev "):
            game.publish_status = "archived"


if __name__ == "__main__":
    seed_demo_browse()
