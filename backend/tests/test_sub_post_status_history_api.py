from fastapi.testclient import TestClient

from backend.tests.helpers import authenticate_as, create_sub_post, create_user


def test_sub_post_status_history_records_create_and_cancel(client: TestClient):
    owner = create_user(client)
    post = create_sub_post(client, owner["id"])

    authenticate_as(owner["id"])
    initial_history_response = client.get(
        f"/need-a-sub/posts/{post['id']}/status-history"
    )
    assert initial_history_response.status_code == 200, initial_history_response.text
    initial_history = initial_history_response.json()
    assert len(initial_history) == 1
    assert initial_history[0]["old_status"] is None
    assert initial_history[0]["new_status"] == "active"

    cancel_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/cancel",
        json={"cancel_reason": "Weather."},
    )
    assert cancel_response.status_code == 200, cancel_response.text

    updated_history_response = client.get(
        f"/need-a-sub/posts/{post['id']}/status-history"
    )
    assert updated_history_response.status_code == 200, updated_history_response.text
    updated_history = updated_history_response.json()
    assert [row["new_status"] for row in updated_history] == ["active", "canceled"]


def test_sub_post_status_history_blocks_non_owner(client: TestClient):
    owner = create_user(client)
    other_user = create_user(client)
    post = create_sub_post(client, owner["id"])

    authenticate_as(other_user["id"])
    response = client.get(f"/need-a-sub/posts/{post['id']}/status-history")

    assert response.status_code == 403, response.text
