from fastapi.testclient import TestClient
from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select

from backend.database import SessionLocal
from backend.models import (
    Booking,
    GameCredit,
    GameCreditUsage,
    GameParticipant,
    Payment,
)
from backend.services.game_credit_service import (
    REDEEMED_USAGE_STATUS,
    RELEASED_USAGE_STATUS,
    RESTORED_USAGE_STATUS,
    redeem_reserved_game_credits,
    reserve_game_credits,
)
from backend.services.stripe_service import (
    StripeConfigError,
    StripePaymentIntentResult,
    StripeRefundResult,
)
from backend.tests.helpers import (
    authenticate_as,
    create_booking,
    create_chat_message,
    create_game,
    create_game_chat,
    create_game_participant,
    create_notification,
    create_payment,
    create_user,
    create_user_payment_method,
    create_venue,
    mark_user_email_verified,
    mock_checkout_payment_method_verification,
    set_user_role,
    unique_suffix,
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


def list_game_notifications(
    client: TestClient,
    user_id: str,
    notification_type: str,
) -> list[dict]:
    authenticate_as(user_id)
    response = client.get(f"/notifications/me?notification_type={notification_type}")

    assert response.status_code == 200, response.text
    return response.json()


def issue_game_credit(
    client: TestClient,
    *,
    admin_id: str,
    user_id: str,
    game_id: str,
    amount_cents: int,
) -> dict:
    authenticate_as(admin_id)
    response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": user_id,
            "amount_cents": amount_cents,
            "credit_reason": "admin_credit",
            "source_game_id": game_id,
            "idempotency_key": f"game-cancel-credit-{unique_suffix()}",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_games_create_get_list_update_and_soft_delete(client: TestClient):
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


def test_game_structural_update_notifies_connected_users(client: TestClient):
    host = create_user(client)
    confirmed_player = create_user(client)
    waitlisted_player = create_user(client)
    pending_payment_player = create_user(client)
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
        confirmed_player["id"],
        game["id"],
        roster_order=2,
    )
    create_game_participant(
        client,
        waitlisted_player["id"],
        game["id"],
        participant_status="waitlisted",
        roster_order=None,
    )
    create_game_participant(
        client,
        pending_payment_player["id"],
        game["id"],
        participant_status="pending_payment",
        roster_order=None,
    )

    starts_at = datetime.fromisoformat(game["starts_at"])
    ends_at = datetime.fromisoformat(game["ends_at"])
    response = client.patch(
        f"/games/{game['id']}",
        json={
            "starts_at": (starts_at + timedelta(minutes=30)).isoformat(),
            "ends_at": (ends_at + timedelta(minutes=30)).isoformat(),
        },
    )
    assert response.status_code == 200, response.text

    for user in (host, confirmed_player, waitlisted_player):
        notifications = list_game_notifications(client, user["id"], "game_updated")
        assert len(notifications) == 1
        notification = notifications[0]
        assert notification["notification_type"] == "game_updated"
        assert notification["related_game_id"] == game["id"]
        assert notification["aggregation_key"] == (
            f"game:{game['id']}:user:{user['id']}:game_updated"
        )
        assert notification["aggregate_count"] is None
        assert notification["action_key"] == "view_game"
        assert notification["action"]["key"] == "view_game"

    pending_notifications = list_game_notifications(
        client,
        pending_payment_player["id"],
        "game_updated",
    )
    assert pending_notifications == []


def test_game_text_and_price_updates_do_not_notify_connected_users(
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
    )
    create_game_participant(client, player["id"], game["id"])

    response = client.patch(
        f"/games/{game['id']}",
        json={
            "description": "Tiny typo cleanup.",
            "game_notes": "Use the north entrance.",
            "parking_notes": "Street parking nearby.",
            "price_per_player_cents": 1400,
        },
    )
    assert response.status_code == 200, response.text

    assert list_game_notifications(client, host["id"], "game_updated") == []
    assert list_game_notifications(client, player["id"], "game_updated") == []


def test_game_structural_update_reuses_notification_row(client: TestClient):
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

    first_response = client.patch(
        f"/games/{game['id']}",
        json={"venue_name_snapshot": "First Updated Field"},
    )
    assert first_response.status_code == 200, first_response.text

    notifications = list_game_notifications(client, player["id"], "game_updated")
    assert len(notifications) == 1
    notification_id = notifications[0]["id"]

    read_response = client.patch(f"/notifications/{notification_id}/read", json={})
    assert read_response.status_code == 200, read_response.text

    second_response = client.patch(
        f"/games/{game['id']}",
        json={"venue_name_snapshot": "Second Updated Field"},
    )
    assert second_response.status_code == 200, second_response.text

    notifications = list_game_notifications(client, player["id"], "game_updated")
    assert len(notifications) == 1
    assert notifications[0]["id"] == notification_id
    assert notifications[0]["is_read"] is False
    assert notifications[0]["read_at"] is None
    assert notifications[0]["aggregate_count"] is None


def test_cancel_game_resolves_game_updated_without_reading_chat(
    client: TestClient,
):
    host = create_user(client)
    player = create_user(client)
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
    create_game_participant(client, player["id"], game["id"])

    authenticate_as(host["id"])
    update_response = client.patch(
        f"/games/{game['id']}",
        json={"venue_name_snapshot": "Updated Cancellation Field"},
    )
    assert update_response.status_code == 200, update_response.text

    game_updated_notifications = list_game_notifications(
        client,
        player["id"],
        "game_updated",
    )
    assert len(game_updated_notifications) == 1
    game_updated_notification = game_updated_notifications[0]
    assert game_updated_notification["is_read"] is False

    authenticate_as(host["id"])
    chat = create_game_chat(client, game["id"])
    create_chat_message(
        client,
        chat["id"],
        host["id"],
        message_body="Cancellation test chat message.",
    )

    chat_notifications = list_game_notifications(client, player["id"], "chat_message")
    assert len(chat_notifications) == 1
    assert chat_notifications[0]["is_read"] is False

    waitlist_promoted_notification = create_notification(
        client,
        player["id"],
        notification_type="waitlist_promoted",
        notification_category="game_activity",
        notification_domain="game",
        source_type="community_game",
        title="Moved into game",
        subject_label=game["title"],
        summary="You were moved into the game.",
        body="A spot opened and you were moved into this game.",
        action_key="view_game",
        related_game_id=game["id"],
        subject_starts_at=game["starts_at"],
        subject_ends_at=game["ends_at"],
        subject_timezone=game["timezone"],
        is_read=False,
    )

    authenticate_as(admin["id"])
    cancel_response = client.post(
        f"/games/{game['id']}/cancel",
        json={"cancel_reason": "Field closure"},
    )
    assert cancel_response.status_code == 200, cancel_response.text

    updated_game_updated_notifications = list_game_notifications(
        client,
        player["id"],
        "game_updated",
    )
    assert len(updated_game_updated_notifications) == 1
    updated_game_updated_notification = updated_game_updated_notifications[0]
    assert updated_game_updated_notification["id"] == game_updated_notification["id"]
    assert updated_game_updated_notification["title"] == "Game updated"
    assert updated_game_updated_notification["is_read"] is True
    assert updated_game_updated_notification["read_at"] is not None
    assert (
        updated_game_updated_notification["event_at"]
        == game_updated_notification["event_at"]
    )

    updated_chat_notifications = list_game_notifications(
        client,
        player["id"],
        "chat_message",
    )
    assert len(updated_chat_notifications) == 1
    assert updated_chat_notifications[0]["is_read"] is False

    waitlist_promoted_notifications = list_game_notifications(
        client,
        player["id"],
        "waitlist_promoted",
    )
    assert len(waitlist_promoted_notifications) == 1
    updated_waitlist_promoted_notification = waitlist_promoted_notifications[0]
    assert updated_waitlist_promoted_notification["id"] == (
        waitlist_promoted_notification["id"]
    )
    assert updated_waitlist_promoted_notification["title"] == "Moved into game"
    assert updated_waitlist_promoted_notification["is_read"] is True
    assert updated_waitlist_promoted_notification["read_at"] is not None
    assert (
        updated_waitlist_promoted_notification["event_at"]
        == waitlist_promoted_notification["event_at"]
    )

    game_cancelled_notifications = list_game_notifications(
        client,
        player["id"],
        "game_cancelled",
    )
    assert len(game_cancelled_notifications) == 1
    assert game_cancelled_notifications[0]["action_key"] is None
    assert game_cancelled_notifications[0]["action"] is None


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
        authenticate_as(recipient["id"])
        notifications_response = client.get(
            "/notifications/me?notification_type=game_cancelled"
        )
        assert notifications_response.status_code == 200, notifications_response.text
        notifications = notifications_response.json()
        assert len(notifications) == 1
        assert notifications[0]["action_key"] is None
        assert notifications[0]["action"] is None

    authenticate_as(admin["id"])
    admin_actions_response = client.get(
        f"/admin/actions?target_game_id={game['id']}&action_type=cancel_game"
    )
    assert admin_actions_response.status_code == 200, admin_actions_response.text
    admin_actions = admin_actions_response.json()
    assert len(admin_actions) == 1
    assert admin_actions[0]["admin_user_id"] == admin["id"]
    assert admin_actions[0]["reason"] == "Support intervention"


