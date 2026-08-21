from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import pytest

from backend.tests.workflows.admin_route_list_high_risk_function_authorization.test_admin_matrix_scope_and_dependencies_contract import (
    EXPECTED_RECENT_ROUTE_KEYS,
    _add_users,
    _auth_headers,
    _client,
    _count_model_rows,
    _get_user_role,
    _install_tokens_for_users,
    _session,
    _user,
)

pytestmark = pytest.mark.suite_type("ordinary")


@dataclass(frozen=True)
class _StaleRecentAdminCase:
    method: str
    route_template: str
    path: str
    payload: dict[str, Any] | None
    protected_effect: str


def _get_user_admin_state(user_id: uuid.UUID) -> dict[str, object]:
    from backend.models import User

    with _session() as db:
        user = db.get(User, user_id)
        assert user is not None
        return {
            "role": user.role,
            "account_status": user.account_status,
            "hosting_status": user.hosting_status,
            "deleted_at": user.deleted_at,
        }


def _admin_mutation_side_effect_counts() -> dict[str, int]:
    from backend.models import (
        AdminAction,
        AdminFinancialOutcome,
        AdminTargetNotice,
        ChatMessage,
        Game,
        GameCredit,
        GameCreditUsage,
        MoneyIssue,
        MoneyIssueEvent,
        Notification,
        PaymentEvent,
        PlatformNotice,
        Refund,
        RefundEvent,
        SubPost,
        Venue,
    )

    protected_models = (
        AdminAction,
        AdminFinancialOutcome,
        AdminTargetNotice,
        ChatMessage,
        Game,
        GameCredit,
        GameCreditUsage,
        MoneyIssue,
        MoneyIssueEvent,
        Notification,
        PaymentEvent,
        PlatformNotice,
        Refund,
        RefundEvent,
        SubPost,
        Venue,
    )
    return {model.__name__: _count_model_rows(model) for model in protected_models}


