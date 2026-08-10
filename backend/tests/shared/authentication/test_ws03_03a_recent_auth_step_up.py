from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import pytest

from backend.database import SessionLocal, get_db
from backend.main import app as main_app
from backend.models import User, UserPaymentMethod
from backend.services.auth_service import (
    RECENT_AUTH_REQUIRED_CODE,
    VerifiedFirebaseIdentity,
    get_verified_firebase_identity,
    is_recent_authentication,
    parse_provider_authenticated_at,
    require_active_user,
    require_recent_active_admin,
    require_recent_active_user,
)
from backend.services.recent_auth_policy import RECENT_AUTH_PROTECTED_ACTIONS
from backend.settings import DEFAULT_RECENT_AUTHENTICATION_WINDOW_SECONDS
from backend.tests.support.factories import create_user, unique_suffix


WINDOW = timedelta(seconds=DEFAULT_RECENT_AUTHENTICATION_WINDOW_SECONDS)
NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)


def _identity(user: dict, authenticated_at: datetime | None) -> VerifiedFirebaseIdentity:
    return VerifiedFirebaseIdentity(
        auth_user_id=user["auth_user_id"],
        email=user["email"],
        email_verified=True,
        authenticated_at=authenticated_at,
    )


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _stub_firebase_tokens(
    monkeypatch: pytest.MonkeyPatch,
    token_payloads: dict[str, dict],
) -> None:
    def verify_firebase_token(id_token: str) -> dict:
        payload = token_payloads.get(id_token)
        if payload is None:
            raise ValueError("Invalid token")
        return payload

    monkeypatch.setattr(
        "backend.services.auth_service.verify_firebase_token",
        verify_firebase_token,
    )


def _build_probe_client(dependency) -> TestClient:
    app = FastAPI()

    @app.get("/probe")
    def probe(current_user: User = Depends(dependency)):
        return {"id": str(current_user.id)}

    def override_db():
        with SessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def _set_user_role(user_id: str, role: str) -> None:
    with SessionLocal() as db:
        user = db.get(User, UUID(user_id))
        assert user is not None
        user.role = role
        db.commit()


def _set_user_account_status(user_id: str, account_status: str) -> None:
    with SessionLocal() as db:
        user = db.get(User, UUID(user_id))
        assert user is not None
        user.account_status = account_status
        db.commit()


def _user_role(user_id: str) -> str:
    with SessionLocal() as db:
        user = db.get(User, UUID(user_id))
        assert user is not None
        return user.role


def _user_account_status(user_id: str) -> str:
    with SessionLocal() as db:
        user = db.get(User, UUID(user_id))
        assert user is not None
        return user.account_status


def _create_payment_method(
    user_id: str,
    *,
    is_default: bool,
) -> str:
    suffix = unique_suffix()
    payment_method_id = uuid4()
    stripe_customer_id = f"cus_{suffix}"

    with SessionLocal() as db:
        user = db.get(User, UUID(user_id))
        assert user is not None
        user.stripe_customer_id = stripe_customer_id
        payment_method = UserPaymentMethod(
            id=payment_method_id,
            user_id=UUID(user_id),
            stripe_customer_id=stripe_customer_id,
            stripe_payment_method_id=f"pm_{suffix}",
            card_fingerprint=f"fp_{suffix}",
            card_brand="visa",
            card_last4="4242",
            exp_month=12,
            exp_year=2030,
            method_status="active",
            is_default=is_default,
            detached_at=None,
            updated_at=NOW,
        )
        db.add(user)
        db.add(payment_method)
        db.commit()

    return str(payment_method_id)


def _payment_method_state(payment_method_id: str) -> tuple[bool, str]:
    with SessionLocal() as db:
        payment_method = db.get(UserPaymentMethod, UUID(payment_method_id))
        assert payment_method is not None
        return payment_method.is_default, payment_method.method_status


def _override_identity(client: TestClient, identity: VerifiedFirebaseIdentity) -> None:
    client.app.dependency_overrides[get_verified_firebase_identity] = lambda: identity


def _direct_route_dependencies(method: str, path: str) -> list[object]:
    for route in main_app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return [dependency.call for dependency in route.dependant.dependencies]
    raise AssertionError(f"Route {method} {path} was not found.")


