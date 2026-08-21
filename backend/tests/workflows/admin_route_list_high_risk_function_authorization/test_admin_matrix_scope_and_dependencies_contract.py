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

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

REPO_ROOT = Path(__file__).resolve().parents[4]
WORKFLOW_DIR = Path(__file__).resolve().parent
MATRIX_PATH = (
    REPO_ROOT
    / "backend/tests/workflows/authorization_matrix_foundation/authorization_matrix.json"
)
REQUIREMENTS_PATH = REPO_ROOT / "backend/tests/support/requirements/ws03_04d.json"
TESTING_RECORD_PATH = WORKFLOW_DIR / "TESTING_RECORD.md"
REGISTER_PATH = (
    REPO_ROOT / "docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md"
)
AUTH_PREFIX = "backend.services.auth_service:"
EXCLUDED_METHODS = {"HEAD", "OPTIONS"}
WORKFLOW_SCOPE = "workflows/admin_route_list_high_risk_function_authorization"
REQUIREMENT_IDS = {f"WS03-04D-R{number}" for number in range(1, 13)}
REQUIRED_REQUIREMENT_IDS = REQUIREMENT_IDS
EXPECTED_D_FAMILY_COUNT = 40
EXPECTED_D_ROUTE_COUNT = 187
EXPECTED_RECENT_ROUTE_COUNT = 22
EXPECTED_TOMBSTONE_ROUTE_COUNT = 45
EXPECTED_INTAKE_SHA = (
    "e8dd5cda0aad2325df5c25d7d80f0e01a4849a9a1de205e91f0ac8d919869eb4"
)
EXPECTED_PLAN_PATH = (
    "docs/production-readiness/planning/passes/ws03/"
    "ws03-04d-admin-route-list-high-risk-function-authorization.md"
)
EXPECTED_REQUIREMENT_DECLARATION = "ws03_04d.json"
LEGACY_TEST_PATH = "backend/tests/" + "legacy/"

REQUIRED_ADMIN_AUTH_DEPENDENCIES = {
    f"{AUTH_PREFIX}get_current_app_user",
    f"{AUTH_PREFIX}get_verified_firebase_identity",
    f"{AUTH_PREFIX}require_active_user",
    f"{AUTH_PREFIX}require_verified_user",
    f"{AUTH_PREFIX}require_active_admin",
}
RECENT_ADMIN_DEPENDENCIES = {
    f"{AUTH_PREFIX}require_recent_active_admin",
    f"{AUTH_PREFIX}require_recent_authentication",
}
EXPECTED_RECENT_ROUTE_KEYS = {
    ("POST", "/admin/community-games/{game_id}/cancel"),
    ("POST", "/admin/game-credits/issue"),
    ("POST", "/admin/game-credits/{game_credit_id}/reverse"),
    ("POST", "/admin/money/financial-outcomes"),
    ("POST", "/admin/money/issues/{money_issue_id}/resolve"),
    ("POST", "/admin/money/issues/{money_issue_id}/retry-credit"),
    ("POST", "/admin/money/refunds/{refund_id}/reconcile"),
    ("POST", "/admin/money/refunds/{refund_id}/retry"),
    ("POST", "/admin/need-a-sub/{post_id}/remove"),
    ("POST", "/admin/official-games/{game_id}/cancel"),
    ("POST", "/admin/official-games/{game_id}/participants/{participant_id}/remove"),
    ("POST", "/admin/users/{user_id}/delete"),
    ("POST", "/admin/users/{user_id}/restore-hosting"),
    ("POST", "/admin/users/{user_id}/restrict-hosting"),
    ("PATCH", "/admin/users/{user_id}/role"),
    ("POST", "/admin/users/{user_id}/suspend"),
    ("POST", "/admin/users/{user_id}/unsuspend"),
    ("DELETE", "/games/{game_id}"),
    ("PATCH", "/payment-events/{payment_event_id}"),
    ("POST", "/admin/platform-notices"),
    ("POST", "/admin/platform-notices/{notice_id}/cancel"),
    ("DELETE", "/venues/{venue_id}"),
}
TOMBSTONE_ANCHOR_ROUTE_KEYS = {
    ("POST", "/admin/actions"),
    ("POST", "/admin/actions/{admin_action_id}/notes"),
    ("DELETE", "/admin/official-games/{game_id}/host"),
    ("DELETE", "/admin/official-games/{game_id}/participants/{participant_id}"),
    ("POST", "/payments"),
    ("PATCH", "/payments/{payment_id}"),
    ("POST", "/notifications"),
    ("GET", "/notifications"),
    ("PATCH", "/notifications/{notification_id}"),
    ("POST", "/venues"),
    ("PATCH", "/venues/{venue_id}"),
}
ADMIN_SOURCE_MODULE_PREFIXES = (
    "backend.routes.admin_",
    "backend.routes.booking_",
    "backend.routes.community_game_detail_routes",
    "backend.routes.game_",
    "backend.routes.host_publish_fee_routes",
    "backend.routes.notification_routes",
    "backend.routes.participant_status_history_routes",
    "backend.routes.payment_",
    "backend.routes.platform_notice_routes",
    "backend.routes.policy_",
    "backend.routes.refund_routes",
    "backend.routes.sub_post_routes",
    "backend.routes.support_flag_routes",
    "backend.routes.user_",
    "backend.routes.venue_",
    "backend.routes.waitlist_entry_routes",
)


