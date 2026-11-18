"""F16 page access, roster boundaries, and community-game lifecycle."""

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from backend.models import GameParticipant, Notification
from backend.tests.factories import (
    make_booking,
    make_community_game_detail,
    make_game,
    make_participant,
    make_user,
)


def ready_player(db, **overrides):
    return make_user(db, date_of_birth=date(1990, 1, 1), **overrides)


def participant_count(db, game):
    return db.scalar(
        select(func.count(GameParticipant.id)).where(GameParticipant.game_id == game.id)
    )


@pytest.mark.page("F16", 1)
def test_visible_game_details_are_public_with_anonymous_roster_totals(
    clock, db, client
):
    for game_type in ("official", "community"):
        game = make_game(
            db, game_type=game_type, starts_at=clock.now + timedelta(days=2)
        )
        make_participant(db, game=game)

        response = client.get(f"/games/{game.id}")

        assert response.status_code == 200, response.text
        assert response.json()["game_type"] == game_type
        assert response.json()["roster_counts"]["occupied_spots"] == 1
        assert response.json()["roster_counts"]["spots_remaining"] == 13


@pytest.mark.page("F16", 2)
def test_community_payment_text_is_returned_only_when_moderation_allows_it(
    clock, db, client
):
    game = make_game(db, game_type="community", starts_at=clock.now + timedelta(days=2))
    detail = make_community_game_detail(
        db, game=game, payment_instructions_snapshot="Pay host before kickoff"
    )
    path = f"/community-game-details?game_id={game.id}"

    visible = client.get(path)
    detail.payment_text_moderation_status = "hidden"
    detail.payment_text_hidden_at = clock.now
    detail.payment_text_hidden_reason = "Test moderation decision"
    db.commit()
    hidden = client.get(path)

    assert visible.status_code == 200, visible.text
    assert (
        visible.json()[0]["payment_instructions_snapshot"] == "Pay host before kickoff"
    )
    assert hidden.status_code == 200, hidden.text
    assert hidden.json()[0]["payment_instructions_snapshot"] is None
    assert hidden.json()[0]["payment_methods_snapshot"] == []


@pytest.mark.page("F16", 3)
def test_player_names_require_sign_in_but_any_signed_in_viewer_can_see_public_roster(
    clock, db, client, firebase
):
    game = make_game(db, starts_at=clock.now + timedelta(days=2))
    make_participant(db, game=game, display_name_snapshot="Roster Player")
    viewer = ready_player(db)
    path = f"/games/{game.id}/participants"

    anonymous = client.get(path)
    signed_in = client.get(path, headers=firebase.sign_in(viewer))

    assert anonymous.status_code == 401
    assert signed_in.status_code == 200, signed_in.text
    assert [row["display_name_snapshot"] for row in signed_in.json()] == [
        "Roster Player"
    ]


@pytest.mark.page("F16", 12)
def test_hidden_game_and_host_payment_details_are_not_disclosed_to_strangers(
    clock, db, client, firebase
):
    game = make_game(
        db,
        game_type="community",
        starts_at=clock.now + timedelta(days=2),
        public_visibility_status="hidden",
    )
    make_community_game_detail(db, game=game)
    stranger = ready_player(db)
    headers = firebase.sign_in(stranger)

    assert client.get(f"/games/{game.id}").status_code == 404
    assert client.get(f"/games/{game.id}", headers=headers).status_code == 404
    assert (
        client.get(f"/games/{game.id}/participants", headers=headers).status_code == 404
    )
    details = client.get(f"/community-game-details?game_id={game.id}", headers=headers)
    assert details.status_code == 404


@pytest.mark.page("F16", 13)
def test_hidden_game_remains_visible_to_host_player_and_admin(
    clock, db, client, firebase
):
    host = ready_player(db, hosting_status="eligible")
    game = make_game(
        db,
        game_type="community",
        host=host,
        starts_at=clock.now + timedelta(days=2),
        public_visibility_status="hidden",
    )
    player = ready_player(db)
    make_participant(db, game=game, user=player)
    admin = ready_player(db, role="admin")

    for viewer in (host, player, admin):
        headers = firebase.sign_in(viewer)
        assert client.get(f"/games/{game.id}", headers=headers).status_code == 200
        assert (
            client.get(f"/games/{game.id}/participants", headers=headers).status_code
            == 200
        )


