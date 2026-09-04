from __future__ import annotations

from typing import get_args

import pytest
from pydantic import ValidationError

from backend.schemas.admin_money_financial_outcome_schema import (
    AdminMoneyFinancialOutcome,
    AdminMoneyFinancialOutcomeCreate,
)
from backend.schemas.admin_official_game_schema import (
    AdminOfficialGameCreate,
    AdminOfficialGameHostAssign,
    AdminOfficialGameHostRemovalExecute,
    AdminOfficialGamePlayerAdd,
    AdminOfficialGamePlayerRemovalExecute,
    AdminOfficialGameUpdate,
    AdminOfficialRemovalOutcome,
)
from backend.schemas.admin_review_schema import (
    AdminReviewCaseAssignment,
    AdminReviewCaseClose,
    AdminReviewCaseMerge,
    AdminReviewCaseNoteCreate,
    AdminReviewCaseReopen,
    AdminReviewClosureOutcome,
)
from backend.schemas.support_flag_schema import (
    SupportFlagResolve,
    SupportResolutionOutcome,
)

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

_PREVIEW_TOKEN = "a" * 64
_REVIEW_CASE_ID = "33333333-3333-4333-8333-333333333333"


def _review_close(**overrides: object) -> AdminReviewCaseClose:
    payload = {
        "outcome": "no_action_needed",
        "reason": "reviewed",
        "expected_case_version": 1,
        "idempotency_key": "review-key",
    }
    payload.update(overrides)
    return AdminReviewCaseClose(**payload)


def _review_note(**overrides: object) -> AdminReviewCaseNoteCreate:
    payload = {
        "body": "review note",
        "expected_case_version": 1,
        "idempotency_key": "review-note-key",
    }
    payload.update(overrides)
    return AdminReviewCaseNoteCreate(**payload)


def _assert_rejected(model_factory, **payload: object) -> None:
    with pytest.raises(ValidationError):
        model_factory(**payload)


def _official_create(**overrides: object) -> AdminOfficialGameCreate:
    payload = {
        "starts_at": "2035-01-15T18:00:00Z",
        "ends_at": "2035-01-15T20:00:00Z",
        "format_label": "5v5",
        "environment_type": "indoor",
        "total_spots": 12,
        "price_per_player_cents": 1200,
    }
    payload.update(overrides)
    return AdminOfficialGameCreate(**payload)


def _host_assign(**overrides: object) -> AdminOfficialGameHostAssign:
    payload = {"host_user_id": "11111111-1111-4111-8111-111111111111"}
    payload.update(overrides)
    return AdminOfficialGameHostAssign(**payload)


def _player_add(**overrides: object) -> AdminOfficialGamePlayerAdd:
    payload = {"user_id": "22222222-2222-4222-8222-222222222222"}
    payload.update(overrides)
    return AdminOfficialGamePlayerAdd(**payload)


def _money_payload(**overrides: object) -> AdminMoneyFinancialOutcomeCreate:
    payload = {
        "outcome": "no_fee_charged",
        "reason": "valid reason",
        "idempotency_key": "a2a-idempotency",
    }
    payload.update(overrides)
    return AdminMoneyFinancialOutcomeCreate(**payload)


@pytest.mark.requirement("WS02-04B2A2A-R4")
def test_admin_official_game_outcome_literals_and_reason_bounds() -> None:
    for outcome in get_args(AdminOfficialRemovalOutcome):
        accepted = AdminOfficialGamePlayerRemovalExecute(
            preview_token=_PREVIEW_TOKEN,
            outcome=outcome,
            reason="approved",
        )
        assert accepted.outcome == outcome

    _assert_rejected(
        AdminOfficialGamePlayerRemovalExecute,
        preview_token=_PREVIEW_TOKEN,
        outcome="invented_outcome",
        reason="approved",
    )

    for factory in (
        _official_create,
        AdminOfficialGameUpdate,
        _host_assign,
        _player_add,
    ):
        assert factory(reason="x" * 1000).reason == "x" * 1000
        _assert_rejected(factory, reason="x" * 1001)

    assert AdminOfficialGameHostRemovalExecute(reason="x" * 1000).reason == "x" * 1000
    _assert_rejected(AdminOfficialGameHostRemovalExecute, reason="")
    _assert_rejected(AdminOfficialGameHostRemovalExecute, reason="x" * 1001)
    _assert_rejected(
        AdminOfficialGamePlayerRemovalExecute,
        preview_token=_PREVIEW_TOKEN,
        outcome="remove_only",
        reason="",
    )