def test_admin_can_cancel_official_game(client: TestClient):
    admin = create_user(client)
    host = create_user(client)
    admin_added_player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue, host_user_id=host["id"])
    booking = create_booking(client, host["id"], game["id"])
    create_game_participant(
        client,
        host["id"],
        game["id"],
        booking_id=booking["id"],
    )
    authenticate_as(admin["id"])
    assign_host_response = client.post(
        f"/admin/official-games/{game['id']}/host",
        json={"host_user_id": host["id"], "reason": "Assign official host."},
    )
    assert assign_host_response.status_code == 200, assign_host_response.text
    assigned_host_notifications = list_game_notifications(
        client,
        host["id"],
        "game_host_assigned",
    )
    assert len(assigned_host_notifications) == 1
    assigned_host_notification = assigned_host_notifications[0]
    assigned_host_event_at = assigned_host_notification["event_at"]
    assert assigned_host_notification["is_read"] is False

    authenticate_as(admin["id"])
    add_player_response = client.post(
        f"/admin/official-games/{game['id']}/players",
        json={
            "user_id": admin_added_player["id"],
            "reason": "Add support player before cancellation.",
        },
    )
    assert add_player_response.status_code == 201, add_player_response.text
    added_player_notifications = list_game_notifications(
        client,
        admin_added_player["id"],
        "game_player_added_by_admin",
    )
    assert len(added_player_notifications) == 1
    added_player_notification = added_player_notifications[0]
    added_player_event_at = added_player_notification["event_at"]
    assert added_player_notification["is_read"] is False

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

    host_notifications = list_game_notifications(
        client,
        host["id"],
        "game_cancelled",
    )
    assert len(host_notifications) == 1
    assert host_notifications[0]["action_key"] is None
    assert host_notifications[0]["action"] is None
    resolved_assigned_host_notifications = list_game_notifications(
        client,
        host["id"],
        "game_host_assigned",
    )
    assert len(resolved_assigned_host_notifications) == 1
    resolved_assigned_host_notification = resolved_assigned_host_notifications[0]
    assert resolved_assigned_host_notification["is_read"] is True
    assert resolved_assigned_host_notification["read_at"] is not None
    assert resolved_assigned_host_notification["event_at"] == assigned_host_event_at
    assert list_game_notifications(client, host["id"], "game_host_removed") == []
    added_player_cancel_notifications = list_game_notifications(
        client,
        admin_added_player["id"],
        "game_cancelled",
    )
    assert len(added_player_cancel_notifications) == 1
    assert added_player_cancel_notifications[0]["action_key"] is None
    assert added_player_cancel_notifications[0]["action"] is None
    resolved_player_added_notifications = list_game_notifications(
        client,
        admin_added_player["id"],
        "game_player_added_by_admin",
    )
    assert len(resolved_player_added_notifications) == 1
    resolved_player_added_notification = resolved_player_added_notifications[0]
    assert resolved_player_added_notification["is_read"] is True
    assert resolved_player_added_notification["read_at"] is not None
    assert resolved_player_added_notification["event_at"] == added_player_event_at
    assert (
        list_game_notifications(
            client,
            admin_added_player["id"],
            "game_player_removed_by_admin",
        )
        == []
    )


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
        authenticate_as(player["id"])
        notifications_response = client.get(
            "/notifications/me?notification_type=game_cancelled"
        )
        assert notifications_response.status_code == 200, notifications_response.text
        assert len(notifications_response.json()) == 1

    authenticate_as(host["id"])
    host_notifications_response = client.get(
        "/notifications/me?notification_type=game_cancelled"
    )
    assert host_notifications_response.status_code == 200, host_notifications_response.text
    assert host_notifications_response.json() == []