@pytest.mark.page("F16", 24)
@pytest.mark.page("F16", 25)
def test_paused_game_blocks_new_join_and_guest_add_but_allows_existing_player_to_leave(
    clock, db, client, firebase
):
    host = ready_player(db, hosting_status="eligible")
    game = make_game(
        db,
        game_type="community",
        host=host,
        starts_at=clock.now + timedelta(days=2),
        join_enforcement_status="paused",
        allow_guests=True,
        host_guest_max=2,
    )
    existing = ready_player(db)
    make_participant(db, game=game, user=existing)
    newcomer = ready_player(db)
    before = participant_count(db, game)

    join = client.post(
        f"/games/{game.id}/join", headers=firebase.sign_in(newcomer), json={}
    )
    add = client.post(
        f"/games/{game.id}/guests/add",
        headers=firebase.sign_in(host),
        json={"guest_count": 1},
    )

    assert join.status_code == 400
    assert add.status_code == 400
    assert participant_count(db, game) == before
    leave = client.post(
        f"/games/{game.id}/leave", headers=firebase.sign_in(existing), json={}
    )
    assert leave.status_code == 200, leave.text


@pytest.mark.page("F16", 25)
def test_joining_resumes_when_pause_is_lifted(clock, db, client, firebase):
    game = make_game(
        db,
        game_type="community",
        starts_at=clock.now + timedelta(days=2),
        join_enforcement_status="paused",
    )
    player = ready_player(db)
    headers = firebase.sign_in(player)
    game.join_enforcement_status = "open"
    db.commit()

    response = client.post(f"/games/{game.id}/join", headers=headers, json={})

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "joined"
    assert participant_count(db, game) == 1


@pytest.mark.page("F16", 14)
def test_joining_closes_at_exactly_five_minutes_after_start(
    clock, db, client, firebase
):
    game = make_game(
        db, game_type="community", starts_at=clock.now - timedelta(minutes=4)
    )
    player = ready_player(db)
    headers = firebase.sign_in(player)

    before_cutoff = client.post(f"/games/{game.id}/join", headers=headers, json={})
    clock.move_to(game.starts_at + timedelta(minutes=5))
    another = ready_player(db)
    at_cutoff = client.post(
        f"/games/{game.id}/join", headers=firebase.sign_in(another), json={}
    )

    assert before_cutoff.status_code == 201, before_cutoff.text
    assert at_cutoff.status_code == 400
    assert participant_count(db, game) == 1


@pytest.mark.page("F16", 14)
def test_host_cancellation_closes_at_start_and_guest_changes_close_five_minutes_later(
    clock, db, client, firebase
):
    host = ready_player(db, hosting_status="eligible")
    game = make_game(
        db,
        game_type="community",
        host=host,
        starts_at=clock.now,
        allow_guests=True,
        host_guest_max=2,
    )
    headers = firebase.sign_in(host)

    cancel = client.post(f"/games/{game.id}/cancel", headers=headers, json={})
    clock.advance(timedelta(minutes=4))
    add_before_cutoff = client.post(
        f"/games/{game.id}/guests/add", headers=headers, json={"guest_count": 1}
    )
    clock.advance(timedelta(minutes=1))
    add_at_cutoff = client.post(
        f"/games/{game.id}/guests/add", headers=headers, json={"guest_count": 1}
    )

    assert cancel.status_code == 400
    assert add_before_cutoff.status_code == 201, add_before_cutoff.text
    assert add_at_cutoff.status_code == 400
    assert participant_count(db, game) == 1


@pytest.mark.page("F16", 19)
def test_unverified_email_can_read_details_but_cannot_join_or_change_attendance(
    clock, db, client, firebase
):
    game = make_game(db, game_type="community", starts_at=clock.now + timedelta(days=2))
    player = ready_player(db)
    make_participant(db, game=game, user=player)
    headers = firebase.sign_in(player, email_verified=False)

    assert client.get(f"/games/{game.id}", headers=headers).status_code == 200
    assert (
        client.post(f"/games/{game.id}/leave", headers=headers, json={}).status_code
        == 403
    )
    assert (
        client.post(f"/games/{game.id}/join", headers=headers, json={}).status_code
        == 403
    )
    assert participant_count(db, game) == 1


