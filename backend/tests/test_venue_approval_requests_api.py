from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.tests.helpers import (
    create_user,
    create_venue,
    create_venue_approval_request,
)


def create_venue_approval_request_setup(client: TestClient) -> tuple[dict, dict, dict]:
    user = create_user(client)
    reviewer = create_user(client)
    venue = create_venue(client, reviewer["id"])
    return user, reviewer, venue


def test_venue_approval_request_create_get_list_and_approve(client: TestClient):
    user, reviewer, venue = create_venue_approval_request_setup(client)

    venue_request = create_venue_approval_request(
        client,
        user["id"],
        requested_country_code="us",
    )
    assert venue_request["requested_country_code"] == "US"

    get_response = client.get(f"/venue-approval-requests/{venue_request['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == venue_request["id"]

    list_by_user_response = client.get(
        f"/venue-approval-requests?submitted_by_user_id={user['id']}"
    )
    assert list_by_user_response.status_code == 200, list_by_user_response.text
    assert any(item["id"] == venue_request["id"] for item in list_by_user_response.json())

    list_by_status_response = client.get(
        "/venue-approval-requests?request_status=pending_review"
    )
    assert list_by_status_response.status_code == 200, list_by_status_response.text
    assert any(
        item["id"] == venue_request["id"] for item in list_by_status_response.json()
    )

    patch_response = client.patch(
        f"/venue-approval-requests/{venue_request['id']}",
        json={
            "request_status": "approved",
            "venue_id": venue["id"],
            "reviewed_by_user_id": reviewer["id"],
            "reviewed_at": datetime.now(UTC).isoformat(),
            "review_notes": "Approved from CI test.",
        },
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["request_status"] == "approved"
    assert patch_response.json()["venue_id"] == venue["id"]
    assert patch_response.json()["reviewed_by_user_id"] == reviewer["id"]


def test_venue_approval_request_reject_approved_without_venue_id(client: TestClient):
    user, reviewer, _venue = create_venue_approval_request_setup(client)
    venue_request = create_venue_approval_request(client, user["id"])

    response = client.patch(
        f"/venue-approval-requests/{venue_request['id']}",
        json={
            "request_status": "approved",
            "venue_id": None,
            "reviewed_by_user_id": reviewer["id"],
            "reviewed_at": datetime.now(UTC).isoformat(),
            "review_notes": "Approved without venue should fail.",
        },
    )

    assert response.status_code == 400, response.text
    assert "Approved venue approval requests require venue_id" in response.text


def test_venue_approval_request_reject_reviewed_status_without_reviewed_at(
    client: TestClient,
):
    user, reviewer, _venue = create_venue_approval_request_setup(client)
    venue_request = create_venue_approval_request(client, user["id"])

    response = client.patch(
        f"/venue-approval-requests/{venue_request['id']}",
        json={
            "request_status": "rejected",
            "reviewed_by_user_id": reviewer["id"],
            "review_notes": "Rejected without reviewed_at should fail.",
        },
    )

    assert response.status_code == 400, response.text
    assert "Reviewed venue approval requests require reviewed_at" in response.text


def test_venue_approval_request_reject_reviewed_status_without_reviewer(
    client: TestClient,
):
    user, _reviewer, _venue = create_venue_approval_request_setup(client)
    venue_request = create_venue_approval_request(client, user["id"])

    response = client.patch(
        f"/venue-approval-requests/{venue_request['id']}",
        json={
            "request_status": "rejected",
            "reviewed_at": datetime.now(UTC).isoformat(),
            "review_notes": "Rejected without reviewer should fail.",
        },
    )

    assert response.status_code == 400, response.text
    assert "reviewed_by_user_id" in response.text


def test_venue_approval_request_reject_invalid_request_status(client: TestClient):
    user = create_user(client)

    response = client.post(
        "/venue-approval-requests",
        json={
            "submitted_by_user_id": user["id"],
            "requested_name": "Bad Status Field",
            "requested_address_line_1": "123 Bad Status Ave",
            "requested_city": "Chicago",
            "requested_state": "IL",
            "requested_postal_code": "60601",
            "requested_country_code": "US",
            "request_status": "waiting",
        },
    )

    assert response.status_code == 400, response.text
    assert "request_status is not supported" in response.text


def test_venue_approval_request_reject_invalid_country_code(client: TestClient):
    user = create_user(client)

    response = client.post(
        "/venue-approval-requests",
        json={
            "submitted_by_user_id": user["id"],
            "requested_name": "Bad Country Code Field",
            "requested_address_line_1": "123 Bad Country Ave",
            "requested_city": "Chicago",
            "requested_state": "IL",
            "requested_postal_code": "60601",
            "requested_country_code": "USA",
        },
    )

    assert response.status_code == 400, response.text
    assert "requested_country_code must be exactly 2 characters" in response.text


def test_venue_approval_request_reject_empty_requested_name(client: TestClient):
    user = create_user(client)

    response = client.post(
        "/venue-approval-requests",
        json={
            "submitted_by_user_id": user["id"],
            "requested_name": "   ",
            "requested_address_line_1": "123 Empty Name Ave",
            "requested_city": "Chicago",
            "requested_state": "IL",
            "requested_postal_code": "60601",
            "requested_country_code": "US",
        },
    )

    assert response.status_code == 400, response.text
    assert "requested_name must not be empty" in response.text


def test_venue_approval_request_reject_empty_country_code(client: TestClient):
    user = create_user(client)

    response = client.post(
        "/venue-approval-requests",
        json={
            "submitted_by_user_id": user["id"],
            "requested_name": "Empty Country Code Field",
            "requested_address_line_1": "123 Empty Country Ave",
            "requested_city": "Chicago",
            "requested_state": "IL",
            "requested_postal_code": "60601",
            "requested_country_code": "  ",
        },
    )

    assert response.status_code == 400, response.text
    assert "requested_country_code must not be empty" in response.text


def test_venue_approval_request_reject_missing_submitter(client: TestClient):
    response = client.post(
        "/venue-approval-requests",
        json={
            "submitted_by_user_id": "00000000-0000-4000-8000-000000000000",
            "requested_name": "Missing Submitter Field",
            "requested_address_line_1": "123 Missing Submitter Ave",
            "requested_city": "Chicago",
            "requested_state": "IL",
            "requested_postal_code": "60601",
            "requested_country_code": "US",
        },
    )

    assert response.status_code == 404, response.text
    assert "Submitted by user not found" in response.text


def test_venue_approval_request_reject_missing_venue_on_approval(client: TestClient):
    user = create_user(client)
    reviewer = create_user(client)
    venue_request = create_venue_approval_request(client, user["id"])

    response = client.patch(
        f"/venue-approval-requests/{venue_request['id']}",
        json={
            "request_status": "approved",
            "venue_id": "00000000-0000-4000-8000-000000000000",
            "reviewed_by_user_id": reviewer["id"],
            "reviewed_at": datetime.now(UTC).isoformat(),
            "review_notes": "Missing venue approval test.",
        },
    )

    assert response.status_code == 404, response.text
    assert "Venue not found" in response.text