def test_cancel_official_game_refunds_paid_payment_and_writes_audit_rows(
    client: TestClient,
    monkeypatch,
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
    refund_calls: list[dict[str, object]] = []

    def fake_create_stripe_refund(**kwargs):
        refund_calls.append(kwargs)
        return StripeRefundResult(
            id="re_official_cancel_success",
            status="succeeded",
            amount_cents=int(kwargs["amount_cents"]),
            currency=str(kwargs["currency"]),
            charge_id=str(kwargs["charge_id"]),
            payment_intent_id=None,
        )

    monkeypatch.setattr(
        "backend.services.game_cancellation_service.create_stripe_refund",
        fake_create_stripe_refund,
    )

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
    payment = payments_response.json()[0]
    assert payment["payment_status"] == "refunded"
    assert refund_calls == [
        {
            "charge_id": payment["provider_charge_id"],
            "amount_cents": payment["amount_cents"],
            "currency": "USD",
            "idempotency_key": f"game_cancel:{game['id']}:payment:{payment['id']}:refund",
            "metadata": {
                "source": "official_game_cancel",
                "game_id": game["id"],
                "booking_id": booking_id,
                "payment_id": payment["id"],
                "admin_user_id": admin["id"],
            },
        }
    ]

    refunds_response = client.get(f"/refunds?booking_id={booking_id}")
    assert refunds_response.status_code == 200, refunds_response.text
    refunds = refunds_response.json()
    assert len(refunds) == 1
    assert refunds[0]["provider_refund_id"] == "re_official_cancel_success"
    assert refunds[0]["refund_status"] == "succeeded"
    assert refunds[0]["amount_cents"] == payment["amount_cents"]
    refunded_notifications = list_game_notifications(
        client,
        player["id"],
        "booking_refunded",
    )
    assert len(refunded_notifications) == 1
    refunded_notification = refunded_notifications[0]
    assert refunded_notification["title"] == "Refund processed"
    assert refunded_notification["action_key"] is None
    assert refunded_notification["action"] is None
    assert refunded_notification["related_game_id"] == game["id"]
    assert refunded_notification["related_booking_id"] == booking_id
    assert refunded_notification["related_payment_id"] == payment["id"]
    assert refunded_notification["related_refund_id"] == refunds[0]["id"]

    authenticate_as(admin["id"])
    admin_actions_response = client.get(
        f"/admin/actions?target_game_id={game['id']}&action_type=cancel_game"
    )
    assert admin_actions_response.status_code == 200, admin_actions_response.text
    admin_actions = admin_actions_response.json()
    assert len(admin_actions) == 1
    assert admin_actions[0]["admin_user_id"] == admin["id"]
    assert admin_actions[0]["reason"] == "Venue closed"
    assert admin_actions[0]["metadata"]["paid_booking_count"] == 1
    assert admin_actions[0]["metadata"]["refund_created_count"] == 1
    assert admin_actions[0]["metadata"]["refund_followup_required"] is False
    assert admin_actions[0]["metadata"]["payment_refund_created"] is True

    history_response = client.get(f"/game-status-history?game_id={game['id']}")
    assert history_response.status_code == 200, history_response.text
    history = history_response.json()
    assert len(history) == 1
    assert history[0]["old_game_status"] == "scheduled"
    assert history[0]["new_game_status"] == "cancelled"
    assert history[0]["change_source"] == "admin"


def test_cancel_official_game_restores_full_credit_booking_without_stripe_refund(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue, price_per_player_cents=1500)
    credit = issue_game_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        amount_cents=1500,
    )

    def fail_create_stripe_refund(**kwargs):
        raise AssertionError("Stripe refund should not run for credit-only booking.")

    monkeypatch.setattr(
        "backend.services.game_cancellation_service.create_stripe_refund",
        fail_create_stripe_refund,
    )

    authenticate_as(player["id"])
    checkout_response = client.post(
        f"/checkout/games/{game['id']}/payment-intent",
        json={"guest_count": 0},
    )
    assert checkout_response.status_code == 201, checkout_response.text
    checkout = checkout_response.json()
    assert checkout["payment_required"] is False
    assert checkout["payment_id"] is None

    authenticate_as(admin["id"])
    cancel_response = client.post(
        f"/games/{game['id']}/cancel",
        json={"cancel_reason": "Weather closure"},
    )
    assert cancel_response.status_code == 200, cancel_response.text

    booking_response = client.get(f"/bookings/{checkout['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "cancelled"
    assert booking["payment_status"] == "credit_restored"

    refunds_response = client.get(f"/refunds?booking_id={checkout['booking_id']}")
    assert refunds_response.status_code == 200, refunds_response.text
    assert refunds_response.json() == []

    with SessionLocal() as db:
        refreshed_credit = db.get(GameCredit, UUID(credit["id"]))
        usages = db.scalars(
            select(GameCreditUsage).where(
                GameCreditUsage.booking_id == UUID(checkout["booking_id"])
            )
        ).all()

    assert refreshed_credit is not None
    assert refreshed_credit.remaining_cents == 1500
    assert refreshed_credit.credit_status == "active"
    assert {usage.usage_status for usage in usages} == {
        REDEEMED_USAGE_STATUS,
        RESTORED_USAGE_STATUS,
    }
    assert sum(
        usage.amount_cents
        for usage in usages
        if usage.usage_status == RESTORED_USAGE_STATUS
    ) == 1500
    restored_notifications = list_game_notifications(
        client,
        player["id"],
        "booking_refunded",
    )
    assert len(restored_notifications) == 1
    restored_notification = restored_notifications[0]
    assert restored_notification["title"] == "Credit restored"
    assert restored_notification["action_key"] is None
    assert restored_notification["action"] is None
    assert restored_notification["related_game_id"] == game["id"]
    assert restored_notification["related_booking_id"] == checkout["booking_id"]
    assert restored_notification["related_payment_id"] is None
    assert restored_notification["related_refund_id"] is None

    authenticate_as(admin["id"])
    admin_actions_response = client.get(
        f"/admin/actions?target_game_id={game['id']}&action_type=cancel_game"
    )
    assert admin_actions_response.status_code == 200, admin_actions_response.text
    metadata = admin_actions_response.json()[0]["metadata"]
    assert metadata["credit_restored_count"] == 1
    assert metadata["credit_restored_cents"] == 1500
    assert metadata["payment_refund_created"] is False
    assert metadata["refund_followup_required"] is False


def test_cancel_official_game_restores_credit_and_refunds_stripe_remainder(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue, price_per_player_cents=1500)
    credit = issue_game_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        amount_cents=500,
    )
    payment_method = create_user_payment_method(
        client,
        player["id"],
        stripe_customer_id="cus_credit_cancel",
        stripe_payment_method_id="pm_credit_cancel",
    )
    mock_checkout_payment_method_verification(monkeypatch, payment_method)

    def fake_create_payment_intent(**kwargs):
        return StripePaymentIntentResult(
            id="pi_credit_cancel",
            client_secret="pi_credit_cancel_secret",
            status="requires_payment_method",
        )

    def fake_confirm_payment_intent(payment_intent_id, **kwargs):
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret="pi_credit_cancel_secret",
            status="processing",
        )

    monkeypatch.setattr(
        "backend.services.checkout_service.create_payment_intent",
        fake_create_payment_intent,
    )
    monkeypatch.setattr(
        "backend.services.checkout_service.confirm_payment_intent",
        fake_confirm_payment_intent,
    )

    authenticate_as(player["id"])
    checkout_response = client.post(
        f"/checkout/games/{game['id']}/payment-intent",
        json={"guest_count": 0, "payment_method_id": payment_method["id"]},
    )
    assert checkout_response.status_code == 201, checkout_response.text
    checkout = checkout_response.json()
    assert checkout["credit_applied_cents"] == 500
    assert checkout["stripe_amount_cents"] == 1000

    with SessionLocal() as db:
        now = datetime.now(UTC)
        booking = db.get(Booking, UUID(checkout["booking_id"]))
        payment = db.get(Payment, UUID(checkout["payment_id"]))
        assert booking is not None
        assert payment is not None
        booking.booking_status = "confirmed"
        booking.payment_status = "paid"
        booking.booked_at = now
        booking.updated_at = now
        payment.payment_status = "succeeded"
        payment.provider_charge_id = "ch_credit_cancel"
        payment.paid_at = now
        payment.updated_at = now
        participants = db.scalars(
            select(GameParticipant).where(
                GameParticipant.booking_id == UUID(checkout["booking_id"])
            )
        ).all()
        for roster_order, participant in enumerate(participants, start=1):
            participant.participant_status = "confirmed"
            participant.confirmed_at = now
            participant.roster_order = roster_order
            participant.updated_at = now
            db.add(participant)
        redeem_reserved_game_credits(
            db,
            UUID(checkout["booking_id"]),
            now=now,
            user_id=UUID(player["id"]),
        )
        db.add(booking)
        db.add(payment)
        db.commit()

    refund_calls: list[dict[str, object]] = []

    def fake_create_stripe_refund(**kwargs):
        refund_calls.append(kwargs)
        return StripeRefundResult(
            id="re_credit_cancel_success",
            status="succeeded",
            amount_cents=int(kwargs["amount_cents"]),
            currency=str(kwargs["currency"]),
            charge_id=str(kwargs["charge_id"]),
            payment_intent_id=None,
        )

    monkeypatch.setattr(
        "backend.services.game_cancellation_service.create_stripe_refund",
        fake_create_stripe_refund,
    )

    authenticate_as(admin["id"])
    cancel_response = client.post(
        f"/games/{game['id']}/cancel",
        json={"cancel_reason": "Venue closure"},
    )
    assert cancel_response.status_code == 200, cancel_response.text

    booking_response = client.get(f"/bookings/{checkout['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    assert booking_response.json()["payment_status"] == "refunded"

    payment_response = client.get(f"/payments/{checkout['payment_id']}")
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["payment_status"] == "refunded"
    assert refund_calls[0]["amount_cents"] == 1000

    with SessionLocal() as db:
        refreshed_credit = db.get(GameCredit, UUID(credit["id"]))
        usages = db.scalars(
            select(GameCreditUsage).where(
                GameCreditUsage.booking_id == UUID(checkout["booking_id"])
            )
        ).all()

    assert refreshed_credit is not None
    assert refreshed_credit.remaining_cents == 500
    assert refreshed_credit.credit_status == "active"
    assert {usage.usage_status for usage in usages} == {
        REDEEMED_USAGE_STATUS,
        RESTORED_USAGE_STATUS,
    }
    refunds_response = client.get(f"/refunds?booking_id={checkout['booking_id']}")
    assert refunds_response.status_code == 200, refunds_response.text
    refunds = refunds_response.json()
    assert len(refunds) == 1
    refunded_notifications = list_game_notifications(
        client,
        player["id"],
        "booking_refunded",
    )
    assert len(refunded_notifications) == 1
    refunded_notification = refunded_notifications[0]
    assert refunded_notification["title"] == "Refund and credit processed"
    assert "Stripe refund was processed" in refunded_notification["body"]
    assert refunded_notification["action_key"] is None
    assert refunded_notification["action"] is None
    assert refunded_notification["related_game_id"] == game["id"]
    assert refunded_notification["related_booking_id"] == checkout["booking_id"]
    assert refunded_notification["related_payment_id"] == checkout["payment_id"]
    assert refunded_notification["related_refund_id"] == refunds[0]["id"]

    authenticate_as(admin["id"])
    admin_actions_response = client.get(
        f"/admin/actions?target_game_id={game['id']}&action_type=cancel_game"
    )
    assert admin_actions_response.status_code == 200, admin_actions_response.text
    metadata = admin_actions_response.json()[0]["metadata"]
    assert metadata["credit_restored_cents"] == 500
    assert metadata["refund_created_count"] == 1
    assert metadata["payment_refund_created"] is True
    assert metadata["refund_followup_required"] is False


def test_cancel_official_game_preserves_payment_when_refund_fails(
    client: TestClient,
    monkeypatch,
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

    def fake_create_stripe_refund(**kwargs):
        raise StripeConfigError("Stripe is not configured.")

    monkeypatch.setattr(
        "backend.services.game_cancellation_service.create_stripe_refund",
        fake_create_stripe_refund,
    )
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
    assert booking["payment_status"] == "paid"

    payments_response = client.get(f"/payments?booking_id={booking_id}")
    assert payments_response.status_code == 200, payments_response.text
    payment = payments_response.json()[0]
    assert payment["payment_status"] == "succeeded"

    refunds_response = client.get(f"/refunds?booking_id={booking_id}")
    assert refunds_response.status_code == 200, refunds_response.text
    refunds = refunds_response.json()
    assert len(refunds) == 1
    assert refunds[0]["provider_refund_id"] is None
    assert refunds[0]["refund_status"] == "failed"
    assert refunds[0]["amount_cents"] == payment["amount_cents"]

    admin_actions_response = client.get(
        f"/admin/actions?target_game_id={game['id']}&action_type=cancel_game"
    )
    assert admin_actions_response.status_code == 200, admin_actions_response.text
    admin_actions = admin_actions_response.json()
    assert len(admin_actions) == 1
    assert admin_actions[0]["metadata"]["refund_failed_count"] == 1
    assert admin_actions[0]["metadata"]["refund_followup_required"] is True
    assert admin_actions[0]["metadata"]["payment_refund_created"] is False


def test_cancel_official_game_missing_charge_id_flags_refund_followup(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    player = create_user(client)
    booking = create_booking(client, player["id"], game["id"])
    create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        price_cents=1300,
    )
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=None,
    )
    authenticate_as(admin["id"])

    cancel_response = client.post(
        f"/games/{game['id']}/cancel",
        json={"cancel_reason": "Venue closed"},
    )

    assert cancel_response.status_code == 200, cancel_response.text

    booking_response = client.get(f"/bookings/{booking['id']}")
    assert booking_response.status_code == 200, booking_response.text
    updated_booking = booking_response.json()
    assert updated_booking["booking_status"] == "cancelled"
    assert updated_booking["payment_status"] == "paid"

    payment_response = client.get(f"/payments/{payment['id']}")
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["payment_status"] == "succeeded"

    refunds_response = client.get(f"/refunds?booking_id={booking['id']}")
    assert refunds_response.status_code == 200, refunds_response.text
    refunds = refunds_response.json()
    assert len(refunds) == 1
    assert refunds[0]["provider_refund_id"] is None
    assert refunds[0]["refund_status"] == "failed"

    admin_actions_response = client.get(
        f"/admin/actions?target_game_id={game['id']}&action_type=cancel_game"
    )
    assert admin_actions_response.status_code == 200, admin_actions_response.text
    admin_actions = admin_actions_response.json()
    assert len(admin_actions) == 1
    assert admin_actions[0]["metadata"]["refund_failed_count"] == 1
    assert admin_actions[0]["metadata"]["refund_missing_charge_count"] == 1
    assert admin_actions[0]["metadata"]["refund_followup_required"] is True
    assert admin_actions[0]["metadata"]["payment_refund_created"] is False


def test_cancel_official_game_keeps_refund_followup_when_one_refund_fails(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)

    missing_charge_player = create_user(client)
    missing_charge_booking = create_booking(
        client,
        missing_charge_player["id"],
        game["id"],
    )
    create_game_participant(
        client,
        missing_charge_player["id"],
        game["id"],
        booking_id=missing_charge_booking["id"],
    )
    create_payment(
        client,
        missing_charge_player["id"],
        booking_id=missing_charge_booking["id"],
        amount_cents=missing_charge_booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=None,
    )

    refunded_player = create_user(client)
    join_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": refunded_player["id"]},
    )
    assert join_response.status_code == 201, join_response.text
    refunded_booking_id = join_response.json()["booking_id"]

    refund_calls: list[dict[str, object]] = []

    def fake_create_stripe_refund(**kwargs):
        refund_calls.append(kwargs)
        return StripeRefundResult(
            id="re_mixed_cancel_success",
            status="succeeded",
            amount_cents=int(kwargs["amount_cents"]),
            currency=str(kwargs["currency"]),
            charge_id=str(kwargs["charge_id"]),
            payment_intent_id=None,
        )

    monkeypatch.setattr(
        "backend.services.game_cancellation_service.create_stripe_refund",
        fake_create_stripe_refund,
    )
    authenticate_as(admin["id"])

    cancel_response = client.post(
        f"/games/{game['id']}/cancel",
        json={"cancel_reason": "Venue closed"},
    )

    assert cancel_response.status_code == 200, cancel_response.text

    missing_booking_response = client.get(
        f"/bookings/{missing_charge_booking['id']}"
    )
    assert missing_booking_response.status_code == 200, missing_booking_response.text
    assert missing_booking_response.json()["payment_status"] == "paid"

    refunded_booking_response = client.get(f"/bookings/{refunded_booking_id}")
    assert refunded_booking_response.status_code == 200, refunded_booking_response.text
    assert refunded_booking_response.json()["payment_status"] == "refunded"
    assert len(refund_calls) == 1

    admin_actions_response = client.get(
        f"/admin/actions?target_game_id={game['id']}&action_type=cancel_game"
    )
    assert admin_actions_response.status_code == 200, admin_actions_response.text
    admin_actions = admin_actions_response.json()
    assert len(admin_actions) == 1
    metadata = admin_actions[0]["metadata"]
    assert metadata["paid_booking_count"] == 2
    assert metadata["refund_created_count"] == 1
    assert metadata["refund_failed_count"] == 1
    assert metadata["refund_missing_charge_count"] == 1
    assert metadata["refund_followup_required"] is True
    assert metadata["payment_refund_created"] is True


