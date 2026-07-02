from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.database import SessionLocal
from backend.models import (
    Game,
    GameCredit,
    GameCreditUsage,
    Notification,
    Payment,
    Refund,
    SupportFlag,
    VenueImage,
)
from backend.services.admin_permission_service import (
    PERMISSION_MONEY_READ,
    PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
    PERMISSION_OFFICIAL_GAMES_READ,
    ROLE_PERMISSIONS,
)
from backend.services.game_credit_service import (
    GameCreditLedgerError,
    RELEASED_USAGE_STATUS,
    redeem_reserved_game_credits,
    reserve_game_credits,
)
from backend.services.stripe_service import (
    StripePaymentIntentResult,
    StripeRefundResult,
)
from backend.tests.helpers import (
    authenticate_as,
    create_booking,
    create_game_participant,
    create_payment,
    create_refund,
    create_user,
    create_user_payment_method,
    create_venue,
    create_waitlist_entry,
    get_money_as_admin,
    get_roster_as_admin,
    mock_checkout_payment_method_verification,
    set_user_role,
    unique_suffix,
)


def build_official_game_payload(**overrides: object) -> dict:
    starts_at = datetime.now(UTC) + timedelta(days=7)
    ends_at = starts_at + timedelta(hours=1)
    payload = {
        "title": "Admin Official Match",
        "venue": {
            "name": "Admin Test Field",
            "address_line_1": "500 Admin Ave",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "country_code": "US",
            "neighborhood": "Loop",
        },
        "starts_at": starts_at.isoformat(),
        "ends_at": ends_at.isoformat(),
        "timezone": "America/Chicago",
        "format_label": "5v5",
        "environment_type": "indoor",
        "total_spots": 10,
        "price_per_player_cents": 1500,
        "reason": "Create official game for test coverage.",
    }
    payload.update(overrides)
    return payload


def parse_response_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def issue_game_credit(
    client: TestClient,
    *,
    admin_id: str,
    user_id: str,
    game_id: str | None = None,
    booking_id: str | None = None,
    payment_id: str | None = None,
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
            "source_booking_id": booking_id,
            "source_payment_id": payment_id,
            "idempotency_key": f"admin-official-credit-{unique_suffix()}",
            "note": "Admin official game credit test.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def set_game_status(game_id: str, game_status: str) -> None:
    with SessionLocal() as db:
        db_game = db.get(Game, UUID(game_id))
        assert db_game is not None
        now = datetime.now(UTC)
        db_game.game_status = game_status
        if game_status == "cancelled":
            db_game.cancelled_at = now
        if game_status == "completed":
            db_game.completed_at = now
        db.commit()


def set_game_starts_at(game_id: str, starts_at: datetime) -> None:
    with SessionLocal() as db:
        db_game = db.get(Game, UUID(game_id))
        assert db_game is not None
        db_game.starts_at = starts_at
        db_game.ends_at = starts_at + timedelta(hours=1)
        db_game.starts_on_local = starts_at.date()
        db.commit()


def set_game_host(game_id: str, host_user_id: str) -> None:
    with SessionLocal() as db:
        db_game = db.get(Game, UUID(game_id))
        assert db_game is not None
        db_game.host_user_id = UUID(host_user_id)
        db.commit()


def create_active_primary_venue_image(venue_id: str, uploaded_by_user_id: str) -> None:
    now = datetime.now(UTC)
    image_id = uuid4()

    with SessionLocal() as db:
        db.add(
            VenueImage(
                id=image_id,
                venue_id=UUID(venue_id),
                uploaded_by_user_id=UUID(uploaded_by_user_id),
                storage_provider="r2",
                storage_object_key=f"venues/{venue_id}/primary-{image_id}.jpg",
                storage_bucket="pickup-lane-dev-media",
                storage_account_id="test-r2-account",
                content_type="image/jpeg",
                size_bytes=1200,
                etag=f"etag-{image_id}",
                image_role="card",
                image_status="active",
                is_primary=True,
                sort_order=0,
                alt_text="Primary venue photo",
                caption="Primary venue photo",
                upload_requested_at=now,
                upload_completed_at=now,
            )
        )
        db.commit()


def set_user_account_status(user_id: str, account_status: str) -> None:
    from backend.models import User

    with SessionLocal() as db:
        db_user = db.get(User, UUID(user_id))
        assert db_user is not None
        db_user.account_status = account_status
        db.commit()


def list_user_notifications(
    client: TestClient,
    user_id: str,
    notification_type: str,
) -> list[dict]:
    authenticate_as(user_id)
    response = client.get(f"/notifications/me?notification_type={notification_type}")

    assert response.status_code == 200, response.text
    return response.json()


def test_admin_can_create_official_game_without_initial_host(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )

    assert response.status_code == 201, response.text
    game = response.json()["game"]
    assert game["game_type"] == "official"
    assert game["payment_collection_type"] == "in_app"
    assert game["policy_mode"] == "official_standard"
    assert game["publish_status"] == "published"
    assert game["created_by_user_id"] == admin["id"]
    assert game["host_user_id"] is None
    assert game["minimum_age"] is None
    assert game["host_guest_max"] == 0

    audit_response = client.get("/admin/actions?action_type=create_official_game")
    assert audit_response.status_code == 200, audit_response.text
    assert any(
        action["target_game_id"] == game["id"] and action["target_user_id"] is None
        for action in audit_response.json()
    )


def test_admin_can_create_official_game_from_existing_venue(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])

    authenticate_as(admin["id"])
    response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(venue_id=venue["id"], venue=None),
    )

    assert response.status_code == 201, response.text
    assert response.json()["game"]["venue_id"] == venue["id"]


def test_admin_create_official_game_records_replacement_source_metadata(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    source_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(title="Wrong Venue Game"),
    )
    assert source_response.status_code == 201, source_response.text
    source_game = source_response.json()["game"]

    replacement_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(
            title="Correct Venue Game",
            replacement_for_game_id=source_game["id"],
            reason=f"Replacement for official game {source_game['id']}.",
        ),
    )
    assert replacement_response.status_code == 201, replacement_response.text
    replacement_game = replacement_response.json()["game"]

    audit_response = client.get("/admin/actions?action_type=create_official_game")
    assert audit_response.status_code == 200, audit_response.text
    replacement_audit = next(
        action
        for action in audit_response.json()
        if action["target_game_id"] == replacement_game["id"]
    )
    assert replacement_audit["reason"] == (
        f"Replacement for official game {source_game['id']}."
    )
    assert replacement_audit["metadata"]["replacement"] == {
        "replacement_for_game_id": source_game["id"],
        "replacement_for_game_title": source_game["title"],
        "replacement_for_game_status": source_game["game_status"],
    }


def test_admin_create_official_game_rejects_invalid_replacement_source(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(
            replacement_for_game_id=str(uuid4()),
        ),
    )

    assert response.status_code == 400, response.text
    assert "replacement_for_game_id" in response.text


def test_admin_can_list_and_get_official_games(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]

    list_response = client.get("/admin/official-games?view=active")
    assert list_response.status_code == 200, list_response.text
    list_body = list_response.json()
    assert list_body["limit"] == 24
    assert list_body["has_more"] is False
    assert list_body["next_cursor"] is None
    listed_game = next(item for item in list_body["games"] if item["id"] == game["id"])
    assert listed_game["title"] == game["title"]
    assert listed_game["starts_on_local"] == game["starts_on_local"]
    assert listed_game["format_label"] == game["format_label"]
    assert listed_game["game_player_group"] == game["game_player_group"]
    assert listed_game["environment_type"] == game["environment_type"]
    assert listed_game["booked_spots"] == 0
    assert listed_game["issues"] == ["missing_host", "missing_photo"]
    assert "game_status" not in listed_game

    get_response = client.get(f"/admin/official-games/{game['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["game"]["id"] == game["id"]


def test_admin_official_games_list_returns_card_data_without_n_plus_one_counts(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    host = create_user(client)
    confirmed_player = create_user(client)
    pending_player = create_user(client)
    waitlisted_player = create_user(client)
    cancelled_player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(title="Photo Ready Official"),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    set_game_host(game["id"], host["id"])
    create_active_primary_venue_image(game["venue_id"], admin["id"])

    create_game_participant(
        client,
        confirmed_player["id"],
        game["id"],
        price_cents=1500,
        participant_status="confirmed",
    )
    create_game_participant(
        client,
        pending_player["id"],
        game["id"],
        price_cents=1500,
        participant_status="pending_payment",
        roster_order=2,
    )
    create_game_participant(
        client,
        waitlisted_player["id"],
        game["id"],
        price_cents=1500,
        participant_status="waitlisted",
        roster_order=3,
    )
    create_game_participant(
        client,
        cancelled_player["id"],
        game["id"],
        price_cents=1500,
        participant_status="cancelled",
        cancellation_type="admin_cancelled",
        roster_order=4,
    )

    monkeypatch.setattr(
        "backend.services.official_game_query_service.create_object_read_url",
        lambda object_key: f"https://read.test/{object_key}",
    )

    response = client.get("/admin/official-games?view=active&search=photo")

    assert response.status_code == 200, response.text
    games = response.json()["games"]
    assert len(games) == 1
    card = games[0]
    assert card["id"] == game["id"]
    assert card["venue_name_snapshot"] == game["venue_name_snapshot"]
    assert card["city_snapshot"] == game["city_snapshot"]
    assert card["state_snapshot"] == game["state_snapshot"]
    assert card["price_per_player_cents"] == 1500
    assert card["currency"] == "USD"
    assert card["total_spots"] == 10
    assert card["booked_spots"] == 2
    assert card["host_user_id"] == host["id"]
    assert card["primary_venue_image_url"].startswith("https://read.test/venues/")
    assert card["issues"] == []


def test_admin_official_games_list_keeps_photo_valid_when_read_url_generation_fails(
    client: TestClient,
    monkeypatch,
):
    from backend.services.r2_storage_service import R2StorageConfigError

    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(title="Photo R2 Official"),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    create_active_primary_venue_image(game["venue_id"], admin["id"])

    def raise_read_url_config_error(object_key: str) -> str:
        del object_key
        raise R2StorageConfigError("Missing R2 config in test.")

    monkeypatch.setattr(
        "backend.services.official_game_query_service.create_object_read_url",
        raise_read_url_config_error,
    )

    response = client.get("/admin/official-games?view=active&search=photo")

    assert response.status_code == 200, response.text
    games = response.json()["games"]
    assert len(games) == 1
    card = games[0]
    assert card["id"] == game["id"]
    assert card["primary_venue_image_url"] is None
    assert card["issues"] == ["missing_host"]


def test_admin_official_games_list_filters_by_view_search_and_date(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    harrison_start = (
        datetime.now(UTC).replace(hour=18, minute=0, second=0, microsecond=0)
        + timedelta(days=7)
    )
    fleet_start = harrison_start + timedelta(days=1)
    harrison_starts_on = harrison_start.date().isoformat()

    authenticate_as(admin["id"])
    harrison_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(
            title="Harrison Park 4v4",
            starts_at=harrison_start.isoformat(),
            ends_at=(harrison_start + timedelta(hours=1)).isoformat(),
        ),
    )
    assert harrison_response.status_code == 201, harrison_response.text
    harrison_game = harrison_response.json()["game"]

    fleet_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(
            title="Fleet Fields 7v7",
            venue={
                "name": "Fleet Fields",
                "address_line_1": "700 Fleet Ave",
                "city": "Chicago",
                "state": "IL",
                "postal_code": "60607",
                "country_code": "US",
                "neighborhood": "West Loop",
            },
            starts_at=fleet_start.isoformat(),
            ends_at=(fleet_start + timedelta(hours=1)).isoformat(),
        ),
    )
    assert fleet_response.status_code == 201, fleet_response.text

    completed_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(
            title="Harrison Completed",
            starts_at=harrison_start.isoformat(),
            ends_at=(harrison_start + timedelta(hours=1)).isoformat(),
        ),
    )
    assert completed_response.status_code == 201, completed_response.text
    completed_game = completed_response.json()["game"]
    set_game_status(completed_game["id"], "completed")

    active_response = client.get(
        "/admin/official-games",
        params={
            "view": "active",
            "search": "harrison",
            "starts_on": harrison_starts_on,
        },
    )
    assert active_response.status_code == 200, active_response.text
    assert [item["id"] for item in active_response.json()["games"]] == [
        harrison_game["id"]
    ]

    completed_list_response = client.get(
        "/admin/official-games",
        params={
            "view": "completed",
            "search": "harrison",
            "starts_on": harrison_starts_on,
        },
    )
    assert completed_list_response.status_code == 200, completed_list_response.text
    completed_games = completed_list_response.json()["games"]
    assert [item["id"] for item in completed_games] == [completed_game["id"]]
    assert completed_games[0]["issues"] == []


