from fastapi.testclient import TestClient
from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from backend.tests.helpers import (
    authenticate_as,
    create_game,
    create_game_participant,
    create_user,
    create_venue,
    mark_user_email_verified,
    set_user_role,
)


def set_game_times(game_id: str, starts_at: datetime, ends_at: datetime | None = None) -> None:
    from backend.database import SessionLocal
    from backend.models import Game

    with SessionLocal() as db:
        db_game = db.get(Game, UUID(game_id))
        assert db_game is not None
        db_game.starts_at = starts_at
        db_game.ends_at = ends_at or starts_at + timedelta(hours=1)
        db.commit()


def build_community_game_payload(
    host: dict,
    venue: dict,
    starts_at: datetime,
    ends_at: datetime,
    timezone_name: str = "America/Chicago",
    **overrides: object,
) -> dict:
    payload = {
        "game_type": "community",
        "payment_collection_type": "external_host",
        "publish_status": "published",
        "game_status": "scheduled",
        "title": "Community Game",
        "venue_id": venue["id"],
        "venue_name_snapshot": venue["name"],
        "address_snapshot": venue["address_line_1"],
        "city_snapshot": venue["city"],
        "state_snapshot": venue["state"],
        "host_user_id": host["id"],
        "created_by_user_id": host["id"],
        "starts_at": starts_at.isoformat(),
        "ends_at": ends_at.isoformat(),
        "timezone": timezone_name,
        "format_label": "5v5",
        "environment_type": "indoor",
        "total_spots": 10,
        "price_per_player_cents": 1200,
        "policy_mode": "custom_hosted",
    }
    payload.update(overrides)
    return payload


def first_sunday_of_november(year: int) -> int:
    november_first = datetime(year, 11, 1, tzinfo=UTC)
    return 1 + ((6 - november_first.weekday()) % 7)


def local_date_string(starts_at: datetime, timezone_name: str) -> str:
    return starts_at.astimezone(ZoneInfo(timezone_name)).date().isoformat()


