from __future__ import annotations

import ast
import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache, partial
from inspect import isfunction, ismethod
from pathlib import Path
from typing import Any

import pytest
from fastapi.routing import APIRoute
from sqlalchemy import func, select
from sqlalchemy.orm import Session

pytestmark = pytest.mark.suite_type("ordinary")

REPO_ROOT = Path(__file__).resolve().parents[4]
MATRIX_PATH = (
    REPO_ROOT
    / "backend/tests/workflows/authorization_matrix_foundation/authorization_matrix.json"
)
REQUIREMENTS_PATH = REPO_ROOT / "backend/tests/support/requirements/ws03_04b.json"
AUTH_PREFIX = "backend.services.auth_service:"
EXCLUDED_METHODS = {"HEAD", "OPTIONS"}
REQUIREMENT_IDS = {f"WS03-04B-R{number}" for number in range(1, 11)}
REQUIRED_REQUIREMENT_IDS = {f"WS03-04B-R{number}" for number in range(1, 10)}
DEFERRED_REQUIREMENT_ID = "WS03-04B-R10"
EXPECTED_B_ROUTE_KEYS = {
    ("DELETE", "/auth/account"),
    ("GET", "/auth/me"),
    ("GET", "/users/me"),
    ("PATCH", "/users/me"),
    ("GET", "/user-settings/me"),
    ("PATCH", "/user-settings/me"),
    ("GET", "/user-stats/me"),
    ("GET", "/notifications/me"),
    ("GET", "/notifications/{notification_id}"),
    ("PATCH", "/notifications/{notification_id}/read"),
    ("GET", "/inbox/app-updates"),
    ("PUT", "/inbox/app-updates/global-seen"),
    ("PUT", "/inbox/app-updates/platform-notices/{notice_id}/read"),
    ("GET", "/inbox/counts"),
    ("GET", "/inbox/game-activity"),
    ("GET", "/user-payment-methods"),
    ("POST", "/user-payment-methods/setup-intent"),
    ("POST", "/user-payment-methods/sync"),
    ("GET", "/user-payment-methods/{payment_method_id}"),
    ("PATCH", "/user-payment-methods/{payment_method_id}/default"),
    ("DELETE", "/user-payment-methods/{payment_method_id}"),
    ("GET", "/game-credits"),
    ("GET", "/game-credits/balance"),
    ("GET", "/payments"),
    ("GET", "/payments/{payment_id}"),
    ("GET", "/refunds"),
    ("GET", "/refunds/{refund_id}"),
    ("GET", "/host-publish-fees/me"),
}


@dataclass
class _StripeFake:
    setup_intent_customer_id: str
    payment_method_customer_id: str
    setup_intents: list[dict[str, object]]
    retrieved_setup_intents: list[str]
    retrieved_payment_methods: list[str]
    default_payment_methods: list[str]
    detached_payment_methods: list[str]
    cleared_customers: list[str]


@dataclass(frozen=True)
class _Identity:
    auth_user_id: str
    email: str
    email_verified: bool
    authenticated_at: datetime | None


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _auth_headers(token: str = "valid-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _recent_time() -> datetime:
    return datetime.now(timezone.utc) - timedelta(seconds=30)


def _stale_time() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=2)


def _install_auth_identities(
    monkeypatch: pytest.MonkeyPatch,
    identities: dict[str, _Identity],
) -> None:
    from backend.services import auth_service

    def verify_token(id_token: str) -> dict[str, object]:
        if id_token not in identities:
            raise ValueError("synthetic invalid token")

        identity = identities[id_token]
        payload: dict[str, object] = {
            "uid": identity.auth_user_id,
            "email": identity.email,
            "email_verified": identity.email_verified,
        }
        if identity.authenticated_at is not None:
            payload["auth_time"] = int(identity.authenticated_at.timestamp())
        return payload

    monkeypatch.setattr(auth_service, "verify_firebase_token", verify_token)


