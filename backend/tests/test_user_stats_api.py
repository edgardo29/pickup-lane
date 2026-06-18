from fastapi.testclient import TestClient

from backend.tests.helpers import (
    authenticate_as,
    create_user,
    create_user_stats,
    set_user_role,
    soft_delete_user,
)


def authenticate_admin(client: TestClient) -> dict:
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    authenticate_as(admin["id"])
    return admin


def test_user_stats_create_get_list_and_update_counts(client: TestClient):
    authenticate_admin(client)
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


def test_user_stats_scaffold_routes_reject_regular_user(client: TestClient):
    user = create_user(client)
    create_user_stats(client, user["id"])
    authenticate_as(user["id"])

    get_response = client.get(f"/user-stats/{user['id']}")
    assert get_response.status_code == 403, get_response.text

    list_response = client.get(f"/user-stats?user_id={user['id']}")
    assert list_response.status_code == 403, list_response.text

    create_response = client.post(
        "/user-stats",
        json={
            "user_id": user["id"],
            "games_played_count": 1,
            "games_hosted_completed_count": 0,
            "no_show_count": 0,
            "late_cancel_count": 0,
            "host_cancel_count": 0,
        },
    )
    assert create_response.status_code == 403, create_response.text

    patch_response = client.patch(
        f"/user-stats/{user['id']}",
        json={"games_played_count": 5},
    )
    assert patch_response.status_code == 403, patch_response.text


def test_user_stats_me_reads_authenticated_user_stats(client: TestClient):
    current_user = create_user(client)
    other_user = create_user(client)
    current_stats = create_user_stats(
        client,
        current_user["id"],
        games_played_count=3,
    )
    other_stats = create_user_stats(
        client,
        other_user["id"],
        games_played_count=9,
    )
    authenticate_as(current_user["id"])

    response = client.get("/user-stats/me")

    assert response.status_code == 200, response.text
    assert response.json()["user_id"] == current_stats["user_id"]
    assert response.json()["games_played_count"] == 3
    assert response.json()["user_id"] != other_stats["user_id"]


def test_user_stats_me_returns_not_found_for_missing_stats(client: TestClient):
    user = create_user(client)
    authenticate_as(user["id"])

    response = client.get("/user-stats/me")

    assert response.status_code == 404, response.text
    assert "User stats not found" in response.text


def test_user_stats_reject_negative_count_on_create(client: TestClient):
    authenticate_admin(client)
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
    authenticate_admin(client)
    user = create_user(client)
    create_user_stats(client, user["id"])

    response = client.patch(
        f"/user-stats/{user['id']}",
        json={"late_cancel_count": -1},
    )

    assert response.status_code == 400, response.text
    assert "late_cancel_count must be greater than or equal to 0" in response.text


def test_user_stats_reject_missing_user(client: TestClient):
    authenticate_admin(client)
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
    authenticate_admin(client)
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
    authenticate_admin(client)
    user = create_user(client)
    user_stats = create_user_stats(client, user["id"])

    soft_delete_user(user["id"])

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
