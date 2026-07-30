from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
import pytest

from backend.database import SessionLocal
from backend.models import Booking, Game
from backend.services.booking_rules import (
    VALID_BOOKING_STATUSES,
    VALID_PAYMENT_STATUSES,
)
from backend.services.game_participant_rules import VALID_PARTICIPANT_STATUSES
from backend.services.game_rules import ACTIVE_PAYMENT_HOLD_BOOKING_STATUSES
from backend.services.game_service import load_game_card_metadata
from backend.tests.support.api_helpers import (
    create_booking,
    create_game,
    create_game_participant,
    create_venue,
)
from backend.tests.support.factories import create_user
from backend.tests.support.time import local_date_string


PENDING_PAYMENT_COMPATIBLE_NON_CAPACITY_PAYMENT_STATUSES = {
    "not_required",
    "unpaid",
    "paid",
    "failed",
    "disputed",
}
REFUND_OR_CREDIT_PAYMENT_STATUSES_REQUIRING_CANCELLED_BOOKING = {
    "partially_refunded",
    "refunded",
    "credit_restored",
}
NON_PENDING_BOOKING_STATUSES = {
    "confirmed",
    "waitlisted",
    "partially_cancelled",
    "cancelled",
    "expired",
    "failed",
}
NON_CAPACITY_PARTICIPANT_STATUSES = {
    "waitlisted",
    "cancelled",
    "late_cancelled",
    "removed",
    "refunded",
}


def _browse_start(days_from_now: int = 7) -> datetime:
    local_start = (
        datetime.now(ZoneInfo("America/Chicago")) + timedelta(days=days_from_now)
    ).replace(hour=18, minute=0, second=0, microsecond=0)
    return local_start.astimezone(UTC)


def _create_browse_game(
    client: TestClient,
    *,
    total_spots: int = 10,
) -> tuple[dict, datetime]:
    admin = create_user(client)
    venue = create_venue(client, admin["id"])
    starts_at = _browse_start()
    game = create_game(
        client,
        admin["id"],
        venue,
        starts_at=starts_at.isoformat(),
        ends_at=(starts_at + timedelta(hours=1)).isoformat(),
        total_spots=total_spots,
    )
    return game, starts_at


def _get_single_browse_card(client: TestClient, starts_at: datetime) -> dict:
    response = client.get(
        "/games/browse",
        params={"starts_on": local_date_string(starts_at, "America/Chicago")},
    )

    assert response.status_code == 200, response.text
    games = response.json()["games"]
    assert len(games) == 1
    return games[0]


def _assert_single_card_capacity(
    client: TestClient,
    starts_at: datetime,
    *,
    expected_occupied_spots: int,
    total_spots: int = 10,
) -> None:
    card = _get_single_browse_card(client, starts_at)
    assert card["participant_count"] == expected_occupied_spots
    assert card["availability"]["occupied_spots"] == expected_occupied_spots
    assert card["availability"]["total_spots"] == total_spots
    assert card["availability"]["spots_remaining"] == max(
        total_spots - expected_occupied_spots,
        0,
    )


def test_browse_game_cards_return_backend_availability_statuses(
    client: TestClient,
):
    admin = create_user(client)
    venue = create_venue(client, admin["id"])
    browse_timezone = ZoneInfo("America/Chicago")
    base_local = (datetime.now(browse_timezone) + timedelta(days=7)).replace(
        hour=18,
        minute=0,
        second=0,
        microsecond=0,
    )
    base_start = base_local.astimezone(UTC)
    open_game = create_game(
        client,
        admin["id"],
        venue,
        starts_at=base_start.isoformat(),
        ends_at=(base_start + timedelta(hours=1)).isoformat(),
        total_spots=6,
    )
    waitlist_open_game = create_game(
        client,
        admin["id"],
        venue,
        starts_at=(base_start + timedelta(hours=1)).isoformat(),
        ends_at=(base_start + timedelta(hours=2)).isoformat(),
        total_spots=6,
        waitlist_enabled=True,
    )
    full_game = create_game(
        client,
        admin["id"],
        venue,
        starts_at=(base_start + timedelta(hours=2)).isoformat(),
        ends_at=(base_start + timedelta(hours=3)).isoformat(),
        total_spots=6,
        waitlist_enabled=False,
    )

    create_game_participant(client, create_user(client)["id"], open_game["id"])
    for _index in range(6):
        create_game_participant(
            client,
            create_user(client)["id"],
            waitlist_open_game["id"],
        )
        create_game_participant(client, create_user(client)["id"], full_game["id"])

    response = client.get(
        "/games/browse",
        params={"starts_on": local_date_string(base_start, "America/Chicago")},
    )

    assert response.status_code == 200, response.text
    games_by_id = {game["id"]: game for game in response.json()["games"]}
    assert games_by_id[open_game["id"]]["availability"] == {
        "status": "open",
        "occupied_spots": 1,
        "total_spots": 6,
        "spots_remaining": 5,
    }
    assert games_by_id[waitlist_open_game["id"]]["availability"] == {
        "status": "waitlist_open",
        "occupied_spots": 6,
        "total_spots": 6,
        "spots_remaining": 0,
    }
    assert games_by_id[full_game["id"]]["availability"] == {
        "status": "full",
        "occupied_spots": 6,
        "total_spots": 6,
        "spots_remaining": 0,
    }