def _stale_recent_admin_cases(target_user_id: uuid.UUID) -> list[_StaleRecentAdminCase]:
    route_id = uuid.uuid4()
    preview_token = "p" * 64
    return [
        _StaleRecentAdminCase(
            "POST",
            "/admin/users/{user_id}/delete",
            f"/admin/users/{target_user_id}/delete",
            {
                "preview_token": preview_token,
                "reason": "Stale admin must not delete user accounts.",
                "idempotency_key": f"ws03d-stale-delete-{uuid.uuid4()}",
            },
            "user deletion",
        ),
        _StaleRecentAdminCase(
            "POST",
            "/admin/users/{user_id}/suspend",
            f"/admin/users/{target_user_id}/suspend",
            {
                "preview_token": preview_token,
                "reason": "Stale admin must not suspend accounts.",
                "idempotency_key": f"ws03d-stale-suspend-{uuid.uuid4()}",
            },
            "account suspension",
        ),
        _StaleRecentAdminCase(
            "POST",
            "/admin/users/{user_id}/unsuspend",
            f"/admin/users/{target_user_id}/unsuspend",
            {
                "reason": "Stale admin must not unsuspend accounts.",
                "idempotency_key": f"ws03d-stale-unsuspend-{uuid.uuid4()}",
            },
            "account unsuspension",
        ),
        _StaleRecentAdminCase(
            "POST",
            "/admin/users/{user_id}/restrict-hosting",
            f"/admin/users/{target_user_id}/restrict-hosting",
            {
                "preview_token": preview_token,
                "reason": "Stale admin must not restrict hosting.",
                "idempotency_key": f"ws03d-stale-hosting-restrict-{uuid.uuid4()}",
            },
            "hosting restriction",
        ),
        _StaleRecentAdminCase(
            "POST",
            "/admin/users/{user_id}/restore-hosting",
            f"/admin/users/{target_user_id}/restore-hosting",
            {
                "reason": "Stale admin must not restore hosting.",
                "idempotency_key": f"ws03d-stale-hosting-restore-{uuid.uuid4()}",
            },
            "hosting restoration",
        ),
        _StaleRecentAdminCase(
            "PATCH",
            "/admin/users/{user_id}/role",
            f"/admin/users/{target_user_id}/role",
            {
                "role": "admin",
                "reason": "Stale admin must not alter roles.",
                "idempotency_key": f"ws03d-stale-role-{uuid.uuid4()}",
            },
            "role change",
        ),
        _StaleRecentAdminCase(
            "POST",
            "/admin/community-games/{game_id}/cancel",
            f"/admin/community-games/{route_id}/cancel",
            {
                "reason": "Stale admin must not cancel community games.",
                "idempotency_key": f"ws03d-stale-community-cancel-{uuid.uuid4()}",
            },
            "community-game cancellation",
        ),
        _StaleRecentAdminCase(
            "POST",
            "/admin/official-games/{game_id}/cancel",
            f"/admin/official-games/{route_id}/cancel",
            {"preview_token": preview_token, "reason": "Stale admin cancellation."},
            "official-game cancellation",
        ),
        _StaleRecentAdminCase(
            "POST",
            "/admin/official-games/{game_id}/participants/{participant_id}/remove",
            f"/admin/official-games/{route_id}/participants/{uuid.uuid4()}/remove",
            {
                "preview_token": preview_token,
                "outcome": "remove_only",
                "reason": "Stale admin participant removal.",
            },
            "participant removal",
        ),
        _StaleRecentAdminCase(
            "POST",
            "/admin/need-a-sub/{post_id}/remove",
            f"/admin/need-a-sub/{route_id}/remove",
            {
                "reason": "Stale admin must not remove Need a Sub posts.",
                "idempotency_key": f"ws03d-stale-sub-remove-{uuid.uuid4()}",
            },
            "Need a Sub removal",
        ),
        _StaleRecentAdminCase(
            "POST",
            "/admin/game-credits/issue",
            "/admin/game-credits/issue",
            {
                "user_id": str(target_user_id),
                "amount_cents": 500,
                "credit_reason": "admin_credit",
                "idempotency_key": f"ws03d-stale-credit-issue-{uuid.uuid4()}",
                "note": "Stale admin must not issue credits.",
            },
            "game-credit issue",
        ),
        _StaleRecentAdminCase(
            "POST",
            "/admin/game-credits/{game_credit_id}/reverse",
            f"/admin/game-credits/{route_id}/reverse",
            {
                "idempotency_key": f"ws03d-stale-credit-reverse-{uuid.uuid4()}",
                "note": "Stale admin must not reverse credits.",
            },
            "game-credit reversal",
        ),
        _StaleRecentAdminCase(
            "POST",
            "/admin/money/financial-outcomes",
            "/admin/money/financial-outcomes",
            {
                "outcome": "no_fee_charged",
                "reason": "Stale admin must not create financial outcomes.",
                "idempotency_key": f"ws03d-stale-financial-outcome-{uuid.uuid4()}",
                "host_user_id": str(target_user_id),
                "amount_cents": 0,
            },
            "financial outcome creation",
        ),
        _StaleRecentAdminCase(
            "POST",
            "/admin/money/issues/{money_issue_id}/resolve",
            f"/admin/money/issues/{route_id}/resolve",
            {
                "resolution_reason_code": "handled_externally",
                "resolution_note": "Stale admin must not resolve money issues.",
                "idempotency_key": f"ws03d-stale-money-resolve-{uuid.uuid4()}",
            },
            "money issue resolution",
        ),
        _StaleRecentAdminCase(
            "POST",
            "/admin/money/issues/{money_issue_id}/retry-credit",
            f"/admin/money/issues/{route_id}/retry-credit",
            {
                "reason": "Stale admin must not retry credit repair.",
                "idempotency_key": f"ws03d-stale-money-retry-credit-{uuid.uuid4()}",
            },
            "money issue credit retry",
        ),
        _StaleRecentAdminCase(
            "POST",
            "/admin/money/refunds/{refund_id}/retry",
            f"/admin/money/refunds/{route_id}/retry",
            {
                "reason": "Stale admin must not retry refunds.",
                "idempotency_key": f"ws03d-stale-refund-retry-{uuid.uuid4()}",
            },
            "refund retry",
        ),
        _StaleRecentAdminCase(
            "POST",
            "/admin/money/refunds/{refund_id}/reconcile",
            f"/admin/money/refunds/{route_id}/reconcile",
            {
                "reason": "Stale admin must not reconcile refunds.",
                "idempotency_key": f"ws03d-stale-refund-reconcile-{uuid.uuid4()}",
            },
            "refund reconciliation",
        ),
        _StaleRecentAdminCase(
            "PATCH",
            "/payment-events/{payment_event_id}",
            f"/payment-events/{route_id}",
            {
                "processing_status": "failed",
                "processing_error": "Stale admin must not update provider events.",
            },
            "payment-event update",
        ),
        _StaleRecentAdminCase(
            "POST",
            "/admin/platform-notices",
            "/admin/platform-notices",
            {
                "idempotency_key": f"ws03d-stale-notice-create-{uuid.uuid4()}",
                "title": "Stale notice",
                "message": "This stale admin request must not publish.",
                "audience_type": "selected_users",
                "selected_user_ids": [str(target_user_id)],
            },
            "platform notice creation",
        ),
        _StaleRecentAdminCase(
            "POST",
            "/admin/platform-notices/{notice_id}/cancel",
            f"/admin/platform-notices/{route_id}/cancel",
            {"cancellation_reason": "Stale admin must not cancel notices."},
            "platform notice cancellation",
        ),
        _StaleRecentAdminCase(
            "DELETE",
            "/games/{game_id}",
            f"/games/{route_id}",
            None,
            "game deletion",
        ),
        _StaleRecentAdminCase(
            "DELETE",
            "/venues/{venue_id}",
            f"/venues/{route_id}",
            None,
            "venue deletion",
        ),
    ]


