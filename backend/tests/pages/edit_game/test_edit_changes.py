"""F18 what a host can change, before and after players join."""

import uuid
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select

from backend.models import CommunityGameDetail, Game, HostPublishFee, Payment, Venue
from backend.tests.conftest import database_now
from backend.tests.factories import (
    make_booking,
    make_community_game_detail,
    make_game,
    make_participant,
    make_user,
    make_venue,
)

CHICAGO = ZoneInfo("America/Chicago")


def hosted_game(db, **overrides):
    """A published, active community game two days out, with its host.

    As when publishing, the host holds a confirmed place on the roster.
    """
    host = make_user(db, hosting_status="eligible")
    values = {"host": host, "starts_at": database_now(db) + timedelta(days=2)}
    values.update(overrides)
    game = make_game(db, game_type="community", **values)
    make_participant(db, game=game, user=host, participant_type="host")
    return game, host


def saved_payment_methods(db, game):
    return (
        db.query(CommunityGameDetail)
        .filter_by(game_id=game.id)
        .one()
        .payment_methods_snapshot
    )


def edit(client, firebase, host, game, **changes):
    return client.patch(
        f"/games/{game.id}/host-edit",
        headers=firebase.sign_in(host),
        json={
            key: value.isoformat() if isinstance(value, datetime) else value
            for key, value in changes.items()
        },
    )


def location(venue_name, street="100 Shared Street"):
    return {
        "venue_name": venue_name,
        "address_line_1": street,
        "city": "Chicago",
        "state": "IL",
        "postal_code": "60601",
    }


def count(db, model):
    return db.scalar(select(func.count(model.id)))


def player_joins(db, game, participant_status="confirmed"):
    booking = make_booking(
        db,
        game=game,
        booking_status="waitlisted"
        if participant_status == "waitlisted"
        else "confirmed",
        payment_status="not_required",
        reservation_status="not_required"
        if participant_status == "waitlisted"
        else "confirmed",
        price_per_player_snapshot_cents=game.price_per_player_cents,
    )
    return make_participant(
        db, game=game, booking=booking, participant_status=participant_status
    )


@pytest.mark.page("F18", 2)
def test_permitted_changes_save_without_a_new_game_or_fee(db, client, firebase):
    game, host = hosted_game(db)
    make_community_game_detail(db, game=game)
    games_before, fees_before = count(db, Game), count(db, HostPublishFee)

    game_response = edit(
        client,
        firebase,
        host,
        game,
        skill_level="advanced",
        custom_rules_text="No slide tackles.",
        game_notes="Bring a light and a dark shirt.",
    )
    details_response = client.put(
        f"/community-game-details/games/{game.id}/host-edit",
        headers=firebase.sign_in(host),
        json={
            "payment_methods_snapshot": [
                {"type": "zelle", "value": "host@example.test"}
            ]
        },
    )

    assert game_response.status_code == 200, game_response.text
    assert details_response.status_code == 200, details_response.text
    body = game_response.json()
    assert (body["skill_level"], body["custom_rules_text"], body["game_notes"]) == (
        "advanced",
        "No slide tackles.",
        "Bring a light and a dark shirt.",
    )
    assert details_response.json()["payment_methods_snapshot"] == [
        {"type": "zelle", "value": "host@example.test"}
    ]
    db.refresh(game)
    assert (game.skill_level, game.custom_rules_text, game.game_notes) == (
        "advanced",
        "No slide tackles.",
        "Bring a light and a dark shirt.",
    )
    assert saved_payment_methods(db, game) == [
        {"type": "zelle", "value": "host@example.test"}
    ]
    assert (count(db, Game), count(db, HostPublishFee)) == (games_before, fees_before)


@pytest.mark.page("F18", 2)
def test_a_free_game_can_become_paid_and_back_before_players_join(db, client, firebase):
    # Published free games collect nothing, as Create Game publishes them.
    game, host = hosted_game(
        db, price_per_player_cents=0, payment_collection_type="none"
    )

    paid = edit(client, firebase, host, game, price_per_player_cents=800)
    db.refresh(game)
    paid_state = (game.price_per_player_cents, game.payment_collection_type)
    free = edit(client, firebase, host, game, price_per_player_cents=0)
    db.refresh(game)

    assert paid.status_code == 200, paid.text
    assert paid_state == (800, "external_host")
    assert free.status_code == 200, free.text
    assert (game.price_per_player_cents, game.payment_collection_type) == (0, "none")


