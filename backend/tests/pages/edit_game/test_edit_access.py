"""F18 who can open and save Edit Game, and for which games."""

from datetime import timedelta

import pytest

from backend.models import CommunityGameDetail, Game
from backend.tests.factories import (
    make_community_game_detail,
    make_game,
    make_participant,
    make_user,
    make_venue,
)


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


VENMO = {"type": "venmo", "value": "@test-host"}
CASH_APP = {"type": "cash_app", "value": "$host"}


def edit_notes(client, headers, game, notes="Bring water."):
    return client.patch(
        f"/games/{game.id}/host-edit", headers=headers, json={"game_notes": notes}
    )


def edit_details(client, headers, game, method=CASH_APP):
    return client.put(
        f"/community-game-details/games/{game.id}/host-edit",
        headers=headers,
        json={"payment_methods_snapshot": [method]},
    )


@pytest.mark.page("F18", 1)
def test_owner_loads_the_community_details_for_editing(clock, db, client, firebase):
    game, host = hosted_game(clock, db)

    response = client.get(
        f"/community-game-details/games/{game.id}/host-edit",
        headers=firebase.sign_in(host),
    )

    assert response.status_code == 200, response.text
    assert response.json()["payment_methods_snapshot"] == [
        {"type": "venmo", "value": "@test-host"}
    ]


@pytest.mark.page("F18", 6)
def test_signed_out_visitor_cannot_load_or_save_an_edit(clock, db, client):
    game, _host = hosted_game(clock, db)

    load = client.get(f"/community-game-details/games/{game.id}/host-edit")
    save = edit_notes(client, {}, game)
    details = edit_details(client, {}, game)

    assert [load.status_code, save.status_code, details.status_code] == [401, 401, 401]
    db.refresh(game)
    assert game.game_notes is None
    assert saved_payment_methods(db, game) == [VENMO]


@pytest.mark.page("F18", 6)
def test_another_user_cannot_load_or_save_the_game(clock, db, client, firebase):
    game, _host = hosted_game(clock, db)
    headers = firebase.sign_in(make_user(db))

    load = client.get(
        f"/community-game-details/games/{game.id}/host-edit", headers=headers
    )
    save = edit_notes(client, headers, game)
    details = client.put(
        f"/community-game-details/games/{game.id}/host-edit",
        headers=headers,
        json={"payment_methods_snapshot": []},
    )

    assert [load.status_code, save.status_code, details.status_code] == [403, 403, 403]
    db.refresh(game)
    assert game.game_notes is None
    assert saved_payment_methods(db, game) == [VENMO]


@pytest.mark.page("F18", 6)
def test_a_missing_game_cannot_be_edited(db, client, firebase):
    headers = firebase.sign_in(make_user(db, hosting_status="eligible"))
    missing_game_id = "00000000-0000-4000-8000-000000000999"

    save = client.patch(
        f"/games/{missing_game_id}/host-edit",
        headers=headers,
        json={"game_notes": "x"},
    )
    details = client.put(
        f"/community-game-details/games/{missing_game_id}/host-edit",
        headers=headers,
        json={"payment_methods_snapshot": [CASH_APP]},
    )

    assert [save.status_code, details.status_code] == [404, 404]
    assert save.json()["detail"] == details.json()["detail"] == "Game not found."
    assert db.query(CommunityGameDetail).count() == 0


@pytest.mark.page("F18", 6)
def test_an_official_game_cannot_be_edited_here(clock, db, client, firebase):
    # Staff create official games, which have no host.
    official = make_game(db, starts_at=clock.now + timedelta(days=2))
    headers = firebase.sign_in(make_user(db, hosting_status="eligible"))

    save = edit_notes(client, headers, official)
    details = edit_details(client, headers, official)

    assert [save.status_code, details.status_code] == [400, 400]
    assert save.json()["detail"] == "Only community games can be edited by hosts."
    assert details.json()["detail"] == (
        "Community game details require a community game."
    )
    db.refresh(official)
    assert official.game_notes is None
    assert db.query(CommunityGameDetail).filter_by(game_id=official.id).count() == 0


@pytest.mark.page("F18", 7)
@pytest.mark.parametrize(
    "game_status", ["cancelled", "completed", "expired", "removed"]
)
def test_a_game_that_is_no_longer_active_rejects_edits(
    clock, db, client, firebase, game_status
):
    now = clock.now
    status_times = {
        "cancelled": {"cancelled_at": now},
        "completed": {"completed_at": now},
    }
    game, host = hosted_game(
        clock, db, game_status=game_status, **status_times.get(game_status, {})
    )
    headers = firebase.sign_in(host)

    save = edit_notes(client, headers, game)
    details = edit_details(client, headers, game)

    assert [save.status_code, details.status_code] == [400, 400]
    assert (
        save.json()["detail"]
        == details.json()["detail"]
        == ("Only published active games can be edited.")
    )
    db.refresh(game)
    assert game.game_notes is None
    assert saved_payment_methods(db, game) == [VENMO]


