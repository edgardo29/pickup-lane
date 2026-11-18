"""F18 who can open and save Edit Game, and for which games."""

from datetime import timedelta

import pytest

from backend.models import CommunityGameDetail, Game
from backend.tests.conftest import database_now
from backend.tests.factories import (
    make_community_game_detail,
    make_game,
    make_participant,
    make_user,
)


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


def edit_notes(client, headers, game, notes="Bring water."):
    return client.patch(
        f"/games/{game.id}/host-edit", headers=headers, json={"game_notes": notes}
    )


@pytest.mark.page("F18", 1)
def test_owner_loads_the_community_details_for_editing(db, client, firebase):
    game, host = hosted_game(db)
    make_community_game_detail(db, game=game)

    response = client.get(
        f"/community-game-details/games/{game.id}/host-edit",
        headers=firebase.sign_in(host),
    )

    assert response.status_code == 200, response.text
    assert response.json()["payment_methods_snapshot"] == [
        {"type": "venmo", "value": "@test-host"}
    ]


@pytest.mark.page("F18", 6)
def test_signed_out_visitor_cannot_edit(db, client):
    game, _host = hosted_game(db)

    response = client.patch(f"/games/{game.id}/host-edit", json={"game_notes": "x"})

    assert response.status_code == 401
    db.refresh(game)
    assert game.game_notes is None


@pytest.mark.page("F18", 6)
def test_another_user_cannot_load_or_save_the_game(db, client, firebase):
    game, _host = hosted_game(db)
    make_community_game_detail(db, game=game)
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
    assert saved_payment_methods(db, game) == [{"type": "venmo", "value": "@test-host"}]


@pytest.mark.page("F18", 6)
def test_missing_or_official_games_cannot_be_host_edited(db, client, firebase):
    host = make_user(db, hosting_status="eligible")
    official = make_game(db, starts_at=database_now(db) + timedelta(days=2))
    headers = firebase.sign_in(host)

    missing = client.patch(
        "/games/00000000-0000-4000-8000-000000000999/host-edit",
        headers=headers,
        json={"game_notes": "x"},
    )
    official_edit = edit_notes(client, headers, official)

    assert missing.status_code == 404
    assert official_edit.status_code == 400
    db.refresh(official)
    assert official.game_notes is None


@pytest.mark.page("F18", 7)
@pytest.mark.parametrize(
    "game_status", ["cancelled", "completed", "expired", "removed"]
)
def test_a_game_that_is_no_longer_active_rejects_edits(
    db, client, firebase, game_status
):
    now = database_now(db)
    status_times = {
        "cancelled": {"cancelled_at": now},
        "completed": {"completed_at": now},
    }
    game, host = hosted_game(
        db, game_status=game_status, **status_times.get(game_status, {})
    )

    response = edit_notes(client, firebase.sign_in(host), game)

    assert response.status_code == 400
    assert response.json()["detail"] == "Only published active games can be edited."
    db.refresh(game)
    assert game.game_notes is None


@pytest.mark.page("F18", 7)
@pytest.mark.parametrize("publish_status", ["draft", "archived"])
def test_an_unpublished_game_rejects_edits(db, client, firebase, publish_status):
    game, host = hosted_game(db, publish_status=publish_status, published_at=None)

    response = edit_notes(client, firebase.sign_in(host), game)

    assert response.status_code == 400
    assert response.json()["detail"] == "Only published active games can be edited."
    db.refresh(game)
    assert game.game_notes is None


@pytest.mark.page("F18", 7)
def test_a_started_game_rejects_edits(db, client, firebase):
    game, host = hosted_game(db, starts_at=database_now(db) - timedelta(minutes=1))

    response = edit_notes(client, firebase.sign_in(host), game)

    assert response.status_code == 400
    assert response.json()["detail"] == "Games cannot be edited after start time."
    db.refresh(game)
    assert game.game_notes is None


@pytest.mark.page("F18", 13)
def test_suspended_owner_can_still_edit_an_existing_game(db, client, firebase):
    game, host = hosted_game(db, price_per_player_cents=500)
    make_community_game_detail(db, game=game)
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
    publish = client.post("/community-games/publish", headers=headers, json={})

    assert [load.status_code, save.status_code, details.status_code] == [200, 200, 200]
    assert publish.status_code == 403
    db.refresh(game)
    assert game.game_notes == "Bring water."
    assert saved_payment_methods(db, game) == [{"type": "cash_app", "value": "$host"}]
    assert db.query(Game).filter(Game.host_user_id == host.id).count() == 1
