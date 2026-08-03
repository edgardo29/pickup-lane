from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from backend.database import SessionLocal
from backend.models import Game


@pytest.fixture
def set_browse_game_times():
    def _set_game_times(
        game_id: str,
        starts_at: datetime,
        ends_at: datetime | None = None,
    ) -> None:
        with SessionLocal() as db:
            db_game = db.get(Game, UUID(game_id))
            assert db_game is not None
            db_game.starts_at = starts_at
            db_game.ends_at = ends_at or starts_at + timedelta(hours=1)
            db_game.starts_on_local = starts_at.astimezone(
                ZoneInfo(db_game.timezone)
            ).date()
            db.commit()

    return _set_game_times


@pytest.fixture
def update_browse_game():
    def _update_game(game_id: str, **fields: object) -> None:
        with SessionLocal() as db:
            db_game = db.get(Game, UUID(game_id))
            assert db_game is not None
            for key, value in fields.items():
                setattr(db_game, key, value)
            db.commit()

    return _update_game