def test_admin_official_games_cancelled_view_includes_abandoned_games(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    cancelled_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(title="Cancelled Official"),
    )
    assert cancelled_response.status_code == 201, cancelled_response.text
    cancelled_game = cancelled_response.json()["game"]
    set_game_status(cancelled_game["id"], "cancelled")

    abandoned_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(title="Abandoned Official"),
    )
    assert abandoned_response.status_code == 201, abandoned_response.text
    abandoned_game = abandoned_response.json()["game"]
    set_game_status(abandoned_game["id"], "abandoned")

    response = client.get("/admin/official-games?view=cancelled")

    assert response.status_code == 200, response.text
    returned_ids = {item["id"] for item in response.json()["games"]}
    assert cancelled_game["id"] in returned_ids
    assert abandoned_game["id"] in returned_ids


def test_admin_official_games_list_cursor_paginates_and_is_query_bound(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    first_start = (
        datetime.now(UTC).replace(hour=18, minute=0, second=0, microsecond=0)
        + timedelta(days=7)
    )

    authenticate_as(admin["id"])
    game_ids: list[str] = []
    for index in range(3):
        starts_at = first_start + timedelta(hours=index)
        create_response = client.post(
            "/admin/official-games",
            json=build_official_game_payload(
                title=f"Cursor Official {index + 1}",
                starts_at=starts_at.isoformat(),
                ends_at=(starts_at + timedelta(hours=1)).isoformat(),
            ),
        )
        assert create_response.status_code == 201, create_response.text
        game_ids.append(create_response.json()["game"]["id"])

    first_page = client.get("/admin/official-games?view=active&limit=2")
    assert first_page.status_code == 200, first_page.text
    first_body = first_page.json()
    assert [item["id"] for item in first_body["games"]] == game_ids[:2]
    assert first_body["has_more"] is True
    assert first_body["next_cursor"]

    second_page = client.get(
        "/admin/official-games",
        params={
            "view": "active",
            "limit": 2,
            "cursor": first_body["next_cursor"],
        },
    )
    assert second_page.status_code == 200, second_page.text
    second_body = second_page.json()
    assert [item["id"] for item in second_body["games"]] == [game_ids[2]]
    assert second_body["has_more"] is False
    assert second_body["next_cursor"] is None

    mismatch_response = client.get(
        "/admin/official-games",
        params={
            "view": "completed",
            "cursor": first_body["next_cursor"],
        },
    )
    assert mismatch_response.status_code == 400, mismatch_response.text
    assert "cursor does not match" in mismatch_response.text


def test_admin_official_games_list_caps_limit(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get("/admin/official-games?view=active&limit=500")

    assert response.status_code == 200, response.text
    assert response.json()["limit"] == 100


def test_admin_can_list_official_game_participants_from_admin_route(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    participant = create_game_participant(
        client,
        player["id"],
        game["id"],
        price_cents=1500,
    )

    response = client.get(f"/admin/official-games/{game['id']}/participants")

    assert response.status_code == 200, response.text
    assert any(item["id"] == participant["id"] for item in response.json())


def test_admin_can_list_official_game_bookings_from_admin_route(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    other_player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    other_game_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(title="Other Admin Official Match"),
    )
    assert other_game_response.status_code == 201, other_game_response.text
    other_game = other_game_response.json()["game"]
    booking = create_booking(client, player["id"], game["id"])
    other_booking = create_booking(client, other_player["id"], other_game["id"])

    response = client.get(f"/admin/official-games/{game['id']}/bookings")

    assert response.status_code == 200, response.text
    bookings = response.json()
    booking_ids = {item["id"] for item in bookings}
    assert booking["id"] in booking_ids
    assert other_booking["id"] not in booking_ids
    assert all(item["game_id"] == game["id"] for item in bookings)


def test_admin_can_list_official_game_waitlist_from_admin_route(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    other_player = create_user(client)
    set_user_role(admin["id"], "admin")
    payment_method = create_user_payment_method(client, player["id"])

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    other_game_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(title="Other Admin Official Match"),
    )
    assert other_game_response.status_code == 201, other_game_response.text
    other_game = other_game_response.json()["game"]
    waitlist_entry = create_waitlist_entry(
        client,
        player["id"],
        game["id"],
        authorized_payment_method_id=payment_method["id"],
        authorized_stripe_payment_method_id=payment_method[
            "stripe_payment_method_id"
        ],
        authorized_payment_method_brand="visa",
        authorized_payment_method_last4="4242",
        authorized_amount_cents=1500,
    )
    other_waitlist_entry = create_waitlist_entry(
        client,
        other_player["id"],
        other_game["id"],
    )

    response = client.get(f"/admin/official-games/{game['id']}/waitlist")

    assert response.status_code == 200, response.text
    waitlist_entries = response.json()
    waitlist_entry_ids = {item["id"] for item in waitlist_entries}
    assert waitlist_entry["id"] in waitlist_entry_ids
    assert other_waitlist_entry["id"] not in waitlist_entry_ids
    assert all(item["game_id"] == game["id"] for item in waitlist_entries)
    assert waitlist_entries[0]["authorized_payment_method_brand"] == "visa"
    assert waitlist_entries[0]["authorized_payment_method_last4"] == "4242"
    assert "authorized_payment_method_id" not in waitlist_entries[0]
    assert "authorized_stripe_payment_method_id" not in waitlist_entries[0]


def test_admin_can_list_official_game_money_from_admin_route(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    cross_game_player = create_user(client)
    participant_refund_player = create_user(client)
    other_player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    other_game_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(title="Other Admin Official Match"),
    )
    assert other_game_response.status_code == 201, other_game_response.text
    other_game = other_game_response.json()["game"]

    booking = create_booking(client, player["id"], game["id"])
    cross_game_booking = create_booking(
        client,
        cross_game_player["id"],
        game["id"],
    )
    other_booking = create_booking(client, other_player["id"], other_game["id"])
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
    )
    other_payment = create_payment(
        client,
        other_player["id"],
        booking_id=other_booking["id"],
        amount_cents=other_booking["total_cents"],
        payment_status="succeeded",
    )
    participant_refund_target = create_game_participant(
        client,
        participant_refund_player["id"],
        game["id"],
        roster_order=2,
    )
    refund = create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        amount_cents=500,
        refund_status="processing",
    )
    other_refund = create_refund(
        client,
        other_payment["id"],
        booking_id=other_booking["id"],
        amount_cents=500,
        refund_status="processing",
    )
    direct_game_payment_id = uuid4()
    participant_refund_id = uuid4()
    # Seed defensive diagnostic linkages that current payment/refund mutation
    # services intentionally do not create, but the read model must still surface.
    with SessionLocal() as db:
        db.add(
            Payment(
                id=direct_game_payment_id,
                payer_user_id=UUID(player["id"]),
                booking_id=None,
                game_id=UUID(game["id"]),
                payment_type="admin_charge",
                provider="stripe",
                provider_payment_intent_id=f"pi_direct_game_{unique_suffix()}",
                provider_charge_id=None,
                idempotency_key=f"direct-game-payment-{unique_suffix()}",
                amount_cents=250,
                currency="USD",
                payment_status="processing",
                payment_metadata={"source": "admin_money_route_coverage"},
            )
        )
        db.add(
            Refund(
                id=participant_refund_id,
                payment_id=UUID(other_payment["id"]),
                booking_id=None,
                participant_id=UUID(participant_refund_target["id"]),
                provider_refund_id=f"re_participant_scope_{unique_suffix()}",
                amount_cents=200,
                currency="USD",
                refund_reason="admin_refund",
                refund_status="processing",
            )
        )
        db.commit()
    credit = issue_game_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        amount_cents=700,
    )
    other_credit = issue_game_credit(
        client,
        admin_id=admin["id"],
        user_id=other_player["id"],
        game_id=other_game["id"],
        amount_cents=700,
    )
    cross_game_credit = issue_game_credit(
        client,
        admin_id=admin["id"],
        user_id=cross_game_player["id"],
        game_id=other_game["id"],
        amount_cents=400,
    )
    source_booking_credit = issue_game_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        booking_id=booking["id"],
        amount_cents=200,
    )
    source_payment_credit = issue_game_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        payment_id=str(direct_game_payment_id),
        amount_cents=150,
    )
    authenticate_as(admin["id"])
    reverse_response = client.post(
        f"/admin/game-credits/{source_payment_credit['id']}/reverse",
        json={
            "idempotency_key": f"reverse-payment-credit-{unique_suffix()}",
            "note": "Reverse payment-linked credit for money route coverage.",
        },
    )
    assert reverse_response.status_code == 200, reverse_response.text
    with SessionLocal() as db:
        now = datetime.now(UTC)
        usages = reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=300,
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            payment_id=UUID(payment["id"]),
            now=now,
            idempotency_scope=f"admin-money-route:{booking['id']}",
        )
        credit_usage_id = str(usages[0].id)
        cross_game_usages = reserve_game_credits(
            db,
            UUID(cross_game_player["id"]),
            amount_cents=400,
            booking_id=UUID(cross_game_booking["id"]),
            game_id=UUID(game["id"]),
            now=now,
            idempotency_scope=f"cross-game-money-route:{cross_game_booking['id']}",
        )
        cross_game_usage_id = str(cross_game_usages[0].id)
        db.commit()

    authenticate_as(admin["id"])
    response = client.get(f"/admin/official-games/{game['id']}/money")

    assert response.status_code == 200, response.text
    body = response.json()
    payment_ids = {item["id"] for item in body["payments"]}
    refund_ids = {item["id"] for item in body["refunds"]}
    credit_ids = {item["id"] for item in body["credits"]}
    credit_usage_ids = {item["id"] for item in body["credit_usages"]}
    assert payment["id"] in payment_ids
    assert str(direct_game_payment_id) in payment_ids
    assert other_payment["id"] not in payment_ids
    assert refund["id"] in refund_ids
    assert str(participant_refund_id) in refund_ids
    assert other_refund["id"] not in refund_ids
    assert credit["id"] in credit_ids
    assert cross_game_credit["id"] in credit_ids
    assert source_booking_credit["id"] in credit_ids
    assert source_payment_credit["id"] in credit_ids
    assert other_credit["id"] not in credit_ids
    assert credit_usage_id in credit_usage_ids
    assert cross_game_usage_id in credit_usage_ids
    assert any(
        item["game_credit_id"] == source_payment_credit["id"]
        and item["payment_id"] == str(direct_game_payment_id)
        and item["booking_id"] is None
        and item["game_id"] is None
        for item in body["credit_usages"]
    )


