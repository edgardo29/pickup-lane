from __future__ import annotations

import inspect
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.schemas.policy_acceptance_schema import PolicyAcceptanceCreate
from backend.schemas.policy_document_schema import PolicyDocumentCreate

pytestmark = pytest.mark.suite_type("ordinary")

ACTIVE_ADMIN_DEPENDENCY = "backend.services.auth_service.require_active_admin"
GET_DB_DEPENDENCY = "backend.database.get_db"
ACCEPTED_AT = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
UPDATED_AT = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
EFFECTIVE_AT = datetime(2025, 1, 1, tzinfo=UTC)
SENTINEL = "B3_POLICY_ACCEPTANCE_BODY_SHOULD_NOT_BECOME_WRITABLE"
UUID_1 = "00000000-0000-4000-8000-000000000001"


@dataclass(frozen=True)
class PolicyAcceptanceTombstone:
    method: str
    path: str
    concrete_path: str
    endpoint_name: str

    @property
    def id(self) -> str:
        return f"{self.method} {self.path}"


POLICY_ACCEPTANCE_TOMBSTONES = (
    PolicyAcceptanceTombstone(
        "POST",
        "/policy-acceptances",
        "/policy-acceptances",
        "create_policy_acceptance",
    ),
    PolicyAcceptanceTombstone(
        "PATCH",
        "/policy-acceptances/{policy_acceptance_id}",
        f"/policy-acceptances/{UUID_1}",
        "update_policy_acceptance",
    ),
)


@pytest.fixture()
def app_with_clean_overrides():
    from backend.main import app

    app.dependency_overrides.clear()
    yield app
    app.dependency_overrides.clear()


def _iter_api_routes() -> Iterable[APIRoute]:
    from backend.main import app

    for route in app.routes:
        if isinstance(route, APIRoute):
            yield route


def _route_by_method_path(method: str, path: str) -> APIRoute:
    matches = [
        route
        for route in _iter_api_routes()
        if route.path == path and method.upper() in route.methods
    ]
    assert len(matches) == 1, f"{method} {path} should have exactly one route"
    return matches[0]


def _callable_name(callable_object: object) -> str:
    module = getattr(callable_object, "__module__", "")
    name = getattr(callable_object, "__name__", repr(callable_object))
    return f"{module}.{name}" if module else name


def _direct_dependency_call_names(route: APIRoute) -> tuple[str, ...]:
    return tuple(_callable_name(dependency.call) for dependency in route.dependant.dependencies)


def _install_active_admin_override(app) -> None:
    from backend.services.auth_service import require_active_admin

    app.dependency_overrides[require_active_admin] = lambda: object()


def _install_rejecting_admin_override(app) -> None:
    from backend.services.auth_service import require_active_admin

    def reject_admin():
        raise HTTPException(status_code=401, detail="synthetic auth failure")

    app.dependency_overrides[require_active_admin] = reject_admin


def _request(client: TestClient, tombstone: PolicyAcceptanceTombstone, **kwargs):
    return client.request(tombstone.method, tombstone.concrete_path, **kwargs)


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _policy_acceptance_count(db: Session) -> int:
    from backend.models import PolicyAcceptance

    return int(db.scalar(select(func.count()).select_from(PolicyAcceptance)) or 0)


