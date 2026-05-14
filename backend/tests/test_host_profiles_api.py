from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.tests.helpers import create_host_profile, create_user


def test_host_profile_create_get_list_and_update_defaults(client: TestClient):
    user = create_user(client)
    host_profile = create_host_profile(client, user["id"])

    get_response = client.get(f"/host-profiles/{host_profile['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == host_profile["id"]

    list_response = client.get(f"/host-profiles?user_id={user['id']}")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == host_profile["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/host-profiles/{host_profile['id']}",
        json={
            "default_payment_methods": ["zelle", "cash"],
            "default_payment_due_timing": "at_arrival",
            "default_player_message": "Message players after they join.",
        },
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["default_payment_methods"] == ["zelle", "cash"]
    assert patch_response.json()["default_payment_due_timing"] == "at_arrival"


def test_host_profile_reject_duplicate_user(client: TestClient):
    user = create_user(client)
    create_host_profile(client, user["id"])

    response = client.post(
        "/host-profiles",
        json={
            "user_id": user["id"],
            "default_payment_methods": ["venmo"],
        },
    )

    assert response.status_code == 409, response.text
    assert "already has a host profile" in response.text


def test_host_profile_requires_setup_fields_before_completion(client: TestClient):
    user = create_user(client)

    response = client.post(
        "/host-profiles",
        json={
            "user_id": user["id"],
            "host_setup_completed_at": datetime.now(UTC).isoformat(),
        },
    )

    assert response.status_code == 400, response.text
    assert "host_setup_completed_at requires" in response.text