@pytest.mark.requirement("WS03-04D-R2", "WS03-04D-R10")
def test_shared_admin_gate_rejects_missing_invalid_ordinary_unverified_and_inactive_users(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("gate-admin", role="admin")
    ordinary = _user("gate-ordinary")
    unverified_admin = _user("gate-unverified-admin", role="admin", email_verified=False)
    suspended_admin = _user(
        "gate-suspended-admin",
        role="admin",
        account_status="suspended",
    )
    _add_users(admin, ordinary, unverified_admin, suspended_admin)
    _install_tokens_for_users(
        monkeypatch,
        {
            "admin-token": admin,
            "ordinary-token": ordinary,
            "unverified-admin-token": unverified_admin,
            "suspended-admin-token": suspended_admin,
        },
        unverified_tokens={"unverified-admin-token"},
    )

    client = _client()

    assert client.get("/admin/me").status_code == 401
    assert client.get("/admin/me", headers=_auth_headers("invalid-token")).status_code == 401
    assert client.get(
        "/admin/me",
        headers=_auth_headers("ordinary-token"),
    ).status_code == 403
    assert client.get(
        "/admin/me",
        headers=_auth_headers("unverified-admin-token"),
    ).status_code == 403
    assert client.get(
        "/admin/me",
        headers=_auth_headers("suspended-admin-token"),
    ).status_code == 403

    response = client.get("/admin/me", headers=_auth_headers("admin-token"))
    assert response.status_code == 200
    assert response.json()["user_id"] == str(admin.id)


@pytest.mark.requirement("WS03-04D-R3", "WS03-04D-R5", "WS03-04D-R10")
def test_stale_admin_recent_auth_denial_does_not_change_target_role_or_audit_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import AdminAction

    admin = _user("stale-role-admin", role="admin")
    target = _user("stale-role-target")
    _add_users(admin, target)
    _install_tokens_for_users(
        monkeypatch,
        {"stale-admin-token": admin},
        stale_tokens={"stale-admin-token"},
    )

    before_admin_actions = _count_model_rows(AdminAction)

    response = _client().patch(
        f"/admin/users/{target.id}/role",
        json={
            "role": "admin",
            "reason": "Recent admin authentication is required.",
            "idempotency_key": f"ws03d-stale-role-{uuid.uuid4()}",
        },
        headers=_auth_headers("stale-admin-token"),
    )

    assert response.status_code == 403
    assert _get_user_role(target.id) == "player"
    assert _count_model_rows(AdminAction) == before_admin_actions


@pytest.mark.requirement(
    "WS03-04D-R3",
    "WS03-04D-R5",
    "WS03-04D-R6",
    "WS03-04D-R7",
    "WS03-04D-R8",
    "WS03-04D-R10",
)
def test_every_recent_admin_high_risk_class_rejects_stale_auth_before_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _user("stale-matrix-admin", role="admin")
    target = _user("stale-matrix-target")
    _add_users(admin, target)
    _install_tokens_for_users(
        monkeypatch,
        {"stale-admin-token": admin},
        stale_tokens={"stale-admin-token"},
    )

    client = _client()
    cases = _stale_recent_admin_cases(target.id)
    assert {(case.method, case.route_template) for case in cases} == (
        EXPECTED_RECENT_ROUTE_KEYS
    )

    before_counts = _admin_mutation_side_effect_counts()
    before_target_state = _get_user_admin_state(target.id)

    for case in cases:
        request = getattr(client, case.method.lower())
        kwargs: dict[str, Any] = {"headers": _auth_headers("stale-admin-token")}
        if case.payload is not None:
            kwargs["json"] = case.payload
        response = request(case.path, **kwargs)
        assert response.status_code == 403, case.protected_effect
        assert _admin_mutation_side_effect_counts() == before_counts, (
            case.protected_effect
        )
        assert _get_user_admin_state(target.id) == before_target_state, (
            case.protected_effect
        )
