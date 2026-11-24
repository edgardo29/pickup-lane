"""The individual facts returned for a Browse card."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from backend.models import CommunityGameDetail
from backend.tests.factories import make_venue


@pytest.fixture
def card_game(clock, db, browse_game):
    venue = make_venue(db, name="Lakefront Turf", city="Chicago", state="IL")
    return browse_game(
        starts_at=clock.now + timedelta(hours=6, minutes=30),
        venue=venue,
        title="Internal official title",
        total_spots=10,
        price_per_player_cents=1250,
    )


@pytest.mark.page("F15", 11)
@pytest.mark.parametrize("game_type", ["official", "community"])
def test_card_includes_its_game_type(clock, browse_game, browse, game_type):
    browse_game(starts_at=clock.now + timedelta(hours=6), game_type=game_type)
    assert browse()["games"][0]["game_type"] == game_type


@pytest.mark.page("F15", 11)
def test_official_card_uses_venue_title(card_game, browse):
    assert browse()["games"][0]["display_title"] == "Lakefront Turf"


@pytest.mark.page("F15", 11)
def test_community_card_uses_host_title(clock, browse_game, browse):
    browse_game(
        starts_at=clock.now + timedelta(hours=6),
        game_type="community",
        title="Sunday Night Run",
    )
    assert browse()["games"][0]["display_title"] == "Sunday Night Run"


@pytest.mark.page("F15", 11)
def test_card_includes_city_and_state(card_game, browse):
    card = browse()["games"][0]
    assert card["city_snapshot"] == "Chicago"
    assert card["state_snapshot"] == "IL"
    assert card["location_label"] == "Chicago, IL"


@pytest.mark.page("F15", 11)
def test_card_includes_start_and_end_time(card_game, browse):
    card = browse()["games"][0]
    assert datetime.fromisoformat(card["starts_at"]) == card_game.starts_at
    assert datetime.fromisoformat(card["ends_at"]) == card_game.ends_at


@pytest.mark.page("F15", 11)
@pytest.mark.parametrize("value", ["men", "women", "coed"])
def test_card_includes_player_group(clock, browse_game, browse, value):
    browse_game(starts_at=clock.now + timedelta(hours=6), game_player_group=value)
    assert browse()["games"][0]["game_player_group"] == value


@pytest.mark.page("F15", 11)
@pytest.mark.parametrize("value", ["5v5", "7v7", "11v11"])
def test_card_includes_format(clock, browse_game, browse, value):
    browse_game(starts_at=clock.now + timedelta(hours=6), format_label=value)
    assert browse()["games"][0]["format_label"] == value


@pytest.mark.page("F15", 11)
@pytest.mark.parametrize("value", ["indoor", "outdoor"])
def test_card_includes_environment(clock, browse_game, browse, value):
    browse_game(starts_at=clock.now + timedelta(hours=6), environment_type=value)
    assert browse()["games"][0]["environment_type"] == value


@pytest.mark.page("F15", 11)
def test_card_includes_total_capacity(card_game, browse):
    card = browse()["games"][0]
    assert card["total_spots"] == 10
    assert card["availability"]["total_spots"] == 10


@pytest.mark.page("F15", 11)
@pytest.mark.parametrize(("cents", "label"), [(1000, "$10"), (1250, "$12.50")])
def test_card_includes_per_player_price(clock, browse_game, browse, cents, label):
    browse_game(starts_at=clock.now + timedelta(hours=6), price_per_player_cents=cents)
    card = browse()["games"][0]
    assert card["price_per_player_cents"] == cents
    assert card["price_label"] == label


@pytest.mark.page("F15", 11)
@pytest.mark.parametrize("game_type", ["official", "community"])
def test_free_card_includes_free_price(clock, browse_game, browse, game_type):
    browse_game(
        starts_at=clock.now + timedelta(hours=6),
        game_type=game_type,
        price_per_player_cents=0,
    )
    assert browse()["games"][0]["price_label"] == "Free"


@pytest.mark.page("F15", 13)
def test_card_omits_host_payment_instructions(clock, db, browse_game, browse):
    game = browse_game(starts_at=clock.now + timedelta(hours=6), game_type="community")
    # The local fixture creates the community detail exactly once.
    detail = db.scalar(
        select(CommunityGameDetail).where(CommunityGameDetail.game_id == game.id)
    )
    detail.payment_instructions_snapshot = "Synthetic private host payment note"
    db.commit()
    card = browse()["games"][0]
    assert not any("payment_instruction" in key for key in card)
    assert "Synthetic private host payment note" not in str(card)


@pytest.mark.page("F15", 13)
def test_card_omits_skill_level(clock, browse_game, browse):
    browse_game(starts_at=clock.now + timedelta(hours=6), skill_level="competitive")
    card = browse()["games"][0]
    assert "skill_level" not in card
    assert "competitive" not in str(card)
