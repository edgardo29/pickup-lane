from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.database import SessionLocal
from backend.models import GameCredit, GameCreditUsage
from backend.services.game_credit_service import (
    GameCreditCalculationError,
    REDEEMED_USAGE_STATUS,
    RELEASED_USAGE_STATUS,
    RESERVED_USAGE_STATUS,
    calculate_game_credit_application,
    calculate_user_game_credit_application,
    get_available_game_credit_balance,
    redeem_reserved_game_credits,
    release_reserved_game_credits,
    reserve_game_credits,
)
from backend.tests.helpers import (
    authenticate_as,
    create_booking,
    create_game,
    create_user,
    create_venue,
    set_user_role,
)


def test_admin_can_issue_list_balance_and_reverse_game_credit(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)

    authenticate_as(admin["id"])
    issue_response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 2500,
            "credit_reason": "official_game_cancelled",
            "source_game_id": game["id"],
            "idempotency_key": "test-credit-issue",
            "note": "Official game cancelled.",
        },
    )

    assert issue_response.status_code == 201, issue_response.text
    credit = issue_response.json()
    assert credit["user_id"] == player["id"]
    assert credit["amount_cents"] == 2500
    assert credit["remaining_cents"] == 2500
    assert credit["credit_status"] == "active"

    balance_response = client.get(f"/game-credits/balance?user_id={player['id']}")
    assert balance_response.status_code == 200, balance_response.text
    assert balance_response.json()["available_credit_cents"] == 2500

    list_response = client.get(f"/game-credits?user_id={player['id']}")
    assert list_response.status_code == 200, list_response.text
    assert len(list_response.json()) == 1

    reverse_response = client.post(
        f"/admin/game-credits/{credit['id']}/reverse",
        json={"idempotency_key": "test-credit-reverse", "note": "Mistake."},
    )
    assert reverse_response.status_code == 200, reverse_response.text
    assert reverse_response.json()["credit_status"] == "reversed"
    assert reverse_response.json()["remaining_cents"] == 0
    with SessionLocal() as db:
        usage = db.scalars(
            select(GameCreditUsage).where(
                GameCreditUsage.game_credit_id == UUID(credit["id"])
            )
        ).one()
        assert usage.usage_type == "reverse"
        assert usage.usage_status == "reversed"
        assert str(usage.game_id) == game["id"]

    balance_after_reverse_response = client.get(
        f"/game-credits/balance?user_id={player['id']}"
    )
    assert balance_after_reverse_response.status_code == 200
    assert balance_after_reverse_response.json()["available_credit_cents"] == 0


def test_regular_user_cannot_issue_game_credit(client: TestClient):
    user = create_user(client)
    player = create_user(client)
    authenticate_as(user["id"])

    response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 2500,
            "credit_reason": "admin_credit",
        },
    )

    assert response.status_code == 403, response.text


def test_credit_source_must_be_official_game(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(
        client,
        admin["id"],
        venue,
        game_type="community",
        payment_collection_type="external_host",
        host_user_id=admin["id"],
        policy_mode="custom_hosted",
    )

    authenticate_as(admin["id"])
    response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 2500,
            "credit_reason": "official_game_cancelled",
            "source_game_id": game["id"],
        },
    )

    assert response.status_code == 400, response.text
    assert "official in-app games" in response.text


def test_expired_credit_is_ignored_in_available_balance(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    authenticate_as(admin["id"])

    response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 2500,
            "credit_reason": "admin_credit",
            "source_game_id": game["id"],
            "expires_at": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        },
    )

    assert response.status_code == 201, response.text
    balance_response = client.get(f"/game-credits/balance?user_id={player['id']}")
    assert balance_response.status_code == 200, balance_response.text
    assert balance_response.json()["available_credit_cents"] == 0


