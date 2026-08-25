from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.models import (
    GameCredit,
    GameCreditUsage,
    GameParticipant,
    Payment,
    Refund,
    RefundEvent,
    WaitlistEntry,
)
import backend.services.database_invariant_policy as invariant_policy

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_REQUIREMENT_IDS = {f"WS04-02B-R{index}" for index in range(1, 10)}


def _source(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text()


def _index_names(model: type[object]) -> set[str]:
    return {index.name for index in model.__table__.indexes if index.name is not None}


def _constraint_names(model: type[object]) -> set[str]:
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if constraint.name is not None
    }


@pytest.mark.requirement("WS04-02B-R1", "WS04-02B-R6", "WS04-02B-R9")
def test_invariant_policy_declares_one_authoritative_disposition_per_invariant() -> None:
    dispositions = invariant_policy.DATABASE_INVARIANT_DISPOSITIONS
    invariant_ids = [
        disposition.invariant_id
        for disposition in dispositions
    ]

    assert invariant_ids == [
        "community_roster_capacity",
        "community_active_participant_identity",
        "waitlist_identity_and_position",
        "waitlist_promotion_capacity_hold",
        "account_deletion_roster_lock_order",
        "official_checkout_and_roster_serialization",
        "payment_identity",
        "refund_identity_and_amount_state",
        "refund_event_identity",
        "host_publish_fee_financial_outcome",
        "game_credit_grant_balance",
        "game_credit_usage_lifecycle",
        "money_issue_operation_identity",
        "admin_support_financial_operation_identity",
        "database_failure_classification",
    ]
    assert len(invariant_ids) == len(set(invariant_ids))

    covered_requirements = {
        requirement_id
        for disposition in dispositions
        for requirement_id in disposition.requirements
    }
    assert covered_requirements == _REQUIREMENT_IDS

    for disposition in dispositions:
        assert disposition.owner
        assert disposition.enforcement
        assert disposition.contention_result
        assert all(requirement_id in _REQUIREMENT_IDS for requirement_id in disposition.requirements)


@pytest.mark.requirement("WS04-02B-R1", "WS04-02B-R5", "WS04-02B-R6")
def test_declared_database_enforcements_exist_on_current_models() -> None:
    participant_indexes = _index_names(GameParticipant)
    waitlist_indexes = _index_names(WaitlistEntry)
    payment_indexes = _index_names(Payment)
    refund_indexes = _index_names(Refund)
    refund_event_indexes = _index_names(RefundEvent)
    credit_constraints = _constraint_names(GameCredit)
    usage_constraints = _constraint_names(GameCreditUsage)
    usage_indexes = _index_names(GameCreditUsage)

    assert "ux_game_participants_active_registered_user_per_game" in participant_indexes
    assert "ux_waitlist_entries_active_user_per_game" in waitlist_indexes
    assert "ux_waitlist_entries_active_position_per_game" in waitlist_indexes
    assert "uq_payments_idempotency_key" in _constraint_names(Payment)
    assert "uq_payments_provider_payment_intent_id" in payment_indexes
    assert "uq_payments_provider_charge_id" in payment_indexes
    assert "uq_refunds_provider_refund_id" in refund_indexes
    assert "uq_refund_events_provider_event_id" in refund_event_indexes
    assert "uq_refund_events_idempotency_key" in refund_event_indexes
    assert "uq_game_credits_idempotency_key" in credit_constraints
    assert "uq_game_credit_usage_idempotency_key" in usage_constraints
    assert "uq_game_credit_usage_one_restore_per_original" in usage_indexes


@pytest.mark.requirement("WS04-02B-R2", "WS04-02B-R3", "WS04-02B-R4")
def test_capacity_mutating_services_use_game_first_locking_and_recompute_after_provider_boundary() -> None:
    roster_source = _source("backend/services/game_roster_service.py")
    waitlist_source = _source("backend/services/game_waitlist_service.py")
    deletion_source = _source("backend/services/account_deletion_service.py")

    assert "def get_locked_game_or_404(" in _source("backend/services/game_service.py")
    assert roster_source.count("get_locked_game_or_404(db, game_id)") >= 5
    assert "db.get(Game, game_id)" not in roster_source

    assert "def promote_waitlist_entries" in waitlist_source
    assert "while True:" in waitlist_source
    assert "restart_after_paid_boundary = True" in waitlist_source
    assert "get_locked_paid_waitlist_auto_promotion_state" in waitlist_source
    assert waitlist_source.count("get_locked_paid_waitlist_auto_promotion_state(") >= 6

    assert "future_roster_game_ids_for_user_deletion" in deletion_source
    assert "lock_future_roster_games_for_account_deletion" in deletion_source
    assert "lock_future_roster_bookings_for_account_deletion" in deletion_source
    assert "for game in locked_games:" in deletion_source
    assert "for game_id in affected_game_ids:" not in deletion_source


@pytest.mark.requirement("WS04-02B-R7", "WS04-02B-R8", "WS04-02B-R9")
def test_policy_and_source_remain_declarative_and_do_not_expand_deferred_scope() -> None:
    policy_source = _source("backend/services/database_invariant_policy.py")
    rendered_policy = repr(invariant_policy.DATABASE_INVARIANT_DISPOSITIONS)
    credit_source = _source("backend/services/game_credit_service.py")
    admin_credit_source = _source("backend/services/game_credit_admin_service.py")

    assert "create_engine" not in policy_source
    assert "create_payment_intent(" not in policy_source
    assert "confirm_payment_intent(" not in policy_source
    assert "DATABASE" + "_URL" not in rendered_policy
    assert "postgresql" + "://" not in rendered_policy
    assert "final production topology" not in rendered_policy.lower()
    assert "WS05 for full payment and provider reconciliation lifecycle" in rendered_policy

    assert "get_ordered_available_credit_grants_for_update" in credit_source
    assert ".with_for_update()" in credit_source
    assert "restore_redeemed_game_credit_usage_record" in credit_source
    assert "existing_restore_for_usage" in credit_source
    assert "reverse_admin_game_credit" in admin_credit_source
    assert "has_reserved_usage_for_credit" in admin_credit_source


@pytest.mark.requirement("WS04-02B-R1", "WS04-02B-R9")
def test_requirement_declaration_matches_frozen_ws04_02b_scope() -> None:
    declaration = json.loads(
        _source("backend/tests/support/requirements/ws04_02b.json")
    )

    requirements = declaration["requirements"]
    assert declaration["schema_version"] == 1
    assert {requirement["id"] for requirement in requirements} == _REQUIREMENT_IDS
    assert {requirement["owning_pass"] for requirement in requirements} == {"WS04-02B"}
    assert {requirement["state"] for requirement in requirements} == {"required"}
    assert {
        requirement["scope"]
        for requirement in requirements
    } == {"workflows/database_invariants_locks_deterministic_concurrency"}
