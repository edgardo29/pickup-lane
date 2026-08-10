from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.database import SessionLocal
from backend.models import PolicyAcceptance, PolicyDocument, User
from backend.observability.correlation import CORRELATION_ID_HEADER
from backend.services.auth_service import (
    VerifiedFirebaseIdentity,
    get_current_app_user,
    get_verified_firebase_identity,
    require_verified_user,
)
from backend.tests.helpers import (
    create_policy_acceptance,
    create_policy_document,
    create_user,
    set_user_role,
    unique_suffix,
)

CORS_ORIGIN = "http://localhost:5173"
POLICY_DOCUMENT_TOMBSTONE_CODE = "policy_document_generic_authoring_removed"
POLICY_ACCEPTANCE_TOMBSTONE_CODE = "policy_acceptance_generic_mutation_removed"


def authenticate_client_as(client: TestClient, user_id: str) -> None:
    def override_current_user() -> User:
        with SessionLocal() as db:
            db_user = db.get(User, UUID(user_id))
            assert db_user is not None
            return db_user

    def override_firebase_identity() -> VerifiedFirebaseIdentity:
        with SessionLocal() as db:
            db_user = db.get(User, UUID(user_id))
            assert db_user is not None
            return VerifiedFirebaseIdentity(
                auth_user_id=db_user.auth_user_id,
                email=db_user.email,
                email_verified=True,
            )

    client.app.dependency_overrides[get_current_app_user] = override_current_user
    client.app.dependency_overrides[get_verified_firebase_identity] = (
        override_firebase_identity
    )
    client.app.dependency_overrides[require_verified_user] = override_current_user


def create_admin_user(client: TestClient) -> dict:
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    return admin


def tombstone_headers() -> dict[str, str]:
    return {"Origin": CORS_ORIGIN}


def json_tombstone_headers() -> dict[str, str]:
    return {**tombstone_headers(), "Content-Type": "application/json"}


def assert_tombstone_response(
    response,
    *,
    expected_code: str,
    absent_values: tuple[str, ...] = (),
) -> None:
    assert response.status_code == 410, response.text
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["access-control-allow-origin"] == CORS_ORIGIN

    body = response.json()
    assert body["code"] == "API.HTTP_ERROR"
    assert body["correlation_id"] == response.headers[CORRELATION_ID_HEADER]
    assert body["detail"]["code"] == expected_code
    assert body["detail"]["message"]
    assert body["message"]

    for value in absent_values:
        assert value not in response.text


def model_count(model) -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(model)) or 0


def get_policy_document_snapshot(policy_document_id: str) -> dict[str, object]:
    with SessionLocal() as db:
        policy_document = db.get(PolicyDocument, UUID(policy_document_id))
        assert policy_document is not None
        return {
            "policy_type": policy_document.policy_type,
            "version": policy_document.version,
            "title": policy_document.title,
            "content_url": policy_document.content_url,
            "content_text": policy_document.content_text,
            "effective_at": policy_document.effective_at,
            "retired_at": policy_document.retired_at,
            "is_active": policy_document.is_active,
        }


def get_policy_acceptance_snapshot(policy_acceptance_id: str) -> dict[str, object]:
    with SessionLocal() as db:
        policy_acceptance = db.get(PolicyAcceptance, UUID(policy_acceptance_id))
        assert policy_acceptance is not None
        return {
            "user_id": str(policy_acceptance.user_id),
            "policy_document_id": str(policy_acceptance.policy_document_id),
            "accepted_at": policy_acceptance.accepted_at,
            "ip_address": policy_acceptance.ip_address,
            "user_agent": policy_acceptance.user_agent,
        }


@pytest.mark.parametrize(
    ("method", "path", "expected_code"),
    [
        ("POST", "/policy-documents", POLICY_DOCUMENT_TOMBSTONE_CODE),
        (
            "PATCH",
            f"/policy-documents/{uuid4()}",
            POLICY_DOCUMENT_TOMBSTONE_CODE,
        ),
        ("POST", "/policy-acceptances", POLICY_ACCEPTANCE_TOMBSTONE_CODE),
        (
            "PATCH",
            f"/policy-acceptances/{uuid4()}",
            POLICY_ACCEPTANCE_TOMBSTONE_CODE,
        ),
    ],
)
def test_policy_legal_tombstones_do_not_parse_malformed_json(
    client: TestClient,
    method: str,
    path: str,
    expected_code: str,
) -> None:
    admin = create_admin_user(client)
    authenticate_client_as(client, admin["id"])
    document_count_before = model_count(PolicyDocument)
    acceptance_count_before = model_count(PolicyAcceptance)

    response = client.request(
        method,
        path,
        content='{"malformed": ',
        headers=json_tombstone_headers(),
    )

    assert_tombstone_response(response, expected_code=expected_code)
    assert model_count(PolicyDocument) == document_count_before
    assert model_count(PolicyAcceptance) == acceptance_count_before


