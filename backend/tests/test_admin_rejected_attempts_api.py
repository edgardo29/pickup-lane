from uuid import uuid4

from fastapi.testclient import TestClient

from backend.tests.helpers import authenticate_as, create_user, set_user_role


def test_moderator_credit_issue_denial_logs_preload_rejected_attempt(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    player = create_user(client)

    authenticate_as(moderator["id"])
    response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 2500,
            "credit_reason": "admin_credit",
            "idempotency_key": "denied-credit-issue",
            "note": "Should not leak into rejected-attempt metadata.",
        },
    )

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text

    authenticate_as(admin["id"])
    list_response = client.get(
        "/admin/rejected-attempts?attempt_type=issue_credit_rejected"
    )

    assert list_response.status_code == 200, list_response.text
    rejected_attempts = list_response.json()
    assert len(rejected_attempts) == 1

    rejected_attempt = rejected_attempts[0]
    assert rejected_attempt["admin_user_id"] == moderator["id"]
    assert rejected_attempt["attempt_type"] == "issue_credit_rejected"
    assert rejected_attempt["rejection_mode"] == "permission_denied_preload"
    assert rejected_attempt["response_status_code"] == 403
    assert rejected_attempt["route_method"] == "POST"
    assert rejected_attempt["route_path"] == "/admin/game-credits/issue"
    assert rejected_attempt["target_user_id"] is None
    assert rejected_attempt["target_game_credit_id"] is None

    metadata = rejected_attempt["metadata"]
    assert metadata["required_permission"] == "admin.money.credit_manage"
    assert metadata["attempted_refs_unverified"] == {"user_id": player["id"]}
    assert "note" not in metadata
    assert "idempotency_key" not in metadata

    get_response = client.get(f"/admin/rejected-attempts/{rejected_attempt['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == rejected_attempt["id"]


def test_moderator_credit_reversal_denial_logs_unverified_credit_id(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    attempted_credit_id = str(uuid4())

    authenticate_as(moderator["id"])
    response = client.post(
        f"/admin/game-credits/{attempted_credit_id}/reverse",
        json={
            "idempotency_key": "denied-credit-reverse",
            "note": "Should not leak into rejected-attempt metadata.",
        },
    )

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text

    authenticate_as(admin["id"])
    list_response = client.get(
        "/admin/rejected-attempts?attempt_type=reverse_credit_rejected"
    )

    assert list_response.status_code == 200, list_response.text
    rejected_attempts = list_response.json()
    assert len(rejected_attempts) == 1

    rejected_attempt = rejected_attempts[0]
    assert rejected_attempt["admin_user_id"] == moderator["id"]
    assert rejected_attempt["attempt_type"] == "reverse_credit_rejected"
    assert rejected_attempt["rejection_mode"] == "permission_denied_preload"
    assert rejected_attempt["route_path"] == (
        "/admin/game-credits/{game_credit_id}/reverse"
    )
    assert rejected_attempt["target_user_id"] is None
    assert rejected_attempt["target_game_credit_id"] is None

    metadata = rejected_attempt["metadata"]
    assert metadata["required_permission"] == "admin.money.credit_manage"
    assert metadata["attempted_refs_unverified"] == {
        "game_credit_id": attempted_credit_id
    }
    assert "note" not in metadata
    assert "idempotency_key" not in metadata


def test_moderator_cannot_read_rejected_attempts(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    player = create_user(client)

    authenticate_as(moderator["id"])
    denied_response = client.post(
        "/admin/game-credits/issue",
        json={
            "user_id": player["id"],
            "amount_cents": 2500,
            "credit_reason": "admin_credit",
        },
    )
    read_response = client.get("/admin/rejected-attempts")

    assert denied_response.status_code == 403, denied_response.text
    assert read_response.status_code == 403, read_response.text

    authenticate_as(admin["id"])
    admin_response = client.get("/admin/rejected-attempts")
    assert admin_response.status_code == 200, admin_response.text
    assert len(admin_response.json()) == 1