def test_cancel_official_game_releases_uncharged_pending_checkout_hold(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    player = create_user(client)
    credit = issue_game_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        amount_cents=500,
    )
    booking = create_booking(
        client,
        player["id"],
        game["id"],
        booking_status="pending_payment",
        payment_status="processing",
    )
    participant = create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        participant_status="pending_payment",
    )
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="requires_payment_method",
    )
    with SessionLocal() as db:
        reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=500,
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            now=datetime.now(UTC),
            idempotency_scope=f"test-pending-cancel:{booking['id']}",
        )
        db.commit()

    authenticate_as(admin["id"])
    cancel_response = client.post(
        f"/games/{game['id']}/cancel",
        json={"cancel_reason": "Weather closure"},
    )

    assert cancel_response.status_code == 200, cancel_response.text

    booking_response = client.get(f"/bookings/{booking['id']}")
    assert booking_response.status_code == 200, booking_response.text
    updated_booking = booking_response.json()
    assert updated_booking["booking_status"] == "cancelled"
    assert updated_booking["payment_status"] == "failed"
    assert updated_booking["cancel_reason"] == "admin_cancelled"

    participant_response = client.get(f"/game-participants/{participant['id']}")
    assert participant_response.status_code == 200, participant_response.text
    updated_participant = participant_response.json()
    assert updated_participant["participant_status"] == "cancelled"
    assert updated_participant["cancellation_type"] == "admin_cancelled"

    payment_response = client.get(f"/payments/{payment['id']}")
    assert payment_response.status_code == 200, payment_response.text
    updated_payment = payment_response.json()
    assert updated_payment["payment_status"] == "canceled"
    assert updated_payment["failure_code"] == "game_cancelled"

    refunds_response = client.get(f"/refunds?booking_id={booking['id']}")
    assert refunds_response.status_code == 200, refunds_response.text
    assert refunds_response.json() == []

    with SessionLocal() as db:
        refreshed_credit = db.get(GameCredit, UUID(credit["id"]))
        usage = db.scalars(
            select(GameCreditUsage).where(
                GameCreditUsage.booking_id == UUID(booking["id"])
            )
        ).one()

    assert refreshed_credit is not None
    assert refreshed_credit.remaining_cents == 500
    assert refreshed_credit.credit_status == "active"
    assert usage.usage_status == RELEASED_USAGE_STATUS
    assert usage.release_reason == "game_cancelled"

    admin_actions_response = client.get(
        f"/admin/actions?target_game_id={game['id']}&action_type=cancel_game"
    )
    assert admin_actions_response.status_code == 200, admin_actions_response.text
    admin_actions = admin_actions_response.json()
    assert len(admin_actions) == 1
    assert admin_actions[0]["metadata"]["uncharged_pending_booking_count"] == 1
    assert admin_actions[0]["metadata"]["credit_released_cents"] == 500
    assert admin_actions[0]["metadata"]["refund_followup_required"] is False
    assert admin_actions[0]["metadata"]["payment_refund_created"] is False


