from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select

from backend.database import SessionLocal
from backend.models import (
    AdminAction,
    Booking,
    BookingPolicyAcceptance,
    BookingStatusHistory,
    Game,
    GameChat,
    GameImage,
    GameParticipant,
    GameStatusHistory,
    HostPublishFee,
    Notification,
    ParticipantStatusHistory,
    SubPost,
    User,
    UserSettings,
    UserStats,
    Venue,
    VenueApprovalRequest,
    WaitlistEntry,
)
from backend.services.auth_service import (
    VerifiedFirebaseIdentity,
    get_current_app_user,
    get_optional_current_app_user,
    get_verified_firebase_identity,
    require_verified_user,
)
from backend.tests.helpers import (
    build_sub_post_payload,
    create_booking,
    create_game_participant,
    create_user,
    create_user_settings,
    create_user_stats,
    set_user_role,
    unique_suffix,
)


def model_count(model) -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(model)) or 0


def get_game_host_user_id(game_id: str) -> str | None:
    with SessionLocal() as db:
        db_game = db.get(Game, UUID(game_id))
        assert db_game is not None
        return str(db_game.host_user_id) if db_game.host_user_id else None


def get_sub_post_status(sub_post_id: str) -> str:
    with SessionLocal() as db:
        db_post = db.get(SubPost, UUID(sub_post_id))
        assert db_post is not None
        return db_post.post_status


def count_admin_actions(*, action_type: str, game_id: str | None = None) -> int:
    statement = select(func.count()).select_from(AdminAction).where(
        AdminAction.action_type == action_type,
    )
    if game_id is not None:
        statement = statement.where(AdminAction.target_game_id == UUID(game_id))

    with SessionLocal() as db:
        return db.scalar(statement) or 0


def count_notifications(
    *,
    notification_type: str,
    related_game_id: str | None = None,
    user_id: str | None = None,
) -> int:
    statement = select(func.count()).select_from(Notification).where(
        Notification.notification_type == notification_type,
    )
    if related_game_id is not None:
        statement = statement.where(Notification.related_game_id == UUID(related_game_id))
    if user_id is not None:
        statement = statement.where(Notification.user_id == UUID(user_id))

    with SessionLocal() as db:
        return db.scalar(statement) or 0


def authenticate_client_as(client: TestClient, user_id: str) -> None:
    def override_current_user() -> User:
        with SessionLocal() as db:
            db_user = db.get(User, UUID(user_id))
            assert db_user is not None
            return db_user

    def override_firebase_identity() -> VerifiedFirebaseIdentity:
        with SessionLocal() as db:
            db_user = db.get(User, UUID(user_id))
            assert db_user is not None
            return VerifiedFirebaseIdentity(
                auth_user_id=db_user.auth_user_id,
                email=db_user.email,
                email_verified=True,
            )

    client.app.dependency_overrides[get_current_app_user] = override_current_user
    client.app.dependency_overrides[get_optional_current_app_user] = override_current_user
    client.app.dependency_overrides[get_verified_firebase_identity] = (
        override_firebase_identity
    )
    client.app.dependency_overrides[require_verified_user] = override_current_user


def build_official_game_payload(**overrides: object) -> dict[str, object]:
    starts_at = datetime.now(UTC) + timedelta(days=7)
    payload: dict[str, object] = {
        "title": "Route Lifecycle Official Match",
        "venue": {
            "name": f"Lifecycle Field {unique_suffix()[:8]}",
            "address_line_1": "500 Lifecycle Ave",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "country_code": "US",
            "neighborhood": "Loop",
        },
        "starts_at": starts_at.isoformat(),
        "ends_at": (starts_at + timedelta(hours=1)).isoformat(),
        "timezone": "America/Chicago",
        "format_label": "5v5",
        "environment_type": "indoor",
        "total_spots": 10,
        "price_per_player_cents": 1500,
        "reason": "Create official game for route lifecycle coverage.",
    }
    payload.update(overrides)
    return payload


def create_admin(client: TestClient) -> dict:
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    return admin


def create_official_game(client: TestClient, admin: dict) -> dict:
    authenticate_client_as(client, admin["id"])
    response = client.post(
        "/admin/official-games",
        json=build_official_game_payload(),
    )
    assert response.status_code == 201, response.text
    return response.json()["game"]


