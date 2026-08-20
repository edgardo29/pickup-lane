from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from backend.tests.workflows.game_community_roster_chat_need_a_sub_relationship_authorization.test_matrix_scope_and_dependencies_contract import (
    _Identity,
    _auth_headers,
    _game,
    _install_auth_identities,
    _participant,
    _recent_time,
    _session,
    _sub_position,
    _sub_post,
    _user,
    _venue,
)

pytestmark = pytest.mark.suite_type("ordinary")

SERVER_CONTROLLED_FIELDS = {
    "user_id",
    "owner_user_id",
    "requester_user_id",
    "buyer_user_id",
    "host_user_id",
    "sender_user_id",
    "acting_user_id",
    "participant_id",
    "booking_id",
    "waitlist_entry_id",
    "payment_id",
    "provider_payment_intent_id",
    "provider_charge_id",
    "stripe_customer_id",
    "created_by_user_id",
    "cancelled_by_user_id",
    "game_status",
    "post_status",
    "request_status",
    "visibility_status",
    "review_status",
    "payment_status",
    "admin_action_id",
}


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS03-04C-R9", "WS03-04C-R11")
def test_c_write_schemas_forbid_server_controlled_mass_assignment_fields() -> None:
    from pydantic import BaseModel

    from backend.schemas.chat_message_schema import ChatMessageCreate
    from backend.schemas.checkout_schema import GameCheckoutPaymentIntentCreate
    from backend.schemas.community_game_detail_schema import CommunityGameDetailHostUpsert
    from backend.schemas.community_game_publish_schema import CommunityGamePublishCreate
    from backend.schemas.game_chat_schema import GameChatEnsureCreate
    from backend.schemas.game_schema import (
        GameBookingGuestAddCreate,
        GameCancelCreate,
        GameGuestAddCreate,
        GameGuestRemoveCreate,
        GameHostEdit,
        GameJoinCreate,
        GameLeaveCreate,
    )
    from backend.schemas.sub_post_chat_message_schema import SubPostChatMessageCreate
    from backend.schemas.sub_post_chat_schema import SubPostChatEnsureCreate
    from backend.schemas.sub_post_request_schema import (
        SubPostRequestAction,
        SubPostRequestCreate,
    )
    from backend.schemas.sub_post_schema import SubPostCancel, SubPostCreate, SubPostUpdate

    write_schemas: list[type[BaseModel]] = [
        ChatMessageCreate,
        GameCheckoutPaymentIntentCreate,
        CommunityGameDetailHostUpsert,
        CommunityGamePublishCreate,
        GameChatEnsureCreate,
        GameBookingGuestAddCreate,
        GameCancelCreate,
        GameGuestAddCreate,
        GameGuestRemoveCreate,
        GameHostEdit,
        GameJoinCreate,
        GameLeaveCreate,
        SubPostChatMessageCreate,
        SubPostChatEnsureCreate,
        SubPostRequestAction,
        SubPostRequestCreate,
        SubPostCancel,
        SubPostCreate,
        SubPostUpdate,
    ]

    allowed_body_fields_by_schema = {
        schema.__name__: set(schema.model_fields)
        for schema in write_schemas
    }
    allowed_exceptions = {
        "GameChatEnsureCreate": {"acting_user_id"},
        "GameCheckoutPaymentIntentCreate": {"payment_method_id"},
        "CommunityGamePublishCreate": {"payment_method_id"},
    }

    for schema in write_schemas:
        assert schema.model_config.get("extra") == "forbid", schema.__name__
        forbidden = SERVER_CONTROLLED_FIELDS - allowed_exceptions.get(schema.__name__, set())
        assert not (set(schema.model_fields) & forbidden), schema.__name__

    assert allowed_body_fields_by_schema["GameHostEdit"] == {
        "venue_name",
        "address_line_1",
        "city",
        "state",
        "postal_code",
        "neighborhood",
        "starts_at",
        "ends_at",
        "format_label",
        "game_player_group",
        "skill_level",
        "environment_type",
        "total_spots",
        "price_per_player_cents",
        "custom_rules_text",
        "game_notes",
        "parking_notes",
    }