def test_cancel_official_game_preserves_processing_payment_for_followup(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    player = create_user(client)
    booking = create_booking(
        client,
        player["id"],
        game["id"],
        booking_status="pending_payment",
        payment_status="processing",
    )
    create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        participant_status="pending_payment",
    )
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="processing",
    )

    authenticate_as(admin["id"])
    cancel_response = client.post(
        f"/games/{game['id']}/cancel",
        json={"cancel_reason": "Venue emergency"},
    )

    assert cancel_response.status_code == 200, cancel_response.text

    booking_response = client.get(f"/bookings/{booking['id']}")
    assert booking_response.status_code == 200, booking_response.text
    updated_booking = booking_response.json()
    assert updated_booking["booking_status"] == "cancelled"
    assert updated_booking["payment_status"] == "processing"

    payment_response = client.get(f"/payments/{payment['id']}")
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["payment_status"] == "processing"

    admin_actions_response = client.get(
        f"/admin/actions?target_game_id={game['id']}&action_type=cancel_game"
    )
    assert admin_actions_response.status_code == 200, admin_actions_response.text
    admin_actions = admin_actions_response.json()
    assert len(admin_actions) == 1
    assert admin_actions[0]["metadata"]["processing_payment_booking_count"] == 1
    assert admin_actions[0]["metadata"]["payment_followup_required"] is True
    assert admin_actions[0]["metadata"]["payment_refund_created"] is False


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


def test_official_game_create_forces_official_only_fields(client: TestClient):
    admin = create_user(client)
    host = create_user(client)
    venue = create_venue(client, admin["id"])

    game = create_game(
        client,
        admin["id"],
        venue,
        host_user_id=host["id"],
        minimum_age=21,
        host_guest_max=4,
        custom_rules_text="Host custom rules should not apply.",
        custom_cancellation_text="Host custom cancellation should not apply.",
    )

    assert game["game_type"] == "official"
    assert game["host_user_id"] is None
    assert game["minimum_age"] is None
    assert game["host_guest_max"] == 0
    assert game["custom_rules_text"] is None
    assert game["custom_cancellation_text"] is None


