from fastapi.testclient import TestClient

from backend.tests.helpers import create_user, create_user_stats


def test_user_stats_create_get_list_and_update_counts(client: TestClient):
    user = create_user(client)
    user_stats = create_user_stats(client, user["id"])

    get_response = client.get(f"/user-stats/{user_stats['user_id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["user_id"] == user_stats["user_id"]

    list_response = client.get(f"/user-stats?user_id={user['id']}")
    assert list_response.status_code == 200, list_response.text
    assert any(item["user_id"] == user["id"] for item in list_response.json())

    patch_response = client.patch(
        f"/user-stats/{user['id']}",
        json={
            "games_played_count": 4,
            "games_hosted_completed_count": 2,
            "no_show_count": 1,
            "late_cancel_count": 1,
            "host_cancel_count": 0,
        },
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["games_played_count"] == 4
    assert patch_response.json()["games_hosted_completed_count"] == 2
    assert patch_response.json()["no_show_count"] == 1


def test_user_stats_reject_negative_count_on_create(client: TestClient):
    user = create_user(client)

    response = client.post(
        "/user-stats",
        json={
            "user_id": user["id"],
            "games_played_count": 1,
            "games_hosted_completed_count": 0,
            "no_show_count": -1,
            "late_cancel_count": 0,
            "host_cancel_count": 0,
        },
    )

    assert response.status_code == 400, response.text
    assert "no_show_count must be greater than or equal to 0" in response.text


def test_user_stats_reject_negative_count_on_update(client: TestClient):
    user = create_user(client)
    create_user_stats(client, user["id"])

    response = client.patch(
        f"/user-stats/{user['id']}",
        json={"late_cancel_count": -1},
    )

    assert response.status_code == 400, response.text
    assert "late_cancel_count must be greater than or equal to 0" in response.text


def test_user_stats_reject_missing_user(client: TestClient):
    response = client.post(
        "/user-stats",
        json={
            "user_id": "00000000-0000-4000-8000-000000000000",
            "games_played_count": 1,
            "games_hosted_completed_count": 0,
            "no_show_count": 0,
            "late_cancel_count": 0,
            "host_cancel_count": 0,
        },
    )

    assert response.status_code == 404, response.text
    assert "User not found" in response.text


def test_user_stats_reject_duplicate_user_stats(client: TestClient):
    user = create_user(client)
    create_user_stats(client, user["id"])

    response = client.post(
        "/user-stats",
        json={
            "user_id": user["id"],
            "games_played_count": 5,
            "games_hosted_completed_count": 0,
            "no_show_count": 0,
            "late_cancel_count": 0,
            "host_cancel_count": 0,
        },
    )

    assert response.status_code == 409, response.text
    assert "This user already has stats" in response.text


def test_user_stats_treat_soft_deleted_user_as_unavailable(client: TestClient):
    user = create_user(client)
    user_stats = create_user_stats(client, user["id"])

    delete_response = client.delete(f"/users/{user['id']}")
    assert delete_response.status_code == 200, delete_response.text

    get_response = client.get(f"/user-stats/{user_stats['user_id']}")
    assert get_response.status_code == 404, get_response.text
    assert "User not found" in get_response.text

    patch_response = client.patch(
        f"/user-stats/{user_stats['user_id']}",
        json={"games_played_count": 5},
    )
    assert patch_response.status_code == 404, patch_response.text
    assert "User not found" in patch_response.text

    list_response = client.get("/user-stats")
    assert list_response.status_code == 200, list_response.text
    assert all(item["user_id"] != user["id"] for item in list_response.json())
