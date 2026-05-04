from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.tests.helpers import (
    create_policy_acceptance,
    create_policy_document,
    create_user,
)


def create_policy_acceptance_setup(client: TestClient) -> tuple[dict, dict]:
    user = create_user(client)
    policy_document = create_policy_document(client)
    return user, policy_document


def test_policy_acceptance_create_get_list_and_update_metadata(client: TestClient):
    user, policy_document = create_policy_acceptance_setup(client)
    policy_acceptance = create_policy_acceptance(
        client,
        user["id"],
        policy_document["id"],
    )

    get_response = client.get(f"/policy-acceptances/{policy_acceptance['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == policy_acceptance["id"]

    list_by_user_response = client.get(f"/policy-acceptances?user_id={user['id']}")
    assert list_by_user_response.status_code == 200, list_by_user_response.text
    assert any(
        item["id"] == policy_acceptance["id"]
        for item in list_by_user_response.json()
    )

    list_by_document_response = client.get(
        f"/policy-acceptances?policy_document_id={policy_document['id']}"
    )
    assert list_by_document_response.status_code == 200, list_by_document_response.text
    assert any(
        item["id"] == policy_acceptance["id"]
        for item in list_by_document_response.json()
    )

    patch_response = client.patch(
        f"/policy-acceptances/{policy_acceptance['id']}",
        json={
            "ip_address": "192.168.1.10",
            "user_agent": "Corrected CI user agent",
        },
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["ip_address"] == "192.168.1.10"
    assert patch_response.json()["user_agent"] == "Corrected CI user agent"


def test_policy_acceptance_can_update_accepted_at(client: TestClient):
    user, policy_document = create_policy_acceptance_setup(client)
    policy_acceptance = create_policy_acceptance(
        client,
        user["id"],
        policy_document["id"],
    )
    corrected_accepted_at = datetime.now(UTC).isoformat()

    response = client.patch(
        f"/policy-acceptances/{policy_acceptance['id']}",
        json={"accepted_at": corrected_accepted_at},
    )

    assert response.status_code == 200, response.text
    assert response.json()["accepted_at"] is not None


def test_policy_acceptance_reject_duplicate_user_policy_document(
    client: TestClient,
):
    user, policy_document = create_policy_acceptance_setup(client)
    create_policy_acceptance(client, user["id"], policy_document["id"])

    response = client.post(
        "/policy-acceptances",
        json={
            "user_id": user["id"],
            "policy_document_id": policy_document["id"],
            "ip_address": "127.0.0.1",
            "user_agent": "Duplicate CI acceptance",
        },
    )

    assert response.status_code == 409, response.text
    assert "This user has already accepted this policy document" in response.text


def test_policy_acceptance_reject_missing_user(client: TestClient):
    policy_document = create_policy_document(client)

    response = client.post(
        "/policy-acceptances",
        json={
            "user_id": "00000000-0000-4000-8000-000000000000",
            "policy_document_id": policy_document["id"],
            "ip_address": "127.0.0.1",
            "user_agent": "Missing user test",
        },
    )

    assert response.status_code == 404, response.text
    assert "User not found" in response.text


def test_policy_acceptance_reject_missing_policy_document(client: TestClient):
    user = create_user(client)

    response = client.post(
        "/policy-acceptances",
        json={
            "user_id": user["id"],
            "policy_document_id": "00000000-0000-4000-8000-000000000000",
            "ip_address": "127.0.0.1",
            "user_agent": "Missing policy document test",
        },
    )

    assert response.status_code == 404, response.text
    assert "Policy document not found" in response.text


def test_policy_acceptance_reject_inactive_policy_document(client: TestClient):
    user = create_user(client)
    policy_document = create_policy_document(client, is_active=False)

    response = client.post(
        "/policy-acceptances",
        json={
            "user_id": user["id"],
            "policy_document_id": policy_document["id"],
            "ip_address": "127.0.0.1",
            "user_agent": "Inactive policy document test",
        },
    )

    assert response.status_code == 400, response.text
    assert "active, non-retired policy document" in response.text


def test_policy_acceptance_reject_retired_policy_document(client: TestClient):
    user = create_user(client)
    effective_at = datetime.now(UTC)
    policy_document = create_policy_document(
        client,
        effective_at=effective_at.isoformat(),
        retired_at=(effective_at.replace(year=effective_at.year + 1)).isoformat(),
        is_active=False,
    )

    response = client.post(
        "/policy-acceptances",
        json={
            "user_id": user["id"],
            "policy_document_id": policy_document["id"],
            "ip_address": "127.0.0.1",
            "user_agent": "Retired policy document test",
        },
    )

    assert response.status_code == 400, response.text
    assert "active, non-retired policy document" in response.text


def test_policy_acceptance_reject_future_effective_policy_document(
    client: TestClient,
):
    user = create_user(client)
    policy_document = create_policy_document(
        client,
        effective_at="2999-01-01T00:00:00+00:00",
    )

    response = client.post(
        "/policy-acceptances",
        json={
            "user_id": user["id"],
            "policy_document_id": policy_document["id"],
            "ip_address": "127.0.0.1",
            "user_agent": "Future policy document test",
        },
    )

    assert response.status_code == 400, response.text
    assert "already effective" in response.text


def test_policy_acceptance_reject_null_accepted_at_update(client: TestClient):
    user, policy_document = create_policy_acceptance_setup(client)
    policy_acceptance = create_policy_acceptance(
        client,
        user["id"],
        policy_document["id"],
    )

    response = client.patch(
        f"/policy-acceptances/{policy_acceptance['id']}",
        json={"accepted_at": None},
    )

    assert response.status_code == 400, response.text
    assert "accepted_at cannot be null" in response.text
