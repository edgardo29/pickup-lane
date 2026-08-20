from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from backend.tests.workflows.game_community_roster_chat_need_a_sub_relationship_authorization.test_matrix_scope_and_dependencies_contract import (
    _Identity,
    _auth_headers,
    _booking,
    _game,
    _install_auth_identities,
    _participant,
    _recent_time,
    _session,
    _sub_position,
    _sub_post,
    _sub_request,
    _user,
    _venue,
    _waitlist_entry,
)

pytestmark = pytest.mark.suite_type("ordinary")


@pytest.mark.requirement("WS03-04C-R2", "WS03-04C-R4", "WS03-04C-R10")
def test_current_relationship_reads_bind_to_authenticated_user_not_query_user_ids(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import (
        SubPostRequestStatusHistory,
        SubPostStatusHistory,
    )

    with _session() as db:
        current = _user("reads-current", email_verified=False)
        other = _user("reads-other", email_verified=True)
        host = _user("reads-host", email_verified=True)
        venue = _venue(host.id, "reads")
        game = _game(host_user_id=host.id, venue_id=venue.id, label="reads")
        own_booking = _booking(game_id=game.id, user_id=current.id, label="own")
        other_booking = _booking(game_id=game.id, user_id=other.id, label="other")
        own_participant = _participant(
            game_id=game.id,
            user_id=current.id,
            booking_id=own_booking.id,
            label="own",
            roster_order=1,
        )
        other_participant = _participant(
            game_id=game.id,
            user_id=other.id,
            booking_id=other_booking.id,
            label="other",
            roster_order=2,
        )
        own_waitlist = _waitlist_entry(
            game_id=game.id,
            user_id=current.id,
            label="own",
            position=1,
        )
        other_waitlist = _waitlist_entry(
            game_id=game.id,
            user_id=other.id,
            label="other",
            position=2,
        )
        own_post = _sub_post(owner_user_id=current.id, label="own")
        other_post = _sub_post(owner_user_id=other.id, label="other")
        own_position = _sub_position(own_post.id, "own")
        other_position = _sub_position(other_post.id, "other")
        current_request = _sub_request(
            sub_post_id=other_post.id,
            position_id=other_position.id,
            requester_user_id=current.id,
            request_status="confirmed",
        )
        other_request = _sub_request(
            sub_post_id=own_post.id,
            position_id=own_position.id,
            requester_user_id=other.id,
            request_status="pending",
        )
        post_history = SubPostStatusHistory(
            id=uuid.uuid4(),
            sub_post_id=own_post.id,
            old_status=None,
            new_status="active",
            changed_by_user_id=current.id,
            change_source="owner",
            change_reason="synthetic setup",
        )
        request_history = SubPostRequestStatusHistory(
            id=uuid.uuid4(),
            sub_post_request_id=current_request.id,
            old_status="pending",
            new_status="confirmed",
            changed_by_user_id=other.id,
            change_source="owner",
            change_reason="synthetic setup",
        )
        db.add_all([current, other, host])
        db.flush()
        db.add(venue)
        db.flush()
        db.add(game)
        db.flush()
        db.add_all([own_booking, other_booking, own_post, other_post])
        db.flush()
        db.add_all(
            [
                own_participant,
                other_participant,
                own_waitlist,
                other_waitlist,
                own_position,
                other_position,
            ]
        )
        db.flush()
        db.add_all([current_request, other_request])
        db.flush()
        db.add_all([post_history, request_history])
        db.commit()
        current_auth_id = current.auth_user_id
        current_email = current.email
        own_booking_id = own_booking.id
        other_booking_id = other_booking.id
        own_participant_id = own_participant.id
        other_participant_id = other_participant.id
        own_waitlist_id = own_waitlist.id
        other_waitlist_id = other_waitlist.id
        game_id = game.id
        current_user_id = current.id
        other_user_id = other.id
        own_post_id = own_post.id
        other_post_id = other_post.id
        current_request_id = current_request.id
        other_request_id = other_request.id

    _install_auth_identities(
        monkeypatch,
        {
            "current-token": _Identity(
                auth_user_id=current_auth_id,
                email=current_email,
                email_verified=False,
                authenticated_at=_recent_time(),
            )
        },
    )
    headers = _auth_headers("current-token")

    own_bookings = client.get("/bookings/me", headers=headers)
    assert own_bookings.status_code == 200
    assert {item["id"] for item in own_bookings.json()} == {str(own_booking_id)}

    own_booking_filter = client.get(
        "/bookings",
        headers=headers,
        params={"buyer_user_id": str(current_user_id)},
    )
    assert own_booking_filter.status_code == 200
    assert {item["id"] for item in own_booking_filter.json()} == {str(own_booking_id)}

    foreign_booking_filter = client.get(
        "/bookings",
        headers=headers,
        params={"buyer_user_id": str(other_user_id)},
    )
    assert foreign_booking_filter.status_code == 403
    assert client.get(f"/bookings/{own_booking_id}", headers=headers).status_code == 200
    assert client.get(f"/bookings/{other_booking_id}", headers=headers).status_code == 403

    checkout_status = client.get(
        f"/checkout/bookings/{own_booking_id}/status",
        headers=headers,
    )
    assert checkout_status.status_code == 200
    assert checkout_status.json()["booking_id"] == str(own_booking_id)
    assert (
        client.get(f"/checkout/bookings/{other_booking_id}/status", headers=headers).status_code
        == 403
    )

    participants = client.get("/game-participants/me", headers=headers)
    assert participants.status_code == 200
    assert {item["id"] for item in participants.json()} == {str(own_participant_id)}
    assert (
        client.get(f"/game-participants/{own_participant_id}", headers=headers).status_code
        == 200
    )
    assert (
        client.get(f"/game-participants/{other_participant_id}", headers=headers).status_code
        == 403
    )
    assert client.get("/game-participants", headers=headers).status_code == 403

    waitlist = client.get("/waitlist-entries/me", headers=headers)
    assert waitlist.status_code == 200
    assert {item["id"] for item in waitlist.json()} == {str(own_waitlist_id)}
    assert client.get(f"/waitlist-entries/{own_waitlist_id}", headers=headers).status_code == 200
    assert (
        client.get(f"/waitlist-entries/{other_waitlist_id}", headers=headers).status_code
        == 403
    )
    assert client.get("/waitlist-entries", headers=headers).status_code == 403

    my_games = client.get("/my-games", headers=headers)
    assert my_games.status_code == 200
    assert my_games.headers["cache-control"] == "private, no-store"
    my_game_ids = {item["game"]["id"] for item in my_games.json()["items"]}
    assert str(game_id) in my_game_ids

    mine = client.get("/need-a-sub/posts/mine", headers=headers)
    assert mine.status_code == 200
    assert {item["id"] for item in mine.json()} == {str(own_post_id)}

    my_requests = client.get("/need-a-sub/my-requests", headers=headers)
    assert my_requests.status_code == 200
    assert {item["id"] for item in my_requests.json()} == {str(current_request_id)}

    owned_post_requests = client.get(
        f"/need-a-sub/posts/{own_post_id}/requests",
        headers=headers,
    )
    assert owned_post_requests.status_code == 200
    assert {item["id"] for item in owned_post_requests.json()} == {str(other_request_id)}
    assert (
        client.get(f"/need-a-sub/posts/{other_post_id}/requests", headers=headers).status_code
        == 403
    )

    post_history_response = client.get(
        f"/need-a-sub/posts/{own_post_id}/status-history",
        headers=headers,
    )
    assert post_history_response.status_code == 200
    assert [item["new_status"] for item in post_history_response.json()] == ["active"]
    assert (
        client.get(
            f"/need-a-sub/posts/{other_post_id}/status-history",
            headers=headers,
        ).status_code
        == 403
    )

    request_history_response = client.get(
        f"/need-a-sub/requests/{current_request_id}/status-history",
        headers=headers,
    )
    assert request_history_response.status_code == 200
    assert [item["new_status"] for item in request_history_response.json()] == [
        "confirmed"
    ]
    assert (
        client.get(
            f"/need-a-sub/requests/{other_request_id}/status-history",
            headers=headers,
        ).status_code
        == 200
    )
