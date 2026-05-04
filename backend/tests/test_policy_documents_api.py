from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from backend.tests.helpers import create_policy_document


def test_policy_document_create_get_list_and_update_content(client: TestClient):
    policy_document = create_policy_document(client)

    get_response = client.get(f"/policy-documents/{policy_document['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == policy_document["id"]

    list_by_type_response = client.get(
        f"/policy-documents?policy_type={policy_document['policy_type']}"
    )
    assert list_by_type_response.status_code == 200, list_by_type_response.text
    assert any(
        item["id"] == policy_document["id"] for item in list_by_type_response.json()
    )

    list_active_response = client.get("/policy-documents?is_active=true")
    assert list_active_response.status_code == 200, list_active_response.text
    assert any(item["id"] == policy_document["id"] for item in list_active_response.json())

    patch_response = client.patch(
        f"/policy-documents/{policy_document['id']}",
        json={
            "title": "CI Privacy Policy Updated",
            "content_text": "Updated CI policy document content.",
        },
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["title"] == "CI Privacy Policy Updated"
    assert patch_response.json()["content_text"] == "Updated CI policy document content."


def test_policy_document_can_be_retired(client: TestClient):
    effective_at = datetime.now(UTC)
    retired_at = effective_at + timedelta(days=30)
    policy_document = create_policy_document(
        client,
        effective_at=effective_at.isoformat(),
    )

    response = client.patch(
        f"/policy-documents/{policy_document['id']}",
        json={
            "retired_at": retired_at.isoformat(),
            "is_active": False,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False
    assert response.json()["retired_at"] is not None


def test_policy_document_reject_invalid_policy_type(client: TestClient):
    response = client.post(
        "/policy-documents",
        json={
            "policy_type": "bad_policy",
            "version": "v1.0",
            "title": "Bad Policy",
            "content_text": "Bad policy content.",
            "effective_at": datetime.now(UTC).isoformat(),
            "is_active": True,
        },
    )

    assert response.status_code == 400, response.text
    assert "policy_type is not supported" in response.text


def test_policy_document_reject_missing_content(client: TestClient):
    response = client.post(
        "/policy-documents",
        json={
            "policy_type": "privacy_policy",
            "version": "v1.0",
            "title": "Missing Content Policy",
            "content_url": None,
            "content_text": None,
            "effective_at": datetime.now(UTC).isoformat(),
            "is_active": True,
        },
    )

    assert response.status_code == 400, response.text
    assert "At least one of content_url or content_text must be provided" in response.text


def test_policy_document_reject_whitespace_only_content(client: TestClient):
    response = client.post(
        "/policy-documents",
        json={
            "policy_type": "privacy_policy",
            "version": "v1.0",
            "title": "Whitespace Content Policy",
            "content_url": "   ",
            "content_text": "   ",
            "effective_at": datetime.now(UTC).isoformat(),
            "is_active": True,
        },
    )

    assert response.status_code == 400, response.text
    assert "At least one of content_url or content_text must be provided" in response.text


def test_policy_document_reject_duplicate_policy_type_version(client: TestClient):
    create_policy_document(
        client,
        policy_type="terms_of_service",
        version="v1.0",
    )

    response = client.post(
        "/policy-documents",
        json={
            "policy_type": "terms_of_service",
            "version": "v1.0",
            "title": "Duplicate Terms",
            "content_text": "Duplicate terms content.",
            "effective_at": datetime.now(UTC).isoformat(),
            "is_active": True,
        },
    )

    assert response.status_code == 409, response.text
    assert "This policy type and version already exists" in response.text


def test_policy_document_reject_retired_before_effective(client: TestClient):
    effective_at = datetime.now(UTC)
    policy_document = create_policy_document(
        client,
        effective_at=effective_at.isoformat(),
    )

    response = client.patch(
        f"/policy-documents/{policy_document['id']}",
        json={
            "retired_at": (effective_at - timedelta(days=1)).isoformat(),
        },
    )

    assert response.status_code == 400, response.text
    assert "retired_at must be greater than effective_at" in response.text


def test_policy_document_reject_empty_title(client: TestClient):
    response = client.post(
        "/policy-documents",
        json={
            "policy_type": "privacy_policy",
            "version": "v1.0",
            "title": "   ",
            "content_text": "Policy content.",
            "effective_at": datetime.now(UTC).isoformat(),
            "is_active": True,
        },
    )

    assert response.status_code == 400, response.text
    assert "title must not be empty" in response.text
