"""F18 what a host can change, before and after players join."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select

from backend.models import CommunityGameDetail, Game, HostPublishFee, Venue
from backend.tests.factories import (
    make_booking,
    make_community_game_detail,
    make_game,
    make_participant,
    make_user,
    make_venue,
)

CHICAGO = ZoneInfo("America/Chicago")


def hosted_game(clock, db, host=None, **overrides):
    """A published, active community game two days out, built as publishing builds it.

    The host holds a confirmed place on the roster; the title, address, and
    host guest limit follow the venue and format; and the community details
    list the host's payment method, or none for a free game.
    """
    # Pass an existing host to build that host another game.
    host = host or make_user(db, hosting_status="eligible")
    venue = make_venue(db)
    format_label = overrides.get("format_label", "7v7")
    values = {
        "host": host,
        "venue": venue,
        "starts_at": clock.now + timedelta(days=2),
        "title": f"{venue.name} {format_label}",
        "address_snapshot": (
            f"{venue.address_line_1}, {venue.city}, {venue.state} {venue.postal_code}"
        ),
        # The format's side size less one, as publishing sets it.
        "host_guest_max": int(format_label.split("v")[0]) - 1,
    }
    values.update(overrides)
    game = make_game(db, game_type="community", **values)
    make_participant(db, game=game, user=host, participant_type="host")
    is_paid = game.price_per_player_cents > 0
    make_community_game_detail(
        db,
        game=game,
        payment_methods_snapshot=[{"type": "venmo", "value": "@test-host"}]
        if is_paid
        else [],
    )
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
def test_permitted_changes_save_before_players_join(clock, db, client, firebase):
    game, host = hosted_game(clock, db)

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


@pytest.mark.page("F18", 2)
def test_saving_creates_no_new_game_and_no_publish_fee(clock, db, client, firebase):
    game, host = hosted_game(clock, db)
    games_before, fees_before = count(db, Game), count(db, HostPublishFee)

    game_response = edit(client, firebase, host, game, game_notes="Field 3.")
    details_response = client.put(
        f"/community-game-details/games/{game.id}/host-edit",
        headers=firebase.sign_in(host),
        json={"payment_methods_snapshot": [{"type": "cash_app", "value": "$host"}]},
    )

    assert (game_response.status_code, details_response.status_code) == (200, 200)
    assert (count(db, Game), count(db, HostPublishFee)) == (games_before, fees_before)


def free_game(clock, db):
    """A published free game, which collects nothing and lists no payment method.

    Create Game publishes a free game this way.
    """
    game, host = hosted_game(
        clock,
        db,
        price_per_player_cents=0,
        payment_collection_type="none",
    )
    return game, host


@pytest.mark.page("F18", 2)
def test_a_free_game_can_become_paid_and_back_before_players_join(
    clock, db, client, firebase
):
    game, host = free_game(clock, db)
    # As Edit Game does for a free game becoming paid, the payment method saves first.
    details = client.put(
        f"/community-game-details/games/{game.id}/host-edit",
        headers=firebase.sign_in(host),
        json={"payment_methods_snapshot": [{"type": "venmo", "value": "@host"}]},
    )

    paid = edit(client, firebase, host, game, price_per_player_cents=800)
    db.refresh(game)
    paid_state = (game.price_per_player_cents, game.payment_collection_type)
    free = edit(client, firebase, host, game, price_per_player_cents=0)
    db.refresh(game)

    assert details.status_code == 200, details.text
    assert paid.status_code == 200, paid.text
    assert paid_state == (800, "external_host")
    assert free.status_code == 200, free.text
    assert (game.price_per_player_cents, game.payment_collection_type) == (0, "none")


def union_park(db):
    return make_venue(
        db, name="Union Park", address_line_1="100 Shared Street", postal_code="60601"
    )


@pytest.mark.page("F18", 3)
def test_changing_to_an_existing_facility_reuses_its_venue_record(
    clock, db, client, firebase
):
    game, host = hosted_game(clock, db)
    existing = union_park(db)
    venues_before = count(db, Venue)

    # The same facility, written with different case, spacing, and a period.
    response = edit(
        client,
        firebase,
        host,
        game,
        **location("  union   park. ", "100 shared street"),
    )

    assert response.status_code == 200, response.text
    db.refresh(game)
    assert game.venue_id == existing.id
    assert count(db, Venue) == venues_before


@pytest.mark.page("F18", 3)
def test_a_distinct_facility_at_a_shared_address_gets_a_new_venue_record(
    clock, db, client, firebase
):
    game, host = hosted_game(clock, db)
    existing = union_park(db)
    old_venue_id = game.venue_id
    venues_before = count(db, Venue)

    response = edit(client, firebase, host, game, **location("Union Park Annex"))

    assert response.status_code == 200, response.text
    db.refresh(game)
    assert game.venue_id not in {existing.id, old_venue_id}
    assert db.get(Venue, game.venue_id).name == "Union Park Annex"
    assert count(db, Venue) == venues_before + 1


@pytest.mark.page("F18", 3)
def test_a_location_change_leaves_the_old_venue_and_its_other_games_alone(
    clock, db, client, firebase
):
    game, host = hosted_game(clock, db)
    old_venue = db.get(Venue, game.venue_id)
    old_identity = (old_venue.name, old_venue.address_line_1, old_venue.postal_code)
    other_game = make_game(db, venue=old_venue, starts_at=clock.now + timedelta(days=4))

    response = edit(client, firebase, host, game, **location("Union Park Annex"))

    assert response.status_code == 200, response.text
    db.refresh(old_venue)
    db.refresh(other_game)
    assert (old_venue.name, old_venue.address_line_1, old_venue.postal_code) == (
        old_identity
    )
    assert other_game.venue_id == old_venue.id


@pytest.mark.page("F18", 3)
def test_neighborhood_alone_does_not_create_another_facility(
    clock, db, client, firebase
):
    game, host = hosted_game(clock, db)
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
def test_capacity_can_increase_after_players_join_and_the_roster_stays(
    clock, db, client, firebase
):
    game, host = hosted_game(clock, db, total_spots=14)
    confirmed = player_joins(db, game)
    waitlisted = player_joins(db, game, "waitlisted")

    response = edit(client, firebase, host, game, total_spots=16)

    assert response.status_code == 200, response.text
    db.refresh(game)
    assert game.total_spots == 16
    db.refresh(confirmed)
    db.refresh(waitlisted)
    assert (confirmed.participant_status, waitlisted.participant_status) == (
        "confirmed",
        "waitlisted",
    )


@pytest.mark.page("F18", 4)
def test_notes_save_after_a_player_joins(clock, db, client, firebase):
    game, host = hosted_game(clock, db)
    player_joins(db, game)

    response = edit(client, firebase, host, game, game_notes="Field 3.")

    assert response.status_code == 200, response.text
    db.refresh(game)
    assert game.game_notes == "Field 3."


@pytest.mark.page("F18", 4)
def test_player_group_and_skill_level_stay_editable_after_players_join(
    clock, db, client, firebase
):
    game, host = hosted_game(clock, db)
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
# A community game takes no in-app payment, so it never has a pending-payment
# place; a non-host player is confirmed or waitlisted.
@pytest.mark.parametrize("participant_status", ["confirmed", "waitlisted"])
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
    clock, db, client, firebase, participant_status, field
):
    game, host = hosted_game(clock, db, price_per_player_cents=500)
    player_joins(db, game, participant_status)
    changes = {
        "starts_at": {
            "starts_at": game.starts_at + timedelta(hours=1),
            "ends_at": game.ends_at + timedelta(hours=1),
        },
        "location": location("Another Field", "200 Other Street"),
        # 6v6 fits the game's 14 spots, so capacity stays the same.
        "format_label": {"format_label": "6v6"},
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
# The places a community game can leave behind; refunds happen only for
# official games, which take in-app payment.
@pytest.mark.parametrize(
    "participant_status", ["cancelled", "late_cancelled", "removed"]
)
def test_a_player_who_has_left_does_not_lock_the_game(
    clock, db, client, firebase, participant_status
):
    game, host = hosted_game(clock, db)
    make_participant(db, game=game, participant_status=participant_status)

    response = edit(client, firebase, host, game, environment_type="indoor")

    assert response.status_code == 200, response.text
    db.refresh(game)
    assert game.environment_type == "indoor"


@pytest.mark.page("F18", 9)
def test_capacity_cannot_drop_after_players_join(clock, db, client, firebase):
    game, host = hosted_game(clock, db, total_spots=16)
    player_joins(db, game)

    response = edit(client, firebase, host, game, total_spots=15)

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Capacity can only be increased after players have joined."
    )
    db.refresh(game)
    assert game.total_spots == 16


@pytest.mark.page("F18", 10)
def test_an_invalid_schedule_is_not_saved(clock, db, client, firebase):
    game, host = hosted_game(clock, db)
    original_start = game.starts_at
    past_start = clock.now - timedelta(hours=1)

    response = edit(
        client,
        firebase,
        host,
        game,
        starts_at=past_start,
        ends_at=past_start + timedelta(hours=1),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Game start time must be in the future."
    db.refresh(game)
    assert game.starts_at == original_start


@pytest.mark.page("F18", 10)
def test_an_invalid_capacity_is_not_saved(clock, db, client, firebase):
    game, host = hosted_game(clock, db, total_spots=14)

    response = edit(client, firebase, host, game, total_spots=500)

    assert response.status_code == 422
    db.refresh(game)
    assert game.total_spots == 14


@pytest.mark.page("F18", 10)
def test_incomplete_location_is_not_saved(clock, db, client, firebase):
    game, host = hosted_game(clock, db)
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
def test_paid_game_needs_a_host_payment_method(clock, db, client, firebase):
    game, host = hosted_game(clock, db, price_per_player_cents=500)

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


@pytest.mark.page("F18", 10)
def test_more_than_two_host_payment_methods_are_not_saved(clock, db, client, firebase):
    game, host = hosted_game(clock, db, price_per_player_cents=500)

    response = client.put(
        f"/community-game-details/games/{game.id}/host-edit",
        headers=firebase.sign_in(host),
        json={
            "payment_methods_snapshot": [
                {"type": "venmo", "value": "@host"},
                {"type": "cash_app", "value": "$host"},
                {"type": "zelle", "value": "host@example.test"},
            ]
        },
    )

    assert response.status_code == 422
    assert saved_payment_methods(db, game) == [{"type": "venmo", "value": "@test-host"}]


@pytest.mark.page("F18", 10)
def test_moving_to_a_date_with_another_of_the_hosts_games_is_rejected(
    clock, db, client, firebase
):
    game, host = hosted_game(clock, db)
    # The host's other game is at 6 PM Chicago time in five days; this edit
    # moves the first game to 8 PM that same Chicago day.
    hosted_game(clock, db, host=host, starts_at=local_start(clock, 5))
    original_start = game.starts_at
    new_start = local_start(clock, 5) + timedelta(hours=2)

    response = edit(
        client,
        firebase,
        host,
        game,
        starts_at=new_start,
        ends_at=new_start + timedelta(hours=1),
    )

    assert response.status_code == 409
    assert (
        response.json()["detail"] == "You already have a community game on this date."
    )
    db.refresh(game)
    assert game.starts_at == original_start


def local_start(clock, days_ahead):
    """6 PM Chicago time, ``days_ahead`` days after today's Chicago date."""
    today = clock.now.astimezone(CHICAGO).date()
    return datetime.combine(today + timedelta(days=days_ahead), time(18), CHICAGO)