def test_browse_capacity_counts_confirmed_registered_and_guest_participants(
    client: TestClient,
):
    confirmed_player = create_user(client)
    game, starts_at = _create_browse_game(client)

    create_game_participant(client, confirmed_player["id"], game["id"])
    create_game_participant(
        client,
        None,
        game["id"],
        participant_type="guest",
        guest_of_user_id=confirmed_player["id"],
        guest_name="Confirmed Guest",
        display_name_snapshot="Confirmed Guest",
        roster_order=2,
    )

    _assert_single_card_capacity(
        client,
        starts_at,
        expected_occupied_spots=2,
    )


@pytest.mark.parametrize(
    "payment_status",
    sorted(ACTIVE_PAYMENT_HOLD_BOOKING_STATUSES),
    ids=sorted(ACTIVE_PAYMENT_HOLD_BOOKING_STATUSES),
)
def test_browse_capacity_counts_valid_unexpired_pending_payment_holds(
    client: TestClient,
    payment_status: str,
):
    pending_player = create_user(client)
    game, starts_at = _create_browse_game(client)
    now_utc = datetime.now(UTC).replace(microsecond=0)
    booking = create_booking(
        client,
        pending_player["id"],
        game["id"],
        booking_status="pending_payment",
        payment_status=payment_status,
        expires_at=(now_utc + timedelta(minutes=10)).isoformat(),
    )
    create_game_participant(
        client,
        pending_player["id"],
        game["id"],
        booking["id"],
        participant_status="pending_payment",
        roster_order=None,
    )

    _assert_single_card_capacity(
        client,
        starts_at,
        expected_occupied_spots=1,
    )


def test_browse_capacity_ignores_expired_pending_payment_hold_before_cleanup(
    client: TestClient,
):
    expired_player = create_user(client)
    game, starts_at = _create_browse_game(client)
    now_utc = datetime.now(UTC).replace(microsecond=0)
    booking = create_booking(
        client,
        expired_player["id"],
        game["id"],
        booking_status="pending_payment",
        payment_status="processing",
        expires_at=(now_utc - timedelta(minutes=10)).isoformat(),
    )
    create_game_participant(
        client,
        expired_player["id"],
        game["id"],
        booking["id"],
        participant_status="pending_payment",
        roster_order=None,
    )

    _assert_single_card_capacity(
        client,
        starts_at,
        expected_occupied_spots=0,
    )


@pytest.mark.parametrize(
    "payment_status",
    sorted(PENDING_PAYMENT_COMPATIBLE_NON_CAPACITY_PAYMENT_STATUSES),
    ids=sorted(PENDING_PAYMENT_COMPATIBLE_NON_CAPACITY_PAYMENT_STATUSES),
)
def test_browse_capacity_ignores_pending_payment_holds_with_non_active_payment_status(
    client: TestClient,
    payment_status: str,
):
    pending_player = create_user(client)
    game, starts_at = _create_browse_game(client)
    now_utc = datetime.now(UTC).replace(microsecond=0)
    booking = create_booking(
        client,
        pending_player["id"],
        game["id"],
        booking_status="pending_payment",
        payment_status=payment_status,
        expires_at=(now_utc + timedelta(minutes=10)).isoformat(),
    )
    create_game_participant(
        client,
        pending_player["id"],
        game["id"],
        booking["id"],
        participant_status="pending_payment",
        roster_order=None,
    )

    _assert_single_card_capacity(
        client,
        starts_at,
        expected_occupied_spots=0,
    )


@pytest.mark.parametrize(
    ("booking_status", "payment_status", "extra_overrides"),
    [
        ("confirmed", "paid", {}),
        ("waitlisted", "unpaid", {}),
        (
            "partially_cancelled",
            "partially_refunded",
            {"cancelled_by_user_id": "__buyer__"},
        ),
        ("cancelled", "failed", {"cancelled_by_user_id": "__buyer__"}),
        ("expired", "failed", {}),
        ("failed", "failed", {}),
    ],
    ids=[
        "confirmed",
        "waitlisted",
        "partially_cancelled",
        "cancelled",
        "expired",
        "failed",
    ],
)
def test_browse_capacity_ignores_pending_participants_without_pending_booking_status(
    client: TestClient,
    booking_status: str,
    payment_status: str,
    extra_overrides: dict[str, object],
):
    pending_player = create_user(client)
    game, starts_at = _create_browse_game(client)
    booking_overrides = dict(extra_overrides)
    if booking_overrides.get("cancelled_by_user_id") == "__buyer__":
        booking_overrides["cancelled_by_user_id"] = pending_player["id"]
    booking = create_booking(
        client,
        pending_player["id"],
        game["id"],
        booking_status=booking_status,
        payment_status=payment_status,
        **booking_overrides,
    )
    create_game_participant(
        client,
        pending_player["id"],
        game["id"],
        booking["id"],
        participant_status="pending_payment",
        roster_order=None,
    )

    _assert_single_card_capacity(
        client,
        starts_at,
        expected_occupied_spots=0,
    )


