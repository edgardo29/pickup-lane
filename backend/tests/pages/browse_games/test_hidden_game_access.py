from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
import pytest

from backend.database import SessionLocal
from backend.models import Booking, User
from backend.services.waitlist_rules import VALID_WAITLIST_STATUSES
from backend.tests.support.assertions import assert_private_no_store
from backend.tests.support.auth import (
    authenticate_optional_as,
    set_user_role,
)
from backend.tests.support.api_helpers import (
    create_booking,
    create_game,
    create_game_participant,
    create_venue,
    create_waitlist_entry,
)
from backend.tests.support.factories import create_user


BOOKING_TIED_WAITLIST_STATUSES = {"accepted", "payment_processing", "payment_failed"}


def _future_iso(minutes: int = 10) -> str:
    return (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat()


def _past_iso(minutes: int = 10) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes)).isoformat()


def _waitlist_lifecycle_overrides(waitlist_status: str) -> dict[str, object]:
    now_utc = datetime.now(UTC).replace(microsecond=0)
    if waitlist_status == "promoted":
        return {
            "promoted_at": (now_utc - timedelta(minutes=1)).isoformat(),
            "promotion_expires_at": (now_utc + timedelta(minutes=10)).isoformat(),
        }
    if waitlist_status == "expired":
        return {"expired_at": (now_utc - timedelta(minutes=1)).isoformat()}
    if waitlist_status == "cancelled":
        return {"cancelled_at": (now_utc - timedelta(minutes=1)).isoformat()}
    return {}


def _create_nonqualifying_promoted_booking(
    client: TestClient,
    user_id: str,
    game_id: str,
) -> dict[str, object]:
    return create_booking(
        client,
        user_id,
        game_id,
        booking_status="waitlisted",
        payment_status="not_required",
    )


def _create_waitlist_entry_for_status(
    client: TestClient,
    user_id: str,
    game_id: str,
    waitlist_status: str,
) -> dict[str, object]:
    overrides = _waitlist_lifecycle_overrides(waitlist_status)
    if waitlist_status in BOOKING_TIED_WAITLIST_STATUSES:
        booking = _create_nonqualifying_promoted_booking(client, user_id, game_id)
        overrides["promoted_booking_id"] = booking["id"]
    return create_waitlist_entry(
        client,
        user_id,
        game_id,
        waitlist_status=waitlist_status,
        **overrides,
    )


def _set_admin_account_state(
    user_id: str,
    *,
    account_status: str = "active",
    deleted_at: datetime | None = None,
) -> None:
    with SessionLocal() as db:
        db_user = db.get(User, UUID(user_id))
        assert db_user is not None
        db_user.role = "admin"
        db_user.account_status = account_status
        db_user.deleted_at = deleted_at
        db.commit()


def _expire_booking(booking_id: str) -> None:
    with SessionLocal() as db:
        db_booking = db.get(Booking, UUID(booking_id))
        assert db_booking is not None
        db_booking.expires_at = datetime.now(UTC) - timedelta(minutes=10)
        db.commit()


def test_visible_game_detail_and_roster_are_public(client: TestClient):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue, host_user_id=host["id"])
    create_game_participant(client, player["id"], game["id"])

    detail_response = client.get(f"/games/{game['id']}")
    roster_response = client.get(f"/games/{game['id']}/participants")

    assert detail_response.status_code == 200, detail_response.text
    assert roster_response.status_code == 200, roster_response.text


def test_hidden_game_invalid_authorization_header_returns_401(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        public_visibility_status="hidden",
    )

    response = client.get(
        f"/games/{game['id']}",
        headers={"Authorization": "not-a-bearer-token"},
    )

    assert response.status_code == 401, response.text


def test_hidden_game_detail_returns_404_for_anonymous_user(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        public_visibility_status="hidden",
    )

    response = client.get(f"/games/{game['id']}")

    assert response.status_code == 404, response.text


def test_hidden_game_detail_returns_404_for_unrelated_user(client: TestClient):
    host = create_user(client)
    unrelated_user = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        public_visibility_status="hidden",
    )

    authenticate_optional_as(unrelated_user["id"])
    response = client.get(f"/games/{game['id']}")

    assert response.status_code == 404, response.text


def test_hidden_game_host_can_view_detail_and_roster_with_private_cache(
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
        payment_collection_type="external_host",
        public_visibility_status="hidden",
    )

    authenticate_optional_as(host["id"])
    detail_response = client.get(f"/games/{game['id']}")
    roster_response = client.get(f"/games/{game['id']}/participants")

    assert detail_response.status_code == 200, detail_response.text
    assert_private_no_store(detail_response)
    assert roster_response.status_code == 200, roster_response.text
    assert_private_no_store(roster_response)