@pytest.mark.page("F18", 12)
def test_a_start_exactly_21_days_ahead_saves(clock, db, client, firebase):
    game, host = hosted_game(clock, db)
    starts_at = local_start(clock, 21)

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
def test_a_start_22_days_ahead_is_rejected(clock, db, client, firebase):
    game, host = hosted_game(clock, db)
    original_start = game.starts_at
    starts_at = local_start(clock, 22)

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


@pytest.mark.page("F18", 17)
@pytest.mark.parametrize("change", ["date", "location"])
def test_the_hosts_own_guests_do_not_lock_date_or_location_changes(
    clock, db, client, firebase, change
):
    game, host = hosted_game(clock, db)
    # Guests the host adds to their own game, as Game Details adds them.
    make_participant(db, game=game, user=host, participant_type="guest")
    make_participant(db, game=game, user=host, participant_type="guest")
    new_start = game.starts_at + timedelta(hours=1)
    changes = {
        "date": {"starts_at": new_start, "ends_at": game.ends_at + timedelta(hours=1)},
        "location": location("Another Field", "200 Other Street"),
    }[change]

    response = edit(client, firebase, host, game, **changes)

    assert response.status_code == 200, response.text
    db.refresh(game)
    if change == "date":
        assert game.starts_at == new_start
    else:
        assert db.get(Venue, game.venue_id).name == "Another Field"


