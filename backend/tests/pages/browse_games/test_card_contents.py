"""What each Browse card contains, and what it must leave out."""

from datetime import UTC, datetime, timedelta

import pytest

from backend.tests.factories import (
    make_community_game_detail,
    make_game,
    make_participant,
    make_venue,
)


def chicago(hour: int, minute: int = 0) -> datetime:
    """A time on 2026-06-15 in America/Chicago (UTC-5 during daylight saving)."""
    return datetime(2026, 6, 15, hour, minute, tzinfo=UTC) + timedelta(hours=5)


@pytest.mark.page("F15", 11)
def test_official_card_shows_venue_name_location_details_spots_and_price(
    clock, db, browse
):
    venue = make_venue(db, name="Lakefront Turf", city="Chicago", state="IL")
    game = make_game(
        db,
        starts_at=chicago(18, 30),
        venue=venue,
        title="Internal official title",
        game_player_group="women",
        format_label="5v5",
        environment_type="indoor",
        total_spots=10,
        price_per_player_cents=1250,
    )
    make_participant(db, game=game)
    make_participant(db, game=game)

    card = browse()["games"][0]

    assert card["game_type"] == "official"
    assert card["display_title"] == "Lakefront Turf"
    assert card["location_label"] == "Chicago, IL"
    assert datetime.fromisoformat(card["starts_at"]) == chicago(18, 30)
    assert datetime.fromisoformat(card["ends_at"]) == chicago(19, 30)
    assert card["time_group_key"] == "18:00"
    assert card["game_player_group"] == "women"
    assert card["format_label"] == "5v5"
    assert card["environment_type"] == "indoor"
    assert card["participant_count"] == 2
    assert card["total_spots"] == 10
    assert card["price_label"] == "$12.50"


@pytest.mark.page("F15", 11)
def test_community_card_shows_host_title_and_free_price(clock, db, browse):
    make_game(
        db,
        starts_at=chicago(19),
        game_type="community",
        title="Sunday Night Run",
        payment_collection_type="none",
        price_per_player_cents=0,
    )

    card = browse()["games"][0]

    assert card["game_type"] == "community"
    assert card["display_title"] == "Sunday Night Run"
    assert card["price_label"] == "Free"


@pytest.mark.page("F15", 1, 13)
def test_card_has_no_skill_level_payment_instructions_or_viewer_state(
    clock, db, client
):
    game = make_game(
        db, starts_at=chicago(19), game_type="community", skill_level="competitive"
    )
    make_community_game_detail(
        db, game=game, payment_instructions_snapshot="Venmo @secret-host-handle"
    )

    response = client.get("/games/browse")

    assert response.status_code == 200, response.text
    card = response.json()["games"][0]
    assert "skill_level" not in card
    assert "competitive" not in response.text
    assert not any("payment_instruction" in field for field in card)
    assert "secret-host-handle" not in response.text
    for viewer_field in ("is_host", "participant_id", "participant_status", "bucket"):
        assert viewer_field not in card
