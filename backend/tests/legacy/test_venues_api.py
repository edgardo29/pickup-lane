from fastapi.testclient import TestClient

from backend.tests.helpers import (
    authenticate_as,
    create_user,
    create_venue,
    run_as_temporary_admin,
    set_user_role,
)


def test_venues_create_get_list_update_and_soft_delete(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])

    get_response = client.get(f"/venues/{venue['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == venue["id"]

    list_response = client.get("/venues")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == venue["id"] for item in list_response.json())

    patch_response = run_as_temporary_admin(
        client,
        lambda: client.patch(
            f"/venues/{venue['id']}",
            json={"name": "Updated Test Field"},
        ),
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["name"] == "Updated Test Field"

    delete_response = run_as_temporary_admin(
        client,
        lambda: client.delete(f"/venues/{venue['id']}"),
    )
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["deleted_at"] is not None


def test_venues_reject_approved_without_approver(client: TestClient):
    response = run_as_temporary_admin(
        client,
        lambda: client.post(
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
        ),
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

    duplicate_response = run_as_temporary_admin(
        client,
        lambda: client.post(
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
        ),
    )

    assert duplicate_response.status_code == 201, duplicate_response.text
    assert duplicate_response.json()["id"] == venue["id"]

    list_response = client.get("/venues")
    assert list_response.status_code == 200, list_response.text
    matching_venues = [
        item for item in list_response.json() if item["name"] == "Reusable Field"
    ]
    assert len(matching_venues) == 1


def test_public_venues_reject_inactive_listing_and_hide_inactive_detail(
    client: TestClient,
):
    user = create_user(client)
    venue = create_venue(client, user["id"], is_active=False, venue_status="inactive")

    list_response = client.get("/venues?include_inactive=true")
    assert list_response.status_code == 403, list_response.text

    get_response = client.get(f"/venues/{venue['id']}")
    assert get_response.status_code == 404, get_response.text


def test_venue_mutations_require_admin_access(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    authenticate_as(user["id"])

    create_response = client.post(
        "/venues",
        json={
            "name": "Denied Field",
            "address_line_1": "400 Denied Ave",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "country_code": "US",
        },
    )
    patch_response = client.patch(
        f"/venues/{venue['id']}",
        json={"name": "Denied Update"},
    )
    delete_response = client.delete(f"/venues/{venue['id']}")

    assert create_response.status_code == 403, create_response.text
    assert patch_response.status_code == 403, patch_response.text
    assert delete_response.status_code == 403, delete_response.text


def test_venue_mutations_reject_player(client: TestClient):
    user = create_user(client)
    venue = create_venue(client, user["id"])
    player = create_user(client)
    authenticate_as(player["id"])

    patch_response = client.patch(
        f"/venues/{venue['id']}",
        json={"name": "Denied Player Update"},
    )
    delete_response = client.delete(f"/venues/{venue['id']}")

    assert patch_response.status_code == 403, patch_response.text
    assert delete_response.status_code == 403, delete_response.text