def create_sub_post_via_api(
    client: TestClient,
    owner_user_id: str,
    **overrides: object,
) -> dict:
    authenticate_client_as(client, owner_user_id)
    response = client.post(
        "/need-a-sub/posts",
        json=build_sub_post_payload(**overrides),
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_official_player(
    client: TestClient,
    *,
    admin: dict,
    game_id: str,
    user_id: str,
    participant_type: str = "registered_user",
) -> dict:
    del admin
    booking = create_booking(
        client,
        user_id,
        game_id,
        price_per_player_snapshot_cents=1500,
        subtotal_cents=1500,
        total_cents=1600,
    )
    return create_game_participant(
        client,
        user_id,
        game_id,
        booking_id=booking["id"],
        display_name_snapshot="Official Player",
        participant_type=participant_type,
        price_cents=1500,
    )


def assert_retired_response(response, *, expected_code: str) -> None:
    assert response.status_code == 410, response.text
    body = response.json()
    assert body["code"] == "API.HTTP_ERROR"
    assert body["correlation_id"]
    assert body["detail"]["code"] == expected_code
    assert body["message"]


RETIRED_MUTATION_ROUTES = (
    ("POST", "/notifications", "notification_admin_scaffold_removed", Notification),
    (
        "PATCH",
        f"/notifications/{uuid4()}",
        "notification_admin_scaffold_removed",
        Notification,
    ),
    ("POST", "/bookings", "booking_scaffold_removed", Booking),
    ("PATCH", f"/bookings/{uuid4()}", "booking_scaffold_removed", Booking),
    ("POST", "/game-participants", "game_participant_scaffold_removed", GameParticipant),
    (
        "PATCH",
        f"/game-participants/{uuid4()}",
        "game_participant_scaffold_removed",
        GameParticipant,
    ),
    ("POST", "/waitlist-entries", "waitlist_entry_scaffold_removed", WaitlistEntry),
    (
        "PATCH",
        f"/waitlist-entries/{uuid4()}",
        "waitlist_entry_scaffold_removed",
        WaitlistEntry,
    ),
    ("POST", "/host-publish-fees", "host_publish_fee_scaffold_removed", HostPublishFee),
    (
        "PATCH",
        f"/host-publish-fees/{uuid4()}",
        "host_publish_fee_scaffold_removed",
        HostPublishFee,
    ),
    ("POST", "/venues", "venue_scaffold_removed", Venue),
    ("PATCH", f"/venues/{uuid4()}", "venue_scaffold_removed", Venue),
    ("POST", "/game-images", "game_image_scaffold_removed", GameImage),
    ("PATCH", f"/game-images/{uuid4()}", "game_image_scaffold_removed", GameImage),
    (
        "POST",
        "/venue-approval-requests",
        "venue_approval_request_scaffold_removed",
        VenueApprovalRequest,
    ),
    (
        "PATCH",
        f"/venue-approval-requests/{uuid4()}",
        "venue_approval_request_scaffold_removed",
        VenueApprovalRequest,
    ),
    ("POST", "/user-settings", "user_settings_scaffold_removed", UserSettings),
    (
        "PATCH",
        f"/user-settings/{uuid4()}",
        "user_settings_scaffold_removed",
        UserSettings,
    ),
    ("POST", "/user-stats", "user_stats_scaffold_removed", UserStats),
    ("PATCH", f"/user-stats/{uuid4()}", "user_stats_scaffold_removed", UserStats),
    ("POST", "/game-chats", "game_chat_scaffold_removed", GameChat),
    ("PATCH", f"/game-chats/{uuid4()}", "game_chat_scaffold_removed", GameChat),
    ("POST", "/admin/actions", "admin_action_scaffold_removed", AdminAction),
    (
        "POST",
        f"/admin/actions/{uuid4()}/notes",
        "admin_action_note_scaffold_removed",
        AdminAction,
    ),
    (
        "POST",
        "/game-status-history",
        "game_status_history_scaffold_removed",
        GameStatusHistory,
    ),
    (
        "PATCH",
        f"/game-status-history/{uuid4()}",
        "game_status_history_scaffold_removed",
        GameStatusHistory,
    ),
    (
        "POST",
        "/booking-status-history",
        "booking_status_history_scaffold_removed",
        BookingStatusHistory,
    ),
    (
        "PATCH",
        f"/booking-status-history/{uuid4()}",
        "booking_status_history_scaffold_removed",
        BookingStatusHistory,
    ),
    (
        "POST",
        "/participant-status-history",
        "participant_status_history_scaffold_removed",
        ParticipantStatusHistory,
    ),
    (
        "PATCH",
        f"/participant-status-history/{uuid4()}",
        "participant_status_history_scaffold_removed",
        ParticipantStatusHistory,
    ),
    (
        "POST",
        "/booking-policy-acceptances",
        "booking_policy_acceptance_scaffold_removed",
        BookingPolicyAcceptance,
    ),
    (
        "PATCH",
        f"/booking-policy-acceptances/{uuid4()}",
        "booking_policy_acceptance_scaffold_removed",
        BookingPolicyAcceptance,
    ),
    (
        "PATCH",
        f"/need-a-sub/posts/{uuid4()}/remove",
        "need_a_sub_legacy_remove_route_removed",
        SubPost,
    ),
    (
        "DELETE",
        f"/admin/official-games/{uuid4()}/participants/{uuid4()}",
        "official_game_player_delete_removed",
        GameParticipant,
    ),
    (
        "DELETE",
        f"/admin/official-games/{uuid4()}/host",
        "official_game_host_delete_removed",
        Game,
    ),
)


@pytest.mark.parametrize(
    ("method", "path", "expected_code", "model"),
    RETIRED_MUTATION_ROUTES,
)
def test_b1_retired_mutation_routes_are_bodyless_tombstones(
    client: TestClient,
    method: str,
    path: str,
    expected_code: str,
    model,
):
    admin = create_admin(client)
    authenticate_client_as(client, admin["id"])
    before_count = model_count(model)

    response = client.request(
        method,
        path,
        content="{",
        headers={"Content-Type": "application/json"},
    )

    assert_retired_response(response, expected_code=expected_code)
    assert model_count(model) == before_count


def test_b1_preserves_current_self_service_read_and_scoped_chat_workflows(
    client: TestClient,
):
    admin = create_admin(client)
    player = create_user(client)
    game = create_official_game(client, admin)
    create_official_player(
        client,
        admin=admin,
        game_id=game["id"],
        user_id=player["id"],
    )
    create_user_settings(client, player["id"])
    create_user_stats(client, player["id"])

    authenticate_client_as(client, player["id"])
    settings_response = client.get("/user-settings/me")
    stats_response = client.get("/user-stats/me")
    chat_response = client.post(
        f"/game-chats/for-game/{game['id']}",
        json={},
    )

    assert settings_response.status_code == 200, settings_response.text
    assert settings_response.json()["user_id"] == player["id"]
    assert stats_response.status_code == 200, stats_response.text
    assert stats_response.json()["user_id"] == player["id"]
    assert chat_response.status_code == 200, chat_response.text
    assert chat_response.json()["game_id"] == game["id"]


def test_b1_need_a_sub_uses_admin_canonical_removal_and_legacy_patch_does_not_mutate(
    client: TestClient,
):
    owner = create_user(client)
    legacy_owner = create_user(client)
    admin = create_admin(client)
    canonical_post = create_sub_post_via_api(client, owner["id"])
    legacy_post = create_sub_post_via_api(client, legacy_owner["id"])

    authenticate_client_as(client, admin["id"])
    canonical_response = client.post(
        f"/admin/need-a-sub/{canonical_post['id']}/remove",
        json={
            "reason": "Moderation removal.",
            "idempotency_key": f"remove-{unique_suffix()}",
        },
    )
    legacy_response = client.request(
        "PATCH",
        f"/need-a-sub/posts/{legacy_post['id']}/remove",
        content="{",
        headers={"Content-Type": "application/json"},
    )

    assert canonical_response.status_code == 200, canonical_response.text
    canonical_body = canonical_response.json()
    assert canonical_body["post_status"] == "removed"
    assert canonical_body["audit_action_id"]
    assert canonical_body["notice_ids"]
    assert_retired_response(
        legacy_response,
        expected_code="need_a_sub_legacy_remove_route_removed",
    )
    assert get_sub_post_status(legacy_post["id"]) == "active"


def test_b1_official_game_host_removal_post_preserves_service_effects(
    client: TestClient,
):
    admin = create_admin(client)
    host = create_user(client)
    game = create_official_game(client, admin)
    participant = create_official_player(
        client,
        admin=admin,
        game_id=game["id"],
        user_id=host["id"],
    )

    authenticate_client_as(client, admin["id"])
    assign_response = client.post(
        f"/admin/official-games/{game['id']}/host",
        json={"host_user_id": host["id"], "reason": "Assign host."},
    )
    assert assign_response.status_code == 200, assign_response.text
    assert assign_response.json()["game"]["host_user_id"] == host["id"]

    invalid_response = client.post(
        f"/admin/official-games/{game['id']}/host/remove",
        json={},
    )
    assert invalid_response.status_code == 422, invalid_response.text
    assert get_game_host_user_id(game["id"]) == host["id"]
    assert (
        count_admin_actions(action_type="remove_official_host", game_id=game["id"])
        == 0
    )

    client.app.dependency_overrides.clear()
    unauthenticated_response = client.post(
        f"/admin/official-games/{game['id']}/host/remove",
        json={"reason": "Remove host."},
    )
    assert unauthenticated_response.status_code == 401
    assert get_game_host_user_id(game["id"]) == host["id"]

    authenticate_client_as(client, admin["id"])
    remove_response = client.post(
        f"/admin/official-games/{game['id']}/host/remove",
        json={"reason": "Remove host."},
    )

    assert remove_response.status_code == 200, remove_response.text
    assert remove_response.json()["game"]["host_user_id"] is None
    assert (
        count_admin_actions(action_type="remove_official_host", game_id=game["id"])
        == 1
    )
    assert (
        count_notifications(
            notification_type="game_host_removed",
            related_game_id=game["id"],
            user_id=host["id"],
        )
        == 1
    )
    assert participant["id"]


def test_b1_official_game_legacy_delete_routes_no_longer_mutate(
    client: TestClient,
):
    admin = create_admin(client)
    host = create_user(client)
    player = create_user(client)
    game = create_official_game(client, admin)
    host_participant = create_official_player(
        client,
        admin=admin,
        game_id=game["id"],
        user_id=host["id"],
    )

    authenticate_client_as(client, admin["id"])
    player_response = client.post(
        f"/admin/official-games/{game['id']}/players",
        json={"user_id": player["id"], "reason": "Add player."},
    )
    assert player_response.status_code == 201, player_response.text
    player_participant = player_response.json()

    assign_response = client.post(
        f"/admin/official-games/{game['id']}/host",
        json={"host_user_id": host["id"], "reason": "Assign host."},
    )
    assert assign_response.status_code == 200, assign_response.text

    legacy_host_response = client.request(
        "DELETE",
        f"/admin/official-games/{game['id']}/host",
        content="{",
        headers={"Content-Type": "application/json"},
    )
    legacy_player_response = client.request(
        "DELETE",
        f"/admin/official-games/{game['id']}/participants/{player_participant['id']}",
        content="{",
        headers={"Content-Type": "application/json"},
    )

    assert_retired_response(
        legacy_host_response,
        expected_code="official_game_host_delete_removed",
    )
    assert_retired_response(
        legacy_player_response,
        expected_code="official_game_player_delete_removed",
    )
    assert get_game_host_user_id(game["id"]) == host["id"]

    authenticate_client_as(client, admin["id"])
    host_participant_response = client.get(
        f"/game-participants/{host_participant['id']}"
    )
    player_participant_response = client.get(
        f"/game-participants/{player_participant['id']}"
    )
    assert host_participant_response.status_code == 200
    assert player_participant_response.status_code == 200
    assert host_participant_response.json()["participant_status"] == "confirmed"
    assert player_participant_response.json()["participant_status"] == "confirmed"


def test_b1_official_game_player_removal_uses_post_preview_execute_flow(
    client: TestClient,
):
    admin = create_admin(client)
    player = create_user(client)
    game = create_official_game(client, admin)

    authenticate_client_as(client, admin["id"])
    add_response = client.post(
        f"/admin/official-games/{game['id']}/players",
        json={"user_id": player["id"], "reason": "Add player."},
    )
    assert add_response.status_code == 201, add_response.text
    participant = add_response.json()

    preview_response = client.post(
        f"/admin/official-games/{game['id']}/participants/"
        f"{participant['id']}/remove-preview",
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()
    assert preview["automatic_outcome_available"] is True
    assert preview["allowed_outcomes"]

    execute_response = client.post(
        f"/admin/official-games/{game['id']}/participants/{participant['id']}/remove",
        json={
            "preview_token": preview["preview_token"],
            "outcome": preview["allowed_outcomes"][0],
            "reason": "Remove player.",
        },
    )

    assert execute_response.status_code == 200, execute_response.text
    assert execute_response.json()["removed_participant_ids"] == [participant["id"]]
    participant_response = client.get(f"/game-participants/{participant['id']}")
    assert participant_response.status_code == 200
    assert participant_response.json()["participant_status"] == "removed"