@dataclass(frozen=True)
class _Identity:
    auth_user_id: str
    email: str
    email_verified: bool
    authenticated_at: datetime | None


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _auth_headers(token: str = "admin-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _client():
    from fastapi.testclient import TestClient

    from backend.main import app

    return TestClient(app)


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


def _install_tokens_for_users(
    monkeypatch: pytest.MonkeyPatch,
    token_users: dict[str, Any],
    *,
    stale_tokens: set[str] | None = None,
    unverified_tokens: set[str] | None = None,
) -> None:
    stale_tokens = stale_tokens or set()
    unverified_tokens = unverified_tokens or set()
    _install_auth_identities(
        monkeypatch,
        {
            token: _Identity(
                auth_user_id=user.auth_user_id,
                email=user.email,
                email_verified=token not in unverified_tokens,
                authenticated_at=_stale_time() if token in stale_tokens else _recent_time(),
            )
            for token, user in token_users.items()
        },
    )


def _user(
    label: str,
    *,
    role: str = "player",
    account_status: str = "active",
    email_verified: bool = True,
    hosting_status: str = "eligible",
) -> Any:
    from backend.models import User

    unique = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"firebase-ws03-04d-{label}-{unique}",
        role=role,
        email=f"ws03-04d-{label}-{unique}@example.invalid",
        email_verified_at=datetime.now(timezone.utc) if email_verified else None,
        first_name=f"WS03D{label}",
        last_name="User",
        date_of_birth=date(1990, 1, 1),
        account_status=account_status,
        hosting_status=hosting_status,
    )


def _add_users(*users: Any) -> None:
    with _session() as db:
        db.add_all(list(users))
        db.commit()
        for user in users:
            db.refresh(user)
            db.expunge(user)


def _count_model_rows(model: type[Any]) -> int:
    from sqlalchemy import func, select

    with _session() as db:
        return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _get_user_role(user_id: uuid.UUID) -> str:
    from backend.models import User

    with _session() as db:
        user = db.get(User, user_id)
        assert user is not None
        return str(user.role)


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


@lru_cache(maxsize=1)
def _d_matrix_routes() -> dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]]:
    routes: dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]] = {}
    for family in _matrix()["route_families"]:
        if family["primary_child_owner"] != "WS03-04D":
            continue
        for route in family["routes"]:
            key = (route["method"], route["path"])
            assert route["child_owner"] == "WS03-04D"
            assert key not in routes, f"duplicate D matrix route key: {key}"
            routes[key] = (family, route)
    return routes


def _d_route_keys() -> set[tuple[str, str]]:
    return set(_d_matrix_routes())


def _d_routes_with_dependency(dependency: str) -> set[tuple[str, str]]:
    return {
        key
        for key, (_family, route) in _d_matrix_routes().items()
        if dependency in route["auth_dependencies"]
    }


def _d_tombstone_route_keys() -> set[tuple[str, str]]:
    return {
        key
        for key, (_family, route) in _d_matrix_routes().items()
        if route["concealment_policy"] == "410"
    }


def _collect_requirement_marker_ids() -> set[str]:
    marker_ids: set[str] = set()
    for test_file in WORKFLOW_DIR.glob("test_*.py"):
        tree = ast.parse(test_file.read_text(encoding="utf-8"))
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