@pytest.mark.page("F18", 3)
def test_location_change_reuses_a_facility_or_creates_a_distinct_one(
    db, client, firebase
):
    game, host = hosted_game(db)
    old_venue_id = game.venue_id
    existing = make_venue(
        db, name="Union Park", address_line_1="100 Shared Street", postal_code="60601"
    )
    venues_before = count(db, Venue)

    reuse = edit(
        client,
        firebase,
        host,
        game,
        **location("  union   park. ", "100 shared street"),
    )
    db.refresh(game)
    reused_venue_id = game.venue_id
    distinct = edit(client, firebase, host, game, **location("Union Park Annex"))
    db.refresh(game)

    assert reuse.status_code == 200, reuse.text
    assert reused_venue_id == existing.id
    assert distinct.status_code == 200, distinct.text
    assert game.venue_id not in {existing.id, old_venue_id}
    assert count(db, Venue) == venues_before + 1
    db.refresh(existing)
    assert existing.name == "Union Park"
    assert db.get(Venue, old_venue_id) is not None


@pytest.mark.page("F18", 3)
def test_neighborhood_alone_does_not_create_another_facility(db, client, firebase):
    game, host = hosted_game(db)
    # Relabeling the neighborhood is not a location change, so it stays
    # editable after players join.
    player_joins(db, game)
    venue = db.get(Venue, game.venue_id)
    venues_before = count(db, Venue)

    response = edit(
        client,
        firebase,
        host,
        game,
        **location(venue.name, venue.address_line_1),
        neighborhood="West Loop",
    )

    assert response.status_code == 200, response.text
    db.refresh(game)
    assert game.venue_id == venue.id
    assert game.neighborhood_snapshot == "West Loop"
    assert count(db, Venue) == venues_before


@pytest.mark.page("F18", 4)
def test_capacity_increase_and_notes_save_after_players_join(db, client, firebase):
    game, host = hosted_game(db, total_spots=14)
    confirmed = player_joins(db, game)
    waitlisted = player_joins(db, game, "waitlisted")

    response = edit(client, firebase, host, game, total_spots=16, game_notes="Field 3.")

    assert response.status_code == 200, response.text
    assert (response.json()["total_spots"], response.json()["game_notes"]) == (
        16,
        "Field 3.",
    )
    db.refresh(game)
    assert (game.total_spots, game.game_notes) == (16, "Field 3.")
    db.refresh(confirmed)
    db.refresh(waitlisted)
    assert (confirmed.participant_status, waitlisted.participant_status) == (
        "confirmed",
        "waitlisted",
    )


@pytest.mark.page("F18", 4)
def test_player_group_and_skill_level_stay_editable_after_players_join(
    db, client, firebase
):
    game, host = hosted_game(db)
    player_joins(db, game)

    response = edit(
        client, firebase, host, game, game_player_group="women", skill_level="advanced"
    )

    assert response.status_code == 200, response.text
    assert (response.json()["game_player_group"], response.json()["skill_level"]) == (
        "women",
        "advanced",
    )
    db.refresh(game)
    assert (game.game_player_group, game.skill_level) == ("women", "advanced")


@pytest.mark.page("F18", 8)
@pytest.mark.parametrize(
    "participant_status", ["confirmed", "waitlisted", "pending_payment"]
)
@pytest.mark.parametrize(
    "field",
    [
        "starts_at",
        "location",
        "format_label",
        "environment_type",
        "price_per_player_cents",
    ],
)
def test_protected_fields_lock_once_a_player_is_active(
    db, client, firebase, participant_status, field
):
    game, host = hosted_game(db, price_per_player_cents=500)
    if participant_status == "pending_payment":
        make_participant(db, game=game, participant_status="pending_payment")
    else:
        player_joins(db, game, participant_status)
    changes = {
        "starts_at": {
            "starts_at": game.starts_at + timedelta(hours=1),
            "ends_at": game.ends_at + timedelta(hours=1),
        },
        "location": location("Another Field", "200 Other Street"),
        "format_label": {"format_label": "6v6", "total_spots": 12},
        "environment_type": {"environment_type": "indoor"},
        "price_per_player_cents": {"price_per_player_cents": 700},
    }[field]
    before = (
        game.starts_at,
        game.ends_at,
        game.venue_id,
        game.format_label,
        game.total_spots,
        game.environment_type,
    )

    response = edit(client, firebase, host, game, **changes)

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Date, time, location, format, indoor/outdoor, and price cannot be changed "
        "after players have joined."
    )
    db.refresh(game)
    assert (
        game.starts_at,
        game.ends_at,
        game.venue_id,
        game.format_label,
        game.total_spots,
        game.environment_type,
    ) == before
    assert game.price_per_player_cents == 500