def test_recent_authentication_accepts_fresh_boundary_and_rejects_stale() -> None:
    cases = [
        (NOW, True),
        (NOW - WINDOW + timedelta(seconds=1), True),
        (NOW - WINDOW, True),
        (NOW - WINDOW - timedelta(microseconds=1), False),
        (NOW + timedelta(microseconds=1), False),
        (None, False),
    ]

    for authenticated_at, expected in cases:
        identity = VerifiedFirebaseIdentity(
            auth_user_id="firebase-user",
            email="user@example.com",
            email_verified=True,
            authenticated_at=authenticated_at,
        )

        assert is_recent_authentication(identity, now=NOW, window=WINDOW) is expected


@pytest.mark.parametrize(
    "claim",
    [
        {},
        {"auth_time": "recent"},
        {"auth_time": True},
        {"auth_time": -1},
        {"auth_time": float("nan")},
        {"auth_time": 10**20},
    ],
)
def test_provider_auth_time_missing_or_malformed_is_unusable(claim: dict) -> None:
    assert parse_provider_authenticated_at(claim) is None


def test_token_refresh_timestamp_does_not_make_old_auth_time_recent() -> None:
    old_auth_time = int((NOW - WINDOW - timedelta(seconds=1)).timestamp())
    refreshed_token_claims = {
        "auth_time": old_auth_time,
        "iat": int(NOW.timestamp()),
        "uid": "firebase-user",
    }
    authenticated_at = parse_provider_authenticated_at(refreshed_token_claims)
    identity = VerifiedFirebaseIdentity(
        auth_user_id="firebase-user",
        email="user@example.com",
        email_verified=True,
        authenticated_at=authenticated_at,
    )

    assert authenticated_at == datetime.fromtimestamp(old_auth_time, tz=UTC)
    assert is_recent_authentication(identity, now=NOW, window=WINDOW) is False


def test_recent_active_user_dependency_uses_verified_auth_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = create_user()
    fresh_auth_time = int((datetime.now(UTC) - timedelta(seconds=20)).timestamp())
    stale_auth_time = int((datetime.now(UTC) - WINDOW - timedelta(seconds=20)).timestamp())
    _stub_firebase_tokens(
        monkeypatch,
        {
            "fresh-token": {
                "uid": user["auth_user_id"],
                "email": user["email"],
                "email_verified": True,
                "auth_time": fresh_auth_time,
            },
            "stale-token": {
                "uid": user["auth_user_id"],
                "email": user["email"],
                "email_verified": True,
                "auth_time": stale_auth_time,
            },
        },
    )
    recent_client = _build_probe_client(require_recent_active_user)
    ordinary_client = _build_probe_client(require_active_user)

    assert (
        recent_client.get("/probe", headers=_auth_headers("fresh-token")).status_code
        == 200
    )
    assert (
        recent_client.get("/probe", headers=_auth_headers("stale-token")).status_code
        == 403
    )
    assert (
        ordinary_client.get("/probe", headers=_auth_headers("stale-token")).status_code
        == 200
    )


def test_stale_recent_auth_public_error_blocks_admin_role_side_effect(
    client: TestClient,
) -> None:
    admin = create_user()
    target = create_user()
    _set_user_role(admin["id"], "admin")
    stale_identity = _identity(admin, datetime.now(UTC) - WINDOW - timedelta(seconds=5))
    _override_identity(client, stale_identity)

    response = client.patch(
        f"/admin/users/{target['id']}/role",
        json={
            "role": "admin",
            "reason": "WS03-03A stale recent-auth test",
            "idempotency_key": "admin-role-stale-test",
        },
    )

    body = response.json()
    assert response.status_code == 403, response.text
    assert body["code"] == RECENT_AUTH_REQUIRED_CODE
    assert body["detail"]["code"] == RECENT_AUTH_REQUIRED_CODE
    assert "auth_time" not in str(body)
    assert _user_role(target["id"]) == "player"