def _install_stripe_fake(
    monkeypatch: pytest.MonkeyPatch,
    *,
    setup_customer_id: str,
    payment_method_customer_id: str | None = None,
) -> _StripeFake:
    from backend.services import payment_method_service
    from backend.services.stripe_service import (
        StripeCustomerResult,
        StripePaymentMethodCardResult,
        StripeSetupIntentResult,
    )

    fake = _StripeFake(
        setup_intent_customer_id=setup_customer_id,
        payment_method_customer_id=payment_method_customer_id or setup_customer_id,
        setup_intents=[],
        retrieved_setup_intents=[],
        retrieved_payment_methods=[],
        default_payment_methods=[],
        detached_payment_methods=[],
        cleared_customers=[],
    )

    def create_customer(**kwargs: object) -> StripeCustomerResult:
        del kwargs
        return StripeCustomerResult(id=setup_customer_id)

    def create_setup_intent(**kwargs: object) -> StripeSetupIntentResult:
        fake.setup_intents.append(dict(kwargs))
        return StripeSetupIntentResult(
            id="seti_ws03_04b_setup",
            client_secret="seti_secret_ws03_04b",
            status="requires_payment_method",
            customer_id=str(kwargs["customer_id"]),
            payment_method_id=None,
        )

    def retrieve_setup_intent(setup_intent_id: str) -> StripeSetupIntentResult:
        fake.retrieved_setup_intents.append(setup_intent_id)
        return StripeSetupIntentResult(
            id=setup_intent_id,
            client_secret=None,
            status="succeeded",
            customer_id=fake.setup_intent_customer_id,
            payment_method_id="pm_ws03_04b_synced",
        )

    def retrieve_payment_method(payment_method_id: str) -> StripePaymentMethodCardResult:
        fake.retrieved_payment_methods.append(payment_method_id)
        return StripePaymentMethodCardResult(
            id=payment_method_id,
            customer_id=fake.payment_method_customer_id,
            card_fingerprint="ws03-04b-synced-fingerprint",
            card_brand="visa",
            card_last4="4242",
            exp_month=12,
            exp_year=2036,
        )

    def set_customer_default_payment_method(
        *,
        customer_id: str,
        payment_method_id: str,
    ) -> None:
        del customer_id
        fake.default_payment_methods.append(payment_method_id)

    def detach_payment_method(payment_method_id: str) -> None:
        fake.detached_payment_methods.append(payment_method_id)

    def clear_customer_default_payment_method(*, customer_id: str) -> None:
        fake.cleared_customers.append(customer_id)

    monkeypatch.setattr(payment_method_service, "stripe_payments_enabled", lambda: True)
    monkeypatch.setattr(payment_method_service, "create_customer", create_customer)
    monkeypatch.setattr(payment_method_service, "create_setup_intent", create_setup_intent)
    monkeypatch.setattr(payment_method_service, "retrieve_setup_intent", retrieve_setup_intent)
    monkeypatch.setattr(payment_method_service, "retrieve_payment_method", retrieve_payment_method)
    monkeypatch.setattr(
        payment_method_service,
        "set_customer_default_payment_method",
        set_customer_default_payment_method,
    )
    monkeypatch.setattr(payment_method_service, "detach_payment_method", detach_payment_method)
    monkeypatch.setattr(
        payment_method_service,
        "clear_customer_default_payment_method",
        clear_customer_default_payment_method,
    )
    return fake


def _callable_identity(callable_obj: Any) -> str:
    if isinstance(callable_obj, partial):
        raise AssertionError(f"Unrepresentable partial dependency: {callable_obj!r}")
    if not (isfunction(callable_obj) or ismethod(callable_obj)):
        raise AssertionError(f"Unrepresentable callable dependency: {callable_obj!r}")

    module = getattr(callable_obj, "__module__", None)
    qualname = getattr(callable_obj, "__qualname__", None)
    if not module or not qualname or "<locals>" in qualname or qualname == "<lambda>":
        raise AssertionError(f"Unstable dependency identity: {callable_obj!r}")

    identity = f"{module}:{qualname}"
    wrapped_seen: set[int] = set()
    wrapped_parts: list[str] = []
    wrapped = getattr(callable_obj, "__wrapped__", None)
    while wrapped is not None:
        if id(wrapped) in wrapped_seen:
            raise AssertionError(f"Wrapper cycle in dependency identity: {callable_obj!r}")
        wrapped_seen.add(id(wrapped))
        wrapped_module = getattr(wrapped, "__module__", None)
        wrapped_qualname = getattr(wrapped, "__qualname__", None)
        if not wrapped_module or not wrapped_qualname or "<locals>" in wrapped_qualname:
            raise AssertionError(f"Unstable wrapped dependency identity: {wrapped!r}")
        wrapped_parts.append(f"{wrapped_module}:{wrapped_qualname}")
        wrapped = getattr(wrapped, "__wrapped__", None)

    if wrapped_parts:
        return f"{identity}[wrapped={'|'.join(wrapped_parts)}]"
    return identity


def _walk_dependency_calls(dependant: Any) -> list[Any]:
    calls: list[Any] = []
    for dependency in dependant.dependencies:
        if dependency.call is not None:
            calls.append(dependency.call)
        calls.extend(_walk_dependency_calls(dependency))
    return calls


def _auth_dependencies(route: APIRoute) -> list[str]:
    identities: dict[str, int] = {}
    for call in _walk_dependency_calls(route.dependant):
        identity = _callable_identity(call)
        if identity.startswith(AUTH_PREFIX):
            previous_id = identities.setdefault(identity, id(call))
            assert previous_id == id(call), f"auth dependency identity collision: {identity}"
    return sorted(identities)


@lru_cache(maxsize=1)
def _matrix() -> dict[str, Any]:
    with MATRIX_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _requirement_declarations() -> dict[str, dict[str, Any]]:
    with REQUIREMENTS_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    assert payload["schema_version"] == 1
    return {entry["id"]: entry for entry in payload["requirements"]}


@lru_cache(maxsize=1)
def _current_route_map() -> dict[tuple[str, str], APIRoute]:
    from backend.main import app

    routes: dict[tuple[str, str], APIRoute] = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in sorted(route.methods - EXCLUDED_METHODS):
            key = (method, route.path_format)
            assert key not in routes, f"duplicate current route key: {key}"
            routes[key] = route
    return routes


def _flatten_matrix_routes() -> dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]]:
    routes: dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]] = {}
    for family in _matrix()["route_families"]:
        for route in family["routes"]:
            key = (route["method"], route["path"])
            assert key not in routes, f"duplicate matrix route key: {key}"
            routes[key] = (family, route)
    return routes


def _collect_requirement_marker_ids() -> set[str]:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    marker_ids: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "requirement":
            continue
        value = node.func.value
        if not (
            isinstance(value, ast.Attribute)
            and value.attr == "mark"
            and isinstance(value.value, ast.Name)
            and value.value.id == "pytest"
        ):
            continue
        marker_ids.update(
            arg.value
            for arg in node.args
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
        )
    return marker_ids


