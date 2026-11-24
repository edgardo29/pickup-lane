import pytest

from backend.models import User
from backend.tests.factories import (
    make_community_game_detail,
    make_game,
    make_participant,
)


@pytest.fixture
def browse(client):
    """Call Browse and check its success status before returning the body."""

    def call(**params):
        response = client.get("/games/browse", params=params)
        assert response.status_code == 200, response.text
        return response.json()

    return call


@pytest.fixture
def browse_game(db):
    """Build Browse data, including the host place created at community publication."""

    def create(**values):
        game = make_game(db, **values)
        if game.game_type == "community":
            host = db.get(User, game.host_user_id)
            make_community_game_detail(db, game=game)
            make_participant(
                db,
                game=game,
                user=host,
                participant_type="host",
                price_cents=0,
                roster_order=1,
            )
        return game

    return create