def test_fresh_recent_auth_allows_admin_role_mutation(client: TestClient) -> None:
    admin = create_user()
    target = create_user()
    _set_user_role(admin["id"], "admin")
    _override_identity(client, _identity(admin, datetime.now(UTC) - timedelta(seconds=5)))

    response = client.patch(
        f"/admin/users/{target['id']}/role",
        json={
            "role": "admin",
            "reason": "WS03-03A fresh recent-auth test",
            "idempotency_key": "admin-role-fresh-test",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["role"] == "admin"
    assert _user_role(target["id"]) == "admin"


def test_stale_recent_auth_blocks_account_lifecycle_and_saved_card_mutations(
    client: TestClient,
) -> None:
    admin = create_user()
    current_user = create_user()
    target = create_user()
    suspended_target = create_user()
    _set_user_role(admin["id"], "admin")
    _set_user_account_status(suspended_target["id"], "suspended")
    default_payment_method_id = _create_payment_method(current_user["id"], is_default=True)
    next_payment_method_id = _create_payment_method(current_user["id"], is_default=False)
    stale_admin_identity = _identity(
        admin,
        datetime.now(UTC) - WINDOW - timedelta(seconds=5),
    )
    stale_user_identity = _identity(
        current_user,
        datetime.now(UTC) - WINDOW - timedelta(seconds=5),
    )

    _override_identity(client, stale_user_identity)
    assert client.request(
        "DELETE",
        "/auth/account",
        json={"confirmation": "DELETE"},
    ).status_code == 403
    assert _user_account_status(current_user["id"]) == "active"

    assert client.patch(
        f"/user-payment-methods/{next_payment_method_id}/default",
    ).status_code == 403
    assert _payment_method_state(default_payment_method_id) == (True, "active")
    assert _payment_method_state(next_payment_method_id) == (False, "active")

    assert client.delete(
        f"/user-payment-methods/{default_payment_method_id}",
    ).status_code == 403
    assert _payment_method_state(default_payment_method_id) == (True, "active")

    _override_identity(client, stale_admin_identity)
    assert client.post(
        f"/admin/users/{target['id']}/suspend",
        json={
            "preview_token": "a" * 64,
            "reason": "WS03-03A stale suspension test",
            "idempotency_key": "admin-suspend-stale-test",
        },
    ).status_code == 403
    assert _user_account_status(target["id"]) == "active"

    assert client.post(
        f"/admin/users/{target['id']}/delete",
        json={
            "preview_token": "b" * 64,
            "reason": "WS03-03A stale delete test",
            "idempotency_key": "admin-delete-stale-test",
        },
    ).status_code == 403
    assert _user_account_status(target["id"]) == "active"

    assert client.post(
        f"/admin/users/{suspended_target['id']}/unsuspend",
        json={
            "reason": "WS03-03A stale unsuspend test",
            "idempotency_key": "admin-unsuspend-stale-test",
        },
    ).status_code == 403
    assert _user_account_status(suspended_target["id"]) == "suspended"


def test_high_risk_route_registry_matches_recent_auth_dependencies() -> None:
    action_ids = {action.action_id for action in RECENT_AUTH_PROTECTED_ACTIONS}
    assert action_ids == {
        "admin_financial_outcome_create",
        "admin_game_credit_issue",
        "admin_game_credit_reverse",
        "admin_money_issue_resolve",
        "admin_money_issue_retry_credit",
        "admin_refund_reconcile",
        "admin_refund_retry",
        "admin_user_delete",
        "admin_user_role_change",
        "admin_user_suspend",
        "admin_user_unsuspend",
        "official_game_cancel_execute",
        "platform_notice_cancel",
        "platform_notice_create",
        "saved_payment_method_default_change",
        "saved_payment_method_detach",
        "self_account_delete",
    }
    route_keys = [
        (action.method, action.route_template) for action in RECENT_AUTH_PROTECTED_ACTIONS
    ]
    assert len(route_keys) == len(set(route_keys))

    for action in RECENT_AUTH_PROTECTED_ACTIONS:
        dependencies = _direct_route_dependencies(action.method, action.route_template)
        dependency_names = {dependency.__name__ for dependency in dependencies}
        assert action.enforcement_dependency in dependency_names


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/games/{game_id}"),
        ("POST", "/checkout/games/{game_id}/payment-intent"),
        ("POST", "/user-payment-methods/setup-intent"),
        ("POST", "/user-payment-methods/sync"),
        ("GET", "/admin/platform-notices"),
        ("POST", "/admin/official-games/{game_id}/cancel-preview"),
    ],
)
def test_ordinary_and_preview_routes_are_not_recent_auth_gated(
    method: str,
    path: str,
) -> None:
    dependencies = _direct_route_dependencies(method, path)

    assert require_recent_active_user not in dependencies
    assert require_recent_active_admin not in dependencies