def test_official_game_money_reads_require_money_permission(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    monkeypatch.setitem(
        ROLE_PERMISSIONS,
        "admin",
        frozenset(
            {
                PERMISSION_OFFICIAL_GAMES_READ,
                PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
            }
        ),
    )
    missing_game_id = "00000000-0000-0000-0000-000000000000"

    authenticate_as(admin["id"])
    game_response = client.get(f"/admin/official-games/{missing_game_id}")
    participant_response = client.get(
        f"/admin/official-games/{missing_game_id}/participants"
    )
    booking_response = client.get(
        f"/admin/official-games/{missing_game_id}/bookings"
    )
    waitlist_response = client.get(
        f"/admin/official-games/{missing_game_id}/waitlist"
    )
    money_response = client.get(f"/admin/official-games/{missing_game_id}/money")
    removal_preview_response = client.post(
        (
            f"/admin/official-games/{missing_game_id}/participants/"
            f"{missing_game_id}/remove-preview"
        )
    )

    assert game_response.status_code == 404, game_response.text
    assert participant_response.status_code == 404, participant_response.text
    assert booking_response.status_code == 403, booking_response.text
    assert waitlist_response.status_code == 403, waitlist_response.text
    assert money_response.status_code == 403, money_response.text
    assert removal_preview_response.status_code == 403, removal_preview_response.text


def test_admin_official_game_cancel_preview_reports_money_without_mutation(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    waitlisted_player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(client, player["id"], game["id"])
    create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        price_cents=booking["total_cents"],
    )
    create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id="ch_admin_cancel_preview",
    )
    create_waitlist_entry(client, waitlisted_player["id"], game["id"])

    authenticate_as(admin["id"])
    response = client.post(f"/admin/official-games/{game['id']}/cancel-preview")

    assert response.status_code == 200, response.text
    preview = response.json()
    assert len(preview["preview_token"]) == 64
    assert preview["required_permissions"] == ["admin.official_games.cancel"]
    assert preview["booking_count"] == 1
    assert preview["participant_count"] == 1
    assert preview["waitlist_entry_count"] == 1
    assert preview["cash_refundable_cents"] == booking["total_cents"]
    assert preview["refund_follow_up_required"] is False
    assert preview["payment_follow_up_required"] is False
    impact = preview["booking_impacts"][0]
    assert impact["booking_id"] == booking["id"]
    assert impact["result_category"] == "stripe_refund"
    assert impact["cash_refundable_cents"] == booking["total_cents"]

    get_response = client.get(f"/admin/official-games/{game['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["game"]["game_status"] == "scheduled"

    refunds_response = get_money_as_admin(client, f"/refunds?booking_id={booking['id']}")
    assert refunds_response.status_code == 200, refunds_response.text
    assert refunds_response.json() == []


def test_admin_official_game_cancel_execution_returns_booking_results(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(client, player["id"], game["id"])
    create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        price_cents=booking["total_cents"],
    )
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id="ch_admin_cancel_execute",
    )
    refund_calls: list[dict[str, object]] = []

    def fake_create_stripe_refund(**kwargs):
        refund_calls.append(kwargs)
        return StripeRefundResult(
            id="re_admin_cancel_execute",
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
    preview_response = client.post(
        f"/admin/official-games/{game['id']}/cancel-preview"
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()
    execute_response = client.post(
        f"/admin/official-games/{game['id']}/cancel",
        json={
            "preview_token": preview["preview_token"],
            "reason": "Venue emergency.",
        },
    )

    assert execute_response.status_code == 200, execute_response.text
    result = execute_response.json()
    assert result["game"]["game_status"] == "cancelled"
    assert result["game"]["cancel_reason"] == "Venue emergency."
    assert result["cancelled_booking_count"] == 1
    assert result["refund_created_count"] == 1
    assert result["refund_follow_up_required"] is False
    assert result["support_flag_ids"] == []
    booking_result = result["booking_results"][0]
    assert booking_result["booking_id"] == booking["id"]
    assert booking_result["result_category"] == "stripe_refunded"
    assert booking_result["cash_refunded_cents"] == booking["total_cents"]
    assert booking_result["refunds"][0]["refund_status"] == "succeeded"
    assert refund_calls[0]["charge_id"] == payment["provider_charge_id"]


def test_admin_official_game_cancel_releases_pending_credit_hold(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(
        client,
        player["id"],
        game["id"],
        booking_status="pending_payment",
        payment_status="requires_action",
        booked_at=None,
    )
    create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        participant_status="pending_payment",
        confirmed_at=None,
        price_cents=booking["total_cents"],
    )
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=800,
        payment_status="requires_action",
    )
    credit = issue_game_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        amount_cents=500,
    )
    with SessionLocal() as db:
        usages = reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=500,
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            payment_id=UUID(payment["id"]),
            now=datetime.now(UTC),
            idempotency_scope=f"admin-cancel-pending:{booking['id']}",
        )
        assert len(usages) == 1
        db.commit()

    authenticate_as(admin["id"])
    preview_response = client.post(
        f"/admin/official-games/{game['id']}/cancel-preview"
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()
    assert preview["credit_releasable_cents"] == 500
    assert preview["booking_impacts"] == [
        {
            "booking_id": booking["id"],
            "buyer_user_id": player["id"],
            "booking_status": "pending_payment",
            "booking_payment_status": "requires_action",
            "participant_count": 1,
            "payment_statuses": ["requires_action"],
            "refund_statuses": [],
            "result_category": "pending_hold_release",
            "cash_refundable_cents": 0,
            "credit_restorable_cents": 0,
            "credit_releasable_cents": 500,
            "follow_up_required": False,
            "follow_up_reason": None,
        }
    ]

    execute_response = client.post(
        f"/admin/official-games/{game['id']}/cancel",
        json={
            "preview_token": preview["preview_token"],
            "reason": "Venue emergency.",
        },
    )

    assert execute_response.status_code == 200, execute_response.text
    result = execute_response.json()
    assert result["credit_released_count"] == 1
    assert result["credit_released_cents"] == 500
    assert result["credit_restored_cents"] == 0
    booking_result = result["booking_results"][0]
    assert booking_result["result_category"] == "pending_hold_released"
    assert booking_result["booking_payment_status"] == "failed"
    assert booking_result["credit_released_cents"] == 500
    assert booking_result["credit_restored_cents"] == 0

    payment_response = get_money_as_admin(client, f"/payments/{payment['id']}")
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["payment_status"] == "canceled"
    with SessionLocal() as db:
        refreshed_credit = db.get(GameCredit, UUID(credit["id"]))
        usage = db.scalars(
            select(GameCreditUsage).where(
                GameCreditUsage.booking_id == UUID(booking["id"])
            )
        ).one()

    assert refreshed_credit is not None
    assert refreshed_credit.remaining_cents == 500
    assert usage.usage_status == RELEASED_USAGE_STATUS


def test_admin_official_game_cancel_rejects_reason_over_500_characters(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    preview_response = client.post(
        f"/admin/official-games/{game['id']}/cancel-preview"
    )
    assert preview_response.status_code == 200, preview_response.text

    execute_response = client.post(
        f"/admin/official-games/{game['id']}/cancel",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "x" * 501,
        },
    )

    assert execute_response.status_code == 422, execute_response.text
    get_response = client.get(f"/admin/official-games/{game['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["game"]["game_status"] == "scheduled"


def test_admin_official_game_cancel_partial_failure_returns_support_follow_up(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(client, player["id"], game["id"])
    create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        price_cents=booking["total_cents"],
    )
    create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id=None,
    )

    preview_response = client.post(
        f"/admin/official-games/{game['id']}/cancel-preview"
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()
    assert preview["refund_follow_up_required"] is True
    assert preview["booking_impacts"][0]["follow_up_reason"] == (
        "missing_stripe_charge_id"
    )

    execute_response = client.post(
        f"/admin/official-games/{game['id']}/cancel",
        json={
            "preview_token": preview["preview_token"],
            "reason": "Venue emergency.",
        },
    )

    assert execute_response.status_code == 200, execute_response.text
    result = execute_response.json()
    assert result["refund_follow_up_required"] is True
    assert result["refund_failed_count"] == 1
    assert result["refund_missing_charge_count"] == 1
    assert len(result["support_flag_ids"]) == 1
    booking_result = result["booking_results"][0]
    assert booking_result["result_category"] == "follow_up_required"
    assert booking_result["follow_up_required"] is True
    assert booking_result["follow_up_reason"] == "missing_stripe_charge_id"
    assert booking_result["refunds"][0]["refund_status"] == "failed"

    with SessionLocal() as db:
        support_flag = db.get(SupportFlag, UUID(result["support_flag_ids"][0]))

    assert support_flag is not None
    assert support_flag.flag_type == "official_cancel_partial_failure"
    assert support_flag.target_game_id == UUID(game["id"])
    assert support_flag.source_admin_action_id is not None


def test_admin_official_game_cancel_credit_failure_happens_before_stripe(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    cash_player = create_user(client)
    credit_player = create_user(client)
    set_user_role(admin["id"], "admin")
    refund_calls: list[dict[str, object]] = []

    def fake_create_stripe_refund(**kwargs):
        refund_calls.append(kwargs)
        raise AssertionError("Stripe must not run before all credit returns succeed.")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    cash_booking = create_booking(client, cash_player["id"], game["id"])
    create_game_participant(
        client,
        cash_player["id"],
        game["id"],
        booking_id=cash_booking["id"],
        price_cents=cash_booking["total_cents"],
    )
    create_payment(
        client,
        cash_player["id"],
        booking_id=cash_booking["id"],
        amount_cents=cash_booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id="ch_cancel_credit_preflight",
    )
    credit_booking = create_booking(client, credit_player["id"], game["id"])
    create_game_participant(
        client,
        credit_player["id"],
        game["id"],
        booking_id=credit_booking["id"],
        price_cents=credit_booking["total_cents"],
    )

    def fail_second_credit_restore(db, booking_id, **kwargs):
        del db, kwargs
        if str(booking_id) == credit_booking["id"]:
            raise GameCreditLedgerError("Credit ledger is inconsistent.")
        return []

    monkeypatch.setattr(
        "backend.services.game_cancellation_service.create_stripe_refund",
        fake_create_stripe_refund,
    )
    monkeypatch.setattr(
        "backend.services.game_cancellation_service.restore_redeemed_game_credits",
        fail_second_credit_restore,
    )

    authenticate_as(admin["id"])
    preview_response = client.post(
        f"/admin/official-games/{game['id']}/cancel-preview"
    )
    assert preview_response.status_code == 200, preview_response.text
    execute_response = client.post(
        f"/admin/official-games/{game['id']}/cancel",
        json={
            "preview_token": preview_response.json()["preview_token"],
            "reason": "Venue emergency.",
        },
    )

    assert execute_response.status_code == 409, execute_response.text
    assert "game was not cancelled" in execute_response.text.lower()
    assert refund_calls == []

    game_response = client.get(f"/admin/official-games/{game['id']}")
    assert game_response.status_code == 200, game_response.text
    assert game_response.json()["game"]["game_status"] == "scheduled"

    with SessionLocal() as db:
        support_flag = db.scalars(
            select(SupportFlag).where(
                SupportFlag.flag_type == "official_cancel_partial_failure",
                SupportFlag.target_game_id == UUID(game["id"]),
                SupportFlag.target_booking_id == UUID(credit_booking["id"]),
            )
        ).one()

    assert support_flag.metadata_["credit_operation"] == "restore"
    assert support_flag.source_admin_action_id is None

    resolve_response = client.post(
        f"/admin/support-flags/{support_flag.id}/resolve",
        json={
            "outcome": "handled_externally",
            "reason": "Verified the first credit follow-up externally.",
        },
    )
    assert resolve_response.status_code == 200, resolve_response.text
    assert resolve_response.json()["flag_status"] == "resolved"

    repeat_preview_response = client.post(
        f"/admin/official-games/{game['id']}/cancel-preview"
    )
    assert repeat_preview_response.status_code == 200, repeat_preview_response.text
    repeat_execute_response = client.post(
        f"/admin/official-games/{game['id']}/cancel",
        json={
            "preview_token": repeat_preview_response.json()["preview_token"],
            "reason": "Venue emergency again.",
        },
    )

    assert repeat_execute_response.status_code == 409, repeat_execute_response.text
    assert refund_calls == []

    with SessionLocal() as db:
        reopened_flags = db.scalars(
            select(SupportFlag).where(
                SupportFlag.flag_type == "official_cancel_partial_failure",
                SupportFlag.target_game_id == UUID(game["id"]),
                SupportFlag.target_booking_id == UUID(credit_booking["id"]),
            )
        ).all()

    assert len(reopened_flags) == 1
    reopened_flag = reopened_flags[0]
    assert reopened_flag.id == support_flag.id
    assert reopened_flag.flag_status == "open"
    assert reopened_flag.resolved_at is None
    assert reopened_flag.resolved_by_user_id is None
    assert reopened_flag.resolution_outcome is None
    assert reopened_flag.resolution_reason is None
    assert reopened_flag.resolution_admin_action_id is None


def test_admin_official_game_cancel_execution_rejects_stale_preview(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    player = create_user(client)
    late_player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(client, player["id"], game["id"])
    create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
    )
    create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=booking["total_cents"],
        payment_status="succeeded",
        provider_charge_id="ch_admin_cancel_stale",
    )

    def fail_create_stripe_refund(**kwargs):
        raise AssertionError("Stripe refund should not run for a stale preview.")

    monkeypatch.setattr(
        "backend.services.game_cancellation_service.create_stripe_refund",
        fail_create_stripe_refund,
    )

    authenticate_as(admin["id"])
    preview_response = client.post(
        f"/admin/official-games/{game['id']}/cancel-preview"
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()

    late_booking = create_booking(client, late_player["id"], game["id"])
    create_game_participant(
        client,
        late_player["id"],
        game["id"],
        booking_id=late_booking["id"],
    )

    authenticate_as(admin["id"])
    execute_response = client.post(
        f"/admin/official-games/{game['id']}/cancel",
        json={
            "preview_token": preview["preview_token"],
            "reason": "Venue emergency.",
        },
    )

    assert execute_response.status_code == 409, execute_response.text
    assert "impact changed" in execute_response.text

    get_response = client.get(f"/admin/official-games/{game['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["game"]["game_status"] == "scheduled"


def test_admin_lookup_routes_return_users_and_venues(client: TestClient):
    admin = create_user(client, first_name="Admin", last_name="Lookup")
    player = create_user(client, first_name="Player", last_name="Lookup")
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"], name="Lookup Field")

    authenticate_as(admin["id"])
    users_response = client.get("/admin/lookups/users?query=lookup")
    venues_response = client.get("/admin/lookups/venues?query=lookup")

    assert users_response.status_code == 200, users_response.text
    assert {user["id"] for user in users_response.json()} >= {
        admin["id"],
        player["id"],
    }
    assert venues_response.status_code == 200, venues_response.text
    assert any(item["id"] == venue["id"] for item in venues_response.json())


def test_admin_can_update_official_game_details(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    starts_at = datetime.now(UTC) + timedelta(days=10)
    ends_at = starts_at + timedelta(hours=1, minutes=30)

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]

    update_response = client.patch(
        f"/admin/official-games/{game['id']}",
        json={
            "title": "Updated Official Match",
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "total_spots": 12,
            "price_per_player_cents": 1000,
            "game_notes": "Bring both shirts.",
            "parking_notes": "Use the north lot.",
            "reason": "Update match details.",
        },
    )

    assert update_response.status_code == 200, update_response.text
    updated_game = update_response.json()["game"]
    assert updated_game["title"] == "Updated Official Match"
    assert updated_game["venue_id"] == game["venue_id"]
    assert updated_game["venue_name_snapshot"] == game["venue_name_snapshot"]
    assert updated_game["total_spots"] == 12
    assert updated_game["price_per_player_cents"] == 1000
    assert updated_game["game_notes"] == "Bring both shirts."
    assert updated_game["parking_notes"] == "Use the north lot."

    audit_response = client.get(
        f"/admin/actions?action_type=update_official_game&target_game_id={game['id']}"
    )
    assert audit_response.status_code == 200, audit_response.text
    audit_rows = audit_response.json()
    assert len(audit_rows) == 1
    assert "price_per_player_cents" in audit_rows[0]["metadata"]["changed_fields"]
    assert audit_rows[0]["target_venue_id"] is None


def test_admin_official_game_update_rejects_capacity_below_roster(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(format_label="3v3", total_spots=10),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]

    for index in range(7):
        player = create_user(client)
        create_game_participant(
            client,
            player["id"],
            game["id"],
            price_cents=1500,
            roster_order=index + 1,
        )

    response = client.patch(
        f"/admin/official-games/{game['id']}",
        json={"total_spots": 6, "reason": "Reduce capacity."},
    )

    assert response.status_code == 400, response.text
    assert "active roster count" in response.text


def test_admin_official_game_update_invalidates_pending_checkout(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    def fake_create_payment_intent(**kwargs):
        return StripePaymentIntentResult(
            id="pi_admin_update_pending",
            client_secret="pi_admin_update_pending_secret",
            status="requires_payment_method",
        )

    def fake_confirm_payment_intent(payment_intent_id, **kwargs):
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret="pi_admin_update_pending_secret",
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

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    credit = issue_game_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        amount_cents=500,
    )

    authenticate_as(player["id"])
    payment_method = create_user_payment_method(
        client,
        player["id"],
        stripe_customer_id="cus_admin_update_pending",
        stripe_payment_method_id="pm_admin_update_pending",
    )
    mock_checkout_payment_method_verification(monkeypatch, payment_method)
    checkout_response = client.post(
        f"/checkout/games/{game['id']}/payment-intent",
        json={
            "guest_count": 0,
            "payment_method_id": payment_method["id"],
        },
    )
    assert checkout_response.status_code == 201, checkout_response.text
    checkout = checkout_response.json()
    assert checkout["credit_applied_cents"] == 500

    authenticate_as(admin["id"])
    update_response = client.patch(
        f"/admin/official-games/{game['id']}",
        json={
            "price_per_player_cents": 1000,
            "reason": "Late discount.",
        },
    )
    assert update_response.status_code == 200, update_response.text

    booking_response = client.get(f"/bookings/{checkout['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "expired"
    assert booking["payment_status"] == "failed"

    payment_response = get_money_as_admin(client, f"/payments/{checkout['payment_id']}")
    assert payment_response.status_code == 200, payment_response.text
    payment = payment_response.json()
    assert payment["payment_status"] == "canceled"
    assert payment["failure_code"] == "admin_game_updated"

    participants_response = get_roster_as_admin(
        client,
        f"/game-participants?booking_id={checkout['booking_id']}",
    )
    assert participants_response.status_code == 200, participants_response.text
    assert {
        participant["participant_status"]
        for participant in participants_response.json()
    } == {"cancelled"}

    with SessionLocal() as db:
        refreshed_credit = db.get(GameCredit, UUID(credit["id"]))
        usage = db.scalars(
            select(GameCreditUsage).where(
                GameCreditUsage.booking_id == UUID(checkout["booking_id"])
            )
        ).one()

    assert refreshed_credit is not None
    assert refreshed_credit.remaining_cents == 500
    assert refreshed_credit.credit_status == "active"
    assert usage.usage_status == RELEASED_USAGE_STATUS
    assert usage.release_reason == "admin_game_updated"

    audit_response = client.get(
        f"/admin/actions?action_type=update_official_game&target_game_id={game['id']}"
    )
    assert audit_response.status_code == 200, audit_response.text
    audit_metadata = audit_response.json()[0]["metadata"]
    assert (
        "price_per_player_cents"
        in audit_metadata["checkout_sensitive_changed_fields"]
    )
    assert audit_metadata["expired_pending_booking_count"] == 1


def test_admin_official_game_update_rejects_removed_edit_fields(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    venue = create_venue(client, admin["id"])

    for payload, rejected_field in (
        ({"venue_id": venue["id"]}, "venue_id"),
        ({"minimum_age": 21}, "minimum_age"),
        ({"host_guest_max": 4}, "host_guest_max"),
        ({"description": "Internal edit"}, "description"),
    ):
        update_response = client.patch(
            f"/admin/official-games/{game['id']}",
            json=payload,
        )
        assert update_response.status_code == 422, update_response.text
        assert rejected_field in update_response.text


def test_admin_can_add_player_with_waived_payment(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]

    add_response = client.post(
        f"/admin/official-games/{game['id']}/players",
        json={
            "user_id": player["id"],
            "reason": "Comp player for helping run warmups.",
        },
    )

    assert add_response.status_code == 201, add_response.text
    participant = add_response.json()
    assert participant["participant_type"] == "admin_added"
    assert participant["participant_status"] == "confirmed"
    assert participant["user_id"] == player["id"]
    assert participant["price_cents"] == 0

    added_notifications = list_user_notifications(
        client,
        player["id"],
        "game_player_added_by_admin",
    )
    assert len(added_notifications) == 1
    added_notification = added_notifications[0]
    assert added_notification["is_read"] is False
    assert added_notification["source_type"] == "official_game"
    assert added_notification["source_label"] == "Official Game"
    assert added_notification["action_key"] == "view_game"
    assert added_notification["action"] is not None
    assert added_notification["related_game_id"] == game["id"]
    assert added_notification["related_participant_id"] == participant["id"]
    assert added_notification["related_booking_id"] == participant["booking_id"]
    assert added_notification["actor_user_id"] == admin["id"]
    assert "No payment was charged" in added_notification["body"]
    assert list_user_notifications(client, player["id"], "game_roster_update") == []
    assert list_user_notifications(client, player["id"], "booking_confirmed") == []

    authenticate_as(admin["id"])
    booking_response = client.get(f"/bookings/{participant['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "confirmed"
    assert booking["payment_status"] == "not_required"
    assert booking["subtotal_cents"] == game["price_per_player_cents"]
    assert booking["discount_cents"] == game["price_per_player_cents"]
    assert booking["total_cents"] == 0

    payments_response = get_money_as_admin(client, f"/payments?booking_id={participant['booking_id']}")
    assert payments_response.status_code == 200, payments_response.text
    assert payments_response.json() == []

    audit_response = client.get(
        f"/admin/actions?action_type=admin_add_player&target_game_id={game['id']}"
    )
    assert audit_response.status_code == 200, audit_response.text
    audit_rows = audit_response.json()
    assert len(audit_rows) == 1
    assert audit_rows[0]["target_user_id"] == player["id"]
    assert audit_rows[0]["metadata"]["payment_handling"] == "waived"
    assert audit_rows[0]["metadata"]["created_payment"] is False


def test_admin_official_game_add_player_rejects_duplicate_and_full_game(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(format_label="3v3", total_spots=6),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]

    add_response = client.post(
        f"/admin/official-games/{game['id']}/players",
        json={"user_id": player["id"]},
    )
    assert add_response.status_code == 201, add_response.text

    duplicate_response = client.post(
        f"/admin/official-games/{game['id']}/players",
        json={"user_id": player["id"]},
    )
    assert duplicate_response.status_code == 400, duplicate_response.text
    assert "already has an active roster row" in duplicate_response.text

    for index in range(5):
        extra_player = create_user(client)
        create_game_participant(
            client,
            extra_player["id"],
            game["id"],
            price_cents=1500,
            roster_order=index + 2,
        )

    full_response = client.post(
        f"/admin/official-games/{game['id']}/players",
        json={"user_id": create_user(client)["id"]},
    )
    assert full_response.status_code == 400, full_response.text
    assert "already full" in full_response.text


def test_admin_can_remove_admin_added_player(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    add_response = client.post(
        f"/admin/official-games/{game['id']}/players",
        json={"user_id": player["id"], "reason": "Waive payment."},
    )
    assert add_response.status_code == 201, add_response.text
    participant = add_response.json()
    added_notification = list_user_notifications(
        client,
        player["id"],
        "game_player_added_by_admin",
    )[0]
    added_event_at = added_notification["event_at"]

    authenticate_as(admin["id"])
    remove_response = client.request(
        "DELETE",
        f"/admin/official-games/{game['id']}/participants/{participant['id']}",
        json={"reason": "Player cannot make it."},
    )

    assert remove_response.status_code == 200, remove_response.text
    removed_participant = remove_response.json()
    assert removed_participant["participant_status"] == "removed"
    assert removed_participant["cancellation_type"] == "admin_cancelled"
    assert removed_participant["attendance_status"] == "not_applicable"

    booking_response = client.get(f"/bookings/{participant['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    booking = booking_response.json()
    assert booking["booking_status"] == "cancelled"
    assert booking["payment_status"] == "not_required"
    assert booking["cancelled_by_user_id"] == admin["id"]

    resolved_added_notification = list_user_notifications(
        client,
        player["id"],
        "game_player_added_by_admin",
    )[0]
    assert resolved_added_notification["is_read"] is True
    assert resolved_added_notification["read_at"] is not None
    assert resolved_added_notification["event_at"] == added_event_at
    removed_notifications = list_user_notifications(
        client,
        player["id"],
        "game_player_removed_by_admin",
    )
    assert len(removed_notifications) == 1
    removed_notification = removed_notifications[0]
    assert removed_notification["is_read"] is False
    assert removed_notification["source_type"] == "official_game"
    assert removed_notification["action_key"] == "view_game"
    assert removed_notification["action"] is not None
    assert removed_notification["related_game_id"] == game["id"]
    assert removed_notification["related_participant_id"] == participant["id"]
    assert removed_notification["related_booking_id"] == participant["booking_id"]
    assert removed_notification["actor_user_id"] == admin["id"]
    assert "Any payment or credit updates" in removed_notification["body"]
    assert list_user_notifications(client, player["id"], "game_roster_update") == []

    authenticate_as(admin["id"])
    audit_response = client.get(
        f"/admin/actions?action_type=admin_remove_player&target_game_id={game['id']}"
    )
    assert audit_response.status_code == 200, audit_response.text
    audit_rows = audit_response.json()
    assert len(audit_rows) == 1
    assert audit_rows[0]["target_participant_id"] == participant["id"]
    assert audit_rows[0]["metadata"]["payment_refund_created"] is False


def test_admin_remove_paid_player_requires_preview_without_mutation(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(client, player["id"], game["id"])
    participant = create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        price_cents=1500,
    )
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=1300,
        payment_status="succeeded",
    )

    remove_response = client.request(
        "DELETE",
        f"/admin/official-games/{game['id']}/participants/{participant['id']}",
        json={"reason": "Admin support removal."},
    )

    assert remove_response.status_code == 409, remove_response.text
    assert "Removal impact preview is required" in remove_response.text
    payment_response = get_money_as_admin(client, f"/payments/{payment['id']}")
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["payment_status"] == "succeeded"

    booking_response = client.get(f"/bookings/{booking['id']}")
    assert booking_response.status_code == 200, booking_response.text
    updated_booking = booking_response.json()
    assert updated_booking["booking_status"] == "confirmed"
    assert updated_booking["payment_status"] == "paid"
    participant_response = get_roster_as_admin(
        client,
        f"/game-participants/{participant['id']}",
    )
    assert participant_response.status_code == 200, participant_response.text
    assert participant_response.json()["participant_status"] == "confirmed"
    assert list_user_notifications(
        client,
        player["id"],
        "game_player_removed_by_admin",
    ) == []

    authenticate_as(admin["id"])
    audit_response = client.get(
        f"/admin/actions?action_type=admin_remove_player&target_game_id={game['id']}"
    )
    assert audit_response.status_code == 200, audit_response.text
    assert audit_response.json() == []


def test_admin_paid_player_removal_preview_reports_impact_without_mutation(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    waitlisted_player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(client, player["id"], game["id"])
    participant = create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        price_cents=1500,
    )
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=1300,
        payment_status="succeeded",
    )
    create_waitlist_entry(
        client,
        waitlisted_player["id"],
        game["id"],
        party_size=1,
    )

    authenticate_as(admin["id"])
    preview_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove-preview"
        )
    )

    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()
    assert preview["selected_participant_id"] == participant["id"]
    assert preview["booking_id"] == booking["id"]
    assert preview["removal_scope"] == "booking_party"
    assert preview["classification"] == "refund_cash"
    assert preview["automatic_outcome_available"] is True
    assert len(preview["preview_token"]) == 64
    assert preview["blocking_reasons"] == []
    assert preview["allowed_outcomes"] == ["refund_cash_and_remove_party"]
    assert preview["required_permissions"] == ["admin.money.refund"]
    assert preview["payment_statuses"] == ["succeeded"]
    assert preview["cash_collected_cents"] == 1300
    assert preview["cash_refundable_cents"] == 1300
    assert preview["cash_refunded_cents"] == 0
    assert preview["affected_participants"] == [
        {
            "id": participant["id"],
            "display_name": participant["display_name_snapshot"],
            "participant_type": "registered_user",
            "participant_status": "confirmed",
            "price_cents": 1500,
            "is_selected": True,
        }
    ]
    assert preview["spots_opened"] == 1
    assert preview["available_spots_after_removal"] == 10
    assert preview["active_waitlist_entry_count"] == 1
    assert preview["active_waitlist_player_count"] == 1
    assert preview["next_waitlist_party_size"] == 1
    assert preview["waitlist_promotion_possible"] is True

    participant_response = get_roster_as_admin(
        client,
        f"/game-participants/{participant['id']}",
    )
    assert participant_response.status_code == 200, participant_response.text
    assert participant_response.json()["participant_status"] == "confirmed"
    booking_response = client.get(f"/bookings/{booking['id']}")
    assert booking_response.status_code == 200, booking_response.text
    assert booking_response.json()["booking_status"] == "confirmed"
    payment_response = get_money_as_admin(client, f"/payments/{payment['id']}")
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["payment_status"] == "succeeded"
    assert list_user_notifications(
        client,
        player["id"],
        "game_player_removed_by_admin",
    ) == []

    authenticate_as(admin["id"])
    audit_response = client.get(
        f"/admin/actions?action_type=admin_remove_player&target_game_id={game['id']}"
    )
    assert audit_response.status_code == 200, audit_response.text
    assert audit_response.json() == []


def test_admin_player_removal_preview_reports_combined_cash_and_credit(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(client, player["id"], game["id"])
    participant = create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        price_cents=1500,
    )
    create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=800,
        payment_status="succeeded",
    )
    credit = issue_game_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        amount_cents=500,
    )

    now = datetime.now(UTC)
    with SessionLocal() as db:
        usages = reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=500,
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            now=now,
            idempotency_scope=f"preview-test:{booking['id']}",
        )
        assert len(usages) == 1
        assert str(usages[0].game_credit_id) == credit["id"]
        redeem_reserved_game_credits(
            db,
            UUID(booking["id"]),
            user_id=UUID(player["id"]),
            now=now,
        )
        db.commit()

    authenticate_as(admin["id"])
    preview_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove-preview"
        )
    )

    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()
    assert preview["classification"] == "refund_cash_and_restore_credit"
    assert preview["allowed_outcomes"] == [
        "refund_cash_restore_credit_and_remove_party"
    ]
    assert set(preview["required_permissions"]) == {
        "admin.money.credit_manage",
        "admin.money.refund",
    }
    assert preview["cash_collected_cents"] == 800
    assert preview["cash_refundable_cents"] == 800
    assert preview["credit_redeemed_cents"] == 500
    assert preview["credit_restorable_cents"] == 500


