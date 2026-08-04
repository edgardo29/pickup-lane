from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.database import SessionLocal
from backend.models import GameCredit, GameCreditUsage
from backend.services.game_credit_service import (
    GameCreditLedgerError,
    GameCreditCalculationError,
    REDEEMED_USAGE_STATUS,
    RELEASED_USAGE_STATUS,
    RESERVED_USAGE_STATUS,
    calculate_game_credit_application,
    calculate_user_game_credit_application,
    get_available_game_credit_balance,
    redeem_reserved_game_credits,
    release_reserved_game_credits,
    release_reserved_game_credit_usage,
    reserve_game_credits,
    restore_redeemed_game_credit_usage,
)
from backend.tests.helpers import (
    authenticate_as,
    create_booking,
    create_game,
    create_payment,
    create_user,
    create_venue,
    set_user_account_status,
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
    assert credit["available_cents"] == 2500
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
    assert reverse_response.json()["available_cents"] == 0
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


def test_admin_can_reverse_partially_used_credit_without_reserved_usage(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])

    authenticate_as(admin["id"])
    issue_response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 2500,
            "credit_reason": "official_game_cancelled",
            "source_game_id": game["id"],
            "idempotency_key": "test-partial-credit-issue",
            "note": "Official game cancelled.",
        },
    )
    assert issue_response.status_code == 201, issue_response.text
    credit = issue_response.json()

    with SessionLocal() as db:
        reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=1000,
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            now=datetime.now(UTC),
            idempotency_scope=f"partial-reverse:{booking['id']}",
        )
        redeem_reserved_game_credits(
            db,
            UUID(booking["id"]),
            now=datetime.now(UTC),
            user_id=UUID(player["id"]),
        )
        db.commit()

    reverse_response = client.post(
        f"/admin/game-credits/{credit['id']}/reverse",
        json={
            "idempotency_key": "test-partial-credit-reverse",
            "note": "Void remaining value.",
        },
    )
    assert reverse_response.status_code == 200, reverse_response.text
    assert reverse_response.json()["credit_status"] == "reversed"
    assert reverse_response.json()["available_cents"] == 0

    with SessionLocal() as db:
        reverse_usage = db.scalars(
            select(GameCreditUsage).where(
                GameCreditUsage.game_credit_id == UUID(credit["id"]),
                GameCreditUsage.usage_type == "reverse",
            )
        ).one()

    assert reverse_usage.amount_cents == 1500
    assert reverse_usage.usage_status == "reversed"


def test_reversed_credit_cannot_be_redeemed_released_or_restored(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])

    authenticate_as(admin["id"])
    issue_response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 1000,
            "credit_reason": "official_game_cancelled",
            "source_game_id": game["id"],
            "idempotency_key": "test-terminal-credit-issue",
            "note": "Official game cancelled.",
        },
    )
    assert issue_response.status_code == 201, issue_response.text
    credit = issue_response.json()

    reverse_response = client.post(
        f"/admin/game-credits/{credit['id']}/reverse",
        json={
            "idempotency_key": "test-terminal-credit-reverse",
            "note": "Void grant.",
        },
    )
    assert reverse_response.status_code == 200, reverse_response.text

    with SessionLocal() as db:
        now = datetime.now(UTC)
        reserved_usage = GameCreditUsage(
            id=uuid4(),
            game_credit_id=UUID(credit["id"]),
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            amount_cents=100,
            currency="USD",
            usage_type="redeem",
            usage_status=RESERVED_USAGE_STATUS,
            idempotency_key=f"stale-reserved:{uuid4()}",
            reserved_at=now,
            created_at=now,
            updated_at=now,
        )
        redeemed_usage = GameCreditUsage(
            id=uuid4(),
            game_credit_id=UUID(credit["id"]),
            booking_id=UUID(booking["id"]),
            game_id=UUID(game["id"]),
            amount_cents=100,
            currency="USD",
            usage_type="redeem",
            usage_status=REDEEMED_USAGE_STATUS,
            idempotency_key=f"stale-redeemed:{uuid4()}",
            redeemed_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add_all([reserved_usage, redeemed_usage])
        db.commit()

        with pytest.raises(GameCreditLedgerError, match="Reversed game credit"):
            release_reserved_game_credit_usage(
                db,
                reserved_usage.id,
                now=datetime.now(UTC),
                reason_code="test_release",
            )
        db.rollback()

        with pytest.raises(GameCreditLedgerError, match="Reversed game credit"):
            restore_redeemed_game_credit_usage(
                db,
                redeemed_usage.id,
                now=datetime.now(UTC),
                restore_reason="test_restore",
            )
        db.rollback()

        with pytest.raises(GameCreditLedgerError, match="Reversed game credit"):
            redeem_reserved_game_credits(
                db,
                UUID(booking["id"]),
                now=datetime.now(UTC),
                user_id=UUID(player["id"]),
            )
        db.rollback()

        refreshed_credit = db.get(GameCredit, UUID(credit["id"]))

    assert refreshed_credit is not None
    assert refreshed_credit.credit_status == "reversed"
    assert refreshed_credit.available_cents == 0


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


def test_admin_cannot_issue_game_credit_to_suspended_user(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    set_user_account_status(player["id"], "suspended")

    authenticate_as(admin["id"])
    response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 2500,
            "credit_reason": "admin_credit",
            "note": "Suspended user should not receive credit.",
        },
    )

    assert response.status_code == 400, response.text
    assert "User account is not active" in response.text


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