@pytest.mark.page("F18", 17)
def test_capacity_cannot_drop_below_the_places_the_host_and_their_guests_hold(
    clock, db, client, firebase
):
    game, host = hosted_game(
        clock,
        db,
        format_label="11v11",
        total_spots=22,
    )
    # The host and the ten guests an 11v11 host may add hold 11 places.
    for _ in range(10):
        make_participant(db, game=game, user=host, participant_type="guest")

    # 5v5 allows 10 spots, one fewer than the places already held.
    response = edit(client, firebase, host, game, format_label="5v5", total_spots=10)

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Capacity cannot drop below the places already taken."
    )
    db.refresh(game)
    assert (game.format_label, game.total_spots) == ("11v11", 22)


@pytest.mark.page("F18", 19)
def test_a_free_game_cannot_become_paid_without_a_host_payment_method(
    clock, db, client, firebase
):
    game, host = free_game(clock, db)

    response = edit(client, firebase, host, game, price_per_player_cents=800)

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Add a host payment method before charging players."
    )
    db.refresh(game)
    assert (game.price_per_player_cents, game.payment_collection_type) == (0, "none")


@pytest.mark.page("F18", 2)
def test_edited_game_notes_appear_on_game_details(clock, db, client, firebase):
    game, host = hosted_game(clock, db)

    response = edit(client, firebase, host, game, game_notes="Field 3, north end.")

    assert response.status_code == 200, response.text
    # Game Details shows the game's description as its notes.
    shown = client.get(f"/games/{game.id}", headers=firebase.sign_in(host))
    assert shown.json()["description"] == "Field 3, north end."
    db.refresh(game)
    assert (game.game_notes, game.description) == (
        "Field 3, north end.",
        "Field 3, north end.",
    )


