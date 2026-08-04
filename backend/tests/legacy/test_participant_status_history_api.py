from fastapi.testclient import TestClient

from backend.tests.helpers import (
    authenticate_as,
    create_booking,
    create_game,
    create_game_participant,
    create_participant_status_history,
    create_user,
    create_venue,
    run_as_temporary_admin,
    set_user_role,
)


def create_participant_status_history_setup(
    client: TestClient,
) -> tuple[dict, dict, dict, dict, dict]:
    user = create_user(client)
    venue = create_venue(client, user["id"])
    game = create_game(client, user["id"], venue)
    booking = create_booking(client, user["id"], game["id"])
    participant = create_game_participant(
        client,
        user["id"],
        game["id"],
        booking["id"],
    )
    return user, venue, game, booking, participant


def test_participant_status_history_create_get_list_and_update_reason(
    client: TestClient,
):
    user, _venue, _game, _booking, participant = (
        create_participant_status_history_setup(client)
    )
    history = create_participant_status_history(
        client,
        participant["id"],
        changed_by_user_id=user["id"],
        change_source="user",
    )

    get_response = run_as_temporary_admin(
        client,
        lambda: client.get(f"/participant-status-history/{history['id']}"),
    )
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == history["id"]

    list_response = run_as_temporary_admin(
        client,
        lambda: client.get(
            f"/participant-status-history?participant_id={participant['id']}"
        ),
    )
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == history["id"] for item in list_response.json())

    patch_response = run_as_temporary_admin(
        client,
        lambda: client.patch(
            f"/participant-status-history/{history['id']}",
            json={"change_reason": "Corrected CI participant reason."},
        ),
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["change_reason"] == "Corrected CI participant reason."


def test_participant_status_history_reject_no_status_change(client: TestClient):
    user, _venue, _game, _booking, participant = (
        create_participant_status_history_setup(client)
    )

    response = run_as_temporary_admin(
        client,
        lambda: client.post(
            "/participant-status-history",
            json={
                "participant_id": participant["id"],
                "old_participant_status": "confirmed",
                "new_participant_status": "confirmed",
                "old_attendance_status": "unknown",
                "new_attendance_status": "unknown",
                "changed_by_user_id": user["id"],
                "change_source": "admin",
                "change_reason": "No real change",
            },
        ),
    )

    assert response.status_code == 400, response.text
    assert "At least one participant or attendance status must change" in response.text


def test_participant_status_history_reject_invalid_attendance_status(
    client: TestClient,
):
    user, _venue, _game, _booking, participant = (
        create_participant_status_history_setup(client)
    )

    response = run_as_temporary_admin(
        client,
        lambda: client.post(
            "/participant-status-history",
            json={
                "participant_id": participant["id"],
                "old_participant_status": "pending_payment",
                "new_participant_status": "confirmed",
                "old_attendance_status": "unknown",
                "new_attendance_status": "present",
                "changed_by_user_id": user["id"],
                "change_source": "admin",
            },
        ),
    )

    assert response.status_code == 400, response.text
    assert "new_attendance_status" in response.text


def test_participant_status_history_reject_missing_actor(client: TestClient):
    _user, _venue, _game, _booking, participant = (
        create_participant_status_history_setup(client)
    )

    response = run_as_temporary_admin(
        client,
        lambda: client.post(
            "/participant-status-history",
            json={
                "participant_id": participant["id"],
                "old_participant_status": "pending_payment",
                "new_participant_status": "confirmed",
                "old_attendance_status": "unknown",
                "new_attendance_status": "attended",
                "changed_by_user_id": "00000000-0000-4000-8000-000000000000",
                "change_source": "admin",
            },
        ),
    )

    assert response.status_code == 404, response.text
    assert "Changed by user not found" in response.text


def test_participant_status_history_reject_lifecycle_field_update(
    client: TestClient,
):
    user, _venue, _game, _booking, participant = (
        create_participant_status_history_setup(client)
    )
    history = create_participant_status_history(
        client,
        participant["id"],
        changed_by_user_id=user["id"],
        change_source="user",
    )

    response = run_as_temporary_admin(
        client,
        lambda: client.patch(
            f"/participant-status-history/{history['id']}",
            json={"new_participant_status": "cancelled"},
        ),
    )

    assert response.status_code == 400, response.text
    assert "cannot be changed" in response.text


def test_participant_status_history_reject_user_source_from_other_user(
    client: TestClient,
):
    _user, _venue, _game, _booking, participant = (
        create_participant_status_history_setup(client)
    )
    other_user = create_user(client)

    response = run_as_temporary_admin(
        client,
        lambda: client.post(
            "/participant-status-history",
            json={
                "participant_id": participant["id"],
                "old_participant_status": "confirmed",
                "new_participant_status": "cancelled",
                "old_attendance_status": "unknown",
                "new_attendance_status": "not_applicable",
                "changed_by_user_id": other_user["id"],
                "change_source": "user",
            },
        ),
    )

    assert response.status_code == 400, response.text
    assert "participant user" in response.text


def test_participant_status_history_admin_source_requires_admin(
    client: TestClient,
):
    user, _venue, _game, _booking, participant = (
        create_participant_status_history_setup(client)
    )

    response = run_as_temporary_admin(
        client,
        lambda: client.post(
            "/participant-status-history",
            json={
                "participant_id": participant["id"],
                "old_participant_status": "confirmed",
                "new_participant_status": "cancelled",
                "old_attendance_status": "unknown",
                "new_attendance_status": "not_applicable",
                "changed_by_user_id": user["id"],
                "change_source": "admin",
            },
        ),
    )

    assert response.status_code == 400, response.text
    assert "admin user" in response.text

    set_user_role(user["id"], "admin")
    admin_response = run_as_temporary_admin(
        client,
        lambda: client.post(
            "/participant-status-history",
            json={
                "participant_id": participant["id"],
                "old_participant_status": "confirmed",
                "new_participant_status": "cancelled",
                "old_attendance_status": "unknown",
                "new_attendance_status": "not_applicable",
                "changed_by_user_id": user["id"],
                "change_source": "admin",
            },
        ),
    )

    assert admin_response.status_code == 201, admin_response.text


def test_participant_status_history_requires_admin_permission(client: TestClient):
    user, _venue, _game, _booking, participant = (
        create_participant_status_history_setup(client)
    )
    history = create_participant_status_history(
        client,
        participant["id"],
        changed_by_user_id=user["id"],
        change_source="user",
    )
    authenticate_as(user["id"])

    get_response = client.get(f"/participant-status-history/{history['id']}")
    list_response = client.get(
        f"/participant-status-history?participant_id={participant['id']}"
    )
    post_response = client.post(
        "/participant-status-history",
        json={
            "participant_id": participant["id"],
            "old_participant_status": "confirmed",
            "new_participant_status": "cancelled",
            "old_attendance_status": "unknown",
            "new_attendance_status": "not_applicable",
            "changed_by_user_id": user["id"],
            "change_source": "user",
        },
    )
    patch_response = client.patch(
        f"/participant-status-history/{history['id']}",
        json={"change_reason": "Denied."},
    )

    assert get_response.status_code == 403, get_response.text
    assert list_response.status_code == 403, list_response.text
    assert post_response.status_code == 403, post_response.text
    assert patch_response.status_code == 403, patch_response.text


def test_participant_status_history_rejects_player(client: TestClient):
    user, _venue, _game, _booking, participant = (
        create_participant_status_history_setup(client)
    )
    history = create_participant_status_history(
        client,
        participant["id"],
        changed_by_user_id=user["id"],
        change_source="user",
    )
    player = create_user(client)
    authenticate_as(player["id"])

    get_response = client.get(f"/participant-status-history/{history['id']}")
    post_response = client.post(
        "/participant-status-history",
        json={
            "participant_id": participant["id"],
            "old_participant_status": "confirmed",
            "new_participant_status": "cancelled",
            "old_attendance_status": "unknown",
            "new_attendance_status": "not_applicable",
            "changed_by_user_id": user["id"],
            "change_source": "user",
        },
    )

    assert get_response.status_code == 403, get_response.text
    assert post_response.status_code == 403, post_response.text
