"""F17 paid official waitlist: a saved card and consent now, a charge only later."""

import pytest
from sqlalchemy import select

from backend.models import Booking, GameParticipant, Payment, WaitlistEntry
from backend.tests.factories import make_booking, make_participant
from backend.tests.pages.game_checkout.conftest import paying_player, upcoming_game

CONSENT = {
    "auto_charge_consent_accepted": True,
    "auto_charge_consent_version": "waitlist-auto-charge-v1",
}


def full_paid_game(db, stripe):
    """A paid official game with one spot, held by a player who can leave."""
    game = upcoming_game(db, total_spots=1, waitlist_enabled=True)
    holder, _card = paying_player(db, stripe)
    booking = make_booking(db, game=game, buyer=holder)
    make_participant(db, game=game, booking=booking, user=holder)
    return game, holder


def join_waitlist(client, firebase, game, user, card, **body):
    return client.post(
        f"/games/{game.id}/join",
        headers=firebase.sign_in(user),
        json={"guest_count": 0, "payment_method_id": str(card.id), **CONSENT, **body},
    )


def payments_for(db, user):
    return db.scalars(select(Payment).where(Payment.payer_user_id == user.id)).all()


def participant_status(db, game, user):
    return db.scalars(
        select(GameParticipant.participant_status).where(
            GameParticipant.game_id == game.id, GameParticipant.user_id == user.id
        )
    ).all()


@pytest.mark.page("F17", 5)
def test_whole_party_is_waitlisted_with_no_charge_now(db, client, firebase, stripe):
    game, _holder = full_paid_game(db, stripe)
    user, card = paying_player(db, stripe)

    response = join_waitlist(client, firebase, game, user, card, guest_count=1)

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "waitlisted"
    statuses = db.scalars(
        select(GameParticipant.participant_status).where(
            GameParticipant.game_id == game.id,
            GameParticipant.participant_status == "waitlisted",
        )
    ).all()
    assert len(statuses) == 2
    entry = db.scalars(
        select(WaitlistEntry).where(WaitlistEntry.user_id == user.id)
    ).one()
    assert entry.party_size == 2
    assert entry.authorized_payment_method_id == card.id
    assert entry.auto_charge_consent_at is not None
    assert payments_for(db, user) == []
    assert stripe.created == []


@pytest.mark.page("F17", 11)
@pytest.mark.parametrize(
    "missing, detail",
    [
        ("card", "Choose a saved card before joining this waitlist."),
        (
            "consent",
            (
                "You must authorize Pickup Lane to charge your saved card if a spot "
                "opens before joining this waitlist."
            ),
        ),
    ],
)
def test_paid_waitlist_needs_a_card_and_consent(
    db, client, firebase, stripe, missing, detail
):
    game, _holder = full_paid_game(db, stripe)
    user, card = paying_player(db, stripe)
    body = {"guest_count": 0, "payment_method_id": str(card.id), **CONSENT}
    if missing == "card":
        body.pop("payment_method_id")
    else:
        body["auto_charge_consent_accepted"] = False

    response = client.post(
        f"/games/{game.id}/join", headers=firebase.sign_in(user), json=body
    )

    assert response.status_code == 400
    assert response.json()["detail"] == detail
    assert participant_status(db, game, user) == []
    assert (
        db.scalars(select(WaitlistEntry).where(WaitlistEntry.user_id == user.id)).all()
        == []
    )


@pytest.mark.page("F17", 16)
def test_opened_spot_confirms_only_after_the_automatic_charge_succeeds(
    db, client, firebase, stripe
):
    game, holder = full_paid_game(db, stripe)
    user, card = paying_player(db, stripe)
    join_waitlist(client, firebase, game, user, card)

    response = client.post(
        f"/games/{game.id}/leave", headers=firebase.sign_in(holder), json={}
    )

    assert response.status_code == 200, response.text
    assert participant_status(db, game, user) == ["confirmed"]
    payment = db.scalars(select(Payment).where(Payment.payer_user_id == user.id)).one()
    assert (payment.payment_status, payment.amount_cents) == ("succeeded", 1000)


@pytest.mark.page("F17", 16)
def test_failed_automatic_charge_does_not_register_the_player(
    db, client, firebase, stripe
):
    game, holder = full_paid_game(db, stripe)
    user, card = paying_player(db, stripe)
    join_waitlist(client, firebase, game, user, card)
    stripe.confirm_status = "requires_payment_method"

    response = client.post(
        f"/games/{game.id}/leave", headers=firebase.sign_in(holder), json={}
    )

    assert response.status_code == 200, response.text
    assert "confirmed" not in participant_status(db, game, user)
    entry = db.scalars(
        select(WaitlistEntry).where(WaitlistEntry.user_id == user.id)
    ).one()
    assert entry.waitlist_status == "payment_failed"
    booking = db.scalars(
        select(Booking).where(
            Booking.game_id == game.id, Booking.buyer_user_id == user.id
        )
    ).one()
    assert booking.booking_status != "confirmed"


@pytest.mark.page("F17", 17)
def test_leaving_a_paid_waitlist_before_an_offer_costs_nothing(
    db, client, firebase, stripe
):
    game, _holder = full_paid_game(db, stripe)
    user, card = paying_player(db, stripe)
    join_waitlist(client, firebase, game, user, card)

    response = client.post(
        f"/games/{game.id}/leave", headers=firebase.sign_in(user), json={}
    )

    assert response.status_code == 200, response.text
    assert "waitlisted" not in participant_status(db, game, user)
    entry = db.scalars(
        select(WaitlistEntry).where(WaitlistEntry.user_id == user.id)
    ).one()
    assert entry.waitlist_status != "active"
    assert payments_for(db, user) == []
    assert stripe.created == []