@pytest.mark.requirement("WS03-04D-R1", "WS03-04D-R2", "WS03-04D-R3")
def test_d_route_inventory_matches_accepted_matrix_and_current_route_table() -> None:
    d_routes = _d_matrix_routes()
    d_families = [
        family
        for family in _matrix()["route_families"]
        if family["primary_child_owner"] == "WS03-04D"
    ]

    assert len(d_families) == EXPECTED_D_FAMILY_COUNT
    assert len(d_routes) == EXPECTED_D_ROUTE_COUNT
    assert all(family["behavior_owner_detail"] == "WS03-04D" for family in d_families)

    current_routes = _current_route_map()
    assert _d_route_keys() <= set(current_routes)

    for key, (_family, matrix_route) in d_routes.items():
        current_route = current_routes[key]
        matrix_dependencies = set(matrix_route["auth_dependencies"])
        current_dependencies = set(_auth_dependencies(current_route))
        assert matrix_dependencies == current_dependencies, key
        assert REQUIRED_ADMIN_AUTH_DEPENDENCIES <= matrix_dependencies, key
        assert matrix_route["negative_proof_owner"] == "WS03-04D"
        assert matrix_route["negative_proof_owner_detail"] == "WS03-04D"
        assert matrix_route["route_disposition"] in {
            "protected",
            "retired_or_tombstone",
        }
        assert matrix_route["source_module"].startswith(ADMIN_SOURCE_MODULE_PREFIXES)


@pytest.mark.requirement("WS03-04D-R1", "WS03-04D-R3", "WS03-04D-R10")
def test_recent_admin_and_tombstone_route_sets_match_frozen_plan() -> None:
    recent_routes = _d_routes_with_dependency(
        f"{AUTH_PREFIX}require_recent_active_admin"
    )
    tombstone_routes = _d_tombstone_route_keys()

    assert recent_routes == EXPECTED_RECENT_ROUTE_KEYS
    assert len(recent_routes) == EXPECTED_RECENT_ROUTE_COUNT
    assert all(
        RECENT_ADMIN_DEPENDENCIES <= set(_d_matrix_routes()[key][1]["auth_dependencies"])
        for key in recent_routes
    )

    assert len(tombstone_routes) == EXPECTED_TOMBSTONE_ROUTE_COUNT
    assert TOMBSTONE_ANCHOR_ROUTE_KEYS <= tombstone_routes
    assert not recent_routes & tombstone_routes


@pytest.mark.requirement("WS03-04D-R11", "WS03-04D-R12")
def test_requirements_markers_record_and_register_preserve_d_traceability() -> None:
    declarations = _requirement_declarations()
    assert set(declarations) == REQUIREMENT_IDS
    assert {
        requirement_id
        for requirement_id, declaration in declarations.items()
        if declaration["state"] == "required"
    } == REQUIRED_REQUIREMENT_IDS
    assert {
        declaration["scope"] for declaration in declarations.values()
    } == {WORKFLOW_SCOPE}

    marker_ids = _collect_requirement_marker_ids()
    assert marker_ids == REQUIREMENT_IDS

    testing_record = TESTING_RECORD_PATH.read_text(encoding="utf-8")
    for requirement_id in REQUIREMENT_IDS:
        assert requirement_id in testing_record
    assert LEGACY_TEST_PATH not in testing_record

    register = REGISTER_PATH.read_text(encoding="utf-8")
    assert "`WS03-04D`" in register
    assert EXPECTED_PLAN_PATH in register
    assert EXPECTED_REQUIREMENT_DECLARATION in register
    assert "WS03-04 parent complete" in register
    assert "WS03-04A-G001" in register
    assert "WS05" in register


@pytest.mark.requirement("WS03-04D-R12")
def test_parent_gap_disposition_sources_remain_explicit_and_non_blocking() -> None:
    gaps = _matrix()["uncovered_gaps"]
    assert gaps == [
        {
            "gap_id": "WS03-04A-G001",
            "state": "covered_elsewhere",
            "title": "Stripe webhook payment lifecycle proof",
            "reason": (
                "POST /stripe/webhook is a provider callback outside ordinary user "
                "authorization; PAY-005/PAY-006 payment/webhook lifecycle, signature, "
                "replay, and idempotent transition proof are owned by WS05 and not "
                "completed by WS03-04A."
            ),
            "owner": "WS05",
            "owner_type": "covered_elsewhere",
            "source_ids": [
                "SRC-FROZEN-PLAN",
                "SRC-BLUEPRINT",
                "SRC-REMEDIATION",
                "SRC-SOURCE-ROUTES-STRIPE-WEBHOOK-ROUTES",
            ],
            "requirement_ids": ["WS03-04A-R8", "WS03-04A-R9"],
            "affected_families": ["stripe_webhook_covered_elsewhere_ws05"],
            "affected_routes": [{"method": "POST", "path": "/stripe/webhook"}],
            "resolution_condition": (
                "WS05 accepts PAY-005/PAY-006 payment/webhook lifecycle evidence "
                "or a later owner decision supersedes the handoff."
            ),
            "blocks_ws03_04a_acceptance": False,
        }
    ]