@pytest.mark.requirement("WS02-04B2A2A-R4")
def test_admin_money_literals_reason_note_and_amount_request_bounds() -> None:
    for outcome in get_args(AdminMoneyFinancialOutcome):
        assert _money_payload(outcome=outcome).outcome == outcome

    _assert_rejected(_money_payload, outcome="invented_outcome")
    assert _money_payload(reason="abc").reason == "abc"
    _assert_rejected(_money_payload, reason="ab")
    assert _money_payload(reason="x" * 1000).reason == "x" * 1000
    _assert_rejected(_money_payload, reason="x" * 1001)
    assert _money_payload(internal_note="x" * 1000).internal_note == "x" * 1000
    _assert_rejected(_money_payload, internal_note="x" * 1001)


@pytest.mark.requirement("WS02-04B2A2A-R4")
def test_admin_review_literals_and_text_bounds() -> None:
    for outcome in get_args(AdminReviewClosureOutcome):
        accepted = _review_close(outcome=outcome, reason="x")
        assert accepted.outcome == outcome

    _assert_rejected(_review_close, outcome="invented_outcome")
    assert _review_close(reason="x").reason == "x"
    assert _review_close(reason="x" * 1000).reason == "x" * 1000
    _assert_rejected(_review_close, reason="")
    _assert_rejected(_review_close, reason="x" * 1001)
    _assert_rejected(_review_close, expected_case_version=0)
    _assert_rejected(_review_close, idempotency_key="short")

    assert _review_note(body="x" * 1000).body == "x" * 1000
    _assert_rejected(_review_note, body="x" * 1001)
    _assert_rejected(_review_note, expected_case_version=0)
    _assert_rejected(_review_note, idempotency_key="short")

    for model_factory, version_field in (
        (AdminReviewCaseAssignment, "expected_case_version"),
        (AdminReviewCaseReopen, "expected_case_version"),
    ):
        payload = {
            "reason": "x" * 1000,
            version_field: 1,
            "idempotency_key": "review-action-key",
        }
        assert model_factory(**payload).reason == "x" * 1000
        _assert_rejected(model_factory, **{**payload, "reason": "x" * 1001})
        _assert_rejected(model_factory, **{**payload, version_field: 0})

    merge_payload = {
        "destination_case_id": _REVIEW_CASE_ID,
        "reason": "x" * 1000,
        "expected_source_version": 1,
        "expected_destination_version": 1,
        "idempotency_key": "review-merge-key",
    }
    assert AdminReviewCaseMerge(**merge_payload).reason == "x" * 1000
    _assert_rejected(AdminReviewCaseMerge, **{**merge_payload, "reason": "x" * 1001})
    _assert_rejected(
        AdminReviewCaseMerge,
        **{**merge_payload, "expected_destination_version": 0},
    )
    _assert_rejected(
        AdminReviewCaseMerge,
        **{**merge_payload, "destination_case_id": "not-a-uuid"},
    )


@pytest.mark.requirement("WS02-04B2A2A-R4")
def test_support_resolution_literals_and_reason_bounds() -> None:
    for outcome in get_args(SupportResolutionOutcome):
        accepted = SupportFlagResolve(outcome=outcome, reason="x")
        assert accepted.outcome == outcome

    _assert_rejected(SupportFlagResolve, outcome="invented_outcome", reason="x")
    assert SupportFlagResolve(outcome="no_action_needed", reason="x").reason == "x"
    assert (
        SupportFlagResolve(outcome="no_action_needed", reason="x" * 1000).reason
        == "x" * 1000
    )
    _assert_rejected(SupportFlagResolve, outcome="no_action_needed", reason="")
    _assert_rejected(SupportFlagResolve, outcome="no_action_needed", reason="x" * 1001)