def test_policy_document_create_tombstone_is_bodyless_and_non_mutating(
    client: TestClient,
) -> None:
    admin = create_admin_user(client)
    authenticate_client_as(client, admin["id"])
    submitted_content = f"submitted-policy-body-{unique_suffix()}"
    submitted_reference = f"submitted-managed-reference-{unique_suffix()}"
    policy_document_count_before = model_count(PolicyDocument)

    response = client.post(
        "/policy-documents",
        json={
            "policy_type": "privacy_policy",
            "version": f"v-{unique_suffix()[:8]}",
            "title": "Retired generic authoring",
            "content_text": submitted_content,
            "content_url": submitted_reference,
            "effective_at": datetime.now(UTC).isoformat(),
            "is_active": True,
        },
        headers=tombstone_headers(),
    )

    assert_tombstone_response(
        response,
        expected_code=POLICY_DOCUMENT_TOMBSTONE_CODE,
        absent_values=(submitted_content, submitted_reference),
    )
    assert model_count(PolicyDocument) == policy_document_count_before


def test_policy_document_update_tombstone_does_not_rewrite_managed_content(
    client: TestClient,
) -> None:
    admin = create_admin_user(client)
    policy_document = create_policy_document(client)
    authenticate_client_as(client, admin["id"])
    original_snapshot = get_policy_document_snapshot(policy_document["id"])
    submitted_content = f"replacement-policy-body-{unique_suffix()}"
    submitted_reference = f"replacement-managed-reference-{unique_suffix()}"

    response = client.patch(
        f"/policy-documents/{policy_document['id']}",
        json={
            "title": "Retired generic update",
            "content_text": submitted_content,
            "content_url": submitted_reference,
            "is_active": False,
        },
        headers=tombstone_headers(),
    )

    assert_tombstone_response(
        response,
        expected_code=POLICY_DOCUMENT_TOMBSTONE_CODE,
        absent_values=(submitted_content, submitted_reference),
    )
    assert get_policy_document_snapshot(policy_document["id"]) == original_snapshot


def test_policy_document_reads_remain_available_for_managed_records(
    client: TestClient,
) -> None:
    policy_document = create_policy_document(
        client,
        policy_type="terms_of_service",
        title="Managed Terms",
    )

    detail_response = client.get(
        f"/policy-documents/{policy_document['id']}",
        headers=tombstone_headers(),
    )
    list_response = client.get(
        "/policy-documents",
        params={"policy_type": "terms_of_service"},
        headers=tombstone_headers(),
    )

    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["id"] == policy_document["id"]
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == policy_document["id"] for item in list_response.json())


def test_policy_acceptance_create_tombstone_cannot_fabricate_evidence(
    client: TestClient,
) -> None:
    admin = create_admin_user(client)
    user = create_user(client)
    policy_document = create_policy_document(client)
    authenticate_client_as(client, admin["id"])
    submitted_time = datetime.now(UTC).isoformat()
    submitted_address = f"submitted-address-metadata-{unique_suffix()[:8]}"
    submitted_user_agent = f"submitted-user-agent-{unique_suffix()[:8]}"
    policy_acceptance_count_before = model_count(PolicyAcceptance)

    response = client.post(
        "/policy-acceptances",
        json={
            "user_id": user["id"],
            "policy_document_id": policy_document["id"],
            "accepted_at": submitted_time,
            "ip_address": submitted_address,
            "user_agent": submitted_user_agent,
        },
        headers=tombstone_headers(),
    )

    assert_tombstone_response(
        response,
        expected_code=POLICY_ACCEPTANCE_TOMBSTONE_CODE,
        absent_values=(submitted_time, submitted_address, submitted_user_agent),
    )
    assert model_count(PolicyAcceptance) == policy_acceptance_count_before


def test_policy_acceptance_update_tombstone_does_not_rewrite_evidence(
    client: TestClient,
) -> None:
    admin = create_admin_user(client)
    user = create_user(client)
    policy_document = create_policy_document(client)
    policy_acceptance = create_policy_acceptance(
        client,
        user["id"],
        policy_document["id"],
        accepted_at=datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
        ip_address="original-address-metadata",
        user_agent="original-user-agent",
    )
    authenticate_client_as(client, admin["id"])
    original_snapshot = get_policy_acceptance_snapshot(policy_acceptance["id"])
    submitted_time = datetime.now(UTC).isoformat()
    submitted_address = f"replacement-address-metadata-{unique_suffix()[:8]}"
    submitted_user_agent = f"replacement-user-agent-{unique_suffix()[:8]}"

    response = client.patch(
        f"/policy-acceptances/{policy_acceptance['id']}",
        json={
            "accepted_at": submitted_time,
            "ip_address": submitted_address,
            "user_agent": submitted_user_agent,
        },
        headers=tombstone_headers(),
    )

    assert_tombstone_response(
        response,
        expected_code=POLICY_ACCEPTANCE_TOMBSTONE_CODE,
        absent_values=(submitted_time, submitted_address, submitted_user_agent),
    )
    assert get_policy_acceptance_snapshot(policy_acceptance["id"]) == original_snapshot


def test_policy_acceptance_reads_remain_available_for_existing_records(
    client: TestClient,
) -> None:
    admin = create_admin_user(client)
    user = create_user(client)
    policy_document = create_policy_document(client)
    policy_acceptance = create_policy_acceptance(
        client,
        user["id"],
        policy_document["id"],
    )
    authenticate_client_as(client, admin["id"])

    detail_response = client.get(
        f"/policy-acceptances/{policy_acceptance['id']}",
        headers=tombstone_headers(),
    )
    list_response = client.get(
        "/policy-acceptances",
        params={
            "user_id": user["id"],
            "policy_document_id": policy_document["id"],
        },
        headers=tombstone_headers(),
    )

    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["id"] == policy_acceptance["id"]
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == policy_acceptance["id"] for item in list_response.json())