def test_admin_paid_guest_removal_preview_requires_manual_allocation(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(
        client,
        player["id"],
        game["id"],
        participant_count=2,
        subtotal_cents=3000,
        platform_fee_cents=0,
        total_cents=3000,
        price_per_player_snapshot_cents=1500,
    )
    create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        price_cents=1500,
        roster_order=1,
    )
    guest = create_game_participant(
        client,
        None,
        game["id"],
        booking_id=booking["id"],
        participant_type="guest",
        guest_of_user_id=player["id"],
        guest_name="Paid Guest",
        display_name_snapshot="Paid Guest",
        price_cents=1500,
        roster_order=2,
    )
    create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=3000,
        payment_status="succeeded",
    )

    authenticate_as(admin["id"])
    preview_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{guest['id']}/remove-preview"
        )
    )

    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()
    assert preview["removal_scope"] == "single_participant"
    assert preview["classification"] == "manual_review_required"
    assert preview["automatic_outcome_available"] is False
    assert preview["allowed_outcomes"] == []
    assert "whole booking" in preview["blocking_reasons"][0]
    assert len(preview["affected_participants"]) == 1
    assert preview["affected_participants"][0]["id"] == guest["id"]


def test_admin_player_removal_preview_reports_active_refund(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(client, player["id"], game["id"])
    participant = create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        price_cents=1500,
    )
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=1300,
        payment_status="succeeded",
    )
    create_refund(
        client,
        payment["id"],
        booking_id=booking["id"],
        amount_cents=500,
        refund_status="pending",
    )

    authenticate_as(admin["id"])
    preview_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove-preview"
        )
    )

    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()
    assert preview["classification"] == "refund_in_progress"
    assert preview["automatic_outcome_available"] is False
    assert preview["refund_statuses"] == ["pending"]
    assert preview["cash_refund_pending_cents"] == 500
    assert preview["cash_refundable_cents"] == 800