@pytest.mark.page("F16", 19)
def test_unverified_email_cannot_start_or_send_game_chat(clock, db, client, firebase):
    host = ready_player(db, hosting_status="eligible")
    player = ready_player(db)
    game = make_game(
        db,
        game_type="community",
        host=host,
        starts_at=clock.now + timedelta(days=2),
    )
    make_participant(db, game=game, user=player)
    room = client.post(
        f"/game-chats/for-game/{game.id}",
        headers=firebase.sign_in(host),
        json={},
    )
    assert room.status_code == 200, room.text
    headers = firebase.sign_in(player, email_verified=False)

    start = client.post(f"/game-chats/for-game/{game.id}", headers=headers, json={})
    send = client.post(
        "/chat-messages",
        headers=headers,
        json={"chat_id": room.json()["id"], "message_body": "Hello"},
    )

    assert start.status_code == 403
    assert send.status_code == 403


@pytest.mark.page("F16", 20)
def test_suspended_player_can_leave_existing_game_but_cannot_join_another(
    clock, db, client, firebase
):
    existing_game = make_game(
        db, game_type="community", starts_at=clock.now + timedelta(days=2)
    )
    new_game = make_game(
        db, game_type="community", starts_at=clock.now + timedelta(days=3)
    )
    player = ready_player(db, account_status="suspended")
    make_participant(db, game=existing_game, user=player)
    headers = firebase.sign_in(player)

    leave = client.post(f"/games/{existing_game.id}/leave", headers=headers, json={})
    join = client.post(f"/games/{new_game.id}/join", headers=headers, json={})

    assert leave.status_code == 200, leave.text
    assert join.status_code == 403
    assert participant_count(db, new_game) == 0


@pytest.mark.page("F16", 20)
def test_suspended_host_may_manage_old_game_but_cannot_join_new_game(
    clock, db, client, firebase
):
    host = ready_player(db, hosting_status="eligible", account_status="suspended")
    game = make_game(
        db,
        game_type="community",
        host=host,
        starts_at=clock.now + timedelta(days=2),
        allow_guests=True,
        host_guest_max=2,
    )
    other_game = make_game(
        db, game_type="community", starts_at=clock.now + timedelta(days=3)
    )
    headers = firebase.sign_in(host)

    add = client.post(
        f"/games/{game.id}/guests/add", headers=headers, json={"guest_count": 1}
    )
    join_other = client.post(f"/games/{other_game.id}/join", headers=headers, json={})

    assert add.status_code == 201, add.text
    assert join_other.status_code == 403
    assert participant_count(db, game) == 1
    assert participant_count(db, other_game) == 0


@pytest.mark.page("F16", 9)
@pytest.mark.page("F16", 28)
def test_community_cancellation_notifies_players_about_original_organizer(
    clock, db, client, firebase
):
    host = ready_player(db, hosting_status="eligible", account_status="suspended")
    game = make_game(
        db, game_type="community", host=host, starts_at=clock.now + timedelta(days=2)
    )
    player = ready_player(db)
    make_booking(db, game=game, buyer=player)
    make_participant(db, game=game, user=player)

    response = client.post(
        f"/games/{game.id}/cancel", headers=firebase.sign_in(host), json={}
    )

    assert response.status_code == 200, response.text
    assert response.json()["game_status"] == "cancelled"
    notification = db.scalar(
        select(Notification).where(
            Notification.user_id == player.id,
            Notification.notification_type == "game_cancelled",
        )
    )
    assert notification is not None
    assert "original organizer" in notification.body
    assert "does not process or guarantee refunds" in notification.body
    assert client.get(f"/games/{game.id}").json()["game_status"] == "cancelled"


@pytest.mark.page("F16", 28)
def test_staff_cancellation_of_suspended_host_game_uses_community_notice(
    clock, db, client, firebase
):
    host = ready_player(db, hosting_status="eligible", account_status="suspended")
    admin = ready_player(db, role="admin")
    game = make_game(
        db, game_type="community", host=host, starts_at=clock.now + timedelta(days=2)
    )
    player = ready_player(db)
    make_booking(db, game=game, buyer=player)
    make_participant(db, game=game, user=player)

    response = client.post(
        f"/admin/community-games/{game.id}/cancel",
        headers=firebase.sign_in(admin),
        json={"reason": "Host safety removal", "idempotency_key": "f16-host-removal"},
    )

    assert response.status_code == 200, response.text
    db.refresh(game)
    assert game.game_status == "cancelled"
    notice = db.scalar(
        select(Notification).where(
            Notification.user_id == player.id,
            Notification.notification_type == "game_cancelled",
        )
    )
    assert notice is not None
    assert "original organizer" in notice.body
    assert "does not process or guarantee refunds" in notice.body


@pytest.mark.page("F16", 12)
def test_unknown_game_id_is_not_found(db, client):
    assert client.get(f"/games/{uuid.uuid4()}").status_code == 404
