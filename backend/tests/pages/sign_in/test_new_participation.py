"""F07 authentication does not override the suspended participation gates."""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from backend.models import SubPostPosition, User
from backend.tests.factories import (
    make_booking,
    make_community_game_detail,
    make_game,
    make_participant,
    make_sub_post,
    make_user,
)

from .conftest import commitments


@pytest.mark.page("F07", 12)
@pytest.mark.parametrize("action", ["publish", "post", "join", "guest", "request"])
def test_suspended_sign_in_grants_no_new_participation(
    clock, db, client, firebase, action
):
    user = make_user(
        db,
        account_status="suspended",
        date_of_birth=date(1990, 1, 1),
        hosting_status="eligible",
        email_verified_at=clock.now,
    )
    headers = firebase.sign_in(user)
    game = make_game(
        db,
        starts_at=clock.now + timedelta(days=3),
        game_type="community",
        price_per_player_cents=0,
    )
    make_participant(
        db, game=game, user=db.get(User, game.host_user_id), participant_type="host"
    )
    make_community_game_detail(db, game=game)
    # Community checkout adds guests to an existing external-payment booking.
    # Include the host's own place, just as publication does.
    guest_game = make_game(
        db,
        starts_at=clock.now + timedelta(days=3),
        game_type="community",
        price_per_player_cents=0,
    )
    make_participant(
        db,
        game=guest_game,
        user=db.get(User, guest_game.host_user_id),
        participant_type="host",
    )
    make_community_game_detail(db, game=guest_game)
    booking = make_booking(
        db, game=guest_game, buyer=user, payment_status="not_required"
    )
    make_participant(db, game=guest_game, booking=booking, user=user)
    post = make_sub_post(
        db, owner=make_user(db), starts_at=clock.now + timedelta(days=3)
    )
    position = db.scalar(
        select(SubPostPosition).where(SubPostPosition.sub_post_id == post.id)
    )
    schedule = {
        "starts_at": (clock.now + timedelta(days=3)).isoformat(),
        "ends_at": (clock.now + timedelta(days=3, hours=1)).isoformat(),
        "timezone": "America/Chicago",
        "format_label": "7v7",
        "game_player_group": "coed",
        "skill_level": "any",
        "environment_type": "outdoor",
    }
    venue = {
        "name": "F07 Test Field",
        "address_line_1": "100 Test Street",
        "city": "Chicago",
        "state": "IL",
        "postal_code": "60601",
    }
    paths = {
        "publish": (
            "/community-games/publish",
            {
                **schedule,
                "total_spots": 14,
                "price_per_player_cents": 0,
                "venue": venue,
            },
        ),
        "post": (
            "/need-a-sub/posts",
            {
                **schedule,
                **{key: value for key, value in venue.items() if key != "name"},
                "location_name": venue["name"],
                "subs_needed": 1,
                "positions": [
                    {
                        "position_label": "field_player",
                        "player_group": "open",
                        "spots_needed": 1,
                        "sort_order": 0,
                    }
                ],
            },
        ),
        "join": (f"/games/{game.id}/join", {}),
        "guest": (f"/games/{guest_game.id}/booking-guests/add", {"guest_count": 1}),
        "request": (
            f"/need-a-sub/posts/{post.id}/requests",
            {"sub_post_position_id": str(position.id)},
        ),
    }
    before = commitments(db)
    assert client.get("/auth/me", headers=headers).status_code == 200
    path, payload = paths[action]
    response = client.post(path, headers=headers, json=payload)
    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Active account required."
    assert commitments(db) == before
    db.refresh(user)
    assert user.account_status == "suspended"