def test_game_credit_application_calculates_checkout_amounts_in_cents():
    no_credit = calculate_game_credit_application(
        1500,
        0,
        minimum_stripe_charge_cents=50,
    )
    assert no_credit.credit_applied_cents == 0
    assert no_credit.minimum_charge_adjustment_cents == 0
    assert no_credit.final_amount_due_cents == 1500
    assert no_credit.stripe_amount_cents == 1500
    assert no_credit.payment_required is True

    no_credit_tiny_total = calculate_game_credit_application(
        25,
        0,
        minimum_stripe_charge_cents=50,
    )
    assert no_credit_tiny_total.credit_applied_cents == 0
    assert no_credit_tiny_total.minimum_charge_adjustment_cents == 0
    assert no_credit_tiny_total.final_amount_due_cents == 25
    assert no_credit_tiny_total.stripe_amount_cents == 25
    assert no_credit_tiny_total.payment_required is True

    partial_credit = calculate_game_credit_application(
        1500,
        500,
        minimum_stripe_charge_cents=50,
    )
    assert partial_credit.credit_applied_cents == 500
    assert partial_credit.minimum_charge_adjustment_cents == 0
    assert partial_credit.final_amount_due_cents == 1000
    assert partial_credit.stripe_amount_cents == 1000
    assert partial_credit.payment_required is True

    full_credit = calculate_game_credit_application(
        1500,
        1500,
        minimum_stripe_charge_cents=50,
    )
    assert full_credit.credit_applied_cents == 1500
    assert full_credit.minimum_charge_adjustment_cents == 0
    assert full_credit.final_amount_due_cents == 0
    assert full_credit.stripe_amount_cents == 0
    assert full_credit.payment_required is False

    extra_credit = calculate_game_credit_application(
        1500,
        2000,
        minimum_stripe_charge_cents=50,
    )
    assert extra_credit.credit_applied_cents == 1500
    assert extra_credit.final_amount_due_cents == 0
    assert extra_credit.stripe_amount_cents == 0
    assert extra_credit.payment_required is False

    uneven_amount = calculate_game_credit_application(
        1299,
        537,
        minimum_stripe_charge_cents=50,
    )
    assert uneven_amount.credit_applied_cents == 537
    assert uneven_amount.final_amount_due_cents == 762
    assert uneven_amount.stripe_amount_cents == 762

    tiny_remainder = calculate_game_credit_application(
        1500,
        1475,
        minimum_stripe_charge_cents=50,
    )
    assert tiny_remainder.credit_applied_cents == 1475
    assert tiny_remainder.minimum_charge_adjustment_cents == 25
    assert tiny_remainder.final_amount_due_cents == 0
    assert tiny_remainder.stripe_amount_cents == 0
    assert tiny_remainder.payment_required is False


def test_game_credit_application_rejects_negative_money_values():
    with pytest.raises(GameCreditCalculationError):
        calculate_game_credit_application(
            -1,
            0,
            minimum_stripe_charge_cents=50,
        )

    with pytest.raises(GameCreditCalculationError):
        calculate_game_credit_application(
            1500,
            -1,
            minimum_stripe_charge_cents=50,
        )