def _user(
    index: int,
    *,
    account_status: str = "active",
    role: str = "player",
    stripe_customer_id: str | None = None,
    email_verified_at: datetime | None = None,
) -> Any:
    from backend.models import User

    unique = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"firebase-ws03-04b-{index}-{unique}",
        role=role,
        email=f"ws03-04b-{index}-{unique}@example.invalid",
        email_verified_at=email_verified_at,
        first_name=f"WS03B{index}",
        last_name="User",
        account_status=account_status,
        hosting_status="eligible",
        stripe_customer_id=stripe_customer_id,
    )


def _settings(user_id: uuid.UUID) -> Any:
    from backend.models import UserSettings

    return UserSettings(
        user_id=user_id,
        push_notifications_enabled=False,
        email_notifications_enabled=False,
        sms_notifications_enabled=False,
        marketing_opt_in=False,
        location_permission_status="unknown",
    )


def _stats(user_id: uuid.UUID) -> Any:
    from backend.models import UserStats

    return UserStats(
        user_id=user_id,
        games_played_count=4,
        games_hosted_completed_count=1,
        no_show_count=0,
        late_cancel_count=0,
        host_cancel_count=0,
    )


def _notification(
    user_id: uuid.UUID,
    index: int,
    *,
    category: str = "app",
    is_read: bool = False,
) -> Any:
    from backend.models import Notification

    now = datetime.now(timezone.utc)
    if category == "app":
        notification_type = "account_security"
        notification_domain = "account"
        source_type = "account"
    else:
        notification_type = "game_updated"
        notification_domain = "game"
        source_type = "game"

    return Notification(
        id=uuid.uuid4(),
        user_id=user_id,
        notification_type=notification_type,
        notification_category=category,
        notification_domain=notification_domain,
        source_type=source_type,
        title=f"Notification {index}",
        subject_label=f"Subject {index}",
        summary=f"Summary {index}",
        body=f"Body {index}",
        event_at=now,
        is_read=is_read,
        read_at=now if is_read else None,
    )


def _platform_notice(index: int, *, audience_type: str, global_sequence: int | None) -> Any:
    from backend.models import PlatformNotice

    now = datetime.now(timezone.utc)
    return PlatformNotice(
        id=uuid.uuid4(),
        title=f"Platform notice {index}",
        message=f"Message {index}",
        audience_type=audience_type,
        global_sequence=global_sequence,
        published_at=now - timedelta(minutes=5),
        idempotency_key_hash=f"{uuid.uuid4().hex}{uuid.uuid4().hex}",
        request_fingerprint=f"{uuid.uuid4().hex}{uuid.uuid4().hex}",
    )


def _global_seen_state(user_id: uuid.UUID, sequence: int) -> Any:
    from backend.models import PlatformNoticeGlobalSeenState

    now = datetime.now(timezone.utc)
    return PlatformNoticeGlobalSeenState(
        user_id=user_id,
        last_seen_global_sequence=sequence,
        created_at=now,
        updated_at=now,
    )


def _payment_method(
    user_id: uuid.UUID,
    customer_id: str,
    index: int,
    *,
    is_default: bool = False,
) -> Any:
    from backend.models import UserPaymentMethod

    return UserPaymentMethod(
        id=uuid.uuid4(),
        user_id=user_id,
        stripe_customer_id=customer_id,
        stripe_payment_method_id=f"pm_ws03_04b_{index}_{uuid.uuid4().hex}",
        card_fingerprint=f"ws03-04b-fingerprint-{index}-{uuid.uuid4()}",
        card_brand="visa",
        card_last4=f"{index:04d}"[-4:],
        exp_month=12,
        exp_year=2036,
        method_status="active",
        is_default=is_default,
    )


def _venue(created_by_user_id: uuid.UUID, index: int) -> Any:
    from backend.models import Venue

    return Venue(
        id=uuid.uuid4(),
        name=f"WS03B Venue {index}",
        address_line_1=f"{index} Test Ave",
        city="Chicago",
        state="IL",
        postal_code="60601",
        country_code="US",
        venue_status="approved",
        created_by_user_id=created_by_user_id,
        approved_by_user_id=created_by_user_id,
        approved_at=datetime.now(timezone.utc),
        is_active=True,
    )


def _community_game(
    *,
    user_id: uuid.UUID,
    venue_id: uuid.UUID,
    index: int,
) -> Any:
    from backend.models import Game

    starts_at = datetime.now(timezone.utc) + timedelta(days=30 + index)
    ends_at = starts_at + timedelta(hours=1)
    return Game(
        id=uuid.uuid4(),
        game_type="community",
        payment_collection_type="none",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title=f"WS03B Community Game {index}",
        venue_id=venue_id,
        venue_name_snapshot=f"WS03B Venue {index}",
        address_snapshot=f"{index} Test Ave",
        city_snapshot="Chicago",
        state_snapshot="IL",
        host_user_id=user_id,
        created_by_user_id=user_id,
        starts_at=starts_at,
        ends_at=ends_at,
        starts_on_local=date.fromisoformat(starts_at.date().isoformat()),
        timezone="America/Chicago",
        sport_type="soccer",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="outdoor",
        total_spots=10,
        price_per_player_cents=0,
        minimum_age=None,
        allow_guests=True,
        max_guests_per_booking=2,
        host_guest_max=0,
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="custom_hosted",
        published_at=datetime.now(timezone.utc),
    )