def test_admin_executes_paid_player_removal_with_successful_refund(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    refund_calls: list[dict] = []
    waitlist_promotion_calls: list[str] = []

    def fake_create_stripe_refund(**kwargs):
        refund_calls.append(kwargs)
        return StripeRefundResult(
            id="re_admin_player_remove",
            status="succeeded",
            amount_cents=kwargs["amount_cents"],
            currency=kwargs["currency"],
            charge_id=kwargs["charge_id"],
            payment_intent_id="pi_admin_player_remove",
        )

    def fake_promote_waitlist_entries(db, game, now):
        del db, now
        waitlist_promotion_calls.append(str(game.id))

    monkeypatch.setattr(
        (
            "backend.services.official_game_player_removal_service"
            ".create_stripe_refund"
        ),
        fake_create_stripe_refund,
    )
    monkeypatch.setattr(
        (
            "backend.services.official_game_player_removal_service"
            ".promote_waitlist_entries"
        ),
        fake_promote_waitlist_entries,
    )

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(client, player["id"], game["id"])
    participant = create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        price_cents=1500,
    )
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=1300,
        payment_status="succeeded",
        provider_charge_id="ch_admin_player_remove",
    )

    preview_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove-preview"
        )
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()

    execute_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove"
        ),
        json={
            "preview_token": preview["preview_token"],
            "outcome": preview["allowed_outcomes"][0],
            "reason": "Player requested a support removal.",
        },
    )

    assert execute_response.status_code == 200, execute_response.text
    result = execute_response.json()
    assert result["outcome"] == "refund_cash_and_remove_party"
    assert result["removed_participant_ids"] == [participant["id"]]
    assert result["booking_status"] == "cancelled"
    assert result["booking_payment_status"] == "refunded"
    assert result["refund_follow_up_required"] is False
    assert result["support_flag_ids"] == []
    assert result["waitlist_advanced_entry_ids"] == []
    assert len(result["refunds"]) == 1
    assert result["refunds"][0]["payment_id"] == payment["id"]
    assert result["refunds"][0]["amount_cents"] == 1300
    assert result["refunds"][0]["refund_status"] == "succeeded"
    assert len(refund_calls) == 1
    assert refund_calls[0]["charge_id"] == "ch_admin_player_remove"
    assert refund_calls[0]["amount_cents"] == 1300
    assert waitlist_promotion_calls == [game["id"]]

    participant_response = get_roster_as_admin(
        client,
        f"/game-participants/{participant['id']}",
    )
    assert participant_response.status_code == 200, participant_response.text
    assert participant_response.json()["participant_status"] == "removed"
    booking_response = client.get(f"/bookings/{booking['id']}")
    assert booking_response.status_code == 200, booking_response.text
    assert booking_response.json()["booking_status"] == "cancelled"
    assert booking_response.json()["payment_status"] == "refunded"
    payment_response = get_money_as_admin(client, f"/payments/{payment['id']}")
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["payment_status"] == "refunded"

    removed_notifications = list_user_notifications(
        client,
        player["id"],
        "game_player_removed_by_admin",
    )
    refunded_notifications = list_user_notifications(
        client,
        player["id"],
        "booking_refunded",
    )
    assert len(removed_notifications) == 1
    assert len(refunded_notifications) == 1
    assert refunded_notifications[0]["title"] == "Refund processed"

    authenticate_as(admin["id"])
    audit_response = client.get(
        f"/admin/actions?action_type=admin_remove_player&target_game_id={game['id']}"
    )
    assert audit_response.status_code == 200, audit_response.text
    audit_rows = audit_response.json()
    assert len(audit_rows) == 1
    assert audit_rows[0]["reason"] == "Player requested a support removal."
    assert audit_rows[0]["metadata"]["removal_outcome"] == (
        "refund_cash_and_remove_party"
    )
    assert audit_rows[0]["metadata"]["refund_created_count"] == 1
    assert audit_rows[0]["metadata"]["refund_follow_up_required"] is False


def test_admin_executes_pending_hold_removal_and_releases_reserved_credit(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(
        client,
        player["id"],
        game["id"],
        booking_status="pending_payment",
        payment_status="requires_action",
        booked_at=None,
    )
    participant = create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        participant_status="pending_payment",
        confirmed_at=None,
        price_cents=1500,
    )
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=800,
        payment_status="requires_action",
    )
    credit = issue_game_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        amount_cents=500,
    )
    with SessionLocal() as db:
        usages = reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=500,
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            payment_id=UUID(payment["id"]),
            now=datetime.now(UTC),
            idempotency_scope=f"pending-removal:{booking['id']}",
        )
        assert len(usages) == 1
        db.commit()

    authenticate_as(admin["id"])
    preview_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove-preview"
        )
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()
    assert preview["classification"] == "release_pending_hold"
    assert preview["allowed_outcomes"] == [
        "release_pending_hold_and_remove_party"
    ]
    assert preview["required_permissions"] == []

    execute_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove"
        ),
        json={
            "preview_token": preview["preview_token"],
            "outcome": preview["allowed_outcomes"][0],
            "reason": "Release the unfinished checkout hold.",
        },
    )

    assert execute_response.status_code == 200, execute_response.text
    result = execute_response.json()
    assert result["outcome"] == "release_pending_hold_and_remove_party"
    assert result["removed_participant_ids"] == [participant["id"]]
    assert result["booking_status"] == "cancelled"
    assert result["booking_payment_status"] == "failed"
    assert result["refunds"] == []
    assert result["credit_restored_cents"] == 0

    booking_response = client.get(f"/bookings/{booking['id']}")
    assert booking_response.status_code == 200, booking_response.text
    assert booking_response.json()["booking_status"] == "cancelled"
    assert booking_response.json()["payment_status"] == "failed"
    payment_response = get_money_as_admin(client, f"/payments/{payment['id']}")
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["payment_status"] == "canceled"
    assert payment_response.json()["failure_code"] == "admin_player_removed"

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
    assert usage.release_reason == "admin_player_removed"


