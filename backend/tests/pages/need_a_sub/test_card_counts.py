"""F20 what each card's needs and counts show."""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from backend.models import SubPostPosition
from backend.tests.factories import make_sub_post_request, make_user

TOMORROW = date(2026, 6, 16)
SEVEN_PM_TOMORROW = datetime(2026, 6, 16, 19, 0, tzinfo=UTC) + timedelta(hours=5)

REQUEST_STATUSES = [
    "pending",
    "confirmed",
    "declined",
    "sub_waitlist",
    "canceled_by_player",
    "canceled_by_owner",
    "no_show_reported",
    "expired",
    "closed_by_admin",
]


def field_and_goalkeeper_post(db, new_post):
    """A coed post needing three Any field players and one Women's goalkeeper."""
    post = new_post(SEVEN_PM_TOMORROW, subs_needed=4)
    field = db.scalar(
        select(SubPostPosition).where(SubPostPosition.sub_post_id == post.id)
    )
    field.spots_needed = 3
    goalkeeper = SubPostPosition(
        id=uuid.uuid4(),
        sub_post_id=post.id,
        position_label="goalkeeper",
        player_group="women",
        spots_needed=1,
        sort_order=1,
    )
    db.add(goalkeeper)
    db.commit()
    return post, field, goalkeeper


def add_request(db, post, position, request_status):
    return make_sub_post_request(
        db,
        post=post,
        requester=make_user(db),
        request_status=request_status,
        sub_post_position_id=position.id,
    )


@pytest.mark.page("F20", 6)
def test_each_card_keeps_every_configured_need_including_a_full_one(
    clock, db, new_post, cards
):
    # One need of each position and player group a post can mix: Men's and
    # Women's field players and an Any goalkeeper. The Women's need is full.
    post = new_post(SEVEN_PM_TOMORROW, subs_needed=4)
    men_field = db.scalar(
        select(SubPostPosition).where(SubPostPosition.sub_post_id == post.id)
    )
    men_field.player_group = "men"
    men_field.spots_needed = 2
    women_field = SubPostPosition(
        id=uuid.uuid4(),
        sub_post_id=post.id,
        position_label="field_player",
        player_group="women",
        spots_needed=1,
        sort_order=1,
    )
    any_goalkeeper = SubPostPosition(
        id=uuid.uuid4(),
        sub_post_id=post.id,
        position_label="goalkeeper",
        player_group="open",
        spots_needed=1,
        sort_order=2,
    )
    db.add_all([women_field, any_goalkeeper])
    db.commit()
    add_request(db, post, women_field, "confirmed")

    card = cards(TOMORROW)["posts"][0]

    assert [
        (
            position["position_label"],
            position["player_group"],
            position["spots_needed"],
            position["confirmed_count"],
        )
        for position in card["positions"]
    ] == [
        ("field_player", "men", 2, 0),
        ("field_player", "women", 1, 1),
        ("goalkeeper", "open", 1, 0),
    ]


@pytest.mark.page("F20", 6)
@pytest.mark.parametrize("request_status", REQUEST_STATUSES)
def test_only_a_confirmed_request_fills_a_spot(
    clock, db, new_post, cards, request_status
):
    post, field, _goalkeeper = field_and_goalkeeper_post(db, new_post)
    add_request(db, post, field, request_status)
    filled = 1 if request_status == "confirmed" else 0

    card = cards(TOMORROW)["posts"][0]

    assert card["confirmed_count"] == filled
    assert card["positions"][0]["confirmed_count"] == filled
    assert card["positions"][0]["spots_needed"] == 3