def test_hidden_game_admin_can_view_detail_and_roster_with_private_cache(
    client: TestClient,
):
    host = create_user(client)
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        public_visibility_status="hidden",
    )

    authenticate_optional_as(admin["id"])
    detail_response = client.get(f"/games/{game['id']}")
    roster_response = client.get(f"/games/{game['id']}/participants")

    assert detail_response.status_code == 200, detail_response.text
    assert_private_no_store(detail_response)
    assert roster_response.status_code == 200, roster_response.text
    assert_private_no_store(roster_response)


@pytest.mark.parametrize(
    ("account_status", "has_deleted_at"),
    [
        ("suspended", False),
        ("pending_deletion", False),
        ("deleted", False),
        ("active", True),
    ],
    ids=["suspended", "pending_deletion", "deleted_status", "deleted_at"],
)
def test_hidden_game_invalid_admin_states_do_not_grant_detail_or_roster_access(
    client: TestClient,
    account_status: str,
    has_deleted_at: bool,
):
    host = create_user(client)
    admin = create_user(client)
    _set_admin_account_state(
        admin["id"],
        account_status=account_status,
        deleted_at=datetime.now(UTC) if has_deleted_at else None,
    )
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        public_visibility_status="hidden",
    )

    authenticate_optional_as(admin["id"])
    detail_response = client.get(f"/games/{game['id']}")
    roster_response = client.get(f"/games/{game['id']}/participants")

    assert detail_response.status_code == 404, detail_response.text
    assert roster_response.status_code == 404, roster_response.text


def test_hidden_confirmed_participant_can_view_detail_and_roster_with_private_cache(
    client: TestClient,
):
    host = create_user(client)
    confirmed_player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        public_visibility_status="hidden",
    )
    create_game_participant(client, confirmed_player["id"], game["id"])

    authenticate_optional_as(confirmed_player["id"])
    detail_response = client.get(f"/games/{game['id']}")
    roster_response = client.get(f"/games/{game['id']}/participants")

    assert detail_response.status_code == 200, detail_response.text
    assert_private_no_store(detail_response)
    assert roster_response.status_code == 200, roster_response.text
    assert_private_no_store(roster_response)


def test_hidden_valid_pending_participant_can_view_detail_and_roster_with_private_cache(
    client: TestClient,
):
    host = create_user(client)
    pending_player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        public_visibility_status="hidden",
    )
    booking = create_booking(
        client,
        pending_player["id"],
        game["id"],
        booking_status="pending_payment",
        payment_status="processing",
        expires_at=_future_iso(),
    )
    create_game_participant(
        client,
        pending_player["id"],
        game["id"],
        booking["id"],
        participant_status="pending_payment",
        roster_order=None,
    )

    authenticate_optional_as(pending_player["id"])
    detail_response = client.get(f"/games/{game['id']}")
    roster_response = client.get(f"/games/{game['id']}/participants")

    assert detail_response.status_code == 200, detail_response.text
    assert_private_no_store(detail_response)
    assert roster_response.status_code == 200, roster_response.text
    assert_private_no_store(roster_response)


def test_hidden_game_expired_pending_participant_cannot_view_detail_or_roster(
    client: TestClient,
):
    host = create_user(client)
    pending_player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        public_visibility_status="hidden",
    )
    booking = create_booking(
        client,
        pending_player["id"],
        game["id"],
        booking_status="pending_payment",
        payment_status="processing",
        expires_at=_past_iso(),
    )
    create_game_participant(
        client,
        pending_player["id"],
        game["id"],
        booking["id"],
        participant_status="pending_payment",
        roster_order=None,
    )

    authenticate_optional_as(pending_player["id"])
    detail_response = client.get(f"/games/{game['id']}")
    roster_response = client.get(f"/games/{game['id']}/participants")

    assert detail_response.status_code == 404, detail_response.text
    assert roster_response.status_code == 404, roster_response.text


def test_hidden_waitlisted_participant_without_waitlist_entry_cannot_view_detail(
    client: TestClient,
):
    host = create_user(client)
    waitlisted_player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        public_visibility_status="hidden",
    )
    create_game_participant(
        client,
        waitlisted_player["id"],
        game["id"],
        participant_status="waitlisted",
        roster_order=None,
    )

    authenticate_optional_as(waitlisted_player["id"])
    detail_response = client.get(f"/games/{game['id']}")
    roster_response = client.get(f"/games/{game['id']}/participants")

    assert detail_response.status_code == 404, detail_response.text
    assert roster_response.status_code == 404, roster_response.text