def test_official_game_update_forces_fields_and_blocks_location_host_changes(
    client: TestClient,
):
    admin = create_user(client)
    host = create_user(client)
    venue = create_venue(client, admin["id"])
    new_venue = create_venue(
        client,
        admin["id"],
        name="Different Official Field",
        address_line_1="222 Different Ave",
    )
    game = create_game(client, admin["id"], venue)

    update_response = client.patch(
        f"/games/{game['id']}",
        json={
            "title": "Official fields normalized",
            "minimum_age": 21,
            "host_guest_max": 4,
            "custom_rules_text": "Nope.",
            "custom_cancellation_text": "Also nope.",
        },
    )

    assert update_response.status_code == 200, update_response.text
    updated_game = update_response.json()
    assert updated_game["title"] == "Official fields normalized"
    assert updated_game["minimum_age"] is None
    assert updated_game["host_guest_max"] == 0
    assert updated_game["custom_rules_text"] is None
    assert updated_game["custom_cancellation_text"] is None

    location_response = client.patch(
        f"/games/{game['id']}",
        json={"venue_id": new_venue["id"]},
    )
    assert location_response.status_code == 400, location_response.text
    assert "venue/location cannot be changed" in location_response.text

    host_response = client.patch(
        f"/games/{game['id']}",
        json={"host_user_id": host["id"]},
    )
    assert host_response.status_code == 400, host_response.text
    assert "host assignment route" in host_response.text


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
            "custom_rules_text": "Please cancel early if you cannot make it.",
            "game_notes": "Bring a ball.",
        },
    )

    assert response.status_code == 201, response.text
    game = response.json()["game"]
    assert game["game_type"] == "community"
    assert game["host_user_id"] == host["id"]
    assert game["custom_rules_text"] == "Please cancel early if you cannot make it."

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


def test_second_community_publish_creates_paid_publish_fee(client: TestClient):
    host = create_user(client)
    mark_user_email_verified(host["id"])
    starts_at = datetime.now(UTC) + timedelta(days=13)

    base_payload = {
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
    }
    first_response = client.post("/community-games/publish", json=base_payload)
    assert first_response.status_code == 201, first_response.text

    second_starts_at = starts_at + timedelta(days=1)
    second_response = client.post(
        "/community-games/publish",
        json={
            **base_payload,
            "starts_at": second_starts_at.isoformat(),
            "ends_at": (second_starts_at + timedelta(hours=2)).isoformat(),
            "venue": {
                **base_payload["venue"],
                "address_line_1": "456 Paid Publish Ave",
                "postal_code": "60602",
            },
        },
    )

    assert second_response.status_code == 201, second_response.text
    second_game = second_response.json()["game"]

    fees_response = client.get(f"/host-publish-fees?game_id={second_game['id']}")
    assert fees_response.status_code == 200, fees_response.text
    paid_fee = fees_response.json()[0]
    assert paid_fee["amount_cents"] == 499
    assert paid_fee["fee_status"] == "paid"
    assert paid_fee["payment_id"] is not None
    assert paid_fee["paid_at"] is not None


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
            "custom_rules_text": "Arrive 10 minutes early.",
            "game_notes": "Bring a light and dark shirt.",
        },
    )

    assert response.status_code == 200, response.text
    updated_game = response.json()
    assert updated_game["format_label"] == "7v7"
    assert updated_game["price_per_player_cents"] == 2500
    assert updated_game["venue_name_snapshot"] == "New Community Field"
    assert updated_game["custom_rules_text"] == "Arrive 10 minutes early."
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
            "custom_rules_text": "Message the host if you are running late.",
            "game_notes": "Use the north entrance.",
        },
    )
    assert notes_response.status_code == 200, notes_response.text
    assert (
        notes_response.json()["custom_rules_text"]
        == "Message the host if you are running late."
    )
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
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
        total_spots=10,
    )

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
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )

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
    assert booking["payment_status"] == "not_required"

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


def test_paid_waitlist_join_requires_auto_charge_consent_and_payment_method(
    client: TestClient,
):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue, format_label="3v3", total_spots=6)

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
        json={"acting_user_id": waitlisted_player["id"]},
    )

    assert response.status_code == 400, response.text
    assert "authorize Pickup Lane" in response.text

    payment_method = create_user_payment_method(client, waitlisted_player["id"])
    missing_method_response = client.post(
        f"/games/{game['id']}/join",
        json={
            "acting_user_id": waitlisted_player["id"],
            "auto_charge_consent_accepted": True,
            "auto_charge_consent_version": "waitlist-auto-charge-v1",
        },
    )
    assert missing_method_response.status_code == 400, missing_method_response.text
    assert "Choose a saved card" in missing_method_response.text

    valid_response = client.post(
        f"/games/{game['id']}/join",
        json={
            "acting_user_id": waitlisted_player["id"],
            "payment_method_id": payment_method["id"],
            "auto_charge_consent_accepted": True,
            "auto_charge_consent_version": "waitlist-auto-charge-v1",
        },
    )
    assert valid_response.status_code == 201, valid_response.text
    assert valid_response.json()["status"] == "waitlisted"


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

    authenticate_as(waitlisted_player["id"])
    notifications_response = client.get("/notifications/me")
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


def test_leave_waitlist_with_guests_keeps_payment_not_required(client: TestClient):
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
    assert booking["payment_status"] == "not_required"
    assert booking["cancel_reason"] == "waitlist_cancelled"


def test_leave_game_promotes_paid_waitlist_after_successful_auto_charge(
    client: TestClient,
    monkeypatch,
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
    payment_method = create_user_payment_method(client, waitlisted_player["id"])
    captured_create: dict[str, object] = {}
    captured_confirm: dict[str, object] = {}

    def fake_create_payment_intent(**kwargs):
        captured_create.update(kwargs)
        return StripePaymentIntentResult(
            id="pi_waitlist_auto_charge_success",
            client_secret=None,
            status="requires_payment_method",
        )

    def fake_confirm_payment_intent(payment_intent_id, **kwargs):
        captured_confirm.update({"payment_intent_id": payment_intent_id, **kwargs})
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret=None,
            status="succeeded",
            latest_charge_id="ch_waitlist_auto_charge_success",
        )

    monkeypatch.setattr(
        "backend.services.game_waitlist_service.create_payment_intent",
        fake_create_payment_intent,
    )
    monkeypatch.setattr(
        "backend.services.game_waitlist_service.confirm_payment_intent",
        fake_confirm_payment_intent,
    )

    waitlist_response = client.post(
        f"/games/{game['id']}/join",
        json={
            "acting_user_id": waitlisted_player["id"],
            "payment_method_id": payment_method["id"],
            "auto_charge_consent_accepted": True,
            "auto_charge_consent_version": "waitlist-auto-charge-v1",
        },
    )
    assert waitlist_response.status_code == 201, waitlist_response.text
    waitlist_body = waitlist_response.json()
    assert waitlist_body["status"] == "waitlisted"

    waitlist_entry_response = client.get(
        f"/waitlist-entries/{waitlist_body['waitlist_entry_id']}"
    )
    assert waitlist_entry_response.status_code == 200, waitlist_entry_response.text
    waitlist_entry = waitlist_entry_response.json()
    assert waitlist_entry["auto_charge_consent_at"] is not None
    assert waitlist_entry["auto_charge_consent_version"] == "waitlist-auto-charge-v1"
    assert waitlist_entry["authorized_payment_method_id"] == payment_method["id"]
    assert waitlist_entry["authorized_amount_cents"] == 1200

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
    payment = payments_response.json()[0]
    assert payment["payment_status"] == "succeeded"
    assert payment["provider_payment_intent_id"] == "pi_waitlist_auto_charge_success"
    assert payment["provider_charge_id"] == "ch_waitlist_auto_charge_success"
    assert captured_create["amount_cents"] == 1200
    assert captured_create["customer_id"] == payment_method["stripe_customer_id"]
    assert captured_confirm["payment_method_id"] == (
        payment_method["stripe_payment_method_id"]
    )
    assert captured_confirm["off_session"] is True

    authenticate_as(waitlisted_player["id"])
    notifications_response = client.get("/notifications/me")
    assert notifications_response.status_code == 200, notifications_response.text
    assert any(
        item["notification_type"] == "waitlist_promoted"
        for item in notifications_response.json()
    )