def test_admin_can_issue_game_credit_with_matching_source_booking_and_payment(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    payment = create_payment(client, player["id"], booking["id"])

    authenticate_as(admin["id"])
    response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 2500,
            "credit_reason": "admin_credit",
            "source_game_id": game["id"],
            "source_booking_id": booking["id"],
            "source_payment_id": payment["id"],
            "idempotency_key": "matching-source-credit",
            "note": "Matching source references.",
        },
    )

    assert response.status_code == 201, response.text
    credit = response.json()
    assert credit["source_game_id"] == game["id"]
    assert credit["source_booking_id"] == booking["id"]
    assert credit["source_payment_id"] == payment["id"]


def test_admin_credit_rejects_source_booking_for_other_user(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    other_player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    other_booking = create_booking(client, other_player["id"], game["id"])

    authenticate_as(admin["id"])
    response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 2500,
            "credit_reason": "admin_credit",
            "source_game_id": game["id"],
            "source_booking_id": other_booking["id"],
            "note": "Mismatched booking owner.",
        },
    )

    assert response.status_code == 400, response.text
    assert "Source booking must belong to the credited user" in response.text


def test_admin_credit_rejects_source_payment_for_other_user(client: TestClient):
    admin = create_user(client)
    player = create_user(client)
    other_player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    other_booking = create_booking(client, other_player["id"], game["id"])
    other_payment = create_payment(
        client,
        other_player["id"],
        other_booking["id"],
    )

    authenticate_as(admin["id"])
    response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 2500,
            "credit_reason": "admin_credit",
            "source_game_id": game["id"],
            "source_payment_id": other_payment["id"],
            "note": "Mismatched payment owner.",
        },
    )

    assert response.status_code == 400, response.text
    assert "Source payment must belong to the credited user" in response.text


def test_admin_credit_rejects_source_payment_for_different_booking(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    booking = create_booking(client, player["id"], game["id"])
    other_booking = create_booking(client, player["id"], game["id"])
    other_payment = create_payment(
        client,
        player["id"],
        other_booking["id"],
    )

    authenticate_as(admin["id"])
    response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 2500,
            "credit_reason": "admin_credit",
            "source_game_id": game["id"],
            "source_booking_id": booking["id"],
            "source_payment_id": other_payment["id"],
            "note": "Mismatched payment booking.",
        },
    )

    assert response.status_code == 400, response.text
    assert "Source payment must belong to the source booking" in response.text


