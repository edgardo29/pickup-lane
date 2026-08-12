from datetime import UTC, datetime, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from backend.database import SessionLocal
from backend.models import Game
from backend.services.game_service import build_browse_game_eligibility_conditions
from backend.tests.support.api_helpers import create_game, create_venue
from backend.tests.support.factories import create_user
from backend.tests.support.time import local_date_string


def test_browse_game_cards_exclude_registration_closed_games(
    client: TestClient,
):
    admin = create_user(client)
    venue = create_venue(client, admin["id"])
    browse_timezone = ZoneInfo("America/Chicago")
    controlled_local_now = (
        datetime.now(browse_timezone) + timedelta(days=7)
    ).replace(hour=12, minute=0, second=0, microsecond=0)
    controlled_now = controlled_local_now.astimezone(UTC)
    visible_start = (controlled_local_now + timedelta(hours=1)).astimezone(UTC)
    closed_start = (controlled_local_now - timedelta(minutes=10)).astimezone(UTC)
    visible_game = create_game(
        client,
        admin["id"],
        venue,
        starts_at=visible_start.isoformat(),
        ends_at=(visible_start + timedelta(hours=1)).isoformat(),
    )
    closed_game = create_game(
        client,
        admin["id"],
        venue,
        starts_at=closed_start.isoformat(),
        ends_at=(closed_start + timedelta(hours=1)).isoformat(),
    )

    with SessionLocal() as db:
        game_ids = {
            str(game.id)
            for game in db.scalars(
                select(Game).where(
                    *build_browse_game_eligibility_conditions(
                        controlled_local_now.date(),
                        now=controlled_now,
                    )
                )
            )
        }

    assert visible_game["id"] in game_ids
    assert closed_game["id"] not in game_ids


@pytest.mark.parametrize(
    ("description", "overrides"),
    [
        ("draft game", {"publish_status": "draft"}),
        ("archived game", {"publish_status": "archived"}),
        ("hidden game", {"public_visibility_status": "hidden"}),
        ("paused game", {"join_enforcement_status": "paused"}),
        ("cancelled game", {"game_status": "cancelled"}),
        ("completed game", {"game_status": "completed"}),
        ("expired game", {"game_status": "expired"}),
        ("removed game", {"game_status": "removed"}),
    ],
    ids=[
        "draft",
        "archived",
        "hidden",
        "paused",
        "cancelled",
        "completed",
        "expired",
        "removed",
    ],
)
def test_browse_excludes_unlistable_game_states(
    client: TestClient,
    description: str,
    overrides: dict[str, object],
):
    admin = create_user(client)
    venue = create_venue(client, admin["id"])
    browse_start = (
        datetime.now(ZoneInfo("America/Chicago")) + timedelta(days=7)
    ).replace(hour=18, minute=0, second=0, microsecond=0)
    starts_at = browse_start.astimezone(UTC)
    visible_game = create_game(
        client,
        admin["id"],
        venue,
        title="Visible Browse Control",
        starts_at=starts_at.isoformat(),
        ends_at=(starts_at + timedelta(hours=1)).isoformat(),
    )
    excluded_game = create_game(
        client,
        admin["id"],
        venue,
        title=f"Excluded {description}",
        starts_at=(starts_at + timedelta(minutes=30)).isoformat(),
        ends_at=(starts_at + timedelta(hours=1, minutes=30)).isoformat(),
        **overrides,
    )

    response = client.get(
        "/games/browse",
        params={"starts_on": local_date_string(starts_at, "America/Chicago")},
    )

    assert response.status_code == 200, response.text
    game_ids = {game["id"] for game in response.json()["games"]}
    assert visible_game["id"] in game_ids
    assert excluded_game["id"] not in game_ids


def test_browse_excludes_deleted_and_wrong_local_date_games(
    client: TestClient,
    update_browse_game: Callable[..., None],
):
    admin = create_user(client)
    venue = create_venue(client, admin["id"])
    browse_start = (
        datetime.now(ZoneInfo("America/Chicago")) + timedelta(days=7)
    ).replace(hour=18, minute=0, second=0, microsecond=0)
    starts_at = browse_start.astimezone(UTC)
    visible_game = create_game(
        client,
        admin["id"],
        venue,
        title="Visible Browse Control",
        starts_at=starts_at.isoformat(),
        ends_at=(starts_at + timedelta(hours=1)).isoformat(),
    )
    deleted_game = create_game(
        client,
        admin["id"],
        venue,
        title="Deleted Browse Game",
        starts_at=(starts_at + timedelta(minutes=30)).isoformat(),
        ends_at=(starts_at + timedelta(hours=1, minutes=30)).isoformat(),
    )
    wrong_date_game = create_game(
        client,
        admin["id"],
        venue,
        title="Wrong Local Date Browse Game",
        starts_at=(starts_at + timedelta(hours=1)).isoformat(),
        ends_at=(starts_at + timedelta(hours=2)).isoformat(),
    )
    update_browse_game(deleted_game["id"], deleted_at=datetime.now(UTC))
    wrong_local_date = starts_at.astimezone(ZoneInfo("America/Chicago")).date()
    update_browse_game(
        wrong_date_game["id"],
        starts_on_local=wrong_local_date + timedelta(days=1),
    )

    response = client.get(
        "/games/browse",
        params={"starts_on": local_date_string(starts_at, "America/Chicago")},
    )

    assert response.status_code == 200, response.text
    game_ids = {game["id"] for game in response.json()["games"]}
    assert visible_game["id"] in game_ids
    assert deleted_game["id"] not in game_ids
    assert wrong_date_game["id"] not in game_ids


def test_browse_includes_official_and_community_games(
    client: TestClient,
):
    admin = create_user(client)
    community_host = create_user(client)
    venue = create_venue(client, admin["id"])
    browse_start = (
        datetime.now(ZoneInfo("America/Chicago")) + timedelta(days=7)
    ).replace(hour=18, minute=0, second=0, microsecond=0)
    starts_at = browse_start.astimezone(UTC)
    official_game = create_game(
        client,
        admin["id"],
        venue,
        game_type="official",
        title="Official Browse Game",
        starts_at=starts_at.isoformat(),
        ends_at=(starts_at + timedelta(hours=1)).isoformat(),
    )
    community_game = create_game(
        client,
        community_host["id"],
        venue,
        game_type="community",
        host_user_id=community_host["id"],
        policy_mode="custom_hosted",
        payment_collection_type="external_host",
        title="Community Browse Game",
        starts_at=(starts_at + timedelta(hours=1)).isoformat(),
        ends_at=(starts_at + timedelta(hours=2)).isoformat(),
    )

    response = client.get(
        "/games/browse",
        params={"starts_on": local_date_string(starts_at, "America/Chicago")},
    )

    assert response.status_code == 200, response.text
    game_ids = {game["id"] for game in response.json()["games"]}
    assert official_game["id"] in game_ids
    assert community_game["id"] in game_ids