@pytest.mark.page("F18", 7)
@pytest.mark.parametrize("publish_status", ["draft", "archived"])
def test_an_unpublished_game_rejects_edits(clock, db, client, firebase, publish_status):
    game, host = hosted_game(
        clock, db, publish_status=publish_status, published_at=None
    )
    headers = firebase.sign_in(host)

    save = edit_notes(client, headers, game)
    details = edit_details(client, headers, game)

    assert [save.status_code, details.status_code] == [400, 400]
    assert (
        save.json()["detail"]
        == details.json()["detail"]
        == ("Only published active games can be edited.")
    )
    db.refresh(game)
    assert game.game_notes is None
    assert saved_payment_methods(db, game) == [VENMO]


@pytest.mark.page("F18", 7)
# At the exact start moment and after it.
@pytest.mark.parametrize("minutes_since_start", [0, 1])
def test_a_started_game_rejects_edits(clock, db, client, firebase, minutes_since_start):
    game, host = hosted_game(
        clock, db, starts_at=clock.now - timedelta(minutes=minutes_since_start)
    )
    headers = firebase.sign_in(host)

    save = edit_notes(client, headers, game)
    details = edit_details(client, headers, game)

    assert [save.status_code, details.status_code] == [400, 400]
    assert (
        save.json()["detail"]
        == details.json()["detail"]
        == ("Games cannot be edited after start time.")
    )
    db.refresh(game)
    assert game.game_notes is None
    assert saved_payment_methods(db, game) == [VENMO]


@pytest.mark.page("F18", 13)
def test_suspended_owner_can_still_edit_an_existing_game(clock, db, client, firebase):
    game, host = hosted_game(clock, db, price_per_player_cents=500)
    host.account_status = "suspended"
    db.commit()
    headers = firebase.sign_in(host)

    load = client.get(
        f"/community-game-details/games/{game.id}/host-edit", headers=headers
    )
    save = edit_notes(client, headers, game)
    details = client.put(
        f"/community-game-details/games/{game.id}/host-edit",
        headers=headers,
        json={"payment_methods_snapshot": [{"type": "cash_app", "value": "$host"}]},
    )

    assert [load.status_code, save.status_code, details.status_code] == [200, 200, 200]
    db.refresh(game)
    assert game.game_notes == "Bring water."
    assert saved_payment_methods(db, game) == [CASH_APP]


def publish_request(starts_at):
    """A complete, free community game a host could publish."""
    return {
        "starts_at": starts_at.isoformat(),
        "ends_at": (starts_at + timedelta(hours=1)).isoformat(),
        "format_label": "7v7",
        "environment_type": "outdoor",
        "total_spots": 14,
        "price_per_player_cents": 0,
        "venue": {
            "name": "Union Park",
            "address_line_1": "1501 W Randolph St",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60607",
        },
    }


@pytest.mark.page("F18", 13)
def test_a_suspended_owner_still_cannot_publish_a_new_game(clock, db, client, firebase):
    game, host = hosted_game(clock, db)
    host.account_status = "suspended"
    db.commit()

    response = client.post(
        "/community-games/publish",
        headers=firebase.sign_in(host),
        json=publish_request(game.starts_at + timedelta(days=3)),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Active account required."
    assert db.query(Game).filter(Game.host_user_id == host.id).count() == 1


@pytest.mark.page("F18", 13)
def test_a_host_restricted_from_publishing_can_still_edit_an_existing_game(
    clock, db, client, firebase
):
    game, host = hosted_game(clock, db)
    host.hosting_status = "restricted"
    db.commit()
    headers = firebase.sign_in(host)

    save = edit_notes(client, headers, game)
    details = edit_details(client, headers, game)

    assert [save.status_code, details.status_code] == [200, 200]
    db.refresh(game)
    assert game.game_notes == "Bring water."
    assert saved_payment_methods(db, game) == [CASH_APP]


@pytest.mark.page("F18", 16)
def test_an_owner_whose_email_is_not_verified_cannot_save_an_edit(
    clock, db, client, firebase
):
    game, host = hosted_game(clock, db)
    headers = firebase.sign_in(host, email_verified=False)

    save = edit_notes(client, headers, game)
    details = edit_details(client, headers, game)

    assert [save.status_code, details.status_code] == [403, 403]
    assert (
        save.json()["detail"]
        == details.json()["detail"]
        == ("Verified email required.")
    )
    db.refresh(game)
    assert game.game_notes is None
    assert saved_payment_methods(db, game) == [VENMO]


@pytest.mark.page("F18", 1)
@pytest.mark.parametrize("case", ["visible", "hidden", "suspended", "unverified"])
def test_the_owner_loads_their_game_with_the_host_shown(
    clock, db, client, firebase, case
):
    # Edit Game opens the form only when the game names this owner as its host.
    visibility = "hidden" if case == "hidden" else "visible"
    game, host = hosted_game(clock, db, public_visibility_status=visibility)
    if case == "suspended":
        host.account_status = "suspended"
        db.commit()
    headers = firebase.sign_in(host, email_verified=case != "unverified")

    response = client.get(f"/games/{game.id}", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["host_user_id"] == str(host.id)