def test_admin_credit_rejects_source_payment_for_different_source_game(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)
    other_game = create_game(client, admin["id"], venue)
    payment = create_payment(
        client,
        player["id"],
        game_id=other_game["id"],
        payment_type="community_publish_fee",
    )

    authenticate_as(admin["id"])
    response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 2500,
            "credit_reason": "admin_credit",
            "source_game_id": game["id"],
            "source_payment_id": payment["id"],
            "note": "Mismatched payment game.",
        },
    )

    assert response.status_code == 400, response.text
    assert "Source payment must belong to the source game" in response.text


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


def test_game_credit_ledger_reserves_releases_and_redeems_oldest_grant_first(
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
            "note": "Soon expiring credit.",
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
            "note": "Later expiring credit.",
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
        assert refreshed_soon_credit.available_cents == 0
        assert refreshed_soon_credit.credit_status == "active"
        assert refreshed_later_credit.available_cents == 700
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
        "Credit with reserved usage cannot be reversed."
    )

    with SessionLocal() as db:
        released_usages = release_reserved_game_credits(
            db,
            UUID(booking["id"]),
            now=datetime.now(UTC),
            reason_code="test_release",
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
        assert restored_soon_credit.available_cents == 500
        assert restored_later_credit.available_cents == 1000

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
        assert redeemed_soon_credit.available_cents == 0
        assert redeemed_soon_credit.credit_status == "used"
        assert redeemed_later_credit.available_cents == 700
        assert redeemed_later_credit.credit_status == "active"


def test_restoring_redeemed_usage_twice_does_not_create_second_movement(
    client: TestClient,
):
    admin = create_user(client)
    player = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game(client, admin["id"], venue)

    authenticate_as(admin["id"])
    credit_response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 1000,
            "credit_reason": "admin_credit",
            "source_game_id": game["id"],
            "idempotency_key": f"restore-duplicate-credit-{uuid4()}",
            "note": "Regression coverage for duplicate restores.",
        },
    )
    assert credit_response.status_code == 201, credit_response.text
    credit = credit_response.json()

    first_booking = create_booking(client, player["id"], game["id"])
    second_booking = create_booking(client, player["id"], game["id"])

    with SessionLocal() as db:
        first_usage = reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=400,
            booking_id=UUID(first_booking["id"]),
            game_id=UUID(game["id"]),
            now=datetime.now(UTC),
            idempotency_scope=f"first-restore-duplicate:{first_booking['id']}",
        )[0]
        redeem_reserved_game_credits(
            db,
            UUID(first_booking["id"]),
            now=datetime.now(UTC),
            user_id=UUID(player["id"]),
        )
        reserve_game_credits(
            db,
            UUID(player["id"]),
            amount_cents=500,
            booking_id=UUID(second_booking["id"]),
            game_id=UUID(game["id"]),
            now=datetime.now(UTC),
            idempotency_scope=f"second-restore-duplicate:{second_booking['id']}",
        )
        redeem_reserved_game_credits(
            db,
            UUID(second_booking["id"]),
            now=datetime.now(UTC),
            user_id=UUID(player["id"]),
        )
        db.commit()

        first_usage = db.get(GameCreditUsage, first_usage.id)
        assert first_usage is not None
        restored_once = restore_redeemed_game_credit_usage(
            db,
            first_usage.id,
            now=datetime.now(UTC),
            restore_reason="first_restore_reason",
        )
        restored_twice = restore_redeemed_game_credit_usage(
            db,
            first_usage.id,
            now=datetime.now(UTC),
            restore_reason="different_restore_reason",
        )
        db.commit()

        restores = db.scalars(
            select(GameCreditUsage).where(
                GameCreditUsage.original_usage_id == first_usage.id,
                GameCreditUsage.usage_type == "restore",
                GameCreditUsage.usage_status == "restored",
            )
        ).all()
        refreshed_credit = db.get(GameCredit, UUID(credit["id"]))

    assert restored_twice.id == restored_once.id
    assert len(restores) == 1
    assert refreshed_credit is not None
    assert refreshed_credit.available_cents == 500


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
            "note": "Minimum charge adjustment.",
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