def test_admin_paid_player_removal_rejects_stale_preview_before_stripe(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    refund_calls: list[dict] = []

    def fail_create_stripe_refund(**kwargs):
        refund_calls.append(kwargs)
        raise AssertionError("Stripe must not be called for a stale preview.")

    monkeypatch.setattr(
        (
            "backend.services.official_game_player_removal_service"
            ".create_stripe_refund"
        ),
        fail_create_stripe_refund,
    )

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(client, player["id"], game["id"])
    participant = create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        price_cents=1500,
    )
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=1300,
        payment_status="succeeded",
        provider_charge_id="ch_stale_preview",
    )
    preview_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove-preview"
        )
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()

    with SessionLocal() as db:
        db_payment = db.get(Payment, UUID(payment["id"]))
        assert db_payment is not None
        db_payment.payment_status = "processing"
        db_payment.updated_at = datetime.now(UTC)
        db.commit()

    execute_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove"
        ),
        json={
            "preview_token": preview["preview_token"],
            "outcome": preview["allowed_outcomes"][0],
            "reason": "This preview is stale.",
        },
    )

    assert execute_response.status_code == 409, execute_response.text
    assert "Removal impact changed" in execute_response.text
    assert refund_calls == []
    participant_response = get_roster_as_admin(
        client,
        f"/game-participants/{participant['id']}",
    )
    assert participant_response.status_code == 200, participant_response.text
    assert participant_response.json()["participant_status"] == "confirmed"


def test_admin_executes_combined_refund_and_credit_restore(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    def fake_create_stripe_refund(**kwargs):
        return StripeRefundResult(
            id="re_admin_combined_remove",
            status="succeeded",
            amount_cents=kwargs["amount_cents"],
            currency=kwargs["currency"],
            charge_id=kwargs["charge_id"],
            payment_intent_id="pi_admin_combined_remove",
        )

    monkeypatch.setattr(
        (
            "backend.services.official_game_player_removal_service"
            ".create_stripe_refund"
        ),
        fake_create_stripe_refund,
    )

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(client, player["id"], game["id"])
    participant = create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        price_cents=1500,
    )
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=800,
        payment_status="succeeded",
        provider_charge_id="ch_admin_combined_remove",
    )
    credit = issue_game_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        amount_cents=500,
    )
    now = datetime.now(UTC)
    with SessionLocal() as db:
        reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=500,
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            payment_id=UUID(payment["id"]),
            now=now,
            idempotency_scope=f"execute-preview-test:{booking['id']}",
        )
        redeem_reserved_game_credits(
            db,
            UUID(booking["id"]),
            user_id=UUID(player["id"]),
            now=now,
        )
        db.commit()

    authenticate_as(admin["id"])
    preview_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove-preview"
        )
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()
    assert preview["classification"] == "refund_cash_and_restore_credit"

    execute_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove"
        ),
        json={
            "preview_token": preview["preview_token"],
            "outcome": preview["allowed_outcomes"][0],
            "reason": "Return both payment sources.",
        },
    )

    assert execute_response.status_code == 200, execute_response.text
    result = execute_response.json()
    assert result["booking_payment_status"] == "refunded"
    assert result["credit_restored_count"] == 1
    assert result["credit_restored_cents"] == 500
    assert result["refunds"][0]["refund_status"] == "succeeded"

    with SessionLocal() as db:
        refreshed_credit = db.get(GameCredit, UUID(credit["id"]))
        usages = list(
            db.scalars(
                select(GameCreditUsage).where(
                    GameCreditUsage.booking_id == UUID(booking["id"])
                )
            ).all()
        )

    assert refreshed_credit is not None
    assert refreshed_credit.remaining_cents == 500
    assert {usage.usage_status for usage in usages} == {"redeemed", "restored"}
    refunded_notifications = list_user_notifications(
        client,
        player["id"],
        "booking_refunded",
    )
    assert len(refunded_notifications) == 1
    assert refunded_notifications[0]["title"] == "Refund and credit processed"


def test_admin_executes_credit_only_player_removal(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(client, player["id"], game["id"])
    participant = create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        price_cents=1500,
    )
    credit = issue_game_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        amount_cents=1300,
    )
    now = datetime.now(UTC)
    with SessionLocal() as db:
        reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=1300,
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            now=now,
            idempotency_scope=f"credit-only-remove:{booking['id']}",
        )
        redeem_reserved_game_credits(
            db,
            UUID(booking["id"]),
            user_id=UUID(player["id"]),
            now=now,
        )
        db.commit()

    authenticate_as(admin["id"])
    preview_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove-preview"
        )
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()
    assert preview["classification"] == "restore_credit"
    assert preview["required_permissions"] == ["admin.money.credit_manage"]

    execute_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove"
        ),
        json={
            "preview_token": preview["preview_token"],
            "outcome": preview["allowed_outcomes"][0],
            "reason": "Restore the full-credit booking.",
        },
    )

    assert execute_response.status_code == 200, execute_response.text
    result = execute_response.json()
    assert result["booking_payment_status"] == "credit_restored"
    assert result["refunds"] == []
    assert result["credit_restored_count"] == 1
    assert result["credit_restored_cents"] == 1300

    with SessionLocal() as db:
        refreshed_credit = db.get(GameCredit, UUID(credit["id"]))

    assert refreshed_credit is not None
    assert refreshed_credit.remaining_cents == 1300
    restored_notifications = list_user_notifications(
        client,
        player["id"],
        "booking_refunded",
    )
    assert len(restored_notifications) == 1
    assert restored_notifications[0]["title"] == "Credit restored"
    assert "booking was removed" in restored_notifications[0]["body"]


def test_admin_paid_player_removal_refund_failure_creates_follow_up(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    def fail_create_stripe_refund(**kwargs):
        del kwargs
        raise RuntimeError("Stripe refund unavailable.")

    monkeypatch.setattr(
        (
            "backend.services.official_game_player_removal_service"
            ".create_stripe_refund"
        ),
        fail_create_stripe_refund,
    )

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(client, player["id"], game["id"])
    participant = create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        price_cents=1500,
    )
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=1300,
        payment_status="succeeded",
        provider_charge_id="ch_failed_admin_remove",
    )
    preview_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove-preview"
        )
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()

    execute_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove"
        ),
        json={
            "preview_token": preview["preview_token"],
            "outcome": preview["allowed_outcomes"][0],
            "reason": "Remove with refund follow-up.",
        },
    )

    assert execute_response.status_code == 200, execute_response.text
    result = execute_response.json()
    assert result["booking_status"] == "cancelled"
    assert result["booking_payment_status"] == "paid"
    assert result["refund_follow_up_required"] is True
    assert result["refunds"][0]["refund_status"] == "failed"
    assert len(result["support_flag_ids"]) == 1

    with SessionLocal() as db:
        db_payment = db.get(Payment, UUID(payment["id"]))
        db_refund = db.get(Refund, UUID(result["refunds"][0]["id"]))
        support_flag = db.get(SupportFlag, UUID(result["support_flag_ids"][0]))

    assert db_payment is not None
    assert db_payment.payment_status == "succeeded"
    assert db_refund is not None
    assert db_refund.refund_status == "failed"
    assert support_flag is not None
    assert support_flag.flag_type == "stripe_refund_failed"
    assert support_flag.target_refund_id == db_refund.id
    assert (
        list_user_notifications(client, player["id"], "booking_refunded")
        == []
    )


def test_admin_paid_player_removal_execution_requires_refund_permission(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(client, player["id"], game["id"])
    participant = create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        price_cents=1500,
    )
    create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=1300,
        payment_status="succeeded",
        provider_charge_id="ch_missing_refund_permission",
    )
    monkeypatch.setitem(
        ROLE_PERMISSIONS,
        "admin",
        frozenset(
            {
                PERMISSION_OFFICIAL_GAMES_READ,
                PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
                PERMISSION_MONEY_READ,
            }
        ),
    )
    authenticate_as(admin["id"])
    preview_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove-preview"
        )
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()

    execute_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove"
        ),
        json={
            "preview_token": preview["preview_token"],
            "outcome": preview["allowed_outcomes"][0],
            "reason": "Permission boundary test.",
        },
    )

    assert execute_response.status_code == 403, execute_response.text


def test_admin_paid_player_removal_execution_requires_money_read(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(
        client,
        player["id"],
        game["id"],
        booking_status="pending_payment",
        payment_status="requires_action",
        booked_at=None,
    )
    participant = create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        participant_status="pending_payment",
        confirmed_at=None,
        price_cents=1500,
    )
    create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=1300,
        payment_status="requires_action",
    )

    preview_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove-preview"
        )
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()
    assert preview["allowed_outcomes"] == [
        "release_pending_hold_and_remove_party"
    ]

    monkeypatch.setitem(
        ROLE_PERMISSIONS,
        "admin",
        frozenset(
            {
                PERMISSION_OFFICIAL_GAMES_READ,
                PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
            }
        ),
    )
    authenticate_as(admin["id"])
    execute_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove"
        ),
        json={
            "preview_token": preview["preview_token"],
            "outcome": preview["allowed_outcomes"][0],
            "reason": "Permission boundary test.",
        },
    )

    assert execute_response.status_code == 403, execute_response.text


def test_admin_remove_guest_notifies_booking_owner_with_guest_copy(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(
        client,
        player["id"],
        game["id"],
        participant_count=2,
        payment_status="not_required",
        discount_cents=1300,
        total_cents=0,
    )
    create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        price_cents=1500,
        roster_order=1,
    )
    guest = create_game_participant(
        client,
        None,
        game["id"],
        booking_id=booking["id"],
        participant_type="guest",
        guest_of_user_id=player["id"],
        guest_name="Guest Player",
        display_name_snapshot="Guest Player",
        price_cents=1500,
        roster_order=2,
    )

    authenticate_as(admin["id"])
    remove_response = client.request(
        "DELETE",
        f"/admin/official-games/{game['id']}/participants/{guest['id']}",
        json={"reason": "Guest removed by support."},
    )

    assert remove_response.status_code == 200, remove_response.text
    removed_guest = remove_response.json()
    assert removed_guest["participant_status"] == "removed"
    booking_response = client.get(f"/bookings/{booking['id']}")
    assert booking_response.status_code == 200, booking_response.text
    updated_booking = booking_response.json()
    assert updated_booking["booking_status"] == "partially_cancelled"
    assert updated_booking["participant_count"] == 1
    removed_notifications = list_user_notifications(
        client,
        player["id"],
        "game_player_removed_by_admin",
    )
    assert len(removed_notifications) == 1
    removed_notification = removed_notifications[0]
    assert removed_notification["title"] == "Guest removed"
    assert "guest was removed" in removed_notification["body"]
    assert removed_notification["related_participant_id"] == guest["id"]
    assert removed_notification["related_booking_id"] == booking["id"]
    assert list_user_notifications(client, player["id"], "game_roster_update") == []


