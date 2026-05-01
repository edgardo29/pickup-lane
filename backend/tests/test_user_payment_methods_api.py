from fastapi.testclient import TestClient

from backend.tests.helpers import create_user, create_user_payment_method


def test_user_payment_methods_create_get_list_and_update(client: TestClient):
    user = create_user(client)
    payment_method = create_user_payment_method(client, user["id"])

    get_response = client.get(f"/user-payment-methods/{payment_method['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == payment_method["id"]

    list_response = client.get(f"/user-payment-methods?user_id={user['id']}")
    assert list_response.status_code == 200, list_response.text
    assert len(list_response.json()) == 1

    patch_response = client.patch(
        f"/user-payment-methods/{payment_method['id']}",
        json={"is_active": False},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["is_active"] is False
    assert patch_response.json()["is_default"] is False


def test_user_payment_methods_reject_duplicate_provider_id(client: TestClient):
    user = create_user(client)
    create_user_payment_method(
        client, user["id"], provider_payment_method_id="pm_duplicate_test"
    )

    duplicate_response = client.post(
        "/user-payment-methods",
        json={
            "user_id": user["id"],
            "provider_payment_method_id": "pm_duplicate_test",
        },
    )

    assert duplicate_response.status_code == 409, duplicate_response.text
    assert "provider_payment_method_id already exists" in duplicate_response.text
