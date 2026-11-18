"""F16 change-related removal records a choice without removing a booking."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from backend.models import (
    AdminAction,
    GameChangeRemovalRequest,
    GameCredit,
    GameParticipant,
    Payment,
    Refund,
)
from backend.tests.factories import make_booking, make_game, make_participant, make_user


def changed_game(db, clock, *, booking_status="confirmed"):
    player = make_user(db)
    admin = make_user(db, role="admin")
    game = make_game(db, starts_at=clock.now + timedelta(hours=2))
    booking = make_booking(
        db,
        game=game,
        buyer=player,
        booking_status=booking_status,
        booked_at=clock.now - timedelta(hours=1),
    )
    make_participant(db, game=game, user=player, booking=booking)
    db.add(
        AdminAction(
            id=uuid.uuid4(),
            admin_user_id=admin.id,
            action_type="update_official_game",
            outcome="succeeded",
            correlation_id=uuid.uuid4(),
            target_game_id=game.id,
            created_at=clock.now - timedelta(minutes=30),
            metadata_={
                "changed_fields": ["format_label"],
                "before": {"format_label": "7v7"},
                "after": {"format_label": "4v4"},
            },
        )
    )
    db.commit()
    return game, booking, player


@pytest.mark.page("F16", 21)
def test_player_reviews_edit_and_requests_removal_without_booking_change(
    clock, db, client, firebase
):
    game, booking, player = changed_game(db, clock)
    headers = firebase.sign_in(player)

    review = client.get(f"/games/{game.id}/change-review", headers=headers)
    response = client.post(
        f"/games/{game.id}/change-removal-requests",
        headers=headers,
        json={"relief_choice": "game_credit"},
    )

    assert review.status_code == 200, review.text
    assert review.json()["changes"][0]["before"] == "7v7"
    assert review.json()["changes"][0]["after"] == "4v4"
    assert review.json()["can_request_removal"] is True
    assert response.status_code == 201, response.text
    assert response.json()["request_status"] == "pending"
    assert response.json()["relief_choice"] == "game_credit"
    db.refresh(booking)
    assert booking.booking_status == "confirmed"
    assert booking.payment_status == "paid"
    assert (
        db.scalar(
            select(func.count(GameParticipant.id)).where(
                GameParticipant.game_id == game.id
            )
        )
        == 1
    )
    assert db.scalar(select(func.count(GameChangeRemovalRequest.id))) == 1
    assert db.scalar(select(func.count(Payment.id))) == 0
    assert db.scalar(select(func.count(Refund.id))) == 0
    assert db.scalar(select(func.count(GameCredit.id))) == 0

    after = client.get(f"/games/{game.id}/change-review", headers=headers)
    assert after.status_code == 200
    assert after.json()["active_request"]["id"] == response.json()["id"]
    assert after.json()["can_request_removal"] is False


@pytest.mark.page("F16", 21)
def test_duplicate_request_is_rejected_without_a_second_row(
    clock, db, client, firebase
):
    game, booking, player = changed_game(db, clock)
    headers = firebase.sign_in(player)
    path = f"/games/{game.id}/change-removal-requests"

    first = client.post(path, headers=headers, json={"relief_choice": "game_credit"})
    second = client.post(
        path, headers=headers, json={"relief_choice": "original_payment_method"}
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 409, second.text
    assert db.scalar(select(func.count(GameChangeRemovalRequest.id))) == 1
    db.refresh(booking)
    assert booking.booking_status == "confirmed"


@pytest.mark.page("F16", 21)
def test_remaining_booking_after_guest_removal_can_request(clock, db, client, firebase):
    game, _, player = changed_game(db, clock, booking_status="partially_cancelled")

    response = client.post(
        f"/games/{game.id}/change-removal-requests",
        headers=firebase.sign_in(player),
        json={"relief_choice": "original_payment_method"},
    )

    assert response.status_code == 201, response.text


@pytest.mark.page("F16", 21)
def test_unrelated_player_cannot_view_or_request_booking_change(
    clock, db, client, firebase
):
    game, _, _ = changed_game(db, clock)
    other = make_user(db)
    headers = firebase.sign_in(other)

    review = client.get(f"/games/{game.id}/change-review", headers=headers)
    request = client.post(
        f"/games/{game.id}/change-removal-requests",
        headers=headers,
        json={"relief_choice": "game_credit"},
    )

    assert review.status_code == 200
    assert review.json() == {
        "changes": [],
        "active_request": None,
        "can_request_removal": False,
    }
    assert request.status_code == 400
    assert db.scalar(select(func.count(GameChangeRemovalRequest.id))) == 0


@pytest.mark.page("F16", 21)
def test_request_closes_at_five_minute_roster_cutoff(clock, db, client, firebase):
    game, _, player = changed_game(db, clock)
    game.starts_at = clock.now - timedelta(minutes=5)
    game.ends_at = clock.now + timedelta(minutes=55)
    db.commit()

    response = client.post(
        f"/games/{game.id}/change-removal-requests",
        headers=firebase.sign_in(player),
        json={"relief_choice": "game_credit"},
    )

    assert response.status_code == 400
    assert db.scalar(select(func.count(GameChangeRemovalRequest.id))) == 0


@pytest.mark.page("F16", 26)
def test_edit_alone_keeps_booking_and_creates_no_request(clock, db, client, firebase):
    game, booking, player = changed_game(db, clock)

    response = client.get(
        f"/games/{game.id}/change-review", headers=firebase.sign_in(player)
    )

    assert response.status_code == 200, response.text
    assert response.json()["can_request_removal"] is True
    db.refresh(booking)
    assert booking.booking_status == "confirmed"
    assert booking.payment_status == "paid"
    assert db.scalar(select(func.count(GameChangeRemovalRequest.id))) == 0