@pytest.mark.requirement("WS03-04C-R9", "WS03-04C-R10")
def test_default_deny_and_extra_field_rejections_create_no_relationship_rows(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import ChatMessage, SubPost, SubPostRequest

    with _session() as db:
        host = _user("deny-host")
        player = _user("deny-player")
        other = _user("deny-other")
        venue = _venue(host.id, "deny")
        game = _game(host_user_id=host.id, venue_id=venue.id, label="deny")
        participant = _participant(
            game_id=game.id,
            user_id=player.id,
            booking_id=None,
            label="deny-player",
        )
        post = _sub_post(owner_user_id=host.id, label="deny")
        position = _sub_position(post.id, "deny")
        db.add_all([host, player, other])
        db.flush()
        db.add(venue)
        db.flush()
        db.add_all([game, post])
        db.flush()
        db.add_all([participant, position])
        db.commit()
        player_auth_id = player.auth_user_id
        player_email = player.email
        other_auth_id = other.auth_user_id
        other_email = other.email
        game_id = game.id
        post_id = post.id
        position_id = position.id
        before_posts = db.scalar(select(func.count()).select_from(SubPost))
        before_requests = db.scalar(select(func.count()).select_from(SubPostRequest))
        before_messages = db.scalar(select(func.count()).select_from(ChatMessage))

    _install_auth_identities(
        monkeypatch,
        {
            "player-token": _Identity(
                auth_user_id=player_auth_id,
                email=player_email,
                email_verified=True,
                authenticated_at=_recent_time(),
            ),
            "other-token": _Identity(
                auth_user_id=other_auth_id,
                email=other_email,
                email_verified=True,
                authenticated_at=_recent_time(),
            ),
        },
    )

    assert client.get("/bookings/me").status_code == 401
    assert client.get("/bookings/me", headers=_auth_headers("invalid-token")).status_code == 401
    assert (
        client.post(
            f"/games/{game_id}/cancel",
            headers=_auth_headers("player-token"),
            json={"cancel_reason": "not host"},
        ).status_code
        == 403
    )
    assert client.get(f"/games/{uuid.uuid4()}").status_code == 404

    rejected_post = client.post(
        "/need-a-sub/posts",
        headers=_auth_headers("player-token"),
        json={
            "owner_user_id": "00000000-0000-0000-0000-000000000000",
            "format_label": "5v5",
            "environment_type": "outdoor",
            "skill_level": "any",
            "game_player_group": "coed",
            "starts_at": "2036-01-01T18:00:00Z",
            "ends_at": "2036-01-01T20:00:00Z",
            "location_name": "Synthetic Field",
            "address_line_1": "1 Synthetic Ave",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "subs_needed": 1,
            "positions": [
                {
                    "position_label": "Defender",
                    "player_group": "any",
                    "spots_needed": 1,
                }
            ],
        },
    )
    assert rejected_post.status_code == 422

    rejected_request = client.post(
        f"/need-a-sub/posts/{post_id}/requests",
        headers=_auth_headers("player-token"),
        json={
            "sub_post_position_id": str(position_id),
            "requester_user_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert rejected_request.status_code == 422

    rejected_chat_message = client.post(
        "/chat-messages",
        headers=_auth_headers("other-token"),
        json={
            "chat_id": "00000000-0000-0000-0000-000000000000",
            "sender_user_id": "00000000-0000-0000-0000-000000000000",
            "message_body": "spoof sender",
        },
    )
    assert rejected_chat_message.status_code == 422

    with _session() as db:
        assert db.scalar(select(func.count()).select_from(SubPost)) == before_posts
        assert db.scalar(select(func.count()).select_from(SubPostRequest)) == before_requests
        assert db.scalar(select(func.count()).select_from(ChatMessage)) == before_messages