def _payment(
    *,
    user_id: uuid.UUID,
    game_id: uuid.UUID,
    index: int,
) -> Any:
    from backend.models import Payment

    now = datetime.now(timezone.utc)
    return Payment(
        id=uuid.uuid4(),
        payer_user_id=user_id,
        game_id=game_id,
        payment_type="community_publish_fee",
        provider="stripe",
        provider_payment_intent_id=f"pi_ws03_04b_{index}_{uuid.uuid4().hex}",
        provider_charge_id=f"ch_ws03_04b_{index}_{uuid.uuid4().hex}",
        idempotency_key=f"ws03-04b-payment-{index}-{uuid.uuid4()}",
        amount_cents=1200,
        currency="USD",
        payment_status="succeeded",
        paid_at=now,
    )


def _host_publish_fee(
    *,
    user_id: uuid.UUID,
    game_id: uuid.UUID,
    payment_id: uuid.UUID,
    index: int,
) -> Any:
    from backend.models import HostPublishFee

    return HostPublishFee(
        id=uuid.uuid4(),
        game_id=game_id,
        host_user_id=user_id,
        payment_id=payment_id,
        amount_cents=1200,
        currency="USD",
        fee_status="paid",
        waiver_reason="none",
        paid_at=datetime.now(timezone.utc),
    )


def _refund(
    *,
    payment_id: uuid.UUID,
    host_publish_fee_id: uuid.UUID,
    requested_by_user_id: uuid.UUID,
    index: int,
) -> Any:
    from backend.models import Refund

    return Refund(
        id=uuid.uuid4(),
        payment_id=payment_id,
        host_publish_fee_id=host_publish_fee_id,
        provider_refund_id=f"re_ws03_04b_{index}_{uuid.uuid4().hex}",
        origin_workflow="community_publish_fee_refund",
        provider="stripe",
        provider_status="processing",
        provider_status_observed_at=datetime.now(timezone.utc),
        provider_charge_id=f"ch_ref_ws03_04b_{index}_{uuid.uuid4().hex}",
        amount_cents=1200,
        currency="USD",
        refund_reason="publish_fee_refund",
        refund_status="pending",
        requested_by_user_id=requested_by_user_id,
    )


def _game_credit(user_id: uuid.UUID, index: int) -> Any:
    from backend.models import GameCredit

    return GameCredit(
        id=uuid.uuid4(),
        user_id=user_id,
        amount_cents=700,
        available_cents=700,
        currency="USD",
        credit_status="active",
        credit_reason="admin_credit",
        idempotency_key=f"ws03-04b-credit-{index}-{uuid.uuid4()}",
    )


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS03-04B-R1", "WS03-04B-R3", "WS03-04B-R9")
def test_matrix_scope_guard_and_requirement_traceability_match_b_boundary() -> None:
    matrix_routes = _flatten_matrix_routes()
    b_routes = {
        key: route
        for key, (family, route) in matrix_routes.items()
        if family["primary_child_owner"] == "WS03-04B"
    }
    b_families = [
        family
        for family in _matrix()["route_families"]
        if family["primary_child_owner"] == "WS03-04B"
    ]

    assert len(b_families) == 11
    assert set(b_routes) == EXPECTED_B_ROUTE_KEYS
    assert len(b_routes) == 28
    assert set(b_routes) <= set(_current_route_map())

    for key, route_entry in b_routes.items():
        family, _route = matrix_routes[key]
        assert family["primary_child_owner"] == "WS03-04B"
        assert route_entry["child_owner"] == "WS03-04B"
        assert route_entry["route_disposition"] == "protected"
        assert route_entry["child_owner"] != "blocked"
        assert "require_verified_user" not in json.dumps(route_entry["auth_dependencies"])
        assert "require_active_admin" not in json.dumps(route_entry["auth_dependencies"])
        assert _auth_dependencies(_current_route_map()[key]) == route_entry["auth_dependencies"]

    declarations = _requirement_declarations()
    assert set(declarations) == REQUIREMENT_IDS
    for requirement_id in REQUIRED_REQUIREMENT_IDS:
        declaration = declarations[requirement_id]
        assert declaration["owning_pass"] == "WS03-04B"
        assert declaration["state"] == "required"
        assert (
            declaration["scope"]
            == "workflows/self_owned_account_notification_financial_authorization"
        )
        assert declaration["reason"].strip()

    deferred = declarations[DEFERRED_REQUIREMENT_ID]
    assert deferred["owning_pass"] == "WS03-04B"
    assert deferred["state"] == "deferred"
    assert deferred["scope"] == "governance"
    assert deferred["reason"].strip()

    marker_ids = _collect_requirement_marker_ids()
    assert REQUIRED_REQUIREMENT_IDS <= marker_ids
    assert DEFERRED_REQUIREMENT_ID not in marker_ids