@pytest.mark.page("F18", 10)
# Just outside each end of Create Game's 3v3 to 11v11 range.
@pytest.mark.parametrize("format_label", ["2v2", "12v12"])
def test_a_format_outside_3v3_to_11v11_is_not_saved(
    clock, db, client, firebase, format_label
):
    # 24 spots would fit either format, so only the format range can refuse it.
    game, host = hosted_game(clock, db, total_spots=24)

    response = edit(client, firebase, host, game, format_label=format_label)

    assert response.status_code == 422
    db.refresh(game)
    assert game.format_label == "7v7"


@pytest.mark.page("F18", 18)
def test_a_refused_game_update_after_the_payment_methods_save_leaves_the_game_free(
    clock, db, client, firebase
):
    game, host = free_game(clock, db)
    # The host already has a game at 6 PM Chicago time in five days.
    hosted_game(clock, db, host=host, starts_at=local_start(clock, 5))
    new_start = local_start(clock, 5) + timedelta(hours=2)

    # As Edit Game does for a free game becoming paid, the payment method saves
    # first; the game update then moves the game onto that same day.
    details = client.put(
        f"/community-game-details/games/{game.id}/host-edit",
        headers=firebase.sign_in(host),
        json={"payment_methods_snapshot": [{"type": "venmo", "value": "@host"}]},
    )
    update = edit(
        client,
        firebase,
        host,
        game,
        price_per_player_cents=800,
        starts_at=new_start,
        ends_at=new_start + timedelta(hours=1),
    )

    assert (details.status_code, update.status_code) == (200, 409)
    db.refresh(game)
    assert (game.price_per_player_cents, game.payment_collection_type) == (0, "none")
    assert saved_payment_methods(db, game) == [{"type": "venmo", "value": "@host"}]
