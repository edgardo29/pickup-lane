from uuid import UUID

from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.services.admin_rejected_attempt_policy import (
    REJECTION_DOMAIN_REJECTED_POSTLOAD,
)
from backend.services.admin_rejected_attempt_service import record_admin_rejected_attempt
from backend.tests.helpers import authenticate_as, create_user, set_user_role


def create_domain_rejected_attempt(admin: dict, target_user: dict) -> str:
    with SessionLocal() as db:
        rejected_attempt = record_admin_rejected_attempt(
            db,
            admin_user_id=UUID(admin["id"]),
            attempt_type="delete_user_rejected",
            rejection_mode=REJECTION_DOMAIN_REJECTED_POSTLOAD,
            response_status_code=400,
            route_method="POST",
            route_path="/admin/users/{user_id}/delete",
            target_user_id=UUID(target_user["id"]),
            metadata={"reason_code": "last_active_admin"},
        )
        return str(rejected_attempt.id)


def test_admin_reads_domain_rejected_attempt(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    target_user = create_user(client)
    rejected_attempt_id = create_domain_rejected_attempt(admin, target_user)

    authenticate_as(admin["id"])
    list_response = client.get(
        "/admin/rejected-attempts?attempt_type=delete_user_rejected"
    )

    assert list_response.status_code == 200, list_response.text
    rejected_attempts = list_response.json()
    assert len(rejected_attempts) == 1

    rejected_attempt = rejected_attempts[0]
    assert rejected_attempt["id"] == rejected_attempt_id
    assert rejected_attempt["admin_user_id"] == admin["id"]
    assert rejected_attempt["attempt_type"] == "delete_user_rejected"
    assert rejected_attempt["rejection_mode"] == REJECTION_DOMAIN_REJECTED_POSTLOAD
    assert rejected_attempt["response_status_code"] == 400
    assert rejected_attempt["route_method"] == "POST"
    assert rejected_attempt["route_path"] == "/admin/users/{user_id}/delete"
    assert rejected_attempt["target_user_id"] == target_user["id"]
    assert rejected_attempt["metadata"] == {"reason_code": "last_active_admin"}

    get_response = client.get(f"/admin/rejected-attempts/{rejected_attempt_id}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == rejected_attempt_id


def test_player_cannot_read_rejected_attempts(client: TestClient):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    target_user = create_user(client)
    create_domain_rejected_attempt(admin, target_user)
    player = create_user(client)

    authenticate_as(player["id"])
    response = client.get("/admin/rejected-attempts")

    assert response.status_code == 403, response.text
    assert "Admin access required" in response.text