def test_admin_remove_requires_action_checkout_party_invalidates_payment(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    def fake_create_payment_intent(**kwargs):
        return StripePaymentIntentResult(
            id="pi_admin_remove_pending",
            client_secret="pi_admin_remove_pending_secret",
            status="requires_payment_method",
        )

    def fake_confirm_payment_intent(payment_intent_id, **kwargs):
        return StripePaymentIntentResult(
            id=payment_intent_id,
            client_secret="pi_admin_remove_pending_secret",
            status="requires_action",
        )

    monkeypatch.setattr(
        "backend.services.checkout_service.create_payment_intent",
        fake_create_payment_intent,
    )
    monkeypatch.setattr(
        "backend.services.checkout_service.confirm_payment_intent",
        fake_confirm_payment_intent,
    )

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    credit = issue_game_credit(
        client,
        admin_id=admin["id"],
        user_id=player["id"],
        game_id=game["id"],
        amount_cents=500,
    )

    authenticate_as(player["id"])
    payment_method = create_user_payment_method(
        client,
        player["id"],
        stripe_customer_id="cus_admin_remove_pending",
        stripe_payment_method_id="pm_admin_remove_pending",
    )
    mock_checkout_payment_method_verification(monkeypatch, payment_method)
    checkout_response = client.post(
        f"/checkout/games/{game['id']}/payment-intent",
        json={
            "guest_count": 1,
            "payment_method_id": payment_method["id"],
        },
    )
    assert checkout_response.status_code == 201, checkout_response.text
    checkout = checkout_response.json()
    assert checkout["credit_applied_cents"] == 500
    participants_response = get_roster_as_admin(
        client,
        f"/game-participants?booking_id={checkout['booking_id']}",
    )
    assert participants_response.status_code == 200, participants_response.text
    pending_participants = participants_response.json()
    guest = next(
        participant
        for participant in pending_participants
        if participant["participant_type"] == "guest"
    )

    authenticate_as(admin["id"])
    remove_response = client.request(
        "DELETE",
        f"/admin/official-games/{game['id']}/participants/{guest['id']}",
        json={"reason": "Clear pending hold."},
    )

    assert remove_response.status_code == 200, remove_response.text
    booking_response = client.get(f"/bookings/{checkout['booking_id']}")
    assert booking_response.status_code == 200, booking_response.text
    assert booking_response.json()["booking_status"] == "cancelled"
    assert booking_response.json()["payment_status"] == "failed"

    payment_response = get_money_as_admin(client, f"/payments/{checkout['payment_id']}")
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["payment_status"] == "canceled"
    assert payment_response.json()["failure_code"] == "admin_player_removed"

    removed_participants_response = get_roster_as_admin(
        client,
        f"/game-participants?booking_id={checkout['booking_id']}",
    )
    assert removed_participants_response.status_code == 200
    assert {
        participant["participant_status"]
        for participant in removed_participants_response.json()
    } == {"removed"}
    assert (
        list_user_notifications(
            client,
            player["id"],
            "game_player_removed_by_admin",
        )
        == []
    )

    with SessionLocal() as db:
        refreshed_credit = db.get(GameCredit, UUID(credit["id"]))
        usage = db.scalars(
            select(GameCreditUsage).where(
                GameCreditUsage.booking_id == UUID(checkout["booking_id"])
            )
        ).one()

    assert refreshed_credit is not None
    assert refreshed_credit.remaining_cents == 500
    assert refreshed_credit.credit_status == "active"
    assert usage.usage_status == RELEASED_USAGE_STATUS
    assert usage.release_reason == "admin_player_removed"


def test_admin_remove_processing_checkout_requires_preview_without_mutation(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(
        client,
        player["id"],
        game["id"],
        booking_status="pending_payment",
        payment_status="processing",
        booked_at=None,
    )
    participant = create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        participant_status="pending_payment",
        confirmed_at=None,
        price_cents=1500,
    )
    payment = create_payment(
        client,
        player["id"],
        booking_id=booking["id"],
        amount_cents=1300,
        payment_status="processing",
    )

    remove_response = client.request(
        "DELETE",
        f"/admin/official-games/{game['id']}/participants/{participant['id']}",
        json={"reason": "Do not race a processing payment."},
    )

    assert remove_response.status_code == 409, remove_response.text
    assert "Removal impact preview is required" in remove_response.text

    preview_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove-preview"
        )
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()
    assert preview["classification"] == "payment_processing"
    assert preview["automatic_outcome_available"] is False
    assert preview["payment_statuses"] == ["processing"]

    booking_response = client.get(f"/bookings/{booking['id']}")
    assert booking_response.status_code == 200, booking_response.text
    assert booking_response.json()["booking_status"] == "pending_payment"
    assert booking_response.json()["payment_status"] == "processing"

    payment_response = get_money_as_admin(client, f"/payments/{payment['id']}")
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["payment_status"] == "processing"

    participant_response = get_roster_as_admin(
        client,
        f"/game-participants/{participant['id']}",
    )
    assert participant_response.status_code == 200, participant_response.text
    assert participant_response.json()["participant_status"] == "pending_payment"