def _create_user(db: Session, *, role: str = "player"):
    from backend.models import User

    user = User(
        id=uuid.uuid4(),
        auth_user_id=f"b3-policy-acceptance-{uuid.uuid4()}",
        role=role,
        email=f"b3-policy-acceptance-{uuid.uuid4()}@example.invalid",
        first_name="Policy",
        last_name="Acceptance",
        account_status="active",
        hosting_status="not_eligible",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_policy_document(db: Session):
    from backend.services.policy_document_service import create_policy_document_record

    return create_policy_document_record(
        db,
        PolicyDocumentCreate(
            policy_type="terms_of_service",
            version=f"accept-{uuid.uuid4().hex[:12]}",
            title="Policy acceptance source document",
            content_text="Controlled policy acceptance setup text.",
            effective_at=EFFECTIVE_AT,
            is_active=True,
        ),
    )


def _create_policy_acceptance(db: Session, *, user=None, policy_document=None):
    from backend.services.policy_acceptance_service import create_policy_acceptance_record

    user = user or _create_user(db)
    policy_document = policy_document or _create_policy_document(db)
    return create_policy_acceptance_record(
        db,
        PolicyAcceptanceCreate(
            user_id=user.id,
            policy_document_id=policy_document.id,
            accepted_at=ACCEPTED_AT,
            ip_address="203.0.113.10",
            user_agent="B3 controlled setup",
        ),
    )


def _snapshot_policy_acceptance(acceptance) -> dict[str, object]:
    return {
        "user_id": acceptance.user_id,
        "policy_document_id": acceptance.policy_document_id,
        "accepted_at": acceptance.accepted_at,
        "ip_address": acceptance.ip_address,
        "user_agent": acceptance.user_agent,
    }


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS02-04B2A2B3-R2")
def test_policy_acceptance_tombstones_are_registered_bodyless_admin_guarded_and_non_mutating() -> None:
    for tombstone in POLICY_ACCEPTANCE_TOMBSTONES:
        route = _route_by_method_path(tombstone.method, tombstone.path)
        dependency_names = _direct_dependency_call_names(route)
        source = inspect.getsource(route.endpoint)
        signature = inspect.signature(route.endpoint)

        assert route.endpoint.__module__ == "backend.routes.policy_acceptance_routes"
        assert route.endpoint.__name__ == tombstone.endpoint_name
        assert route.body_field is None, tombstone.id
        assert route.dependant.body_params == [], tombstone.id
        assert ACTIVE_ADMIN_DEPENDENCY in dependency_names, tombstone.id
        assert GET_DB_DEPENDENCY not in dependency_names, tombstone.id
        assert "Request" not in source, tombstone.id
        assert ".json(" not in source, tombstone.id
        assert ".body(" not in source, tombstone.id
        assert "create_policy_acceptance_record" not in source, tombstone.id
        assert "update_policy_acceptance_record" not in source, tombstone.id
        assert "request" not in signature.parameters, tombstone.id


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS02-04B2A2B3-R2")
def test_policy_acceptance_tombstones_return_410_only_after_admin_authentication(
    app_with_clean_overrides,
) -> None:
    _install_active_admin_override(app_with_clean_overrides)
    with TestClient(app_with_clean_overrides, follow_redirects=False, raise_server_exceptions=False) as client:
        for tombstone in POLICY_ACCEPTANCE_TOMBSTONES:
            response = _request(client, tombstone)
            assert response.status_code == 410, tombstone.id

    app_with_clean_overrides.dependency_overrides.clear()
    _install_rejecting_admin_override(app_with_clean_overrides)
    with TestClient(app_with_clean_overrides, follow_redirects=False, raise_server_exceptions=False) as client:
        for tombstone in POLICY_ACCEPTANCE_TOMBSTONES:
            response = _request(client, tombstone)
            assert response.status_code == 401, tombstone.id
            assert response.status_code != 410, tombstone.id


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS02-04B2A2B3-R2")
def test_policy_acceptance_json_and_malformed_payloads_do_not_revive_body_validation(
    app_with_clean_overrides,
) -> None:
    _install_active_admin_override(app_with_clean_overrides)

    with TestClient(app_with_clean_overrides, follow_redirects=False, raise_server_exceptions=False) as client:
        for tombstone in POLICY_ACCEPTANCE_TOMBSTONES:
            json_response = _request(
                client,
                tombstone,
                json={
                    "user_id": str(uuid.uuid4()),
                    "policy_document_id": str(uuid.uuid4()),
                    "accepted_at": UPDATED_AT.isoformat(),
                    "ip_address": "198.51.100.12",
                    "user_agent": SENTINEL,
                    "unexpected_evidence": SENTINEL,
                },
            )
            malformed_response = _request(
                client,
                tombstone,
                content=b'{"user_agent": ',
                headers={"Content-Type": "application/json"},
            )

            assert json_response.status_code == 410, tombstone.id
            assert json_response.status_code != 422, tombstone.id
            assert SENTINEL not in json_response.text, tombstone.id
            assert malformed_response.status_code == 410, tombstone.id
            assert malformed_response.status_code != 422, tombstone.id


@pytest.mark.requirement("WS02-04B2A2B3-R2")
def test_body_bearing_policy_acceptance_post_tombstone_does_not_create_rows(
    app_with_clean_overrides,
) -> None:
    _install_active_admin_override(app_with_clean_overrides)

    with _session() as db:
        before_count = _policy_acceptance_count(db)
        with TestClient(app_with_clean_overrides, follow_redirects=False, raise_server_exceptions=False) as client:
            response = client.post(
                "/policy-acceptances",
                json={
                    "user_id": str(uuid.uuid4()),
                    "policy_document_id": str(uuid.uuid4()),
                    "accepted_at": UPDATED_AT.isoformat(),
                    "ip_address": "198.51.100.12",
                    "user_agent": SENTINEL,
                },
            )
        db.rollback()

        assert response.status_code == 410
        assert _policy_acceptance_count(db) == before_count


@pytest.mark.requirement("WS02-04B2A2B3-R2")
def test_body_bearing_policy_acceptance_patch_tombstone_does_not_mutate_existing_row(
    app_with_clean_overrides,
) -> None:
    _install_active_admin_override(app_with_clean_overrides)

    with _session() as db:
        acceptance = _create_policy_acceptance(db)
        original = _snapshot_policy_acceptance(acceptance)

        with TestClient(app_with_clean_overrides, follow_redirects=False, raise_server_exceptions=False) as client:
            response = client.patch(
                f"/policy-acceptances/{acceptance.id}",
                json={
                    "accepted_at": UPDATED_AT.isoformat(),
                    "ip_address": "198.51.100.99",
                    "user_agent": SENTINEL,
                    "user_id": str(uuid.uuid4()),
                    "policy_document_id": str(uuid.uuid4()),
                },
            )
        db.rollback()
        db.refresh(acceptance)

        assert response.status_code == 410
        assert _snapshot_policy_acceptance(acceptance) == original


@pytest.mark.requirement("WS02-04B2A2B3-R3")
def test_internal_setup_can_create_policy_acceptance_and_admin_reads_remain_available(
    app_with_clean_overrides,
) -> None:
    _install_active_admin_override(app_with_clean_overrides)

    with _session() as db:
        acceptance = _create_policy_acceptance(db)

        with TestClient(app_with_clean_overrides, follow_redirects=False, raise_server_exceptions=False) as client:
            detail_response = client.get(f"/policy-acceptances/{acceptance.id}")
            list_response = client.get(
                "/policy-acceptances",
                params={
                    "user_id": str(acceptance.user_id),
                    "policy_document_id": str(acceptance.policy_document_id),
                },
            )

        assert detail_response.status_code == 200
        assert detail_response.json()["id"] == str(acceptance.id)
        assert list_response.status_code == 200
        assert str(acceptance.id) in {item["id"] for item in list_response.json()}


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS02-04B2A2B3-R3")
def test_rejected_callers_cannot_use_policy_acceptance_admin_read_surfaces(
    app_with_clean_overrides,
) -> None:
    _install_rejecting_admin_override(app_with_clean_overrides)

    with TestClient(app_with_clean_overrides, follow_redirects=False, raise_server_exceptions=False) as client:
        detail_response = client.get(f"/policy-acceptances/{uuid.uuid4()}")
        list_response = client.get("/policy-acceptances")

    assert detail_response.status_code == 401
    assert list_response.status_code == 401
    assert detail_response.status_code != 200
    assert list_response.status_code != 200
