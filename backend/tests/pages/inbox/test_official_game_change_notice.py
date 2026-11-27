"""The official-game change notice in Game Activity, sent by Edit Official Game."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from backend.models import GameCredit, Notification, Payment, Refund
from backend.tests.factories import make_booking, make_game, make_participant, make_user


def book_official_game(db, clock, player):
    game = make_game(db, starts_at=clock.now + timedelta(days=4))
    booking = make_booking(db, game=game, buyer=player)
    participant = make_participant(db, game=game, booking=booking, user=player)
    return game, booking, participant


def edit_official_game(client, firebase, db, game, changes):
    response = client.patch(
        f"/admin/official-games/{game.id}",
        headers=firebase.sign_in(make_user(db, role="admin")),
        json=changes,
    )
    assert response.status_code == 200, response.text


def money_record_counts(db):
    return [
        db.scalar(select(func.count()).select_from(model))
        for model in (Payment, Refund, GameCredit)
    ]


@pytest.mark.page("F25", 14)
def test_an_official_game_edit_sends_each_player_a_notice_explaining_the_change(
    clock, db, client, firebase, inbox_user, inbox_headers
):
    game, _, _ = book_official_game(db, clock, inbox_user)
    new_start = game.starts_at + timedelta(hours=2)

    edit_official_game(
        client,
        firebase,
        db,
        game,
        {
            "starts_at": new_start.isoformat(),
            "ends_at": (new_start + timedelta(hours=1)).isoformat(),
        },
    )
    response = client.get("/inbox/game-activity", headers=inbox_headers)

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert [item["notification_type"] for item in items] == ["game_updated"]
    item = items[0]
    assert item["message"] == (
        "The start time and end time changed after you booked. Review the latest "
        "details. You may keep your booking or request removal and choose a refund "
        "to the original payment method or Pickup Lane game credit. This notice "
        "does not change your booking or issue money."
    )
    assert item["action"]["path"] == f"/games/{game.id}"


@pytest.mark.page("F25", 14)
def test_changing_only_the_price_also_sends_the_notice(
    clock, db, client, firebase, inbox_user, inbox_headers
):
    game, _, _ = book_official_game(db, clock, inbox_user)

    edit_official_game(
        client,
        firebase,
        db,
        game,
        {"price_per_player_cents": game.price_per_player_cents + 500},
    )
    response = client.get("/inbox/game-activity", headers=inbox_headers)

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert [item["notification_type"] for item in items] == ["game_updated"]
    item = items[0]
    assert item["message"].startswith("The price changed after you booked.")


@pytest.mark.page("F25", 14)
def test_the_change_notice_does_not_change_the_booking_or_issue_money(
    clock, db, client, firebase, inbox_user
):
    game, booking, participant = book_official_game(db, clock, inbox_user)
    money_before = money_record_counts(db)

    edit_official_game(
        client,
        firebase,
        db,
        game,
        {"skill_level": "advanced"},
    )

    notices = db.scalars(
        select(Notification.notification_type).where(
            Notification.user_id == inbox_user.id
        )
    ).all()
    assert notices == ["game_updated"]
    db.refresh(booking)
    db.refresh(participant)
    assert booking.booking_status == "confirmed"
    assert booking.payment_status == "paid"
    assert participant.participant_status == "confirmed"
    assert money_record_counts(db) == money_before


@pytest.mark.page("F25", 14)
def test_a_player_whose_booking_is_partly_cancelled_also_gets_the_choice(
    clock, db, client, firebase, inbox_user, inbox_headers
):
    game = make_game(db, starts_at=clock.now + timedelta(days=4))
    # The player booked a guest, then cancelled only the guest's place.
    booking = make_booking(
        db,
        game=game,
        buyer=inbox_user,
        participant_count=2,
        booking_status="partially_cancelled",
        cancelled_by_user_id=inbox_user.id,
    )
    make_participant(db, game=game, booking=booking, user=inbox_user)
    make_participant(
        db,
        game=game,
        booking=booking,
        user=inbox_user,
        participant_type="guest",
        participant_status="cancelled",
    )

    edit_official_game(client, firebase, db, game, {"skill_level": "advanced"})
    response = client.get("/inbox/game-activity", headers=inbox_headers)

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert [item["notification_type"] for item in items] == ["game_updated"]
    assert "You may keep your booking or request removal" in items[0]["message"]