def test_admin_remove_player_without_booking_requires_preview(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    participant = create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=None,
        price_cents=1500,
    )

    remove_response = client.request(
        "DELETE",
        f"/admin/official-games/{game['id']}/participants/{participant['id']}",
        json={"reason": "Missing booking context."},
    )

    assert remove_response.status_code == 409, remove_response.text
    assert "Removal impact preview is required" in remove_response.text
    preview_response = client.post(
        (
            f"/admin/official-games/{game['id']}/participants/"
            f"{participant['id']}/remove-preview"
        )
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()
    assert preview["classification"] == "blocked_missing_booking"
    assert preview["automatic_outcome_available"] is False
    assert preview["booking_id"] is None
    participant_response = get_roster_as_admin(
        client,
        f"/game-participants/{participant['id']}",
    )
    assert participant_response.status_code == 200, participant_response.text
    assert participant_response.json()["participant_status"] == "confirmed"


def test_admin_can_assign_replace_and_remove_official_game_host_designation(
    client: TestClient,
):
    admin = create_user(client)
    first_host = create_user(client)
    second_host = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    assert game["host_user_id"] is None

    booking = create_booking(client, first_host["id"], game["id"])
    first_participant = create_game_participant(
        client,
        first_host["id"],
        game["id"],
        booking_id=booking["id"],
        price_cents=1500,
        roster_order=1,
    )
    guest = create_game_participant(
        client,
        None,
        game["id"],
        booking_id=booking["id"],
        participant_type="guest",
        guest_of_user_id=first_host["id"],
        guest_name="Host guest",
        display_name_snapshot="Host guest",
        price_cents=1500,
        roster_order=2,
    )
    payment = create_payment(
        client,
        first_host["id"],
        booking_id=booking["id"],
        amount_cents=1300,
        payment_status="succeeded",
    )
    add_response = client.post(
        f"/admin/official-games/{game['id']}/players",
        json={"user_id": second_host["id"], "reason": "Waive payment."},
    )
    assert add_response.status_code == 201, add_response.text
    second_participant = add_response.json()

    assign_response = client.post(
        f"/admin/official-games/{game['id']}/host",
        json={
            "host_user_id": first_host["id"],
            "reason": "Assign first host.",
        },
    )
    assert assign_response.status_code == 200, assign_response.text
    assert assign_response.json()["game"]["host_user_id"] == first_host["id"]

    first_host_assigned_notifications = list_user_notifications(
        client,
        first_host["id"],
        "game_host_assigned",
    )
    assert len(first_host_assigned_notifications) == 1
    first_host_assigned = first_host_assigned_notifications[0]
    first_host_assigned_event_at = first_host_assigned["event_at"]
    assert first_host_assigned["is_read"] is False
    assert first_host_assigned["read_at"] is None
    assert first_host_assigned["source_type"] == "official_game"
    assert first_host_assigned["source_label"] == "Official Game"
    assert first_host_assigned["action_key"] == "view_game"
    assert first_host_assigned["action"] is not None
    assert first_host_assigned["related_game_id"] == game["id"]
    assert first_host_assigned["related_participant_id"] == first_participant["id"]
    assert first_host_assigned["related_booking_id"] == booking["id"]
    assert first_host_assigned["actor_user_id"] == admin["id"]
    assert "assigned you as host" in first_host_assigned["body"]
    assert (
        list_user_notifications(client, first_host["id"], "game_host_removed")
        == []
    )

    authenticate_as(admin["id"])
    same_host_response = client.post(
        f"/admin/official-games/{game['id']}/host",
        json={"host_user_id": first_host["id"], "reason": "No-op reassignment."},
    )
    assert same_host_response.status_code == 200, same_host_response.text
    assert same_host_response.json()["game"]["host_user_id"] == first_host["id"]
    assert (
        len(
            list_user_notifications(
                client,
                first_host["id"],
                "game_host_assigned",
            )
        )
        == 1
    )
    assert (
        list_user_notifications(client, first_host["id"], "game_host_removed")
        == []
    )

    authenticate_as(admin["id"])
    change_response = client.post(
        f"/admin/official-games/{game['id']}/host",
        json={
            "host_user_id": second_host["id"],
            "reason": "Change host.",
        },
    )
    assert change_response.status_code == 200, change_response.text
    assert change_response.json()["game"]["host_user_id"] == second_host["id"]

    first_host_assigned_after_change = list_user_notifications(
        client,
        first_host["id"],
        "game_host_assigned",
    )[0]
    assert first_host_assigned_after_change["is_read"] is True
    assert first_host_assigned_after_change["read_at"] is not None
    assert first_host_assigned_after_change["event_at"] == first_host_assigned_event_at
    first_host_removed_notifications = list_user_notifications(
        client,
        first_host["id"],
        "game_host_removed",
    )
    assert len(first_host_removed_notifications) == 1
    first_host_removed = first_host_removed_notifications[0]
    assert first_host_removed["is_read"] is False
    assert first_host_removed["source_type"] == "official_game"
    assert first_host_removed["action_key"] == "view_game"
    assert first_host_removed["action"] is not None
    assert first_host_removed["related_game_id"] == game["id"]
    assert first_host_removed["related_participant_id"] == first_participant["id"]
    assert first_host_removed["related_booking_id"] == booking["id"]
    assert first_host_removed["actor_user_id"] == admin["id"]
    assert "removed you as host" in first_host_removed["body"]
    second_host_assigned_notifications = list_user_notifications(
        client,
        second_host["id"],
        "game_host_assigned",
    )
    assert len(second_host_assigned_notifications) == 1
    second_host_assigned = second_host_assigned_notifications[0]
    second_host_assigned_event_at = second_host_assigned["event_at"]
    assert second_host_assigned["is_read"] is False
    assert second_host_assigned["related_participant_id"] == second_participant["id"]
    assert second_host_assigned["related_booking_id"] == second_participant["booking_id"]
    assert (
        list_user_notifications(client, second_host["id"], "game_host_removed")
        == []
    )

    authenticate_as(admin["id"])
    first_participant_response = client.get(
        f"/game-participants/{first_participant['id']}"
    )
    assert first_participant_response.status_code == 200
    updated_first_participant = first_participant_response.json()
    assert updated_first_participant["participant_type"] == "registered_user"
    assert updated_first_participant["participant_status"] == "confirmed"
    assert updated_first_participant["booking_id"] == booking["id"]

    second_participant_response = client.get(
        f"/game-participants/{second_participant['id']}"
    )
    assert second_participant_response.status_code == 200
    updated_second_participant = second_participant_response.json()
    assert updated_second_participant["participant_type"] == "admin_added"
    assert updated_second_participant["participant_status"] == "confirmed"
    assert updated_second_participant["booking_id"] == second_participant["booking_id"]

    guest_response = client.get(f"/game-participants/{guest['id']}")
    assert guest_response.status_code == 200
    updated_guest = guest_response.json()
    assert updated_guest["participant_type"] == "guest"
    assert updated_guest["participant_status"] == "confirmed"
    assert updated_guest["guest_of_user_id"] == first_host["id"]

    payment_response = get_money_as_admin(client, f"/payments/{payment['id']}")
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["payment_status"] == "succeeded"

    authenticate_as(admin["id"])
    remove_response = client.request(
        "DELETE",
        f"/admin/official-games/{game['id']}/host",
        json={"reason": "No host needed."},
    )
    assert remove_response.status_code == 200, remove_response.text
    assert remove_response.json()["game"]["host_user_id"] is None

    second_after_remove_response = client.get(
        f"/game-participants/{second_participant['id']}"
    )
    assert second_after_remove_response.status_code == 200
    assert second_after_remove_response.json()["participant_type"] == "admin_added"
    assert second_after_remove_response.json()["participant_status"] == "confirmed"

    second_host_assigned_after_remove = list_user_notifications(
        client,
        second_host["id"],
        "game_host_assigned",
    )[0]
    assert second_host_assigned_after_remove["is_read"] is True
    assert second_host_assigned_after_remove["read_at"] is not None
    assert second_host_assigned_after_remove["event_at"] == second_host_assigned_event_at
    second_host_removed_notifications = list_user_notifications(
        client,
        second_host["id"],
        "game_host_removed",
    )
    assert len(second_host_removed_notifications) == 1
    assert second_host_removed_notifications[0]["is_read"] is False
    assert second_host_removed_notifications[0]["related_game_id"] == game["id"]
    assert (
        second_host_removed_notifications[0]["related_participant_id"]
        == second_participant["id"]
    )
    assert (
        second_host_removed_notifications[0]["related_booking_id"]
        == second_participant["booking_id"]
    )

    authenticate_as(admin["id"])
    assign_audit_response = client.get(
        f"/admin/actions?action_type=assign_official_host&target_game_id={game['id']}"
    )
    assert assign_audit_response.status_code == 200, assign_audit_response.text
    assign_audit_rows = assign_audit_response.json()
    assert len(assign_audit_rows) == 2
    assert {row["target_user_id"] for row in assign_audit_rows} == {
        first_host["id"],
        second_host["id"],
    }

    remove_audit_response = client.get(
        f"/admin/actions?action_type=remove_official_host&target_game_id={game['id']}"
    )
    assert remove_audit_response.status_code == 200, remove_audit_response.text
    assert len(remove_audit_response.json()) == 1


def test_admin_official_game_host_self_actions_emit_no_notifications(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    create_game_participant(
        client,
        admin["id"],
        game["id"],
        price_cents=1500,
    )

    assign_response = client.post(
        f"/admin/official-games/{game['id']}/host",
        json={"host_user_id": admin["id"], "reason": "Self host assignment."},
    )
    assert assign_response.status_code == 200, assign_response.text
    assert assign_response.json()["game"]["host_user_id"] == admin["id"]
    assert list_user_notifications(client, admin["id"], "game_host_assigned") == []

    authenticate_as(admin["id"])
    remove_response = client.request(
        "DELETE",
        f"/admin/official-games/{game['id']}/host",
        json={"reason": "Self host removal."},
    )
    assert remove_response.status_code == 200, remove_response.text
    assert remove_response.json()["game"]["host_user_id"] is None
    assert list_user_notifications(client, admin["id"], "game_host_removed") == []


def test_admin_official_game_host_rejects_off_roster_user(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]

    response = client.post(
        f"/admin/official-games/{game['id']}/host",
        json={"host_user_id": player["id"]},
    )

    assert response.status_code == 400, response.text
    assert "confirmed roster player" in response.text


def test_admin_official_game_host_rejects_ineligible_roster_statuses(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]

    for index, participant_status in enumerate(
        ["pending_payment", "waitlisted", "cancelled", "removed", "refunded"]
    ):
        player = create_user(client)
        overrides = {
            "participant_status": participant_status,
            "price_cents": 1500,
            "roster_order": index + 1,
        }
        if participant_status in {"cancelled", "removed", "refunded"}:
            overrides["cancellation_type"] = "admin_cancelled"
        create_game_participant(
            client,
            player["id"],
            game["id"],
            **overrides,
        )

        response = client.post(
            f"/admin/official-games/{game['id']}/host",
            json={"host_user_id": player["id"]},
        )

        assert response.status_code == 400, response.text
        assert "confirmed roster player" in response.text


def test_admin_official_game_host_rejects_inactive_user(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    create_game_participant(client, player["id"], game["id"], price_cents=1500)
    set_user_account_status(player["id"], "suspended")

    response = client.post(
        f"/admin/official-games/{game['id']}/host",
        json={"host_user_id": player["id"]},
    )

    assert response.status_code == 400, response.text
    assert "not active" in response.text


def test_admin_official_game_host_rejects_invalid_game_state_and_started_game(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    create_game_participant(client, player["id"], game["id"], price_cents=1500)

    set_game_status(game["id"], "cancelled")
    cancelled_response = client.post(
        f"/admin/official-games/{game['id']}/host",
        json={"host_user_id": player["id"]},
    )
    assert cancelled_response.status_code == 400, cancelled_response.text
    assert "published scheduled or full" in cancelled_response.text

    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(title="Started Official Match"),
    )
    assert create_response.status_code == 201, create_response.text
    started_game = create_response.json()["game"]
    create_game_participant(client, player["id"], started_game["id"], price_cents=1500)
    set_game_starts_at(started_game["id"], datetime.now(UTC) - timedelta(minutes=1))

    started_response = client.post(
        f"/admin/official-games/{started_game['id']}/host",
        json={"host_user_id": player["id"]},
    )
    assert started_response.status_code == 400, started_response.text
    assert "before the game starts" in started_response.text


def test_admin_remove_player_rejects_current_official_host(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    booking = create_booking(client, player["id"], game["id"])
    participant = create_game_participant(
        client,
        player["id"],
        game["id"],
        booking_id=booking["id"],
        price_cents=1500,
    )
    assign_response = client.post(
        f"/admin/official-games/{game['id']}/host",
        json={"host_user_id": player["id"]},
    )
    assert assign_response.status_code == 200, assign_response.text

    response = client.request(
        "DELETE",
        f"/admin/official-games/{game['id']}/participants/{participant['id']}",
        json={"reason": "Remove host directly."},
    )

    assert response.status_code == 400, response.text
    assert "Remove host designation" in response.text
    participant_response = client.get(f"/game-participants/{participant['id']}")
    assert participant_response.status_code == 200
    assert participant_response.json()["participant_status"] == "confirmed"


def test_generic_user_delete_disabled_for_current_future_official_host(
    client: TestClient,
):
    admin = create_user(client)
    host = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    create_game_participant(client, host["id"], game["id"], price_cents=1500)
    assign_response = client.post(
        f"/admin/official-games/{game['id']}/host",
        json={"host_user_id": host["id"]},
    )
    assert assign_response.status_code == 200, assign_response.text

    delete_response = client.delete(f"/users/{host['id']}")

    assert delete_response.status_code == 403, delete_response.text
    assert "Generic user mutations are disabled" in delete_response.text
    user_response = client.get(f"/users/{host['id']}")
    assert user_response.status_code == 200
    assert user_response.json()["deleted_at"] is None
    game_response = client.get(f"/admin/official-games/{game['id']}")
    assert game_response.status_code == 200
    assert game_response.json()["game"]["host_user_id"] == host["id"]


def test_generic_game_delete_rejects_official_game(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]

    delete_response = client.delete(f"/games/{game['id']}")

    assert delete_response.status_code == 400, delete_response.text
    assert "cancelled instead of deleted" in delete_response.text
    game_response = client.get(f"/admin/official-games/{game['id']}")
    assert game_response.status_code == 200
    assert game_response.json()["game"]["deleted_at"] is None


def test_account_delete_clears_future_official_host_without_cancelling_game(
    client: TestClient,
    monkeypatch,
):
    admin = create_user(client)
    host = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    participant = create_game_participant(
        client,
        host["id"],
        game["id"],
        price_cents=1500,
    )
    assign_response = client.post(
        f"/admin/official-games/{game['id']}/host",
        json={"host_user_id": host["id"]},
    )
    assert assign_response.status_code == 200, assign_response.text
    assigned_host_notifications = list_user_notifications(
        client,
        host["id"],
        "game_host_assigned",
    )
    assert len(assigned_host_notifications) == 1
    assigned_host_event_at = assigned_host_notifications[0]["event_at"]
    assert assigned_host_notifications[0]["is_read"] is False

    monkeypatch.setattr(
        "backend.services.auth_service.verify_firebase_token",
        lambda token: {"uid": host["auth_user_id"], "email_verified": True},
    )
    monkeypatch.setattr(
        "backend.services.account_deletion_service.delete_firebase_user",
        lambda auth_user_id: None,
    )

    delete_response = client.request(
        "DELETE",
        "/auth/account",
        headers={"Authorization": "Bearer test-token"},
        json={"confirmation": "DELETE"},
    )

    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["deleted_at"] is not None
    authenticate_as(admin["id"])
    game_response = client.get(f"/admin/official-games/{game['id']}")
    assert game_response.status_code == 200
    updated_game = game_response.json()["game"]
    assert updated_game["host_user_id"] is None
    assert updated_game["game_status"] == "scheduled"
    participant_response = client.get(f"/game-participants/{participant['id']}")
    assert participant_response.status_code == 200
    updated_participant = participant_response.json()
    assert updated_participant["participant_status"] == "cancelled"
    assert updated_participant["display_name_snapshot"] == "Deleted User"
    with SessionLocal() as db:
        assigned_notification = db.scalars(
            select(Notification).where(
                Notification.user_id == UUID(host["id"]),
                Notification.related_game_id == UUID(game["id"]),
                Notification.notification_type == "game_host_assigned",
            )
        ).one()
        removed_notifications = db.scalars(
            select(Notification).where(
                Notification.user_id == UUID(host["id"]),
                Notification.related_game_id == UUID(game["id"]),
                Notification.notification_type == "game_host_removed",
            )
        ).all()

    assert assigned_notification.is_read is True
    assert assigned_notification.read_at is not None
    assert assigned_notification.event_at == parse_response_datetime(
        assigned_host_event_at
    )
    assert removed_notifications == []


def test_admin_can_remove_official_game_host_without_body(client: TestClient):
    admin = create_user(client)
    host = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]
    participant = create_game_participant(
        client,
        host["id"],
        game["id"],
        price_cents=1500,
    )
    assign_response = client.post(
        f"/admin/official-games/{game['id']}/host",
        json={"host_user_id": host["id"]},
    )
    assert assign_response.status_code == 200, assign_response.text

    response = client.delete(f"/admin/official-games/{game['id']}/host")

    assert response.status_code == 200, response.text
    assert response.json()["game"]["host_user_id"] is None
    participant_response = client.get(f"/game-participants/{participant['id']}")
    assert participant_response.status_code == 200
    assert participant_response.json()["participant_status"] == "confirmed"


def test_admin_official_game_list_rejects_invalid_view_filter(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    response = client.get("/admin/official-games?view=weird")

    assert response.status_code == 400, response.text
    assert "view must be" in response.text


def test_admin_official_game_routes_reject_non_admin(client: TestClient):
    user = create_user(client)

    authenticate_as(user["id"])
    response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )

    assert response.status_code == 403, response.text

    patch_response = client.patch(
        "/admin/official-games/00000000-0000-0000-0000-000000000000",
        json={"title": "Nope"},
    )
    assert patch_response.status_code == 403, patch_response.text

    add_player_response = client.post(
        "/admin/official-games/00000000-0000-0000-0000-000000000000/players",
        json={"user_id": user["id"]},
    )
    assert add_player_response.status_code == 403, add_player_response.text

    assign_host_response = client.post(
        "/admin/official-games/00000000-0000-0000-0000-000000000000/host",
        json={"host_user_id": user["id"]},
    )
    assert assign_host_response.status_code == 403, assign_host_response.text

    remove_host_response = client.delete(
        "/admin/official-games/00000000-0000-0000-0000-000000000000/host",
    )
    assert remove_host_response.status_code == 403, remove_host_response.text

    participants_response = client.get(
        "/admin/official-games/00000000-0000-0000-0000-000000000000/participants"
    )
    assert participants_response.status_code == 403, participants_response.text

    bookings_response = client.get(
        "/admin/official-games/00000000-0000-0000-0000-000000000000/bookings"
    )
    assert bookings_response.status_code == 403, bookings_response.text

    waitlist_response = client.get(
        "/admin/official-games/00000000-0000-0000-0000-000000000000/waitlist"
    )
    assert waitlist_response.status_code == 403, waitlist_response.text

    lookup_users_response = client.get("/admin/lookups/users")
    assert lookup_users_response.status_code == 403, lookup_users_response.text

    lookup_venues_response = client.get("/admin/lookups/venues")
    assert lookup_venues_response.status_code == 403, lookup_venues_response.text


def test_admin_official_game_create_rejects_client_managed_invariants(
    client: TestClient,
):
    admin = create_user(client)
    host = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    for payload, rejected_field in (
        (build_official_game_payload(game_type="community"), "game_type"),
        (build_official_game_payload(host_user_id=host["id"]), "host_user_id"),
        (build_official_game_payload(minimum_age=18), "minimum_age"),
        (build_official_game_payload(host_guest_max=4), "host_guest_max"),
        (build_official_game_payload(description="Internal edit"), "description"),
    ):
        response = client.post("/admin/official-games", json=payload)
        assert response.status_code == 422, response.text
        assert rejected_field in response.text


def test_admin_official_game_update_rejects_client_managed_invariants(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")

    authenticate_as(admin["id"])
    create_response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    game = create_response.json()["game"]

    response = client.patch(
        f"/admin/official-games/{game['id']}",
        json={"game_type": "community"},
    )

    assert response.status_code == 422, response.text
    assert "game_type" in response.text


def test_admin_official_game_create_requires_one_venue_source(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])

    authenticate_as(admin["id"])
    response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(venue_id=venue["id"]),
    )

    assert response.status_code == 400, response.text
    assert "either venue_id or venue" in response.text