def test_hidden_game_pending_booking_buyer_can_view_detail_but_not_roster(
    client: TestClient,
):
    host = create_user(client)
    booking_buyer = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        public_visibility_status="hidden",
        total_spots=10,
    )
    create_booking(
        client,
        booking_buyer["id"],
        game["id"],
        booking_status="pending_payment",
        payment_status="processing",
        expires_at=_future_iso(),
    )

    authenticate_optional_as(booking_buyer["id"])
    detail_response = client.get(f"/games/{game['id']}")
    roster_response = client.get(f"/games/{game['id']}/participants")

    assert detail_response.status_code == 200, detail_response.text
    assert_private_no_store(detail_response)
    assert roster_response.status_code == 404, roster_response.text


@pytest.mark.parametrize(
    ("booking_status", "payment_status", "overrides"),
    [
        ("confirmed", "paid", {}),
        (
            "partially_cancelled",
            "partially_refunded",
            {"cancelled_by_user_id": "__buyer__"},
        ),
    ],
    ids=["confirmed", "partially_cancelled"],
)
def test_hidden_game_booking_buyer_without_remaining_participant_cannot_view_detail(
    client: TestClient,
    booking_status: str,
    payment_status: str,
    overrides: dict[str, object],
):
    host = create_user(client)
    booking_buyer = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        public_visibility_status="hidden",
        total_spots=10,
    )
    booking_overrides = dict(overrides)
    if booking_overrides.get("cancelled_by_user_id") == "__buyer__":
        booking_overrides["cancelled_by_user_id"] = booking_buyer["id"]
    create_booking(
        client,
        booking_buyer["id"],
        game["id"],
        booking_status=booking_status,
        payment_status=payment_status,
        **booking_overrides,
    )

    authenticate_optional_as(booking_buyer["id"])
    detail_response = client.get(f"/games/{game['id']}")
    roster_response = client.get(f"/games/{game['id']}/participants")

    assert detail_response.status_code == 404, detail_response.text
    assert roster_response.status_code == 404, roster_response.text


@pytest.mark.parametrize(
    ("booking_status", "payment_status", "overrides"),
    [
        ("confirmed", "paid", {}),
        (
            "partially_cancelled",
            "partially_refunded",
            {"cancelled_by_user_id": "__buyer__"},
        ),
    ],
    ids=["confirmed", "partially_cancelled"],
)
def test_hidden_game_booking_buyer_with_only_cancelled_slot_cannot_view_detail(
    client: TestClient,
    booking_status: str,
    payment_status: str,
    overrides: dict[str, object],
):
    host = create_user(client)
    booking_buyer = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        public_visibility_status="hidden",
        total_spots=10,
    )
    booking_overrides = dict(overrides)
    if booking_overrides.get("cancelled_by_user_id") == "__buyer__":
        booking_overrides["cancelled_by_user_id"] = booking_buyer["id"]
    booking = create_booking(
        client,
        booking_buyer["id"],
        game["id"],
        booking_status=booking_status,
        payment_status=payment_status,
        **booking_overrides,
    )
    create_game_participant(
        client,
        booking_buyer["id"],
        game["id"],
        booking["id"],
        participant_status="cancelled",
        cancellation_type="on_time",
        cancelled_at=datetime.now(UTC).isoformat(),
        attendance_status="not_applicable",
        roster_order=None,
    )

    authenticate_optional_as(booking_buyer["id"])
    detail_response = client.get(f"/games/{game['id']}")
    roster_response = client.get(f"/games/{game['id']}/participants")

    assert detail_response.status_code == 404, detail_response.text
    assert roster_response.status_code == 404, roster_response.text