def test_games_create_get_list_update_and_soft_delete(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)

    get_response = client.get(f"/games/{game['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == game["id"]

    list_response = client.get("/games")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == game["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/games/{game['id']}",
        json={"title": "Updated CI Test Match"},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["title"] == "Updated CI Test Match"

    delete_response = client.delete(f"/games/{game['id']}")
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["deleted_at"] is not None


def test_host_can_cancel_own_community_game(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )

    authenticate_as(host["id"])
    response = client.post(
        f"/games/{game['id']}/cancel",
        json={"cancel_reason": "  Weather   changed\nquickly.  "},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["game_status"] == "cancelled"
    assert body["cancelled_at"] is not None
    assert body["cancelled_by_user_id"] == host["id"]
    assert body["cancel_reason"] == "Weather changed quickly."


def test_host_cannot_cancel_community_game_after_start_time(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    set_game_times(game["id"], datetime.now(UTC) - timedelta(minutes=1))

    authenticate_as(host["id"])
    response = client.post(f"/games/{game['id']}/cancel", json={})

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Games cannot be cancelled after start time."


def test_non_host_cannot_cancel_community_game(client: TestClient):
    host = create_user(client)
    other_user = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )

    authenticate_as(other_user["id"])
    response = client.post(f"/games/{game['id']}/cancel", json={})

    assert response.status_code == 403, response.text
    assert "Only the community game host or an admin" in response.text


def test_admin_can_cancel_community_game_and_notify_host(client: TestClient):
    host = create_user(client)
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    player = create_user(client)
    join_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"]},
    )
    assert join_response.status_code == 201, join_response.text

    authenticate_as(admin["id"])
    response = client.post(
        f"/games/{game['id']}/cancel",
        json={"cancel_reason": "Support intervention"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["game_status"] == "cancelled"
    assert body["cancelled_by_user_id"] == admin["id"]
    assert body["cancel_reason"] == "Support intervention"

    participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert participants_response.status_code == 200, participants_response.text
    assert all(
        item["cancellation_type"] == "admin_cancelled"
        for item in participants_response.json()
    )

    for recipient in [host, player]:
        notifications_response = client.get(
            f"/notifications?user_id={recipient['id']}&notification_type=game_cancelled"
        )
        assert notifications_response.status_code == 200, notifications_response.text
        assert len(notifications_response.json()) == 1

    admin_actions_response = client.get(
        f"/admin-actions?target_game_id={game['id']}&action_type=cancel_game"
    )
    assert admin_actions_response.status_code == 200, admin_actions_response.text
    admin_actions = admin_actions_response.json()
    assert len(admin_actions) == 1
    assert admin_actions[0]["admin_user_id"] == admin["id"]
    assert admin_actions[0]["reason"] == "Support intervention"


def test_admin_can_cancel_official_game(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)

    authenticate_as(admin["id"])
    response = client.post(
        f"/games/{game['id']}/cancel",
        json={"cancel_reason": "Field closure"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["game_status"] == "cancelled"
    assert body["cancelled_by_user_id"] == admin["id"]
    assert body["cancel_reason"] == "Field closure"


def test_non_admin_cannot_cancel_official_game(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)

    authenticate_as(user["id"])
    response = client.post(f"/games/{game['id']}/cancel", json={})

    assert response.status_code == 403, response.text
    assert "Only an admin" in response.text


def test_cancel_game_requires_authentication(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(
        client,
        user["id"],
        venue,
        game_type="community",
        host_user_id=user["id"],
        policy_mode="custom_hosted",
    )

    response = client.post(f"/games/{game['id']}/cancel", json={})

    assert response.status_code == 401, response.text


def test_cancel_community_game_cancels_roster_waitlist_and_notifies_members(
    client: TestClient,
):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        format_label="3v3",
        total_spots=6,
    )
    joined_players = []

    for _index in range(6):
        player = create_user(client)
        join_response = client.post(
            f"/games/{game['id']}/join",
            json={"acting_user_id": player["id"]},
        )
        assert join_response.status_code == 201, join_response.text
        joined_players.append(player)

    waitlisted_player = create_user(client)
    waitlist_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": waitlisted_player["id"]},
    )
    assert waitlist_response.status_code == 201, waitlist_response.text
    assert waitlist_response.json()["status"] == "waitlisted"

    authenticate_as(host["id"])
    cancel_response = client.post(f"/games/{game['id']}/cancel", json={})

    assert cancel_response.status_code == 200, cancel_response.text
    assert cancel_response.json()["game_status"] == "cancelled"

    participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert participants_response.status_code == 200, participants_response.text
    participants = participants_response.json()
    assert all(item["participant_status"] == "cancelled" for item in participants)
    assert all(item["cancellation_type"] == "host_cancelled" for item in participants)

    bookings_response = client.get(f"/bookings?game_id={game['id']}")
    assert bookings_response.status_code == 200, bookings_response.text
    bookings = bookings_response.json()
    assert len(bookings) == 7
    assert all(item["booking_status"] == "cancelled" for item in bookings)
    assert all(item["payment_status"] == "not_required" for item in bookings)

    waitlist_entries_response = client.get(f"/waitlist-entries?game_id={game['id']}")
    assert waitlist_entries_response.status_code == 200, waitlist_entries_response.text
    assert waitlist_entries_response.json()[0]["waitlist_status"] == "cancelled"

    for player in [*joined_players, waitlisted_player]:
        notifications_response = client.get(
            f"/notifications?user_id={player['id']}&notification_type=game_cancelled"
        )
        assert notifications_response.status_code == 200, notifications_response.text
        assert len(notifications_response.json()) == 1

    host_notifications_response = client.get(
        f"/notifications?user_id={host['id']}&notification_type=game_cancelled"
    )
    assert host_notifications_response.status_code == 200, host_notifications_response.text
    assert host_notifications_response.json() == []


def test_cancel_official_game_refunds_demo_payments_and_writes_audit_rows(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    player = create_user(client)
    join_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"]},
    )
    assert join_response.status_code == 201, join_response.text
    booking_id = join_response.json()["booking_id"]

    authenticate_as(admin["id"])
    cancel_response = client.post(
        f"/games/{game['id']}/cancel",
        json={"cancel_reason": "Venue closed"},
    )

    assert cancel_response.status_code == 200, cancel_response.text

    booking_response = client.get(f"/bookings/{booking_id}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "cancelled"
    assert booking["payment_status"] == "refunded"
    assert booking["cancel_reason"] == "admin_cancelled"

    payments_response = client.get(f"/payments?booking_id={booking_id}")
    assert payments_response.status_code == 200, payments_response.text
    assert payments_response.json()[0]["payment_status"] == "refunded"

    admin_actions_response = client.get(
        f"/admin-actions?target_game_id={game['id']}&action_type=cancel_game"
    )
    assert admin_actions_response.status_code == 200, admin_actions_response.text
    admin_actions = admin_actions_response.json()
    assert len(admin_actions) == 1
    assert admin_actions[0]["admin_user_id"] == admin["id"]
    assert admin_actions[0]["reason"] == "Venue closed"

    history_response = client.get(f"/game-status-history?game_id={game['id']}")
    assert history_response.status_code == 200, history_response.text
    history = history_response.json()
    assert len(history) == 1
    assert history[0]["old_game_status"] == "scheduled"
    assert history[0]["new_game_status"] == "cancelled"
    assert history[0]["change_source"] == "admin"


def test_cancel_game_archives_chat_and_blocks_chat_reads(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    create_game_participant(
        client,
        host["id"],
        game["id"],
        participant_type="host",
        price_cents=0,
    )
    create_game_participant(client, player["id"], game["id"])
    chat_response = client.post(
        "/game-chats",
        json={"game_id": game["id"], "chat_status": "active"},
    )
    assert chat_response.status_code == 201, chat_response.text
    chat = chat_response.json()

    authenticate_as(host["id"])
    cancel_response = client.post(f"/games/{game['id']}/cancel", json={})
    assert cancel_response.status_code == 200, cancel_response.text

    get_chat_response = client.get(f"/game-chats/{chat['id']}")
    assert get_chat_response.status_code == 200, get_chat_response.text
    assert get_chat_response.json()["chat_status"] == "archived"

    authenticate_as(player["id"])
    messages_response = client.get(
        f"/chat-messages?chat_id={chat['id']}&moderation_status=visible"
    )
    assert messages_response.status_code == 403, messages_response.text


def test_cancel_game_cannot_be_retried(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )

    authenticate_as(host["id"])
    first_response = client.post(f"/games/{game['id']}/cancel", json={})
    second_response = client.post(f"/games/{game['id']}/cancel", json={})

    assert first_response.status_code == 200, first_response.text
    assert second_response.status_code == 409, second_response.text


def test_games_reject_invalid_schedule(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])

    response = client.post(
        "/games",
        json={
            "game_type": "official",
            "payment_collection_type": "in_app",
            "publish_status": "draft",
            "game_status": "scheduled",
            "title": "Bad Schedule",
            "venue_id": venue["id"],
            "venue_name_snapshot": venue["name"],
            "address_snapshot": venue["address_line_1"],
            "city_snapshot": venue["city"],
            "state_snapshot": venue["state"],
            "created_by_user_id": user["id"],
            "starts_at": "2026-01-01T10:00:00Z",
            "ends_at": "2026-01-01T09:00:00Z",
            "format_label": "5v5",
            "environment_type": "indoor",
            "total_spots": 10,
            "price_per_player_cents": 1200,
            "policy_mode": "official_standard",
        },
    )

    assert response.status_code == 400, response.text
    assert "ends_at must be greater than starts_at" in response.text


def test_games_reject_past_start_time(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    starts_at = datetime.now(UTC) - timedelta(hours=1)
    ends_at = starts_at + timedelta(hours=2)

    response = client.post(
        "/games",
        json={
            "game_type": "official",
            "payment_collection_type": "in_app",
            "publish_status": "published",
            "game_status": "scheduled",
            "title": "Past Start",
            "venue_id": venue["id"],
            "venue_name_snapshot": venue["name"],
            "address_snapshot": venue["address_line_1"],
            "city_snapshot": venue["city"],
            "state_snapshot": venue["state"],
            "created_by_user_id": user["id"],
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "format_label": "5v5",
            "environment_type": "indoor",
            "total_spots": 10,
            "price_per_player_cents": 1200,
            "policy_mode": "official_standard",
        },
    )

    assert response.status_code == 400, response.text
    assert "start time must be in the future" in response.text


def test_games_reject_total_spots_below_format_minimum(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    starts_at = datetime.now(UTC) + timedelta(days=5)
    ends_at = starts_at + timedelta(hours=2)

    response = client.post(
        "/games",
        json={
            "game_type": "official",
            "payment_collection_type": "in_app",
            "publish_status": "published",
            "game_status": "scheduled",
            "title": "Too Few Spots",
            "venue_id": venue["id"],
            "venue_name_snapshot": venue["name"],
            "address_snapshot": venue["address_line_1"],
            "city_snapshot": venue["city"],
            "state_snapshot": venue["state"],
            "created_by_user_id": user["id"],
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "format_label": "7v7",
            "environment_type": "indoor",
            "total_spots": 10,
            "price_per_player_cents": 1200,
            "policy_mode": "official_standard",
        },
    )

    assert response.status_code == 400, response.text
    assert "at least 14" in response.text


def test_community_host_can_only_publish_one_active_game_per_local_date(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    starts_at = (datetime.now(UTC) + timedelta(days=8)).replace(
        hour=18, minute=0, second=0, microsecond=0
    )
    ends_at = starts_at + timedelta(hours=2)
    create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        starts_at=starts_at.isoformat(),
        ends_at=ends_at.isoformat(),
    )

    response = client.post(
        "/games",
        json={
            "game_type": "community",
            "payment_collection_type": "external_host",
            "publish_status": "published",
            "game_status": "scheduled",
            "title": "Second Community Game",
            "venue_id": venue["id"],
            "venue_name_snapshot": venue["name"],
            "address_snapshot": venue["address_line_1"],
            "city_snapshot": venue["city"],
            "state_snapshot": venue["state"],
            "host_user_id": host["id"],
            "created_by_user_id": host["id"],
            "starts_at": (starts_at + timedelta(hours=3)).isoformat(),
            "ends_at": (starts_at + timedelta(hours=5)).isoformat(),
            "timezone": "America/Chicago",
            "format_label": "5v5",
            "environment_type": "indoor",
            "total_spots": 10,
            "price_per_player_cents": 1200,
            "policy_mode": "custom_hosted",
        },
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "You already have a community game on this date."


def test_community_host_allows_same_utc_date_when_local_dates_differ(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    utc_day = (datetime.now(UTC) + timedelta(days=8)).replace(
        hour=1, minute=30, second=0, microsecond=0
    )
    first_game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        starts_at=utc_day.isoformat(),
        ends_at=(utc_day + timedelta(hours=1)).isoformat(),
    )
    second_start = utc_day.replace(hour=18)
    second_game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        starts_at=second_start.isoformat(),
        ends_at=(second_start + timedelta(hours=1)).isoformat(),
    )

    assert utc_day.date() == second_start.date()
    assert first_game["starts_on_local"] == local_date_string(
        utc_day, "America/Chicago"
    )
    assert second_game["starts_on_local"] == local_date_string(
        second_start, "America/Chicago"
    )
    assert first_game["starts_on_local"] != second_game["starts_on_local"]


def test_community_host_rejects_different_utc_dates_when_local_date_matches(
    client: TestClient,
):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    starts_at = (datetime.now(UTC) + timedelta(days=9)).replace(
        hour=18, minute=0, second=0, microsecond=0
    )
    first_game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        starts_at=starts_at.isoformat(),
        ends_at=(starts_at + timedelta(hours=1)).isoformat(),
    )
    second_start = starts_at + timedelta(hours=10)

    assert starts_at.date() != second_start.date()
    assert first_game["starts_on_local"] == local_date_string(
        second_start, "America/Chicago"
    )

    response = client.post(
        "/games",
        json=build_community_game_payload(
            host,
            venue,
            second_start,
            second_start + timedelta(hours=1),
            title="Different UTC Same Local Date",
        ),
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "You already have a community game on this date."


def test_community_host_date_rule_uses_each_game_timezone(client: TestClient):
    host = create_user(client)
    new_york_venue = create_venue(
        client,
        host["id"],
        name="NYC Test Field",
        city="New York",
        state="NY",
        postal_code="10001",
    )
    los_angeles_venue = create_venue(
        client,
        host["id"],
        name="LA Test Field",
        city="Los Angeles",
        state="CA",
        postal_code="90001",
    )
    starts_at = (datetime.now(UTC) + timedelta(days=10)).replace(
        hour=6, minute=30, second=0, microsecond=0
    )
    new_york_game = create_game(
        client,
        host["id"],
        new_york_venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        starts_at=starts_at.isoformat(),
        ends_at=(starts_at + timedelta(hours=1)).isoformat(),
        timezone="America/New_York",
    )
    los_angeles_game = create_game(
        client,
        host["id"],
        los_angeles_venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        starts_at=starts_at.isoformat(),
        ends_at=(starts_at + timedelta(hours=1)).isoformat(),
        timezone="America/Los_Angeles",
    )

    assert new_york_game["starts_on_local"] == local_date_string(
        starts_at, "America/New_York"
    )
    assert los_angeles_game["starts_on_local"] == local_date_string(
        starts_at, "America/Los_Angeles"
    )
    assert new_york_game["starts_on_local"] != los_angeles_game["starts_on_local"]


def test_community_host_date_rule_handles_dst_boundary(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    dst_year = datetime.now(UTC).year + 1
    transition_day = first_sunday_of_november(dst_year)
    first_start = datetime(dst_year, 11, transition_day, 5, 30, tzinfo=UTC)
    second_start = datetime(dst_year, 11, transition_day, 8, 30, tzinfo=UTC)
    first_game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        starts_at=first_start.isoformat(),
        ends_at=(first_start + timedelta(hours=1)).isoformat(),
    )

    response = client.post(
        "/games",
        json=build_community_game_payload(
            host,
            venue,
            second_start,
            second_start + timedelta(hours=1),
            title="DST Boundary Community Game",
        ),
    )

    expected_local_date = local_date_string(first_start, "America/Chicago")
    assert expected_local_date == local_date_string(second_start, "America/Chicago")
    assert first_game["starts_on_local"] == expected_local_date
    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "You already have a community game on this date."


def test_cancelled_community_game_does_not_block_same_day_publish(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    starts_at = (datetime.now(UTC) + timedelta(days=9)).replace(
        hour=18, minute=0, second=0, microsecond=0
    )
    create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        game_status="cancelled",
        starts_at=starts_at.isoformat(),
        ends_at=(starts_at + timedelta(hours=2)).isoformat(),
    )

    allowed_game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        starts_at=(starts_at + timedelta(hours=3)).isoformat(),
        ends_at=(starts_at + timedelta(hours=5)).isoformat(),
    )

    assert allowed_game["game_status"] == "scheduled"


def test_community_host_edit_rejects_same_local_date_collision(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    first_start = (datetime.now(UTC) + timedelta(days=10)).replace(
        hour=18, minute=0, second=0, microsecond=0
    )
    second_start = first_start + timedelta(days=1)
    create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        starts_at=first_start.isoformat(),
        ends_at=(first_start + timedelta(hours=2)).isoformat(),
    )
    second_game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        starts_at=second_start.isoformat(),
        ends_at=(second_start + timedelta(hours=2)).isoformat(),
    )

    response = client.patch(
        f"/games/{second_game['id']}/host-edit",
        json={
            "acting_user_id": host["id"],
            "starts_at": (first_start + timedelta(hours=4)).isoformat(),
            "ends_at": (first_start + timedelta(hours=6)).isoformat(),
        },
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "You already have a community game on this date."


def test_official_games_are_not_limited_by_community_host_date_rule(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    starts_at = (datetime.now(UTC) + timedelta(days=12)).replace(
        hour=18, minute=0, second=0, microsecond=0
    )
    first_game = create_game(
        client,
        user["id"],
        venue,
        starts_at=starts_at.isoformat(),
        ends_at=(starts_at + timedelta(hours=2)).isoformat(),
    )
    second_game = create_game(
        client,
        user["id"],
        venue,
        starts_at=(starts_at + timedelta(hours=3)).isoformat(),
        ends_at=(starts_at + timedelta(hours=5)).isoformat(),
    )

    assert first_game["game_type"] == "official"
    assert second_game["game_type"] == "official"


def test_publish_community_game_endpoint_creates_publish_records_transactionally(
    client: TestClient,
):
    host = create_user(client)
    mark_user_email_verified(host["id"])
    starts_at = datetime.now(UTC) + timedelta(days=13)

    response = client.post(
        "/community-games/publish",
        json={
            "host_user_id": host["id"],
            "starts_at": starts_at.isoformat(),
            "ends_at": (starts_at + timedelta(hours=2)).isoformat(),
            "timezone": "America/Chicago",
            "format_label": "7v7",
            "environment_type": "outdoor",
            "total_spots": 14,
            "price_per_player_cents": 2500,
            "venue": {
                "name": "Community Publish Field",
                "address_line_1": "123 Publish Ave",
                "city": "Chicago",
                "state": "IL",
                "postal_code": "60601",
                "country_code": "US",
                "neighborhood": "Loop",
            },
            "payment_methods_snapshot": [{"type": "venmo", "value": "@host"}],
            "game_notes": "Bring a ball.",
        },
    )

    assert response.status_code == 201, response.text
    game = response.json()["game"]
    assert game["game_type"] == "community"
    assert game["host_user_id"] == host["id"]

    participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert participants_response.status_code == 200, participants_response.text
    assert any(
        participant["participant_type"] == "host"
        for participant in participants_response.json()
    )

    details_response = client.get(f"/community-game-details?game_id={game['id']}")
    assert details_response.status_code == 200, details_response.text
    assert details_response.json()[0]["payment_methods_snapshot"] == [
        {"type": "venmo", "value": "@host"}
    ]


def test_host_edit_allows_host_to_update_empty_community_game(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        title="Original Community Game",
    )
    starts_at = datetime.now(UTC) + timedelta(days=10)
    ends_at = starts_at + timedelta(hours=2)

    response = client.patch(
        f"/games/{game['id']}/host-edit",
        json={
            "acting_user_id": host["id"],
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "format_label": "7v7",
            "environment_type": "outdoor",
            "total_spots": 14,
            "price_per_player_cents": 2500,
            "venue_name": "New Community Field",
            "address_line_1": "123 Main St",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60607",
            "neighborhood": "West Loop",
            "game_notes": "Bring a light and dark shirt.",
        },
    )

    assert response.status_code == 200, response.text
    updated_game = response.json()
    assert updated_game["format_label"] == "7v7"
    assert updated_game["price_per_player_cents"] == 2500
    assert updated_game["venue_name_snapshot"] == "New Community Field"
    assert updated_game["game_notes"] == "Bring a light and dark shirt."


def test_host_edit_rejects_after_start_time(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    set_game_times(game["id"], datetime.now(UTC) - timedelta(minutes=1))

    response = client.patch(
        f"/games/{game['id']}/host-edit",
        json={
            "acting_user_id": host["id"],
            "game_notes": "Too late to change this.",
        },
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Games cannot be edited after start time."


def test_host_edit_reuses_existing_matching_venue(client: TestClient):
    host = create_user(client)
    original_venue = create_venue(client, host["id"])
    reusable_venue = create_venue(
        client,
        host["id"],
        name="Reusable Community Field",
        address_line_1="456 Shared Ave",
        city="Chicago",
        state="IL",
        postal_code="60608",
        neighborhood="Pilsen",
    )
    game = create_game(
        client,
        host["id"],
        original_venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )

    response = client.patch(
        f"/games/{game['id']}/host-edit",
        json={
            "acting_user_id": host["id"],
            "venue_name": "Reusable Community Field",
            "address_line_1": "456 Shared Ave",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60608",
            "neighborhood": "Pilsen",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["venue_id"] == reusable_venue["id"]


def test_host_edit_blocks_major_changes_after_players_join(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    create_game_participant(client, player["id"], game["id"])

    price_response = client.patch(
        f"/games/{game['id']}/host-edit",
        json={
            "acting_user_id": host["id"],
            "price_per_player_cents": 1800,
        },
    )
    assert price_response.status_code == 400, price_response.text
    assert "cannot be changed after players have joined" in price_response.text

    notes_response = client.patch(
        f"/games/{game['id']}/host-edit",
        json={
            "acting_user_id": host["id"],
            "game_notes": "Use the north entrance.",
        },
    )
    assert notes_response.status_code == 200, notes_response.text
    assert notes_response.json()["game_notes"] == "Use the north entrance."


def test_join_game_creates_booking_and_participant(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)

    response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"]},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "joined"
    assert body["participant_id"]
    assert body["booking_id"]

    participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert participants_response.status_code == 200, participants_response.text
    assert any(
        item["user_id"] == player["id"] and item["participant_status"] == "confirmed"
        for item in participants_response.json()
    )


def test_join_game_allows_signup_inside_start_grace_window(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)
    set_game_times(game["id"], datetime.now(UTC) - timedelta(minutes=4))

    response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"]},
    )

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "joined"


def test_join_game_rejects_signup_after_start_grace_window(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)
    set_game_times(game["id"], datetime.now(UTC) - timedelta(minutes=6))

    response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"]},
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Joining is closed for this game."


def test_join_game_with_guests_creates_party_booking_and_guest_participants(
    client: TestClient,
):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)

    response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"], "guest_count": 2},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "joined"
    assert body["booking_id"]

    booking_response = client.get(f"/bookings/{body['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["participant_count"] == 3
    assert booking["booking_status"] == "confirmed"
    assert booking["payment_status"] == "paid"
    assert booking["total_cents"] == game["price_per_player_cents"] * 3

    participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert participants_response.status_code == 200, participants_response.text
    participants = [
        item
        for item in participants_response.json()
        if item["booking_id"] == body["booking_id"]
    ]
    assert len(participants) == 3
    assert sum(item["participant_type"] == "guest" for item in participants) == 2
    assert {item["participant_status"] for item in participants} == {"confirmed"}
    assert all(
        item["guest_of_user_id"] == player["id"]
        for item in participants
        if item["participant_type"] == "guest"
    )

    payments_response = client.get(f"/payments?booking_id={body['booking_id']}")
    assert payments_response.status_code == 200, payments_response.text
    payments = payments_response.json()
    assert len(payments) == 1
    assert payments[0]["payment_status"] == "succeeded"
    assert payments[0]["amount_cents"] == game["price_per_player_cents"] * 3


def test_confirmed_player_can_add_guests_to_existing_booking(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue, max_guests_per_booking=2)
    join_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"]},
    )
    assert join_response.status_code == 201, join_response.text
    booking_id = join_response.json()["booking_id"]

    response = client.post(
        f"/games/{game['id']}/booking-guests/add",
        json={"acting_user_id": player["id"], "guest_count": 2},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "guests_added"
    assert body["added_count"] == 2
    assert body["booking_id"] == booking_id

    booking_response = client.get(f"/bookings/{booking_id}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["participant_count"] == 3
    assert booking["booking_status"] == "confirmed"
    assert booking["payment_status"] == "paid"
    assert booking["total_cents"] == game["price_per_player_cents"] * 3

    participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert participants_response.status_code == 200, participants_response.text
    participants = [
        item
        for item in participants_response.json()
        if item["booking_id"] == booking_id
    ]
    assert len(participants) == 3
    assert sum(item["participant_type"] == "guest" for item in participants) == 2
    assert all(
        item["guest_of_user_id"] == player["id"]
        for item in participants
        if item["participant_type"] == "guest"
    )

    payments_response = client.get(f"/payments?booking_id={booking_id}")
    assert payments_response.status_code == 200, payments_response.text
    payment_amounts = sorted(item["amount_cents"] for item in payments_response.json())
    assert payment_amounts == [
        game["price_per_player_cents"],
        game["price_per_player_cents"] * 2,
    ]


def test_community_player_add_guests_keeps_payment_not_required(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        max_guests_per_booking=2,
    )
    join_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"]},
    )
    assert join_response.status_code == 201, join_response.text
    booking_id = join_response.json()["booking_id"]

    response = client.post(
        f"/games/{game['id']}/booking-guests/add",
        json={"acting_user_id": player["id"], "guest_count": 1},
    )

    assert response.status_code == 201, response.text
    booking_response = client.get(f"/bookings/{booking_id}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["participant_count"] == 2
    assert booking["payment_status"] == "not_required"

    payments_response = client.get(f"/payments?booking_id={booking_id}")
    assert payments_response.status_code == 200, payments_response.text
    assert payments_response.json() == []


def test_waitlisted_player_cannot_add_guests_to_booking(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue, total_spots=10)

    for _ in range(10):
        player = create_user(client)
        join_response = client.post(
            f"/games/{game['id']}/join",
            json={"acting_user_id": player["id"]},
        )
        assert join_response.status_code == 201, join_response.text

    waitlisted_player = create_user(client)
    waitlist_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": waitlisted_player["id"]},
    )
    assert waitlist_response.status_code == 201, waitlist_response.text
    assert waitlist_response.json()["status"] == "waitlisted"

    response = client.post(
        f"/games/{game['id']}/booking-guests/add",
        json={"acting_user_id": waitlisted_player["id"], "guest_count": 1},
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Only confirmed players can add guests."


def test_confirmed_player_cannot_add_guests_when_no_spots_left(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue, total_spots=10, max_guests_per_booking=2)
    join_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"]},
    )
    assert join_response.status_code == 201, join_response.text

    for _ in range(9):
        other_player = create_user(client)
        other_join_response = client.post(
            f"/games/{game['id']}/join",
            json={"acting_user_id": other_player["id"]},
        )
        assert other_join_response.status_code == 201, other_join_response.text

    response = client.post(
        f"/games/{game['id']}/booking-guests/add",
        json={"acting_user_id": player["id"], "guest_count": 1},
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Not enough spots are available for guests."


def test_join_game_rejects_too_many_guests(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue, max_guests_per_booking=2)

    response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"], "guest_count": 3},
    )

    assert response.status_code == 400, response.text
    assert "allows up to 2 guests" in response.text


def test_join_game_waitlists_whole_party_when_not_enough_spots(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)

    for _index in range(8):
        player = create_user(client)
        fill_response = client.post(
            f"/games/{game['id']}/join",
            json={"acting_user_id": player["id"]},
        )
        assert fill_response.status_code == 201, fill_response.text

    waitlisted_player = create_user(client)
    response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": waitlisted_player["id"], "guest_count": 2},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "waitlisted"
    assert body["booking_id"]
    assert body["waitlist_entry_id"]

    waitlist_response = client.get(f"/waitlist-entries/{body['waitlist_entry_id']}")
    assert waitlist_response.status_code == 200, waitlist_response.text
    assert waitlist_response.json()["party_size"] == 3

    booking_response = client.get(f"/bookings/{body['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["participant_count"] == 3
    assert booking["booking_status"] == "waitlisted"
    assert booking["payment_status"] == "unpaid"

    participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert participants_response.status_code == 200, participants_response.text
    participants = [
        item
        for item in participants_response.json()
        if item["booking_id"] == body["booking_id"]
    ]
    assert len(participants) == 3
    assert sum(item["participant_type"] == "guest" for item in participants) == 2
    assert {item["participant_status"] for item in participants} == {"waitlisted"}


def test_community_external_host_join_creates_no_player_payment(
    client: TestClient,
):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        price_per_player_cents=1500,
    )

    response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"], "guest_count": 1},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "joined"

    booking_response = client.get(f"/bookings/{body['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "confirmed"
    assert booking["payment_status"] == "not_required"
    assert booking["participant_count"] == 2
    assert booking["total_cents"] == 3000

    payments_response = client.get(f"/payments?booking_id={body['booking_id']}")
    assert payments_response.status_code == 200, payments_response.text
    assert payments_response.json() == []


def test_community_free_join_creates_no_player_payment(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        payment_collection_type="none",
        price_per_player_cents=0,
    )

    response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"]},
    )

    assert response.status_code == 201, response.text
    booking_response = client.get(f"/bookings/{response.json()['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "confirmed"
    assert booking["payment_status"] == "not_required"
    assert booking["total_cents"] == 0

    payments_response = client.get(f"/payments?booking_id={booking['id']}")
    assert payments_response.status_code == 200, payments_response.text
    assert payments_response.json() == []


def test_community_waitlist_creates_no_player_payment(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        format_label="3v3",
        total_spots=6,
        price_per_player_cents=1500,
    )

    for _index in range(6):
        player = create_user(client)
        fill_response = client.post(
            f"/games/{game['id']}/join",
            json={"acting_user_id": player["id"]},
        )
        assert fill_response.status_code == 201, fill_response.text

    waitlisted_player = create_user(client)
    response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": waitlisted_player["id"], "guest_count": 1},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "waitlisted"

    booking_response = client.get(f"/bookings/{body['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "waitlisted"
    assert booking["payment_status"] == "not_required"
    assert booking["participant_count"] == 2

    payments_response = client.get(f"/payments?booking_id={body['booking_id']}")
    assert payments_response.status_code == 200, payments_response.text
    assert payments_response.json() == []


def test_community_waitlist_promotion_creates_no_player_payment(
    client: TestClient,
):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        format_label="3v3",
        total_spots=6,
        price_per_player_cents=1500,
    )
    joined_players = []

    for _index in range(6):
        player = create_user(client)
        fill_response = client.post(
            f"/games/{game['id']}/join",
            json={"acting_user_id": player["id"]},
        )
        assert fill_response.status_code == 201, fill_response.text
        joined_players.append(player)

    waitlisted_player = create_user(client)
    waitlist_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": waitlisted_player["id"]},
    )
    assert waitlist_response.status_code == 201, waitlist_response.text
    waitlist_body = waitlist_response.json()

    leave_response = client.post(
        f"/games/{game['id']}/leave",
        json={"acting_user_id": joined_players[0]["id"]},
    )
    assert leave_response.status_code == 200, leave_response.text

    promoted_booking_response = client.get(f"/bookings/{waitlist_body['booking_id']}")
    assert promoted_booking_response.status_code == 200, promoted_booking_response.text
    promoted_booking = promoted_booking_response.json()
    assert promoted_booking["booking_status"] == "confirmed"
    assert promoted_booking["payment_status"] == "not_required"

    payments_response = client.get(f"/payments?booking_id={waitlist_body['booking_id']}")
    assert payments_response.status_code == 200, payments_response.text
    assert payments_response.json() == []

    notifications_response = client.get(f"/notifications?user_id={waitlisted_player['id']}")
    assert notifications_response.status_code == 200, notifications_response.text
    promotion_notice = next(
        item
        for item in notifications_response.json()
        if item["notification_type"] == "waitlist_promoted"
    )
    assert "charged" not in promotion_notice["body"].lower()


def test_leave_game_rejects_drop_after_start_grace_window_without_promotion(
    client: TestClient,
):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        format_label="3v3",
        total_spots=6,
        price_per_player_cents=1500,
    )
    joined_players = []

    for _index in range(6):
        player = create_user(client)
        fill_response = client.post(
            f"/games/{game['id']}/join",
            json={"acting_user_id": player["id"]},
        )
        assert fill_response.status_code == 201, fill_response.text
        joined_players.append(player)

    waitlisted_player = create_user(client)
    waitlist_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": waitlisted_player["id"]},
    )
    assert waitlist_response.status_code == 201, waitlist_response.text
    waitlist_body = waitlist_response.json()
    set_game_times(game["id"], datetime.now(UTC) - timedelta(minutes=6))

    leave_response = client.post(
        f"/games/{game['id']}/leave",
        json={"acting_user_id": joined_players[0]["id"]},
    )
    assert leave_response.status_code == 400, leave_response.text
    assert leave_response.json()["detail"] == "Attendance changes are closed for this game."

    waitlisted_booking_response = client.get(f"/bookings/{waitlist_body['booking_id']}")
    assert waitlisted_booking_response.status_code == 200, waitlisted_booking_response.text
    waitlisted_booking = waitlisted_booking_response.json()
    assert waitlisted_booking["booking_status"] == "waitlisted"
    assert waitlisted_booking["payment_status"] == "not_required"


def test_community_leave_game_keeps_payment_not_required(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        price_per_player_cents=1500,
    )
    join_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"]},
    )
    assert join_response.status_code == 201, join_response.text

    response = client.post(
        f"/games/{game['id']}/leave",
        json={"acting_user_id": player["id"]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["refund_eligible"] is False

    booking_response = client.get(f"/bookings/{join_response.json()['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "cancelled"
    assert booking["payment_status"] == "not_required"


def test_leave_game_cancels_participant(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)
    join_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"]},
    )
    assert join_response.status_code == 201, join_response.text

    response = client.post(
        f"/games/{game['id']}/leave",
        json={"acting_user_id": player["id"]},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "left_game"
    assert body["refund_eligible"] is True

    participant_response = client.get(f"/game-participants/{body['participant_id']}")
    assert participant_response.status_code == 200, participant_response.text
    assert participant_response.json()["participant_status"] == "cancelled"


def test_leave_game_cancels_guest_participants_for_booking(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)
    join_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"], "guest_count": 2},
    )
    assert join_response.status_code == 201, join_response.text
    booking_id = join_response.json()["booking_id"]

    response = client.post(
        f"/games/{game['id']}/leave",
        json={"acting_user_id": player["id"]},
    )

    assert response.status_code == 200, response.text

    participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert participants_response.status_code == 200, participants_response.text
    participants = [
        item
        for item in participants_response.json()
        if item["booking_id"] == booking_id
    ]
    assert len(participants) == 3
    assert {item["participant_status"] for item in participants} == {"cancelled"}


def test_remove_guest_keeps_player_joined_and_marks_payment_partially_refunded(
    client: TestClient,
):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)
    join_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"], "guest_count": 2},
    )
    assert join_response.status_code == 201, join_response.text
    booking_id = join_response.json()["booking_id"]

    response = client.post(
        f"/games/{game['id']}/guests/remove",
        json={"acting_user_id": player["id"], "remove_count": 1},
    )

    assert response.status_code == 200, response.text
    assert response.json()["removed_count"] == 1

    booking_response = client.get(f"/bookings/{booking_id}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["participant_count"] == 2
    assert booking["booking_status"] == "partially_cancelled"
    assert booking["payment_status"] == "partially_refunded"

    participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert participants_response.status_code == 200, participants_response.text
    participants = [
        item
        for item in participants_response.json()
        if item["booking_id"] == booking_id
    ]
    assert sum(item["participant_status"] == "cancelled" for item in participants) == 1
    assert sum(item["participant_status"] == "confirmed" for item in participants) == 2

    payments_response = client.get(f"/payments?booking_id={booking_id}")
    assert payments_response.status_code == 200, payments_response.text
    assert payments_response.json()[0]["payment_status"] == "partially_refunded"


def test_community_remove_guest_keeps_payment_not_required(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        price_per_player_cents=1500,
    )
    join_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player["id"], "guest_count": 2},
    )
    assert join_response.status_code == 201, join_response.text
    booking_id = join_response.json()["booking_id"]

    response = client.post(
        f"/games/{game['id']}/guests/remove",
        json={"acting_user_id": player["id"], "remove_count": 1},
    )

    assert response.status_code == 200, response.text

    booking_response = client.get(f"/bookings/{booking_id}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "partially_cancelled"
    assert booking["payment_status"] == "not_required"

    payments_response = client.get(f"/payments?booking_id={booking_id}")
    assert payments_response.status_code == 200, payments_response.text
    assert payments_response.json() == []


def test_leave_waitlist_with_guests_keeps_booking_unpaid(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)

    for _index in range(8):
        player = create_user(client)
        fill_response = client.post(
            f"/games/{game['id']}/join",
            json={"acting_user_id": player["id"]},
        )
        assert fill_response.status_code == 201, fill_response.text

    waitlisted_player = create_user(client)
    join_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": waitlisted_player["id"], "guest_count": 2},
    )
    assert join_response.status_code == 201, join_response.text
    booking_id = join_response.json()["booking_id"]

    response = client.post(
        f"/games/{game['id']}/leave",
        json={"acting_user_id": waitlisted_player["id"]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "left_waitlist"

    booking_response = client.get(f"/bookings/{booking_id}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "cancelled"
    assert booking["payment_status"] == "unpaid"
    assert booking["cancel_reason"] == "waitlist_cancelled"


def test_leave_game_promotes_waitlist_party_when_enough_spots_open(
    client: TestClient,
):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue, format_label="3v3", total_spots=6)
    joined_players = []

    for _index in range(6):
        player = create_user(client)
        fill_response = client.post(
            f"/games/{game['id']}/join",
            json={"acting_user_id": player["id"]},
        )
        assert fill_response.status_code == 201, fill_response.text
        joined_players.append(player)

    waitlisted_player = create_user(client)
    waitlist_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": waitlisted_player["id"]},
    )
    assert waitlist_response.status_code == 201, waitlist_response.text
    waitlist_body = waitlist_response.json()
    assert waitlist_body["status"] == "waitlisted"

    leave_response = client.post(
        f"/games/{game['id']}/leave",
        json={"acting_user_id": joined_players[0]["id"]},
    )
    assert leave_response.status_code == 200, leave_response.text

    promoted_booking_response = client.get(f"/bookings/{waitlist_body['booking_id']}")
    assert promoted_booking_response.status_code == 200, promoted_booking_response.text
    promoted_booking = promoted_booking_response.json()
    assert promoted_booking["booking_status"] == "confirmed"
    assert promoted_booking["payment_status"] == "paid"

    waitlist_entry_response = client.get(
        f"/waitlist-entries/{waitlist_body['waitlist_entry_id']}"
    )
    assert waitlist_entry_response.status_code == 200, waitlist_entry_response.text
    waitlist_entry = waitlist_entry_response.json()
    assert waitlist_entry["waitlist_status"] == "accepted"
    assert waitlist_entry["promoted_booking_id"] == waitlist_body["booking_id"]

    participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert participants_response.status_code == 200, participants_response.text
    promoted_participant = next(
        item
        for item in participants_response.json()
        if item["user_id"] == waitlisted_player["id"]
    )
    assert promoted_participant["participant_status"] == "confirmed"

    payments_response = client.get(f"/payments?booking_id={waitlist_body['booking_id']}")
    assert payments_response.status_code == 200, payments_response.text
    assert payments_response.json()[0]["payment_status"] == "succeeded"

    notifications_response = client.get(f"/notifications?user_id={waitlisted_player['id']}")
    assert notifications_response.status_code == 200, notifications_response.text
    assert any(
        item["notification_type"] == "waitlist_promoted"
        for item in notifications_response.json()
    )


def test_host_can_add_and_remove_host_guests(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        format_label="3v3",
        total_spots=6,
    )
    host_participant = create_game_participant(
        client,
        host["id"],
        game["id"],
        participant_type="host",
        price_cents=0,
    )
    assert host_participant["participant_type"] == "host"

    add_response = client.post(
        f"/games/{game['id']}/guests/add",
        json={"acting_user_id": host["id"], "guest_count": 2},
    )
    assert add_response.status_code == 201, add_response.text
    assert add_response.json()["added_count"] == 2

    participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert participants_response.status_code == 200, participants_response.text
    host_guests = [
        item
        for item in participants_response.json()
        if item["participant_type"] == "guest"
        and item["guest_of_user_id"] == host["id"]
        and item["participant_status"] == "confirmed"
    ]
    assert len(host_guests) == 2
    assert all(item["booking_id"] is None for item in host_guests)
    assert all(item["price_cents"] == 0 for item in host_guests)

    remove_response = client.post(
        f"/games/{game['id']}/guests/remove",
        json={"acting_user_id": host["id"], "remove_count": 1},
    )
    assert remove_response.status_code == 200, remove_response.text
    assert remove_response.json()["removed_count"] == 1

    updated_participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert updated_participants_response.status_code == 200, updated_participants_response.text
    updated_host_guests = [
        item
        for item in updated_participants_response.json()
        if item["participant_type"] == "guest" and item["guest_of_user_id"] == host["id"]
    ]
    assert sum(item["participant_status"] == "confirmed" for item in updated_host_guests) == 1
    assert sum(item["participant_status"] == "cancelled" for item in updated_host_guests) == 1


def test_host_guest_limit_uses_format_side_not_player_guest_limit(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        format_label="4v4",
        total_spots=8,
        max_guests_per_booking=2,
    )
    create_game_participant(
        client,
        host["id"],
        game["id"],
        participant_type="host",
        price_cents=0,
    )

    assert game["host_guest_max"] == 3

    add_response = client.post(
        f"/games/{game['id']}/guests/add",
        json={"acting_user_id": host["id"], "guest_count": 3},
    )
    assert add_response.status_code == 201, add_response.text
    assert add_response.json()["added_count"] == 3

    over_limit_response = client.post(
        f"/games/{game['id']}/guests/add",
        json={"acting_user_id": host["id"], "guest_count": 1},
    )
    assert over_limit_response.status_code == 400, over_limit_response.text
    assert "up to 3 host guests" in over_limit_response.text


def test_host_guest_add_does_not_override_roster_capacity(client: TestClient):
    host = create_user(client)
    player_one = create_user(client)
    player_two = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        format_label="4v4",
        total_spots=8,
    )
    create_game_participant(
        client,
        host["id"],
        game["id"],
        participant_type="host",
        price_cents=0,
    )
    join_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player_one["id"], "guest_count": 2},
    )
    assert join_response.status_code == 201, join_response.text
    second_join_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": player_two["id"], "guest_count": 2},
    )
    assert second_join_response.status_code == 201, second_join_response.text

    add_response = client.post(
        f"/games/{game['id']}/guests/add",
        json={"acting_user_id": host["id"], "guest_count": 2},
    )
    assert add_response.status_code == 400, add_response.text
    assert "Not enough spots" in add_response.text
