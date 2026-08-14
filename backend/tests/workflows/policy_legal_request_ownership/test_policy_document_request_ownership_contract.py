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

from backend.schemas.policy_document_schema import PolicyDocumentCreate

pytestmark = pytest.mark.suite_type("ordinary")

ACTIVE_ADMIN_DEPENDENCY = "backend.services.auth_service.require_active_admin"
GET_DB_DEPENDENCY = "backend.database.get_db"
PAST = datetime(2025, 1, 1, tzinfo=UTC)
RETIRED = datetime(2025, 6, 1, tzinfo=UTC)
FUTURE = datetime(2035, 1, 1, tzinfo=UTC)
SENTINEL = "B3_POLICY_DOCUMENT_BODY_SHOULD_NOT_BECOME_WRITABLE"
UUID_1 = "00000000-0000-4000-8000-000000000001"


@dataclass(frozen=True)
class PolicyDocumentTombstone:
    method: str
    path: str
    concrete_path: str
    endpoint_name: str

    @property
    def id(self) -> str:
        return f"{self.method} {self.path}"


POLICY_DOCUMENT_TOMBSTONES = (
    PolicyDocumentTombstone(
        "POST",
        "/policy-documents",
        "/policy-documents",
        "create_policy_document",
    ),
    PolicyDocumentTombstone(
        "PATCH",
        "/policy-documents/{policy_document_id}",
        f"/policy-documents/{UUID_1}",
        "update_policy_document",
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


def _request(client: TestClient, tombstone: PolicyDocumentTombstone, **kwargs):
    return client.request(tombstone.method, tombstone.concrete_path, **kwargs)


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _policy_document_count(db: Session) -> int:
    from backend.models import PolicyDocument

    return int(db.scalar(select(func.count()).select_from(PolicyDocument)) or 0)


def _policy_document_payload(
    *,
    version: str,
    policy_type: str = "terms_of_service",
    title: str | None = None,
    content_text: str | None = None,
    effective_at: datetime = PAST,
    retired_at: datetime | None = None,
    is_active: bool = True,
) -> PolicyDocumentCreate:
    return PolicyDocumentCreate(
        policy_type=policy_type,
        version=version,
        title=title or f"Policy document {version}",
        content_text=content_text or f"Controlled setup content {version}.",
        effective_at=effective_at,
        retired_at=retired_at,
        is_active=is_active,
    )


def _create_policy_document(db: Session, **overrides):
    from backend.services.policy_document_service import create_policy_document_record

    return create_policy_document_record(
        db,
        _policy_document_payload(**overrides),
    )


def _snapshot_policy_document(document) -> dict[str, object]:
    return {
        "policy_type": document.policy_type,
        "version": document.version,
        "title": document.title,
        "content_url": document.content_url,
        "content_text": document.content_text,
        "effective_at": document.effective_at,
        "retired_at": document.retired_at,
        "is_active": document.is_active,
    }


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS02-04B2A2B3-R1")
def test_policy_document_tombstones_are_registered_bodyless_admin_guarded_and_non_mutating() -> None:
    for tombstone in POLICY_DOCUMENT_TOMBSTONES:
        route = _route_by_method_path(tombstone.method, tombstone.path)
        dependency_names = _direct_dependency_call_names(route)
        source = inspect.getsource(route.endpoint)
        signature = inspect.signature(route.endpoint)

        assert route.endpoint.__module__ == "backend.routes.policy_document_routes"
        assert route.endpoint.__name__ == tombstone.endpoint_name
        assert route.body_field is None, tombstone.id
        assert route.dependant.body_params == [], tombstone.id
        assert ACTIVE_ADMIN_DEPENDENCY in dependency_names, tombstone.id
        assert GET_DB_DEPENDENCY not in dependency_names, tombstone.id
        assert "Request" not in source, tombstone.id
        assert ".json(" not in source, tombstone.id
        assert ".body(" not in source, tombstone.id
        assert "create_policy_document_record" not in source, tombstone.id
        assert "update_policy_document_record" not in source, tombstone.id
        assert "request" not in signature.parameters, tombstone.id


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS02-04B2A2B3-R1")
def test_policy_document_tombstones_return_410_only_after_admin_authentication(
    app_with_clean_overrides,
) -> None:
    _install_active_admin_override(app_with_clean_overrides)
    with TestClient(app_with_clean_overrides, follow_redirects=False, raise_server_exceptions=False) as client:
        for tombstone in POLICY_DOCUMENT_TOMBSTONES:
            response = _request(client, tombstone)
            assert response.status_code == 410, tombstone.id

    app_with_clean_overrides.dependency_overrides.clear()
    _install_rejecting_admin_override(app_with_clean_overrides)
    with TestClient(app_with_clean_overrides, follow_redirects=False, raise_server_exceptions=False) as client:
        for tombstone in POLICY_DOCUMENT_TOMBSTONES:
            response = _request(client, tombstone)
            assert response.status_code == 401, tombstone.id
            assert response.status_code != 410, tombstone.id


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS02-04B2A2B3-R1")
def test_policy_document_json_and_malformed_payloads_do_not_revive_body_validation(
    app_with_clean_overrides,
) -> None:
    _install_active_admin_override(app_with_clean_overrides)

    with TestClient(app_with_clean_overrides, follow_redirects=False, raise_server_exceptions=False) as client:
        for tombstone in POLICY_DOCUMENT_TOMBSTONES:
            json_response = _request(
                client,
                tombstone,
                json={
                    "title": SENTINEL,
                    "content_url": "https://example.invalid/policy",
                    "is_active": False,
                },
            )
            malformed_response = _request(
                client,
                tombstone,
                content=b'{"title": ',
                headers={"Content-Type": "application/json"},
            )

            assert json_response.status_code == 410, tombstone.id
            assert json_response.status_code != 422, tombstone.id
            assert SENTINEL not in json_response.text, tombstone.id
            assert malformed_response.status_code == 410, tombstone.id
            assert malformed_response.status_code != 422, tombstone.id


@pytest.mark.requirement("WS02-04B2A2B3-R1")
def test_body_bearing_policy_document_post_tombstone_does_not_create_rows(
    app_with_clean_overrides,
) -> None:
    _install_active_admin_override(app_with_clean_overrides)

    with _session() as db:
        before_count = _policy_document_count(db)
        with TestClient(app_with_clean_overrides, follow_redirects=False, raise_server_exceptions=False) as client:
            response = client.post(
                "/policy-documents",
                json={
                    "policy_type": "terms_of_service",
                    "version": "caller-owned-v1",
                    "title": SENTINEL,
                    "content_text": "caller-owned legal text",
                    "effective_at": PAST.isoformat(),
                    "is_active": True,
                },
            )
        db.rollback()

        assert response.status_code == 410
        assert _policy_document_count(db) == before_count


@pytest.mark.requirement("WS02-04B2A2B3-R1")
def test_body_bearing_policy_document_patch_tombstone_does_not_mutate_existing_row(
    app_with_clean_overrides,
) -> None:
    _install_active_admin_override(app_with_clean_overrides)

    with _session() as db:
        document = _create_policy_document(db, version="patch-source")
        original = _snapshot_policy_document(document)

        with TestClient(app_with_clean_overrides, follow_redirects=False, raise_server_exceptions=False) as client:
            response = client.patch(
                f"/policy-documents/{document.id}",
                json={
                    "title": SENTINEL,
                    "content_url": "https://example.invalid/changed",
                    "content_text": "caller-owned replacement text",
                    "is_active": False,
                },
            )
        db.rollback()
        db.refresh(document)

        assert response.status_code == 410
        assert _snapshot_policy_document(document) == original


@pytest.mark.requirement("WS02-04B2A2B3-R3")
def test_internal_setup_can_create_policy_documents_and_public_reads_preserve_eligible_documents(
    app_with_clean_overrides,
) -> None:
    with _session() as db:
        document = _create_policy_document(
            db,
            version="eligible-read",
            content_text="Current public policy content.",
        )

        with TestClient(app_with_clean_overrides, follow_redirects=False, raise_server_exceptions=False) as client:
            detail_response = client.get(f"/policy-documents/{document.id}")
            list_response = client.get(
                "/policy-documents",
                params={"policy_type": document.policy_type},
            )

        assert detail_response.status_code == 200
        assert detail_response.json()["id"] == str(document.id)
        assert list_response.status_code == 200
        assert str(document.id) in {item["id"] for item in list_response.json()}


@pytest.mark.requirement("WS02-04B2A2B3-R3")
def test_public_policy_document_reads_exclude_inactive_retired_and_future_effective_documents(
    app_with_clean_overrides,
) -> None:
    with _session() as db:
        ineligible_documents = (
            _create_policy_document(
                db,
                policy_type="privacy_policy",
                version="inactive",
                is_active=False,
            ),
            _create_policy_document(
                db,
                policy_type="privacy_policy",
                version="retired",
                retired_at=RETIRED,
            ),
            _create_policy_document(
                db,
                policy_type="privacy_policy",
                version="future",
                effective_at=FUTURE,
            ),
        )

        with TestClient(app_with_clean_overrides, follow_redirects=False, raise_server_exceptions=False) as client:
            detail_responses = [
                client.get(f"/policy-documents/{document.id}")
                for document in ineligible_documents
            ]
            list_response = client.get(
                "/policy-documents",
                params={"policy_type": "privacy_policy"},
            )

        assert [response.status_code for response in detail_responses] == [404, 404, 404]
        assert list_response.status_code == 200
        returned_ids = {item["id"] for item in list_response.json()}
        assert returned_ids.isdisjoint({str(document.id) for document in ineligible_documents})