@pytest.mark.parametrize(
    ("booking_status", "overrides"),
    [
        ("confirmed", {}),
        ("partially_cancelled", {"cancelled_by_user_id": "__buyer__"}),
    ],
    ids=["confirmed", "partially_cancelled"],
)
def test_hidden_game_booking_buyer_with_remaining_active_slot_can_view_detail_only(
    client: TestClient,
    booking_status: str,
    overrides: dict[str, object],
):
    host = create_user(client)
    booking_buyer = create_user(client)
    guest_owner = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        public_visibility_status="hidden",
        total_spots=10,
    )
    booking_overrides = dict(overrides)
    if booking_overrides.get("cancelled_by_user_id") == "__buyer__":
        booking_overrides["cancelled_by_user_id"] = booking_buyer["id"]
    booking = create_booking(
        client,
        booking_buyer["id"],
        game["id"],
        booking_status=booking_status,
        payment_status="paid",
        **booking_overrides,
    )
    create_game_participant(
        client,
        None,
        game["id"],
        booking["id"],
        participant_type="guest",
        guest_of_user_id=guest_owner["id"],
        guest_name="Guest Player",
        display_name_snapshot="Guest Player",
    )

    authenticate_optional_as(booking_buyer["id"])
    detail_response = client.get(f"/games/{game['id']}")
    roster_response = client.get(f"/games/{game['id']}/participants")

    assert detail_response.status_code == 200, detail_response.text
    assert_private_no_store(detail_response)
    assert roster_response.status_code == 404, roster_response.text


def test_hidden_game_expired_pending_booking_buyer_cannot_view_detail(
    client: TestClient,
):
    host = create_user(client)
    booking_buyer = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        public_visibility_status="hidden",
        total_spots=10,
    )
    booking = create_booking(
        client,
        booking_buyer["id"],
        game["id"],
        booking_status="pending_payment",
        payment_status="processing",
        expires_at=_future_iso(),
    )
    _expire_booking(booking["id"])

    authenticate_optional_as(booking_buyer["id"])
    response = client.get(f"/games/{game['id']}")

    assert response.status_code == 404, response.text


@pytest.mark.parametrize(
    "waitlist_status",
    ["active", "promoted", "payment_processing"],
    ids=["active", "promoted", "payment_processing"],
)
def test_hidden_game_active_waitlist_states_can_view_detail_only(
    client: TestClient,
    waitlist_status: str,
):
    host = create_user(client)
    waitlist_user = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        public_visibility_status="hidden",
    )
    _create_waitlist_entry_for_status(
        client,
        waitlist_user["id"],
        game["id"],
        waitlist_status,
    )

    authenticate_optional_as(waitlist_user["id"])
    detail_response = client.get(f"/games/{game['id']}")
    roster_response = client.get(f"/games/{game['id']}/participants")

    assert detail_response.status_code == 200, detail_response.text
    assert_private_no_store(detail_response)
    assert roster_response.status_code == 404, roster_response.text


@pytest.mark.parametrize(
    "waitlist_status",
    [
        "accepted",
        "declined",
        "expired",
        "cancelled",
        "removed",
        "payment_failed",
    ],
    ids=[
        "accepted",
        "declined",
        "expired",
        "cancelled",
        "removed",
        "payment_failed",
    ],
)
def test_hidden_game_inactive_waitlist_states_do_not_grant_detail_access(
    client: TestClient,
    waitlist_status: str,
):
    host = create_user(client)
    waitlist_user = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        public_visibility_status="hidden",
    )
    _create_waitlist_entry_for_status(
        client,
        waitlist_user["id"],
        game["id"],
        waitlist_status,
    )

    authenticate_optional_as(waitlist_user["id"])
    response = client.get(f"/games/{game['id']}")

    assert response.status_code == 404, response.text


def test_hidden_game_waitlist_status_matrix_matches_authoritative_values():
    qualifying_statuses = {"active", "promoted", "payment_processing"}
    nonqualifying_statuses = {
        "accepted",
        "declined",
        "expired",
        "cancelled",
        "removed",
        "payment_failed",
    }

    assert qualifying_statuses.isdisjoint(nonqualifying_statuses)
    assert qualifying_statuses | nonqualifying_statuses == VALID_WAITLIST_STATUSES


def test_hidden_game_accepted_waitlist_access_comes_from_confirmed_participant(
    client: TestClient,
):
    host = create_user(client)
    waitlist_user = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        public_visibility_status="hidden",
    )
    _create_waitlist_entry_for_status(
        client,
        waitlist_user["id"],
        game["id"],
        "accepted",
    )

    authenticate_optional_as(waitlist_user["id"])
    waitlist_only_response = client.get(f"/games/{game['id']}")
    assert waitlist_only_response.status_code == 404, waitlist_only_response.text

    create_game_participant(client, waitlist_user["id"], game["id"])
    confirmed_response = client.get(f"/games/{game['id']}")
    assert confirmed_response.status_code == 200, confirmed_response.text
    assert_private_no_store(confirmed_response)