@pytest.mark.requirement("WS03-04B-R2", "WS03-04B-R3", "WS03-04B-R8")
def test_current_user_profile_settings_and_stats_use_unverified_current_user(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _session() as db:
        user = _user(1, email_verified_at=None)
        other = _user(2)
        db.add_all([user, other, _settings(user.id), _settings(other.id), _stats(user.id), _stats(other.id)])
        db.commit()
        user_id = user.id
        other_id = other.id
        user_auth_id = user.auth_user_id
        user_email = user.email

    _install_auth_identities(
        monkeypatch,
        {
            "valid-token": _Identity(
                auth_user_id=user_auth_id,
                email=user_email,
                email_verified=False,
                authenticated_at=_recent_time(),
            )
        },
    )

    for path in ("/auth/me", "/users/me", "/user-settings/me", "/user-stats/me"):
        response = client.get(path, headers=_auth_headers())
        assert response.status_code == 200

    assert client.get("/users/me", headers=_auth_headers()).json()["id"] == str(user_id)
    assert client.get("/user-settings/me", headers=_auth_headers()).json()["user_id"] == str(user_id)
    assert client.get("/user-stats/me", headers=_auth_headers()).json()["user_id"] == str(user_id)

    profile_response = client.patch(
        "/users/me",
        headers=_auth_headers(),
        json={"first_name": "Allowed", "home_city": "Chicago"},
    )
    assert profile_response.status_code == 200
    assert profile_response.json()["id"] == str(user_id)
    with _session() as db:
        from backend.models import User

        current_user = db.get(User, user_id)
        other_user = db.get(User, other_id)
        assert current_user.first_name == "Allowed"
        assert current_user.role == "player"
        assert current_user.account_status == "active"
        assert other_user.first_name != "Allowed"

    rejected_profile = client.patch(
        "/users/me",
        headers=_auth_headers(),
        json={
            "first_name": "Rejected",
            "email": "attacker@example.invalid",
            "role": "admin",
            "account_status": "deleted",
            "profile_photo_url": "https://example.invalid/photo.png",
        },
    )
    assert rejected_profile.status_code == 422

    settings_response = client.patch(
        "/user-settings/me",
        headers=_auth_headers(),
        json={"push_notifications_enabled": True, "selected_city": "Chicago"},
    )
    assert settings_response.status_code == 200
    assert settings_response.json()["user_id"] == str(user_id)
    assert settings_response.json()["push_notifications_enabled"] is True

    rejected_settings = client.patch(
        "/user-settings/me",
        headers=_auth_headers(),
        json={"user_id": str(other_id), "created_at": "2026-01-01T00:00:00Z"},
    )
    assert rejected_settings.status_code == 422

    with _session() as db:
        from backend.models import User, UserSettings

        current_user = db.get(User, user_id)
        current_settings = db.get(UserSettings, user_id)
        other_settings = db.get(UserSettings, other_id)
        assert current_user.email == user_email
        assert current_user.role == "player"
        assert current_user.account_status == "active"
        assert current_user.profile_photo_url is None
        assert current_settings.push_notifications_enabled is True
        assert other_settings.selected_city is None


@pytest.mark.requirement("WS03-04B-R3", "WS03-04B-R5", "WS03-04B-R8")
def test_credential_status_and_recent_auth_denials_have_no_mutation_side_effects(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    firebase_deletes: list[str] = []
    with _session() as db:
        active_user = _user(3, stripe_customer_id="cus_ws03_04b_active")
        suspended_user = _user(4, account_status="suspended")
        active_card = _payment_method(active_user.id, "cus_ws03_04b_active", 1)
        db.add_all([active_user, suspended_user, _settings(active_user.id), _stats(active_user.id), active_card])
        db.commit()
        active_user_id = active_user.id
        active_auth_id = active_user.auth_user_id
        active_email = active_user.email
        suspended_auth_id = suspended_user.auth_user_id
        suspended_email = suspended_user.email
        active_card_id = active_card.id

    _install_auth_identities(
        monkeypatch,
        {
            "stale-token": _Identity(
                auth_user_id=active_auth_id,
                email=active_email,
                email_verified=False,
                authenticated_at=_stale_time(),
            ),
            "suspended-token": _Identity(
                auth_user_id=suspended_auth_id,
                email=suspended_email,
                email_verified=False,
                authenticated_at=_recent_time(),
            ),
        },
    )
    fake = _install_stripe_fake(monkeypatch, setup_customer_id="cus_ws03_04b_active")

    from backend.services import account_deletion_service

    monkeypatch.setattr(
        account_deletion_service,
        "delete_firebase_user",
        lambda auth_user_id: firebase_deletes.append(auth_user_id),
    )

    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers=_auth_headers("invalid-token")).status_code == 401
    assert client.get("/auth/me", headers=_auth_headers("stale-token")).status_code == 200
    assert client.get("/inbox/counts", headers=_auth_headers("suspended-token")).status_code == 403

    stale_default = client.patch(
        f"/user-payment-methods/{active_card_id}/default",
        headers=_auth_headers("stale-token"),
    )
    assert stale_default.status_code == 403

    stale_delete = client.request(
        "DELETE",
        "/auth/account",
        headers=_auth_headers("stale-token"),
        json={"confirmation": "DELETE"},
    )
    assert stale_delete.status_code == 403

    with _session() as db:
        from backend.models import User, UserPaymentMethod

        user = db.get(User, active_user_id)
        card = db.get(UserPaymentMethod, active_card_id)
        assert user.account_status == "active"
        assert user.auth_user_id == active_auth_id
        assert card.is_default is False
        assert card.method_status == "active"
    assert fake.default_payment_methods == []
    assert fake.detached_payment_methods == []
    assert firebase_deletes == []


@pytest.mark.requirement("WS03-04B-R2", "WS03-04B-R3", "WS03-04B-R8")
def test_self_delete_requires_confirmation_and_deletes_only_the_token_user(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    firebase_deletes: list[str] = []
    with _session() as db:
        user = _user(5)
        other = _user(6)
        db.add_all([user, other, _settings(user.id), _settings(other.id), _stats(user.id), _stats(other.id)])
        db.commit()
        user_id = user.id
        other_id = other.id
        user_auth_id = user.auth_user_id
        user_email = user.email
        other_auth_id = other.auth_user_id

    _install_auth_identities(
        monkeypatch,
        {
            "delete-token": _Identity(
                auth_user_id=user_auth_id,
                email=user_email,
                email_verified=False,
                authenticated_at=_recent_time(),
            )
        },
    )

    from backend.services import account_deletion_service

    monkeypatch.setattr(
        account_deletion_service,
        "delete_firebase_user",
        lambda auth_user_id: firebase_deletes.append(auth_user_id),
    )

    invalid_confirmation = client.request(
        "DELETE",
        "/auth/account",
        headers=_auth_headers("delete-token"),
        json={"confirmation": "not delete"},
    )
    assert invalid_confirmation.status_code in {400, 422}
    assert firebase_deletes == []

    deleted = client.request(
        "DELETE",
        "/auth/account",
        headers=_auth_headers("delete-token"),
        json={"confirmation": "DELETE"},
    )
    assert deleted.status_code == 200
    assert firebase_deletes == [user_auth_id]

    with _session() as db:
        from backend.models import User

        deleted_user = db.get(User, user_id)
        other_user = db.get(User, other_id)
        assert deleted_user.account_status == "deleted"
        assert deleted_user.auth_user_id is None
        assert deleted_user.deleted_at is not None
        assert other_user.account_status == "active"
        assert other_user.auth_user_id == other_auth_id


@pytest.mark.requirement("WS03-04B-R4", "WS03-04B-R8")
def test_notifications_and_inbox_are_concealed_and_current_user_scoped(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _session() as db:
        from backend.models import (
            PlatformNoticeRecipient,
            PlatformNoticeSelectedRead,
        )

        user = _user(7)
        other = _user(8)
        own_app = _notification(user.id, 1, category="app")
        other_app = _notification(other.id, 2, category="app")
        own_game = _notification(user.id, 3, category="game_activity")
        other_game = _notification(other.id, 4, category="game_activity")
        global_sequence = 9_000_000_000_000 + uuid.uuid4().int % 1_000_000
        global_notice = _platform_notice(
            3,
            audience_type="all_eligible_users",
            global_sequence=global_sequence,
        )
        own_selected = _platform_notice(1, audience_type="selected_users", global_sequence=None)
        other_selected = _platform_notice(2, audience_type="selected_users", global_sequence=None)
        db.add_all([user, other])
        db.flush()
        db.add_all(
            [
                own_app,
                other_app,
                own_game,
                other_game,
                global_notice,
                own_selected,
                other_selected,
            ]
        )
        db.flush()
        db.add_all(
            [
                PlatformNoticeRecipient(notice_id=own_selected.id, user_id=user.id),
                PlatformNoticeRecipient(notice_id=other_selected.id, user_id=other.id),
                _global_seen_state(user.id, global_sequence - 1),
                _global_seen_state(other.id, global_sequence + 5),
            ]
        )
        db.commit()
        user_id = user.id
        other_id = other.id
        user_auth_id = user.auth_user_id
        user_email = user.email
        own_app_id = own_app.id
        own_game_id = own_game.id
        other_app_id = other_app.id
        global_notice_id = global_notice.id
        global_notice_sequence = global_sequence
        other_selected_id = other_selected.id
        own_selected_id = own_selected.id

    _install_auth_identities(
        monkeypatch,
        {
            "valid-token": _Identity(
                auth_user_id=user_auth_id,
                email=user_email,
                email_verified=False,
                authenticated_at=_recent_time(),
            )
        },
    )

    app_list = client.get(
        "/notifications/me",
        headers=_auth_headers(),
        params={"notification_category": "app"},
    )
    assert app_list.status_code == 200
    assert {item["id"] for item in app_list.json()} == {str(own_app_id)}

    app_updates = client.get("/inbox/app-updates", headers=_auth_headers())
    assert app_updates.status_code == 200
    app_update_payload = app_updates.json()
    app_update_source_ids = {item["source_id"] for item in app_update_payload["items"]}
    assert {
        str(own_app_id),
        str(global_notice_id),
        str(own_selected_id),
    } <= app_update_source_ids
    assert str(other_app_id) not in app_update_source_ids
    assert str(other_selected_id) not in app_update_source_ids
    assert app_update_payload["global_seen_token"]

    counts = client.get("/inbox/counts", headers=_auth_headers())
    assert counts.status_code == 200
    assert counts.json() == {
        "app_updates_new_count": 3,
        "game_activity_unread_count": 1,
    }

    valid_seen = client.put(
        "/inbox/app-updates/global-seen",
        headers=_auth_headers(),
        json={"seen_token": app_update_payload["global_seen_token"]},
    )
    assert valid_seen.status_code == 200
    assert valid_seen.json() == {
        "app_updates_new_count": 2,
        "game_activity_unread_count": 1,
    }

    game_activity = client.get("/inbox/game-activity", headers=_auth_headers())
    assert game_activity.status_code == 200
    assert {item["source_id"] for item in game_activity.json()["items"]} == {str(own_game_id)}

    assert (
        client.get(f"/notifications/{other_app_id}", headers=_auth_headers()).status_code
        == 404
    )
    rejected_read = client.patch(
        f"/notifications/{other_app_id}/read",
        headers=_auth_headers(),
    )
    assert rejected_read.status_code == 404

    rejected_selected = client.put(
        f"/inbox/app-updates/platform-notices/{other_selected_id}/read",
        headers=_auth_headers(),
    )
    assert rejected_selected.status_code == 404

    own_selected_read = client.put(
        f"/inbox/app-updates/platform-notices/{own_selected_id}/read",
        headers=_auth_headers(),
    )
    repeated_selected_read = client.put(
        f"/inbox/app-updates/platform-notices/{own_selected_id}/read",
        headers=_auth_headers(),
    )
    assert own_selected_read.status_code == 200
    assert repeated_selected_read.status_code == 200

    from backend.services.inbox_service import encode_global_seen_token

    wrong_user_token = encode_global_seen_token(
        highest_global_sequence=20,
        user_id=other_id,
    )
    rejected_seen = client.put(
        "/inbox/app-updates/global-seen",
        headers=_auth_headers(),
        json={"seen_token": wrong_user_token},
    )
    assert rejected_seen.status_code == 400

    with _session() as db:
        from backend.models import (
            Notification,
            PlatformNoticeGlobalSeenState,
        )

        other_notification = db.get(Notification, other_app_id)
        assert other_notification.is_read is False
        assert (
            db.get(PlatformNoticeGlobalSeenState, user_id).last_seen_global_sequence
            == global_notice_sequence
        )
        assert (
            db.get(PlatformNoticeGlobalSeenState, other_id).last_seen_global_sequence
            == global_notice_sequence + 5
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(PlatformNoticeSelectedRead)
                .where(PlatformNoticeSelectedRead.notice_id == own_selected_id)
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(PlatformNoticeSelectedRead)
                .where(PlatformNoticeSelectedRead.notice_id == other_selected_id)
            )
            == 0
        )


@pytest.mark.requirement(
    "WS03-04B-R3",
    "WS03-04B-R5",
    "WS03-04B-R8",
)
def test_saved_cards_enforce_owner_recent_auth_and_provider_customer_boundaries(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _session() as db:
        user = _user(9, stripe_customer_id="cus_ws03_04b_user")
        other = _user(10, stripe_customer_id="cus_ws03_04b_other")
        own_card = _payment_method(user.id, "cus_ws03_04b_user", 1)
        other_card = _payment_method(other.id, "cus_ws03_04b_other", 2, is_default=True)
        db.add_all([user, other, own_card, other_card])
        db.commit()
        user_auth_id = user.auth_user_id
        user_email = user.email
        own_card_id = own_card.id
        own_stripe_payment_method_id = own_card.stripe_payment_method_id
        other_card_id = other_card.id

    _install_auth_identities(
        monkeypatch,
        {
            "card-token": _Identity(
                auth_user_id=user_auth_id,
                email=user_email,
                email_verified=False,
                authenticated_at=_recent_time(),
            )
        },
    )
    fake = _install_stripe_fake(
        monkeypatch,
        setup_customer_id="cus_ws03_04b_user",
        payment_method_customer_id="cus_ws03_04b_user",
    )

    listed = client.get("/user-payment-methods", headers=_auth_headers("card-token"))
    assert listed.status_code == 200
    assert {item["id"] for item in listed.json()} == {str(own_card_id)}

    assert (
        client.get(
            f"/user-payment-methods/{other_card_id}",
            headers=_auth_headers("card-token"),
        ).status_code
        == 404
    )

    defaulted = client.patch(
        f"/user-payment-methods/{own_card_id}/default",
        headers=_auth_headers("card-token"),
    )
    assert defaulted.status_code == 200
    assert fake.default_payment_methods == [own_stripe_payment_method_id]

    rejected_default = client.patch(
        f"/user-payment-methods/{other_card_id}/default",
        headers=_auth_headers("card-token"),
    )
    rejected_detach = client.delete(
        f"/user-payment-methods/{other_card_id}",
        headers=_auth_headers("card-token"),
    )
    assert rejected_default.status_code == 404
    assert rejected_detach.status_code == 404
    assert fake.detached_payment_methods == []

    rejected_setup_fields = client.post(
        "/user-payment-methods/setup-intent",
        headers=_auth_headers("card-token"),
        json={"set_as_default": True, "stripe_customer_id": "cus_attacker"},
    )
    assert rejected_setup_fields.status_code == 422
    setup_intent = client.post(
        "/user-payment-methods/setup-intent",
        headers=_auth_headers("card-token"),
        json={"set_as_default": True},
    )
    assert setup_intent.status_code == 201
    assert setup_intent.json()["client_secret"] == "seti_secret_ws03_04b"

    fake.setup_intent_customer_id = "cus_ws03_04b_other"
    rejected_sync = client.post(
        "/user-payment-methods/sync",
        headers=_auth_headers("card-token"),
        json={"setup_intent_id": "seti_wrong_customer", "set_as_default": True},
    )
    rejected_sync_fields = client.post(
        "/user-payment-methods/sync",
        headers=_auth_headers("card-token"),
        json={"setup_intent_id": "seti_any", "user_id": str(uuid.uuid4())},
    )
    assert rejected_sync.status_code == 403
    assert rejected_sync_fields.status_code == 422
    assert fake.retrieved_setup_intents == ["seti_wrong_customer"]
    assert fake.retrieved_payment_methods == []

    detached = client.delete(
        f"/user-payment-methods/{own_card_id}",
        headers=_auth_headers("card-token"),
    )
    repeated_detach = client.delete(
        f"/user-payment-methods/{own_card_id}",
        headers=_auth_headers("card-token"),
    )
    assert detached.status_code == 200
    assert repeated_detach.status_code == 200
    assert detached.json()["id"] == str(own_card_id)
    assert detached.json()["method_status"] == "detached"
    assert repeated_detach.json()["method_status"] == "detached"
    assert fake.detached_payment_methods == [own_stripe_payment_method_id]
    assert fake.cleared_customers == ["cus_ws03_04b_user"]

    with _session() as db:
        from backend.models import UserPaymentMethod

        own = db.get(UserPaymentMethod, own_card_id)
        other_pm = db.get(UserPaymentMethod, other_card_id)
        assert own.is_default is False
        assert own.method_status == "detached"
        assert own.detached_at is not None
        assert other_pm.is_default is True
        assert other_pm.method_status == "active"
        assert (
            db.scalar(select(func.count()).select_from(UserPaymentMethod))
            == 2
        )


@pytest.mark.requirement("WS03-04B-R6", "WS03-04B-R7", "WS03-04B-R8")
def test_financial_reads_and_admin_exceptions_are_current_user_scoped(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _session() as db:
        user = _user(11)
        other = _user(12)
        user_venue = _venue(user.id, 1)
        other_venue = _venue(other.id, 2)
        user_game = _community_game(user_id=user.id, venue_id=user_venue.id, index=1)
        other_game = _community_game(user_id=other.id, venue_id=other_venue.id, index=2)
        user_payment = _payment(user_id=user.id, game_id=user_game.id, index=1)
        other_payment = _payment(user_id=other.id, game_id=other_game.id, index=2)
        user_fee = _host_publish_fee(
            user_id=user.id,
            game_id=user_game.id,
            payment_id=user_payment.id,
            index=1,
        )
        other_fee = _host_publish_fee(
            user_id=other.id,
            game_id=other_game.id,
            payment_id=other_payment.id,
            index=2,
        )
        user_refund = _refund(
            payment_id=user_payment.id,
            host_publish_fee_id=user_fee.id,
            requested_by_user_id=user.id,
            index=1,
        )
        other_refund = _refund(
            payment_id=other_payment.id,
            host_publish_fee_id=other_fee.id,
            requested_by_user_id=other.id,
            index=2,
        )
        user_credit = _game_credit(user.id, 1)
        other_credit = _game_credit(other.id, 2)
        db.add_all([user, other])
        db.flush()
        db.add_all([user_venue, other_venue])
        db.flush()
        db.add_all([user_game, other_game])
        db.flush()
        db.add_all([user_payment, other_payment])
        db.flush()
        db.add_all([user_fee, other_fee])
        db.flush()
        db.add_all([user_refund, other_refund, user_credit, other_credit])
        db.commit()
        user_id = user.id
        user_auth_id = user.auth_user_id
        user_email = user.email
        other_id = other.id
        user_payment_id = user_payment.id
        other_payment_id = other_payment.id
        other_refund_id = other_refund.id
        user_fee_id = user_fee.id
        user_credit_id = user_credit.id

    _install_auth_identities(
        monkeypatch,
        {
            "money-token": _Identity(
                auth_user_id=user_auth_id,
                email=user_email,
                email_verified=False,
                authenticated_at=_recent_time(),
            )
        },
    )

    credits = client.get("/game-credits", headers=_auth_headers("money-token"))
    assert credits.status_code == 200
    assert {item["id"] for item in credits.json()} == {str(user_credit_id)}
    credit_balance = client.get(
        "/game-credits/balance",
        headers=_auth_headers("money-token"),
    )
    assert credit_balance.status_code == 200
    assert credit_balance.json() == {
        "user_id": str(user_id),
        "available_credit_cents": 700,
        "currency": "USD",
    }
    assert (
        client.get(
            "/game-credits",
            headers=_auth_headers("money-token"),
            params={"user_id": str(other_id)},
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/game-credits/balance",
            headers=_auth_headers("money-token"),
            params={"user_id": str(other_id)},
        ).status_code
        == 403
    )

    payments = client.get("/payments", headers=_auth_headers("money-token"))
    assert payments.status_code == 200
    assert {item["id"] for item in payments.json()} == {str(user_payment_id)}
    assert (
        client.get(
            "/payments",
            headers=_auth_headers("money-token"),
            params={"payer_user_id": str(other_id)},
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/payments/{other_payment_id}",
            headers=_auth_headers("money-token"),
        ).status_code
        == 403
    )

    refunds = client.get("/refunds", headers=_auth_headers("money-token"))
    assert refunds.status_code == 200
    assert {item["payment_id"] for item in refunds.json()} == {str(user_payment_id)}
    other_payment_filter = client.get(
        "/refunds",
        headers=_auth_headers("money-token"),
        params={"payment_id": str(other_payment_id)},
    )
    assert other_payment_filter.status_code == 200
    assert other_payment_filter.json() == []
    assert (
        client.get(
            f"/refunds/{other_refund_id}",
            headers=_auth_headers("money-token"),
        ).status_code
        == 403
    )

    host_fees = client.get("/host-publish-fees/me", headers=_auth_headers("money-token"))
    assert host_fees.status_code == 200
    assert {item["id"] for item in host_fees.json()} == {str(user_fee_id)}