@pytest.mark.page("F18", 8)
@pytest.mark.parametrize(
    "participant_status", ["cancelled", "late_cancelled", "removed", "refunded"]
)
def test_a_player_who_has_left_does_not_lock_the_game(
    db, client, firebase, participant_status
):
    game, host = hosted_game(db)
    make_participant(db, game=game, participant_status=participant_status)

    response = edit(client, firebase, host, game, environment_type="indoor")

    assert response.status_code == 200, response.text
    db.refresh(game)
    assert game.environment_type == "indoor"


@pytest.mark.page("F18", 9)
def test_capacity_cannot_drop_after_players_join(db, client, firebase):
    game, host = hosted_game(db, total_spots=16)
    player_joins(db, game)

    response = edit(client, firebase, host, game, total_spots=15)

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Capacity can only be increased after players have joined."
    )
    db.refresh(game)
    assert game.total_spots == 16


@pytest.mark.page("F18", 9)
def test_price_cannot_change_after_a_paid_booking(db, client, firebase):
    game, host = hosted_game(db, price_per_player_cents=500)
    booking = make_booking(db, game=game)
    db.add(
        Payment(
            id=uuid.uuid4(),
            payer_user_id=booking.buyer_user_id,
            booking_id=booking.id,
            payment_type="booking",
            provider="stripe",
            idempotency_key=f"test-payment-{uuid.uuid4().hex}",
            amount_cents=500,
            currency="USD",
            payment_status="succeeded",
            paid_at=database_now(db),
        )
    )
    booking.booking_status = "cancelled"
    booking.cancelled_at = database_now(db)
    booking.reservation_status = "released"
    db.commit()

    response = edit(client, firebase, host, game, price_per_player_cents=600)

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Price cannot be changed after a booking payment exists."
    )
    db.refresh(game)
    assert game.price_per_player_cents == 500


@pytest.mark.page("F18", 10)
def test_invalid_schedule_or_capacity_is_not_saved(db, client, firebase):
    game, host = hosted_game(db, total_spots=14)
    original_end = game.ends_at

    end_before_start = edit(
        client, firebase, host, game, ends_at=game.starts_at - timedelta(minutes=30)
    )
    too_many_spots = edit(client, firebase, host, game, total_spots=500)

    assert end_before_start.status_code == 400
    assert (
        end_before_start.json()["detail"] == "ends_at must be greater than starts_at."
    )
    assert too_many_spots.status_code == 422
    db.refresh(game)
    assert (game.ends_at, game.total_spots) == (original_end, 14)


@pytest.mark.page("F18", 10)
def test_incomplete_location_is_not_saved(db, client, firebase):
    game, host = hosted_game(db)
    venue_id = game.venue_id

    response = edit(
        client, firebase, host, game, **{**location("New Field"), "city": ""}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Location edits require venue name, street, city, state, and postal code."
    )
    db.refresh(game)
    assert game.venue_id == venue_id


@pytest.mark.page("F18", 10)
def test_paid_game_needs_a_host_payment_method(db, client, firebase):
    game, host = hosted_game(db, price_per_player_cents=500)
    make_community_game_detail(db, game=game)

    response = client.put(
        f"/community-game-details/games/{game.id}/host-edit",
        headers=firebase.sign_in(host),
        json={"payment_methods_snapshot": []},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Paid community games require at least one host payment method."
    )
    assert saved_payment_methods(db, game) == [{"type": "venmo", "value": "@test-host"}]


def local_start(db, days_ahead):
    """6 PM Chicago time, ``days_ahead`` days after today's Chicago date."""
    today = database_now(db).astimezone(CHICAGO).date()
    return datetime.combine(today + timedelta(days=days_ahead), time(18), CHICAGO)


@pytest.mark.page("F18", 12)
def test_a_start_exactly_21_days_ahead_saves(db, client, firebase):
    game, host = hosted_game(db)
    starts_at = local_start(db, 21)

    response = edit(
        client,
        firebase,
        host,
        game,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
    )

    assert response.status_code == 200, response.text
    db.refresh(game)
    assert game.starts_on_local == starts_at.date()


@pytest.mark.page("F18", 12)
def test_a_start_22_days_ahead_is_rejected(db, client, firebase):
    game, host = hosted_game(db)
    original_start = game.starts_at
    starts_at = local_start(db, 22)

    response = edit(
        client,
        firebase,
        host,
        game,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Community games can start no more than 21 days ahead."
    )
    db.refresh(game)
    assert game.starts_at == original_start
