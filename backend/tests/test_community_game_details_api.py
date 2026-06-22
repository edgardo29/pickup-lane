from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from backend.database import SessionLocal
from backend.models import CommunityGameDetail
from backend.tests.helpers import (
    authenticate_as,
    create_community_game_detail,
    create_game,
    create_user,
    create_venue,
    run_as_temporary_admin,
    set_user_role,
    unique_suffix,
)


def test_community_game_detail_create_get_list_and_update(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    detail = create_community_game_detail(client, game["id"])

    get_response = client.get(f"/community-game-details/{detail['id']}")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == detail["id"]

    list_response = client.get(f"/community-game-details?game_id={game['id']}")
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == detail["id"] for item in list_response.json())

    patch_response = run_as_temporary_admin(
        client,
        lambda: client.patch(
            f"/community-game-details/{detail['id']}",
            json={
                "payment_methods_snapshot": [
                    {"type": "zelle", "value": "zelle@example.com"}
                ],
                "payment_instructions_snapshot": "Pay the host after confirmation.",
            },
        ),
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["payment_methods_snapshot"] == [
        {"type": "zelle", "value": "zelle@example.com"}
    ]
    assert (
        patch_response.json()["payment_instructions_snapshot"]
        == "Pay the host after confirmation."
    )


def test_community_game_detail_rejects_official_game(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(client, host["id"], venue)

    response = run_as_temporary_admin(
        client,
        lambda: client.post(
            "/community-game-details",
            json={
                "game_id": game["id"],
                "payment_methods_snapshot": [{"type": "venmo", "value": "@host"}],
            },
        ),
    )

    assert response.status_code == 400, response.text
    assert "require a community game" in response.text


def test_community_game_detail_rejects_duplicate_game(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    create_community_game_detail(client, game["id"])

    response = run_as_temporary_admin(
        client,
        lambda: client.post(
            "/community-game-details",
            json={
                "game_id": game["id"],
                "payment_methods_snapshot": [{"type": "cash", "value": "Cash"}],
            },
        ),
    )

    assert response.status_code == 409, response.text
    assert "already has community game details" in response.text


def test_community_game_detail_generic_create_requires_admin(client: TestClient):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )

    response = client.post(
        "/community-game-details",
        json={
            "game_id": game["id"],
            "payment_methods_snapshot": [{"type": "venmo", "value": "@host"}],
        },
    )

    assert response.status_code == 401, response.text


def test_community_game_detail_host_upsert_creates_and_updates(
    client: TestClient,
):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    authenticate_as(host["id"])

    create_response = client.put(
        f"/community-game-details/games/{game['id']}/host-edit",
        json={
            "payment_methods_snapshot": [{"type": "venmo", "value": "@host"}],
            "payment_instructions_snapshot": "Pay after joining.",
        },
    )
    assert create_response.status_code == 200, create_response.text
    detail = create_response.json()
    assert detail["game_id"] == game["id"]
    assert detail["payment_methods_snapshot"] == [{"type": "venmo", "value": "@host"}]

    update_response = client.put(
        f"/community-game-details/games/{game['id']}/host-edit",
        json={
            "payment_methods_snapshot": [
                {"type": "zelle", "value": "zelle@example.com"}
            ],
            "payment_instructions_snapshot": None,
        },
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["id"] == detail["id"]
    assert update_response.json()["payment_methods_snapshot"] == [
        {"type": "zelle", "value": "zelle@example.com"}
    ]
    assert update_response.json()["payment_instructions_snapshot"] is None


def test_community_game_detail_host_upsert_rejects_non_host(client: TestClient):
    host = create_user(client)
    other_user = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    authenticate_as(other_user["id"])

    get_response = client.get(
        f"/community-game-details/games/{game['id']}/host-edit"
    )
    update_response = client.put(
        f"/community-game-details/games/{game['id']}/host-edit",
        json={"payment_methods_snapshot": [{"type": "venmo", "value": "@host"}]},
    )

    assert get_response.status_code == 403, get_response.text
    assert get_response.json()["detail"] == "Only the game host can edit this game."
    assert update_response.status_code == 403, update_response.text
    assert update_response.json()["detail"] == "Only the game host can edit this game."


def test_community_game_detail_host_upsert_rejects_request_game_id(
    client: TestClient,
):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    authenticate_as(host["id"])

    response = client.put(
        f"/community-game-details/games/{game['id']}/host-edit",
        json={
            "game_id": game["id"],
            "payment_methods_snapshot": [{"type": "venmo", "value": "@host"}],
        },
    )

    assert response.status_code == 422, response.text


def test_hidden_community_payment_text_uses_scoped_public_and_host_responses(
    client: TestClient,
):
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    detail = create_community_game_detail(
        client,
        game["id"],
        payment_methods_snapshot=[{"type": "venmo", "value": "@host"}],
        payment_instructions_snapshot="Pay after joining.",
    )

    authenticate_as(moderator["id"])
    hide_response = client.post(
        f"/admin/community-games/{game['id']}/hide-payment-text",
        json={
            "reason": "Unsafe payment content.",
            "idempotency_key": f"hide-host-scope-{unique_suffix()}",
        },
    )
    assert hide_response.status_code == 200, hide_response.text

    public_response = client.get(f"/community-game-details/{detail['id']}")
    assert public_response.status_code == 200, public_response.text
    public_detail = public_response.json()
    assert public_detail["payment_methods_snapshot"] == []
    assert public_detail["payment_instructions_snapshot"] is None
    assert public_detail["payment_text_moderation_status"] == "hidden"
    assert "payment_text_hidden_at" not in public_detail
    assert "payment_text_hidden_by_user_id" not in public_detail
    assert "payment_text_hidden_reason" not in public_detail

    authenticate_as(host["id"])
    host_response = client.get(
        f"/community-game-details/games/{game['id']}/host-edit"
    )
    assert host_response.status_code == 200, host_response.text
    host_detail = host_response.json()
    assert host_detail["payment_methods_snapshot"] == [
        {"type": "venmo", "value": "@host"}
    ]
    assert host_detail["payment_instructions_snapshot"] == "Pay after joining."
    assert host_detail["payment_text_moderation_status"] == "hidden"
    assert "payment_text_hidden_at" not in host_detail
    assert "payment_text_hidden_by_user_id" not in host_detail
    assert "payment_text_hidden_reason" not in host_detail

    update_response = client.put(
        f"/community-game-details/games/{game['id']}/host-edit",
        json={
            "payment_methods_snapshot": [{"type": "venmo", "value": "@host"}],
            "payment_instructions_snapshot": "Updated host instructions.",
        },
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["payment_instructions_snapshot"] == (
        "Updated host instructions."
    )
    assert update_response.json()["payment_text_moderation_status"] == "hidden"
    assert "payment_text_hidden_reason" not in update_response.json()


def test_hidden_community_payment_text_requires_internal_reason(
    client: TestClient,
):
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        policy_mode="custom_hosted",
    )
    detail = create_community_game_detail(client, game["id"])

    with SessionLocal() as db:
        db_detail = db.get(CommunityGameDetail, UUID(detail["id"]))
        assert db_detail is not None
        db_detail.payment_text_moderation_status = "hidden"
        db_detail.payment_text_hidden_at = datetime.now(UTC)
        db_detail.payment_text_hidden_reason = "   "

        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