def test_paid_waitlist_requires_action_fails_auto_promotion_and_notifies_buyer(
    client: TestClient,
    monkeypatch,
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
    payment_method = create_user_payment_method(client, waitlisted_player["id"])

    def fake_create_payment_intent(**kwargs):
        return StripePaymentIntentResult(
            id="pi_waitlist_auto_charge_requires_action",
            client_secret=None,
            status="requires_payment_method",
        )

    def fake_confirm_payment_intent(payment_intent_id, **kwargs):
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret=None,
            status="requires_action",
        )

    monkeypatch.setattr(
        "backend.services.game_waitlist_service.create_payment_intent",
        fake_create_payment_intent,
    )
    monkeypatch.setattr(
        "backend.services.game_waitlist_service.confirm_payment_intent",
        fake_confirm_payment_intent,
    )

    waitlist_response = client.post(
        f"/games/{game['id']}/join",
        json={
            "acting_user_id": waitlisted_player["id"],
            "payment_method_id": payment_method["id"],
            "auto_charge_consent_accepted": True,
            "auto_charge_consent_version": "waitlist-auto-charge-v1",
        },
    )
    assert waitlist_response.status_code == 201, waitlist_response.text
    waitlist_body = waitlist_response.json()

    leave_response = client.post(
        f"/games/{game['id']}/leave",
        json={"acting_user_id": joined_players[0]["id"]},
    )
    assert leave_response.status_code == 200, leave_response.text

    booking_response = client.get(f"/bookings/{waitlist_body['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "failed"
    assert booking["payment_status"] == "failed"

    waitlist_entry_response = client.get(
        f"/waitlist-entries/{waitlist_body['waitlist_entry_id']}"
    )
    assert waitlist_entry_response.status_code == 200, waitlist_entry_response.text
    waitlist_entry = waitlist_entry_response.json()
    assert waitlist_entry["waitlist_status"] == "payment_failed"

    participants_response = client.get(f"/game-participants?game_id={game['id']}")
    assert participants_response.status_code == 200, participants_response.text
    failed_participant = next(
        item
        for item in participants_response.json()
        if item["user_id"] == waitlisted_player["id"]
    )
    assert failed_participant["participant_status"] == "removed"
    assert failed_participant["cancellation_type"] == "payment_failed"

    payments_response = client.get(f"/payments?booking_id={waitlist_body['booking_id']}")
    assert payments_response.status_code == 200, payments_response.text
    payment = payments_response.json()[0]
    assert payment["payment_status"] == "requires_action"

    notifications = list_game_notifications(
        client,
        waitlisted_player["id"],
        "payment_failed",
    )
    assert len(notifications) == 1
    assert "removed from the waitlist" in notifications[0]["body"]
    assert (
        list_game_notifications(client, waitlisted_player["id"], "waitlist_promoted")
        == []
    )


def test_paid_waitlist_processing_holds_capacity_and_blocks_duplicate_join(
    client: TestClient,
    monkeypatch,
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
    payment_method = create_user_payment_method(client, waitlisted_player["id"])

    def fake_create_payment_intent(**kwargs):
        return StripePaymentIntentResult(
            id="pi_waitlist_auto_charge_processing_hold",
            client_secret=None,
            status="requires_payment_method",
        )

    def fake_confirm_payment_intent(payment_intent_id, **kwargs):
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret=None,
            status="processing",
        )

    monkeypatch.setattr(
        "backend.services.game_waitlist_service.create_payment_intent",
        fake_create_payment_intent,
    )
    monkeypatch.setattr(
        "backend.services.game_waitlist_service.confirm_payment_intent",
        fake_confirm_payment_intent,
    )

    waitlist_response = client.post(
        f"/games/{game['id']}/join",
        json={
            "acting_user_id": waitlisted_player["id"],
            "payment_method_id": payment_method["id"],
            "auto_charge_consent_accepted": True,
            "auto_charge_consent_version": "waitlist-auto-charge-v1",
        },
    )
    assert waitlist_response.status_code == 201, waitlist_response.text
    waitlist_body = waitlist_response.json()

    leave_response = client.post(
        f"/games/{game['id']}/leave",
        json={"acting_user_id": joined_players[0]["id"]},
    )
    assert leave_response.status_code == 200, leave_response.text

    waitlist_entry_response = client.get(
        f"/waitlist-entries/{waitlist_body['waitlist_entry_id']}"
    )
    assert waitlist_entry_response.status_code == 200, waitlist_entry_response.text
    assert waitlist_entry_response.json()["waitlist_status"] == "payment_processing"

    booking_response = client.get(f"/bookings/{waitlist_body['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "pending_payment"
    assert booking["payment_status"] == "processing"

    participants_response = client.get(
        f"/game-participants?booking_id={waitlist_body['booking_id']}"
    )
    assert participants_response.status_code == 200, participants_response.text
    assert {
        participant["participant_status"]
        for participant in participants_response.json()
    } == {"pending_payment"}

    duplicate_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": waitlisted_player["id"]},
    )
    assert duplicate_response.status_code == 409, duplicate_response.text
    assert "already joined" in duplicate_response.text

    next_waitlisted_player = create_user(client)
    next_payment_method = create_user_payment_method(
        client,
        next_waitlisted_player["id"],
    )
    next_response = client.post(
        f"/games/{game['id']}/join",
        json={
            "acting_user_id": next_waitlisted_player["id"],
            "payment_method_id": next_payment_method["id"],
            "auto_charge_consent_accepted": True,
            "auto_charge_consent_version": "waitlist-auto-charge-v1",
        },
    )
    assert next_response.status_code == 201, next_response.text
    assert next_response.json()["status"] == "waitlisted"

    assert list_game_notifications(client, waitlisted_player["id"], "waitlist_promoted") == []
    assert list_game_notifications(client, waitlisted_player["id"], "payment_failed") == []


def test_paid_waitlist_failed_auto_charge_moves_to_next_active_party(
    client: TestClient,
    monkeypatch,
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

    first_waitlisted_player = create_user(client)
    first_payment_method = create_user_payment_method(
        client,
        first_waitlisted_player["id"],
    )
    second_waitlisted_player = create_user(client)
    second_payment_method = create_user_payment_method(
        client,
        second_waitlisted_player["id"],
    )
    created_intent_ids: list[str] = []

    def fake_create_payment_intent(**kwargs):
        intent_id = f"pi_waitlist_auto_charge_{len(created_intent_ids) + 1}"
        created_intent_ids.append(intent_id)
        return StripePaymentIntentResult(
            id=intent_id,
            client_secret=None,
            status="requires_payment_method",
        )

    def fake_confirm_payment_intent(payment_intent_id, **kwargs):
        if payment_intent_id == created_intent_ids[0]:
            return StripePaymentIntentResult(
                id=payment_intent_id,
                client_secret=None,
                status="requires_action",
            )

        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret=None,
            status="succeeded",
            latest_charge_id="ch_second_waitlist_auto_charge",
        )

    monkeypatch.setattr(
        "backend.services.game_waitlist_service.create_payment_intent",
        fake_create_payment_intent,
    )
    monkeypatch.setattr(
        "backend.services.game_waitlist_service.confirm_payment_intent",
        fake_confirm_payment_intent,
    )

    first_waitlist_response = client.post(
        f"/games/{game['id']}/join",
        json={
            "acting_user_id": first_waitlisted_player["id"],
            "payment_method_id": first_payment_method["id"],
            "auto_charge_consent_accepted": True,
            "auto_charge_consent_version": "waitlist-auto-charge-v1",
        },
    )
    assert first_waitlist_response.status_code == 201, first_waitlist_response.text
    first_waitlist_body = first_waitlist_response.json()

    second_waitlist_response = client.post(
        f"/games/{game['id']}/join",
        json={
            "acting_user_id": second_waitlisted_player["id"],
            "payment_method_id": second_payment_method["id"],
            "auto_charge_consent_accepted": True,
            "auto_charge_consent_version": "waitlist-auto-charge-v1",
        },
    )
    assert second_waitlist_response.status_code == 201, second_waitlist_response.text
    second_waitlist_body = second_waitlist_response.json()

    leave_response = client.post(
        f"/games/{game['id']}/leave",
        json={"acting_user_id": joined_players[0]["id"]},
    )
    assert leave_response.status_code == 200, leave_response.text

    first_booking_response = client.get(
        f"/bookings/{first_waitlist_body['booking_id']}"
    )
    assert first_booking_response.status_code == 200, first_booking_response.text
    first_booking = first_booking_response.json()
    assert first_booking["booking_status"] == "failed"
    assert first_booking["payment_status"] == "failed"

    first_waitlist_entry_response = client.get(
        f"/waitlist-entries/{first_waitlist_body['waitlist_entry_id']}"
    )
    assert first_waitlist_entry_response.status_code == 200
    assert first_waitlist_entry_response.json()["waitlist_status"] == "payment_failed"

    second_booking_response = client.get(
        f"/bookings/{second_waitlist_body['booking_id']}"
    )
    assert second_booking_response.status_code == 200, second_booking_response.text
    second_booking = second_booking_response.json()
    assert second_booking["booking_status"] == "confirmed"
    assert second_booking["payment_status"] == "paid"

    second_waitlist_entry_response = client.get(
        f"/waitlist-entries/{second_waitlist_body['waitlist_entry_id']}"
    )
    assert second_waitlist_entry_response.status_code == 200
    assert second_waitlist_entry_response.json()["waitlist_status"] == "accepted"

    first_payments_response = client.get(
        f"/payments?booking_id={first_waitlist_body['booking_id']}"
    )
    assert first_payments_response.status_code == 200, first_payments_response.text
    assert first_payments_response.json()[0]["payment_status"] == "requires_action"

    second_payments_response = client.get(
        f"/payments?booking_id={second_waitlist_body['booking_id']}"
    )
    assert second_payments_response.status_code == 200, second_payments_response.text
    second_payment = second_payments_response.json()[0]
    assert second_payment["payment_status"] == "succeeded"
    assert second_payment["provider_charge_id"] == "ch_second_waitlist_auto_charge"

    assert (
        len(
            list_game_notifications(
                client,
                first_waitlisted_player["id"],
                "payment_failed",
            )
        )
        == 1
    )
    assert (
        list_game_notifications(
            client,
            first_waitlisted_player["id"],
            "waitlist_promoted",
        )
        == []
    )
    assert (
        len(
            list_game_notifications(
                client,
                second_waitlisted_player["id"],
                "waitlist_promoted",
            )
        )
        == 1
    )
    assert (
        list_game_notifications(
            client,
            second_waitlisted_player["id"],
            "payment_failed",
        )
        == []
    )


def test_waitlist_promotion_skips_oversized_party_without_splitting(
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
        fill_response = client.post(
            f"/games/{game['id']}/join",
            json={"acting_user_id": player["id"]},
        )
        assert fill_response.status_code == 201, fill_response.text
        joined_players.append(player)

    oversized_player = create_user(client)
    oversized_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": oversized_player["id"], "guest_count": 1},
    )
    assert oversized_response.status_code == 201, oversized_response.text
    oversized_body = oversized_response.json()
    assert oversized_body["status"] == "waitlisted"

    fitting_player = create_user(client)
    fitting_response = client.post(
        f"/games/{game['id']}/join",
        json={"acting_user_id": fitting_player["id"]},
    )
    assert fitting_response.status_code == 201, fitting_response.text
    fitting_body = fitting_response.json()
    assert fitting_body["status"] == "waitlisted"

    leave_response = client.post(
        f"/games/{game['id']}/leave",
        json={"acting_user_id": joined_players[0]["id"]},
    )
    assert leave_response.status_code == 200, leave_response.text

    oversized_waitlist_response = client.get(
        f"/waitlist-entries/{oversized_body['waitlist_entry_id']}"
    )
    assert oversized_waitlist_response.status_code == 200
    oversized_waitlist = oversized_waitlist_response.json()
    assert oversized_waitlist["waitlist_status"] == "active"
    assert oversized_waitlist["position"] == 1

    oversized_booking_response = client.get(f"/bookings/{oversized_body['booking_id']}")
    assert oversized_booking_response.status_code == 200, oversized_booking_response.text
    oversized_booking = oversized_booking_response.json()
    assert oversized_booking["booking_status"] == "waitlisted"
    assert oversized_booking["participant_count"] == 2

    fitting_waitlist_response = client.get(
        f"/waitlist-entries/{fitting_body['waitlist_entry_id']}"
    )
    assert fitting_waitlist_response.status_code == 200
    assert fitting_waitlist_response.json()["waitlist_status"] == "accepted"

    fitting_booking_response = client.get(f"/bookings/{fitting_body['booking_id']}")
    assert fitting_booking_response.status_code == 200, fitting_booking_response.text
    fitting_booking = fitting_booking_response.json()
    assert fitting_booking["booking_status"] == "confirmed"

    participants_response = client.get(
        f"/game-participants?booking_id={fitting_body['booking_id']}"
    )
    assert participants_response.status_code == 200, participants_response.text
    assert {
        participant["participant_status"]
        for participant in participants_response.json()
    } == {"confirmed"}


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