def test_game_credit_ledger_reserves_releases_and_redeems_oldest_expiring_first(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    authenticate_as(admin["id"])
    soon_credit_response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 500,
            "credit_reason": "admin_credit",
            "source_game_id": game["id"],
            "idempotency_key": "soon-expiring-credit",
            "expires_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        },
    )
    later_credit_response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 1000,
            "credit_reason": "admin_credit",
            "source_game_id": game["id"],
            "idempotency_key": "later-expiring-credit",
            "expires_at": (datetime.now(UTC) + timedelta(days=10)).isoformat(),
        },
    )
    assert soon_credit_response.status_code == 201, soon_credit_response.text
    assert later_credit_response.status_code == 201, later_credit_response.text
    soon_credit = soon_credit_response.json()
    later_credit = later_credit_response.json()
    booking = create_booking(
        client,
        player["id"],
        game["id"],
        booking_status="pending_payment",
        payment_status="processing",
        subtotal_cents=800,
        platform_fee_cents=0,
        discount_cents=0,
        total_cents=800,
        price_per_player_snapshot_cents=800,
        platform_fee_snapshot_cents=0,
    )

    with SessionLocal() as db:
        now = datetime.now(UTC)
        usages = reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=800,
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            now=now,
            idempotency_scope=f"checkout:{booking['id']}",
        )
        repeat_usages = reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=800,
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            now=now,
            idempotency_scope=f"checkout:{booking['id']}",
        )
        db.commit()

        assert [usage.amount_cents for usage in usages] == [500, 300]
        assert [usage.id for usage in repeat_usages] == [usage.id for usage in usages]
        assert {usage.usage_status for usage in usages} == {RESERVED_USAGE_STATUS}

        refreshed_soon_credit = db.get(GameCredit, UUID(soon_credit["id"]))
        refreshed_later_credit = db.get(GameCredit, UUID(later_credit["id"]))
        assert refreshed_soon_credit is not None
        assert refreshed_later_credit is not None
        assert refreshed_soon_credit.remaining_cents == 0
        assert refreshed_soon_credit.credit_status == "active"
        assert refreshed_later_credit.remaining_cents == 700
        assert (
            get_available_game_credit_balance(db, UUID(player["id"]), now=now)
            == 700
        )

    authenticate_as(admin["id"])
    reverse_reserved_response = client.post(
        f"/admin/game-credits/{soon_credit['id']}/reverse",
        json={"note": "Cannot reverse while reserved."},
    )
    assert reverse_reserved_response.status_code == 400, (
        reverse_reserved_response.text
    )
    assert reverse_reserved_response.json()["detail"] == (
        "Only active unused credit can be reversed."
    )

    with SessionLocal() as db:
        released_usages = release_reserved_game_credits(
            db,
            UUID(booking["id"]),
            now=datetime.now(UTC),
            release_reason="test_release",
            user_id=UUID(player["id"]),
        )
        db.commit()

        assert {usage.usage_status for usage in released_usages} == {
            RELEASED_USAGE_STATUS
        }
        assert sum(usage.amount_cents for usage in released_usages) == 800
        restored_soon_credit = db.get(GameCredit, UUID(soon_credit["id"]))
        restored_later_credit = db.get(GameCredit, UUID(later_credit["id"]))
        assert restored_soon_credit is not None
        assert restored_later_credit is not None
        assert restored_soon_credit.remaining_cents == 500
        assert restored_later_credit.remaining_cents == 1000

    second_booking = create_booking(
        client,
        player["id"],
        game["id"],
        booking_status="pending_payment",
        payment_status="processing",
        subtotal_cents=800,
        platform_fee_cents=0,
        discount_cents=0,
        total_cents=800,
        price_per_player_snapshot_cents=800,
        platform_fee_snapshot_cents=0,
    )
    with SessionLocal() as db:
        reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=800,
            booking_id=UUID(second_booking["id"]),
            game_id=UUID(game["id"]),
            now=datetime.now(UTC),
            idempotency_scope=f"checkout:{second_booking['id']}",
        )
        redeemed_usages = redeem_reserved_game_credits(
            db,
            UUID(second_booking["id"]),
            now=datetime.now(UTC),
            user_id=UUID(player["id"]),
        )
        db.commit()

        assert {usage.usage_status for usage in redeemed_usages} == {
            REDEEMED_USAGE_STATUS
        }
        redeemed_soon_credit = db.get(GameCredit, UUID(soon_credit["id"]))
        redeemed_later_credit = db.get(GameCredit, UUID(later_credit["id"]))
        assert redeemed_soon_credit is not None
        assert redeemed_later_credit is not None
        assert redeemed_soon_credit.remaining_cents == 0
        assert redeemed_soon_credit.credit_status == "used"
        assert redeemed_later_credit.remaining_cents == 700
        assert redeemed_later_credit.credit_status == "active"


def test_user_game_credit_application_uses_available_balance(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)

    authenticate_as(admin["id"])
    response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 1475,
            "credit_reason": "admin_credit",
            "source_game_id": game["id"],
            "idempotency_key": "minimum-charge-adjustment-credit",
        },
    )
    assert response.status_code == 201, response.text

    with SessionLocal() as db:
        application = calculate_user_game_credit_application(
            db,
            UUID(player["id"]),
            total_amount_cents=1500,
            now=datetime.now(UTC),
            minimum_stripe_charge_cents=50,
        )

    assert application.available_credit_cents == 1475
    assert application.credit_applied_cents == 1475
    assert application.minimum_charge_adjustment_cents == 25
    assert application.final_amount_due_cents == 0
    assert application.payment_required is False