def test_browse_capacity_ignores_pending_payment_participant_without_booking(
    client: TestClient,
):
    game, starts_at = _create_browse_game(client)
    create_game_participant(
        client,
        create_user(client)["id"],
        game["id"],
        participant_status="pending_payment",
        roster_order=None,
    )

    _assert_single_card_capacity(
        client,
        starts_at,
        expected_occupied_spots=0,
    )


@pytest.mark.parametrize(
    "participant_status",
    sorted(NON_CAPACITY_PARTICIPANT_STATUSES),
    ids=sorted(NON_CAPACITY_PARTICIPANT_STATUSES),
)
def test_browse_capacity_ignores_non_capacity_participant_statuses(
    client: TestClient,
    participant_status: str,
):
    game, starts_at = _create_browse_game(client)
    overrides: dict[str, object] = {
        "participant_status": participant_status,
        "roster_order": None,
    }
    cancellation_type_by_status = {
        "cancelled": "on_time",
        "late_cancelled": "late",
        "removed": "admin_cancelled",
        "refunded": "admin_cancelled",
    }
    if cancellation_type := cancellation_type_by_status.get(participant_status):
        overrides["cancelled_at"] = datetime.now(UTC).isoformat()
        overrides["cancellation_type"] = cancellation_type
    create_game_participant(
        client,
        create_user(client)["id"],
        game["id"],
        **overrides,
    )

    _assert_single_card_capacity(
        client,
        starts_at,
        expected_occupied_spots=0,
    )


def test_browse_capacity_status_matrices_match_authoritative_values():
    assert ACTIVE_PAYMENT_HOLD_BOOKING_STATUSES.isdisjoint(
        PENDING_PAYMENT_COMPATIBLE_NON_CAPACITY_PAYMENT_STATUSES,
    )
    assert ACTIVE_PAYMENT_HOLD_BOOKING_STATUSES.isdisjoint(
        REFUND_OR_CREDIT_PAYMENT_STATUSES_REQUIRING_CANCELLED_BOOKING,
    )
    assert PENDING_PAYMENT_COMPATIBLE_NON_CAPACITY_PAYMENT_STATUSES.isdisjoint(
        REFUND_OR_CREDIT_PAYMENT_STATUSES_REQUIRING_CANCELLED_BOOKING,
    )
    assert (
        ACTIVE_PAYMENT_HOLD_BOOKING_STATUSES
        | PENDING_PAYMENT_COMPATIBLE_NON_CAPACITY_PAYMENT_STATUSES
        | REFUND_OR_CREDIT_PAYMENT_STATUSES_REQUIRING_CANCELLED_BOOKING
    ) == VALID_PAYMENT_STATUSES
    assert {"pending_payment"}.isdisjoint(NON_PENDING_BOOKING_STATUSES)
    assert (
        {"pending_payment"} | NON_PENDING_BOOKING_STATUSES
    ) == VALID_BOOKING_STATUSES
    assert {"confirmed", "pending_payment"}.isdisjoint(
        NON_CAPACITY_PARTICIPANT_STATUSES,
    )
    assert (
        {"confirmed", "pending_payment"} | NON_CAPACITY_PARTICIPANT_STATUSES
    ) == VALID_PARTICIPANT_STATUSES


def test_browse_capacity_treats_expires_at_equal_now_as_expired(
    client: TestClient,
):
    admin = create_user(client)
    pending_player = create_user(client)
    venue = create_venue(client, admin["id"])
    fixed_now = datetime.now(UTC).replace(microsecond=0)
    starts_at = (fixed_now + timedelta(days=7)).replace(
        hour=18,
        minute=0,
        second=0,
        microsecond=0,
    )
    game = create_game(
        client,
        admin["id"],
        venue,
        starts_at=starts_at.isoformat(),
        ends_at=(starts_at + timedelta(hours=1)).isoformat(),
        total_spots=10,
    )
    booking = create_booking(
        client,
        pending_player["id"],
        game["id"],
        booking_status="pending_payment",
        payment_status="processing",
        expires_at=(fixed_now + timedelta(minutes=2)).isoformat(),
    )
    create_game_participant(
        client,
        pending_player["id"],
        game["id"],
        booking["id"],
        participant_status="pending_payment",
        roster_order=None,
    )

    with SessionLocal() as db:
        db_booking = db.get(Booking, UUID(booking["id"]))
        assert db_booking is not None
        db_booking.expires_at = fixed_now
        db.commit()

        db_game = db.get(Game, UUID(game["id"]))
        assert db_game is not None
        participant_counts, _game_images, _venue_images = load_game_card_metadata(
            db,
            [db_game],
            now=fixed_now,
        )

    assert participant_counts.get(UUID(game["id"]), 0) == 0
