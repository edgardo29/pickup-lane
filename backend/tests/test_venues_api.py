from fastapi.testclient import TestClient

from backend.tests.helpers import create_user, create_venue


def test_venues_create_get_list_update_and_soft_delete(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])

    get_response = client.get(f"/venues/{venue['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == venue["id"]

    list_response = client.get("/venues")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == venue["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/venues/{venue['id']}",
        json={"name": "Updated Test Field"},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["name"] == "Updated Test Field"

    delete_response = client.delete(f"/venues/{venue['id']}")
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["deleted_at"] is not None


def test_venues_reject_approved_without_approver(client: TestClient):
    response = client.post(
        "/venues",
        json={
            "name": "Needs Approver",
            "address_line_1": "999 Test Ave",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "country_code": "US",
            "venue_status": "approved",
        },
    )

    assert response.status_code == 400, response.text
    assert "approved_by_user_id" in response.text


def test_venues_reuse_matching_active_venue(client: TestClient):
    user = create_user(client)
    venue = create_venue(
        client,
        user["id"],
        name="Reusable Field",
        address_line_1="500 Match Ave",
        city="Chicago",
        state="IL",
        postal_code="60607",
        neighborhood="West Loop",
    )

    duplicate_response = client.post(
        "/venues",
        json={
            "name": "Reusable Field",
            "address_line_1": "500 Match Ave",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60607",
            "country_code": "US",
            "neighborhood": "West Loop",
            "venue_status": "approved",
            "created_by_user_id": user["id"],
            "approved_by_user_id": user["id"],
            "is_active": True,
        },
    )

    assert duplicate_response.status_code == 201, duplicate_response.text
    assert duplicate_response.json()["id"] == venue["id"]

    list_response = client.get("/venues")
    assert list_response.status_code == 200, list_response.text
    matching_venues = [
        item for item in list_response.json() if item["name"] == "Reusable Field"
    ]
    assert len(matching_venues) == 1
