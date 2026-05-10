from fastapi.testclient import TestClient

from backend.tests.helpers import authenticate_as, create_sub_post, create_user


def test_sub_post_request_status_history_records_request_and_accept(client: TestClient):
    owner = create_user(client)
    requester = create_user(client)
    post = create_sub_post(client, owner["id"])

    authenticate_as(requester["id"])
    request_response = client.post(
        f"/need-a-sub/posts/{post['id']}/requests",
        json={"sub_post_position_id": post["positions"][0]["id"]},
    )
    assert request_response.status_code == 201, request_response.text
    request = request_response.json()

    history_response = client.get(
        f"/need-a-sub/requests/{request['id']}/status-history"
    )
    assert history_response.status_code == 200, history_response.text
    history = history_response.json()
    assert len(history) == 1
    assert history[0]["new_status"] == "pending"
    assert history[0]["change_source"] == "requester"

    authenticate_as(owner["id"])
    accept_response = client.patch(f"/need-a-sub/requests/{request['id']}/accept")
    assert accept_response.status_code == 200, accept_response.text

    owner_history_response = client.get(
        f"/need-a-sub/requests/{request['id']}/status-history"
    )
    assert owner_history_response.status_code == 200, owner_history_response.text
    owner_history = owner_history_response.json()
    assert [row["new_status"] for row in owner_history] == ["pending", "confirmed"]


def test_sub_post_request_status_history_blocks_unrelated_user(client: TestClient):
    owner = create_user(client)
    requester = create_user(client)
    unrelated = create_user(client)
    post = create_sub_post(client, owner["id"])

    authenticate_as(requester["id"])
    request = client.post(
        f"/need-a-sub/posts/{post['id']}/requests",
        json={"sub_post_position_id": post["positions"][0]["id"]},
    ).json()

    authenticate_as(unrelated["id"])
    response = client.get(f"/need-a-sub/requests/{request['id']}/status-history")

    assert response.status_code == 403, response.text
