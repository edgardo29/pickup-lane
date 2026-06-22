from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event

from backend.database import SessionLocal, engine
from backend.models import AdminAction, SubPost, User
from backend.schemas.admin_community_schema import (
    AdminCommunityGameHidePaymentTextCreate,
    AdminCommunityGameReviewFlagCreate,
)
from backend.services import admin_community_service
from backend.services.support_flag_service import create_support_flag
from backend.tests.helpers import (
    authenticate_as,
    create_admin_action,
    create_community_game_detail,
    create_game,
    create_game_participant,
    create_host_publish_fee,
    create_sub_post,
    create_user,
    create_venue,
    set_user_role,
    unique_suffix,
)


def create_community_game(client: TestClient, host: dict, **overrides: object) -> dict:
    venue = create_venue(client, host["id"])
    payload = {
        "game_type": "community",
        "host_user_id": host["id"],
        "created_by_user_id": host["id"],
        "policy_mode": "custom_hosted",
    }
    payload.update(overrides)
    return create_game(client, host["id"], venue, **payload)


def test_admin_community_games_list_returns_support_safe_shape(
    client: TestClient,
):
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    host = create_user(
        client,
        first_name="Casey",
        last_name="Host",
        email="casey.host@example.com",
    )
    game = create_community_game(client, host, title="Sunday Community 5v5")
    create_community_game_detail(client, game["id"])
    player = create_user(client)
    create_game_participant(client, player["id"], game["id"])
    create_game_participant(
        client,
        None,
        game["id"],
        participant_type="guest",
        guest_of_user_id=player["id"],
        guest_name="Guest Player",
        display_name_snapshot="Guest Player",
    )
    create_host_publish_fee(client, game["id"], host["id"])

    authenticate_as(moderator["id"])
    response = client.get("/admin/community-games", params={"query": "sunday"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_count"] == 1
    assert body["offset"] == 0
    assert body["limit"] == 50
    assert [item["id"] for item in body["games"]] == [game["id"]]
    listed_game = body["games"][0]
    assert listed_game["title"] == "Sunday Community 5v5"
    assert listed_game["payment_collection_type"] == "external_host"
    assert listed_game["timezone"] == game["timezone"]
    assert listed_game["host"] == {
        "id": host["id"],
        "display_name": "Casey Host",
        "account_status": "active",
        "hosting_status": "not_eligible",
    }
    assert "email" not in listed_game["host"]
    assert listed_game["participant_summary"]["confirmed_count"] == 2
    assert listed_game["participant_summary"]["registered_user_count"] == 1
    assert listed_game["participant_summary"]["guest_count"] == 1
    assert listed_game["moderation_state"] == {
        "host_payment_snapshot_present": True,
        "unsafe_payment_text_hidden": False,
        "payment_text_hidden_at": None,
        "payment_text_hidden_by_user_id": None,
        "payment_text_hidden_reason": None,
        "review_flag_status": "not_flagged",
    }


def test_admin_community_games_search_hides_email_from_moderator(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    host = create_user(
        client,
        first_name="Hidden",
        last_name="Host",
        email=f"hidden-host-{unique_suffix()}@example.com",
    )
    game = create_community_game(client, host, title="Email Hidden Community Game")

    authenticate_as(moderator["id"])
    moderator_response = client.get(
        "/admin/community-games",
        params={"query": host["email"]},
    )

    authenticate_as(admin["id"])
    admin_response = client.get(
        "/admin/community-games",
        params={"query": host["email"]},
    )

    assert moderator_response.status_code == 200, moderator_response.text
    assert moderator_response.json()["total_count"] == 0
    assert moderator_response.json()["games"] == []
    assert admin_response.status_code == 200, admin_response.text
    assert admin_response.json()["total_count"] == 1
    assert [item["id"] for item in admin_response.json()["games"]] == [game["id"]]


def test_admin_community_game_detail_scopes_publish_fee_and_returns_audit_summary(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    host = create_user(client, first_name="Taylor", last_name="Host")
    game = create_community_game(client, host)
    detail = create_community_game_detail(
        client,
        game["id"],
        payment_methods_snapshot=[{"type": "venmo", "value": "@host"}],
        payment_instructions_snapshot="Pay before kickoff.",
    )
    fee = create_host_publish_fee(client, game["id"], host["id"])
    action = create_admin_action(
        client,
        admin["id"],
        action_type="hide_unsafe_community_payment_text",
        target_game_id=game["id"],
        target_user_id=host["id"],
        reason="Unsafe payment text reviewed.",
        metadata={"source": "ci"},
    )

    authenticate_as(moderator["id"])
    response = client.get(f"/admin/community-games/{game['id']}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["game"]["id"] == game["id"]
    assert "created_by_user_id" not in body["game"]
    assert "cancelled_by_user_id" not in body["game"]
    assert "completed_by_user_id" not in body["game"]
    assert "deleted_at" not in body["game"]
    assert "host_user_id" not in body["game"]
    assert body["host"]["id"] == host["id"]
    assert body["payment_snapshot"] == {
        "id": detail["id"],
        "payment_methods_snapshot": [{"type": "venmo", "value": "@host"}],
        "payment_instructions_snapshot": "Pay before kickoff.",
        "payment_text_moderation_status": "visible",
        "payment_text_hidden_at": None,
        "payment_text_hidden_by_user_id": None,
        "payment_text_hidden_reason": None,
        "created_at": detail["created_at"],
        "updated_at": detail["updated_at"],
    }
    assert body["publish_fee"] is None
    assert body["audit_actions"] == [
        {
            "id": action["id"],
            "admin_user_id": admin["id"],
            "action_type": "hide_unsafe_community_payment_text",
            "reason": "Unsafe payment text reviewed.",
            "created_at": action["created_at"],
        }
    ]
    assert body["capabilities"] == {
        "can_read_audit": True,
        "can_read_publish_fee": False,
        "can_flag_game": True,
        "can_resolve_review_flags": False,
        "can_hide_unsafe_payment_text": True,
        "can_cancel_game": False,
    }

    authenticate_as(admin["id"])
    admin_response = client.get(f"/admin/community-games/{game['id']}")

    assert admin_response.status_code == 200, admin_response.text
    admin_body = admin_response.json()
    assert admin_body["publish_fee"] == {
        "id": fee["id"],
        "amount_cents": 0,
        "currency": "USD",
        "fee_status": "waived",
        "waiver_reason": "first_game_free",
        "paid_at": None,
        "payment_status": None,
        "created_at": fee["created_at"],
        "updated_at": fee["updated_at"],
    }
    assert "payment_id" not in admin_body["publish_fee"]
    assert admin_body["capabilities"]["can_read_publish_fee"] is True


def test_admin_community_games_batches_participant_summary_queries(
    client: TestClient,
):
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    first_host = create_user(client)
    second_host = create_user(client)
    first_game = create_community_game(
        client,
        first_host,
        title="First Community Game",
    )
    second_game = create_community_game(
        client,
        second_host,
        title="Second Community Game",
    )
    first_player = create_user(client)
    second_player = create_user(client)
    create_game_participant(client, first_player["id"], first_game["id"])
    create_game_participant(client, second_player["id"], second_game["id"])
    participant_statements: list[str] = []

    def capture_participant_query(
        connection,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ):
        del connection, cursor, parameters, context, executemany
        if "FROM game_participants" in statement:
            participant_statements.append(statement)

    authenticate_as(moderator["id"])
    event.listen(engine, "before_cursor_execute", capture_participant_query)
    try:
        response = client.get("/admin/community-games")
    finally:
        event.remove(engine, "before_cursor_execute", capture_participant_query)

    assert response.status_code == 200, response.text
    assert len(response.json()["games"]) == 2
    assert len(participant_statements) == 1


def test_admin_community_games_list_supports_offset_pagination(
    client: TestClient,
):
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    first_host = create_user(client)
    second_host = create_user(client)
    first_game = create_community_game(client, first_host)
    second_game = create_community_game(client, second_host)

    authenticate_as(moderator["id"])
    first_response = client.get(
        "/admin/community-games",
        params={"limit": 1, "offset": 0},
    )
    second_response = client.get(
        "/admin/community-games",
        params={"limit": 1, "offset": 1},
    )

    assert first_response.status_code == 200, first_response.text
    assert second_response.status_code == 200, second_response.text
    first_body = first_response.json()
    second_body = second_response.json()
    assert first_body["total_count"] == 2
    assert second_body["total_count"] == 2
    assert first_body["offset"] == 0
    assert second_body["offset"] == 1
    assert {
        first_body["games"][0]["id"],
        second_body["games"][0]["id"],
    } == {first_game["id"], second_game["id"]}


def test_moderator_support_flag_limit_counts_only_visible_flags(
    client: TestClient,
):
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    host = create_user(client)
    game = create_community_game(client, host)

    with SessionLocal() as db:
        visible_flag = create_support_flag(
            db,
            flag_type="community_game_review_required",
            source="admin",
            title="Community game review required",
            summary="This support-safe flag should remain visible.",
            target_game_id=UUID(game["id"]),
            idempotency_key=f"visible-community-flag-{unique_suffix()}",
        )
        sensitive_flag = create_support_flag(
            db,
            flag_type="official_cancel_partial_failure",
            source="official_game",
            title="Sensitive cancellation follow-up",
            summary="This money-sensitive flag must not consume the visible limit.",
            target_game_id=UUID(game["id"]),
            idempotency_key=f"sensitive-community-flag-{unique_suffix()}",
        )
        visible_flag.created_at = datetime.now(UTC) - timedelta(minutes=1)
        sensitive_flag.created_at = datetime.now(UTC)
        db.commit()
        visible_flag_id = str(visible_flag.id)

    authenticate_as(moderator["id"])
    response = client.get(
        f"/admin/community-games/{game['id']}",
        params={"support_flag_limit": 1},
    )
    generic_response = client.get(
        "/admin/support-flags",
        params={"limit": 1},
    )

    assert response.status_code == 200, response.text
    assert [flag["id"] for flag in response.json()["support_flags"]] == [
        visible_flag_id
    ]
    assert response.json()["support_flag_total_count"] == 1
    assert generic_response.status_code == 200, generic_response.text
    assert [flag["id"] for flag in generic_response.json()] == [visible_flag_id]


def test_admin_community_game_detail_paginates_flags_and_audit_independently(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    host = create_user(client)
    game = create_community_game(client, host)

    with SessionLocal() as db:
        older_flag = create_support_flag(
            db,
            flag_type="community_game_review_required",
            source="admin",
            title="Older visible flag",
            summary="Older visible support flag.",
            target_game_id=UUID(game["id"]),
            idempotency_key=f"older-community-flag-{unique_suffix()}",
        )
        newer_flag = create_support_flag(
            db,
            flag_type="community_game_review_required",
            source="admin",
            title="Newer visible flag",
            summary="Newer visible support flag.",
            target_game_id=UUID(game["id"]),
            idempotency_key=f"newer-community-flag-{unique_suffix()}",
        )
        older_flag.created_at = datetime.now(UTC) - timedelta(minutes=2)
        newer_flag.created_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
        older_flag_id = str(older_flag.id)

    create_admin_action(
        client,
        admin["id"],
        action_type="hide_unsafe_community_payment_text",
        target_game_id=game["id"],
        reason="First community audit row.",
    )
    create_admin_action(
        client,
        admin["id"],
        action_type="hide_unsafe_community_payment_text",
        target_game_id=game["id"],
        reason="Second community audit row.",
    )

    authenticate_as(moderator["id"])
    response = client.get(
        f"/admin/community-games/{game['id']}",
        params={
            "support_flag_limit": 1,
            "support_flag_offset": 1,
            "audit_limit": 1,
            "audit_offset": 1,
        },
    )

    assert response.status_code == 200, response.text
    detail = response.json()
    assert detail["support_flag_total_count"] == 2
    assert detail["support_flag_offset"] == 1
    assert detail["support_flag_limit"] == 1
    assert [flag["id"] for flag in detail["support_flags"]] == [older_flag_id]
    assert detail["audit_total_count"] == 2
    assert detail["audit_offset"] == 1
    assert detail["audit_limit"] == 1
    assert len(detail["audit_actions"]) == 1


def test_moderator_flags_community_game_for_admin_review(
    client: TestClient,
):
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    host = create_user(client)
    game = create_community_game(client, host)
    create_community_game_detail(client, game["id"])

    authenticate_as(moderator["id"])
    response = client.post(
        f"/admin/community-games/{game['id']}/flag-for-review",
        json={
            "reason": "Host behavior needs an admin policy review.",
            "idempotency_key": f"community-review-{unique_suffix()}",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["game_id"] == game["id"]
    assert body["idempotent_replay"] is False
    assert body["support_flag"]["flag_type"] == "community_game_review_required"
    assert body["support_flag"]["flag_status"] == "open"
    assert body["support_flag"]["summary"] == (
        "Host behavior needs an admin policy review."
    )
    assert body["moderation_state"]["review_flag_status"] == "open"

    detail_response = client.get(f"/admin/community-games/{game['id']}")

    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert detail["moderation_state"]["review_flag_status"] == "open"
    assert detail["capabilities"]["can_resolve_review_flags"] is False
    assert [flag["id"] for flag in detail["support_flags"]] == [
        body["support_flag"]["id"]
    ]

    support_flag_response = client.get(
        f"/admin/support-flags/{body['support_flag']['id']}"
    )
    assert support_flag_response.status_code == 200, support_flag_response.text
    support_flag_body = support_flag_response.json()
    assert {
        "metadata",
        "idempotency_key",
        "source_admin_action_id",
        "created_by_user_id",
        "resolved_by_user_id",
        "resolution_admin_action_id",
    }.isdisjoint(support_flag_body)


def test_community_review_flag_service_enforces_permission(
    client: TestClient,
):
    host = create_user(client)
    regular_user = create_user(client)
    game = create_community_game(client, host)

    with SessionLocal() as db:
        db_regular_user = db.get(User, UUID(regular_user["id"]))
        assert db_regular_user is not None
        with pytest.raises(HTTPException) as exc_info:
            admin_community_service.flag_admin_community_game_for_review(
                db,
                game_id=UUID(game["id"]),
                admin_user=db_regular_user,
                payload=AdminCommunityGameReviewFlagCreate(
                    reason="This service call must be denied.",
                    idempotency_key=f"community-review-denied-{unique_suffix()}",
                ),
            )

    assert exc_info.value.status_code == 403


def test_community_game_review_flag_is_idempotent_and_blocks_open_duplicate(
    client: TestClient,
):
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    host = create_user(client)
    game = create_community_game(client, host)
    idempotency_key = f"community-review-replay-{unique_suffix()}"
    payload = {
        "reason": "Community game needs policy review.",
        "idempotency_key": idempotency_key,
    }

    authenticate_as(moderator["id"])
    first_response = client.post(
        f"/admin/community-games/{game['id']}/flag-for-review",
        json=payload,
    )
    replay_response = client.post(
        f"/admin/community-games/{game['id']}/flag-for-review",
        json=payload,
    )
    mismatch_response = client.post(
        f"/admin/community-games/{game['id']}/flag-for-review",
        json={
            "reason": "Different review reason.",
            "idempotency_key": idempotency_key,
        },
    )
    duplicate_response = client.post(
        f"/admin/community-games/{game['id']}/flag-for-review",
        json={
            "reason": "Another review request.",
            "idempotency_key": f"community-review-duplicate-{unique_suffix()}",
        },
    )

    assert first_response.status_code == 200, first_response.text
    assert replay_response.status_code == 200, replay_response.text
    assert replay_response.json()["idempotent_replay"] is True
    assert replay_response.json()["support_flag"]["id"] == (
        first_response.json()["support_flag"]["id"]
    )
    assert mismatch_response.status_code == 409, mismatch_response.text
    assert duplicate_response.status_code == 409, duplicate_response.text


def test_only_admin_can_resolve_community_game_review_flag(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    host = create_user(client)
    game = create_community_game(client, host)

    authenticate_as(moderator["id"])
    create_response = client.post(
        f"/admin/community-games/{game['id']}/flag-for-review",
        json={
            "reason": "Admin review is required.",
            "idempotency_key": f"community-review-resolve-{unique_suffix()}",
        },
    )
    assert create_response.status_code == 200, create_response.text
    support_flag_id = create_response.json()["support_flag"]["id"]
    resolution_payload = {
        "outcome": "handled_externally",
        "reason": "Admin reviewed the game and handled the follow-up.",
        "idempotency_key": f"community-review-resolution-{unique_suffix()}",
    }

    moderator_response = client.post(
        f"/admin/support-flags/{support_flag_id}/resolve",
        json={
            "outcome": "no_action_needed",
            "reason": "Moderator must not resolve this flag.",
            "idempotency_key": f"moderator-review-resolution-{unique_suffix()}",
        },
    )
    assert moderator_response.status_code == 403, moderator_response.text

    authenticate_as(admin["id"])
    missing_key_response = client.post(
        f"/admin/support-flags/{support_flag_id}/resolve",
        json={
            "outcome": "handled_externally",
            "reason": "Community review resolution requires retry protection.",
        },
    )
    admin_response = client.post(
        f"/admin/support-flags/{support_flag_id}/resolve",
        json=resolution_payload,
    )
    replay_response = client.post(
        f"/admin/support-flags/{support_flag_id}/resolve",
        json=resolution_payload,
    )
    mismatch_response = client.post(
        f"/admin/support-flags/{support_flag_id}/resolve",
        json={
            **resolution_payload,
            "reason": "A different resolution request.",
        },
    )

    assert missing_key_response.status_code == 400, missing_key_response.text
    assert admin_response.status_code == 200, admin_response.text
    assert admin_response.json()["flag_status"] == "resolved"
    assert admin_response.json()["resolution_outcome"] == "handled_externally"
    assert replay_response.status_code == 200, replay_response.text
    assert replay_response.json()["flag_status"] == "resolved"
    assert mismatch_response.status_code == 409, mismatch_response.text

    detail_response = client.get(f"/admin/community-games/{game['id']}")

    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert detail["moderation_state"]["review_flag_status"] == "resolved"
    assert detail["capabilities"]["can_resolve_review_flags"] is True
    assert detail["support_flags"][0]["resolution_reason"] == (
        "Admin reviewed the game and handled the follow-up."
    )

    audit_response = client.get(
        "/admin/actions",
        params={"target_support_flag_id": support_flag_id},
    )
    assert audit_response.status_code == 200, audit_response.text
    resolution_actions = [
        action
        for action in audit_response.json()
        if action["action_type"] == "resolve_support_flag"
    ]
    assert len(resolution_actions) == 1
    assert resolution_actions[0]["idempotency_key"] == (
        resolution_payload["idempotency_key"]
    )


def test_admin_community_game_hide_payment_text_hides_public_snapshot_and_audits(
    client: TestClient,
):
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    host = create_user(client)
    game = create_community_game(client, host)
    detail = create_community_game_detail(
        client,
        game["id"],
        payment_methods_snapshot=[{"type": "venmo", "value": "@unsafe-host"}],
        payment_instructions_snapshot="Unsafe payment text.",
    )

    authenticate_as(moderator["id"])
    response = client.post(
        f"/admin/community-games/{game['id']}/hide-payment-text",
        json={
            "reason": "Unsafe external payment text.",
            "idempotency_key": f"hide-payment-text-{unique_suffix()}",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["game_id"] == game["id"]
    assert body["idempotent_replay"] is False
    assert body["payment_snapshot"]["id"] == detail["id"]
    assert body["payment_snapshot"]["payment_methods_snapshot"] == [
        {"type": "venmo", "value": "@unsafe-host"}
    ]
    assert body["payment_snapshot"]["payment_instructions_snapshot"] == (
        "Unsafe payment text."
    )
    assert body["payment_snapshot"]["payment_text_moderation_status"] == "hidden"
    assert body["payment_snapshot"]["payment_text_hidden_at"] is not None
    assert body["payment_snapshot"]["payment_text_hidden_by_user_id"] == moderator["id"]
    assert body["payment_snapshot"]["payment_text_hidden_reason"] == (
        "Unsafe external payment text."
    )
    assert body["moderation_state"]["host_payment_snapshot_present"] is True
    assert body["moderation_state"]["unsafe_payment_text_hidden"] is True
    assert body["moderation_state"]["payment_text_hidden_reason"] == (
        "Unsafe external payment text."
    )

    public_response = client.get(
        "/community-game-details",
        params={"game_id": game["id"]},
    )

    assert public_response.status_code == 200, public_response.text
    public_detail = public_response.json()[0]
    assert public_detail["payment_methods_snapshot"] == []
    assert public_detail["payment_instructions_snapshot"] is None
    assert public_detail["payment_text_moderation_status"] == "hidden"
    assert "payment_text_hidden_at" not in public_detail
    assert "payment_text_hidden_by_user_id" not in public_detail
    assert "payment_text_hidden_reason" not in public_detail

    audit_response = client.get(
        "/admin/actions",
        params={
            "action_type": "hide_unsafe_community_payment_text",
            "target_game_id": game["id"],
        },
    )

    assert audit_response.status_code == 200, audit_response.text
    audit_action = audit_response.json()[0]
    assert audit_action["id"] == body["audit_action_id"]
    assert audit_action["target_game_id"] == game["id"]
    assert audit_action["target_user_id"] == host["id"]
    assert audit_action["reason"] == "Unsafe external payment text."
    assert audit_action["metadata"] == {
        "source": "admin_community_game_detail",
        "before": {
            "payment_text_moderation_status": "visible",
            "payment_method_count": 1,
            "had_payment_instructions": True,
        },
        "after": {
            "payment_text_moderation_status": "hidden",
            "payment_method_count": 1,
            "had_payment_instructions": True,
        },
    }
    assert "@unsafe-host" not in str(audit_action["metadata"])
    assert "Unsafe payment text." not in str(audit_action["metadata"])


def test_admin_community_game_hide_payment_text_is_idempotent(
    client: TestClient,
):
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    host = create_user(client)
    game = create_community_game(client, host)
    create_community_game_detail(
        client,
        game["id"],
        payment_methods_snapshot=[{"type": "venmo", "value": "@host"}],
    )
    idempotency_key = f"hide-payment-replay-{unique_suffix()}"
    payload = {
        "reason": "Unsafe external payment text.",
        "idempotency_key": idempotency_key,
    }

    authenticate_as(moderator["id"])
    first_response = client.post(
        f"/admin/community-games/{game['id']}/hide-payment-text",
        json=payload,
    )
    replay_response = client.post(
        f"/admin/community-games/{game['id']}/hide-payment-text",
        json=payload,
    )
    mismatch_response = client.post(
        f"/admin/community-games/{game['id']}/hide-payment-text",
        json={
            "reason": "Different reason.",
            "idempotency_key": idempotency_key,
        },
    )

    assert first_response.status_code == 200, first_response.text
    assert replay_response.status_code == 200, replay_response.text
    assert replay_response.json()["idempotent_replay"] is True
    assert replay_response.json()["audit_action_id"] == (
        first_response.json()["audit_action_id"]
    )
    assert mismatch_response.status_code == 409, mismatch_response.text


def test_admin_community_game_hide_payment_text_rechecks_replay_after_lock(
    client: TestClient,
    monkeypatch,
):
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    host = create_user(client)
    game = create_community_game(client, host)
    create_community_game_detail(
        client,
        game["id"],
        payment_methods_snapshot=[{"type": "venmo", "value": "@host"}],
    )
    payload = {
        "reason": "Unsafe external payment text.",
        "idempotency_key": f"hide-payment-race-{unique_suffix()}",
    }

    authenticate_as(moderator["id"])
    first_response = client.post(
        f"/admin/community-games/{game['id']}/hide-payment-text",
        json=payload,
    )
    assert first_response.status_code == 200, first_response.text

    original_lookup = (
        admin_community_service.get_existing_hide_payment_text_action
    )
    lookup_count = 0

    def miss_before_lock_then_find(*args, **kwargs):
        nonlocal lookup_count
        lookup_count += 1
        if lookup_count == 1:
            return None
        return original_lookup(*args, **kwargs)

    monkeypatch.setattr(
        admin_community_service,
        "get_existing_hide_payment_text_action",
        miss_before_lock_then_find,
    )
    replay_response = client.post(
        f"/admin/community-games/{game['id']}/hide-payment-text",
        json=payload,
    )

    assert replay_response.status_code == 200, replay_response.text
    assert replay_response.json()["idempotent_replay"] is True
    assert replay_response.json()["audit_action_id"] == (
        first_response.json()["audit_action_id"]
    )
    assert lookup_count == 2


def test_admin_community_game_hide_payment_text_requires_permission(
    client: TestClient,
):
    regular_user = create_user(client)
    host = create_user(client)
    game = create_community_game(client, host)
    create_community_game_detail(client, game["id"])

    authenticate_as(regular_user["id"])
    response = client.post(
        f"/admin/community-games/{game['id']}/hide-payment-text",
        json={
            "reason": "Unsafe external payment text.",
            "idempotency_key": f"hide-denied-{unique_suffix()}",
        },
    )

    assert response.status_code == 403, response.text


def test_community_hide_payment_text_service_enforces_permission(
    client: TestClient,
):
    regular_user = create_user(client)
    host = create_user(client)
    game = create_community_game(client, host)
    create_community_game_detail(client, game["id"])

    with SessionLocal() as db:
        db_regular_user = db.get(User, UUID(regular_user["id"]))
        assert db_regular_user is not None
        with pytest.raises(HTTPException) as exc_info:
            admin_community_service.hide_admin_community_game_payment_text(
                db,
                game_id=UUID(game["id"]),
                admin_user=db_regular_user,
                payload=AdminCommunityGameHidePaymentTextCreate(
                    reason="This service call must be denied.",
                    idempotency_key=f"hide-payment-denied-{unique_suffix()}",
                ),
            )

    assert exc_info.value.status_code == 403


def test_admin_community_games_requires_community_read_permission(
    client: TestClient,
):
    regular_user = create_user(client)
    authenticate_as(regular_user["id"])

    list_response = client.get("/admin/community-games")
    detail_response = client.get(
        "/admin/community-games/00000000-0000-4000-8000-000000000001"
    )
    hide_response = client.post(
        "/admin/community-games/00000000-0000-4000-8000-000000000001/hide-payment-text",
        json={
            "reason": "Unsafe external payment text.",
            "idempotency_key": "hide-denied-read",
        },
    )
    flag_response = client.post(
        "/admin/community-games/00000000-0000-4000-8000-000000000001/flag-for-review",
        json={
            "reason": "Review denied.",
            "idempotency_key": "flag-denied-read",
        },
    )

    assert list_response.status_code == 403, list_response.text
    assert detail_response.status_code == 403, detail_response.text
    assert hide_response.status_code == 403, hide_response.text
    assert flag_response.status_code == 403, flag_response.text


def test_admin_community_game_detail_rejects_official_game(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    official_game = create_game(client, admin["id"], venue)

    authenticate_as(admin["id"])
    response = client.get(f"/admin/community-games/{official_game['id']}")

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "Community game not found."


def test_admin_need_a_sub_list_and_detail_include_removed_history(
    client: TestClient,
):
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    owner = create_user(client, first_name="Morgan", last_name="Owner")
    requester = create_user(client, first_name="Riley", last_name="Sub")
    post = create_sub_post(client, owner["id"], team_name="Lakefront FC")

    authenticate_as(requester["id"])
    request_response = client.post(
        f"/need-a-sub/posts/{post['id']}/requests",
        json={"sub_post_position_id": post["positions"][0]["id"]},
    )
    assert request_response.status_code == 201, request_response.text
    request = request_response.json()

    authenticate_as(owner["id"])
    accept_response = client.patch(
        f"/need-a-sub/requests/{request['id']}/accept"
    )
    assert accept_response.status_code == 200, accept_response.text

    authenticate_as(moderator["id"])
    remove_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/remove",
        json={
            "remove_reason": "Removed for support review.",
            "idempotency_key": f"remove-sub-post-{unique_suffix()}",
        },
    )
    assert remove_response.status_code == 200, remove_response.text

    list_response = client.get(
        "/admin/need-a-sub",
        params={"post_status": "removed", "query": "Lakefront"},
    )

    assert list_response.status_code == 200, list_response.text
    list_body = list_response.json()
    assert list_body["total_count"] == 1
    assert list_body["offset"] == 0
    assert list_body["limit"] == 50
    assert [item["id"] for item in list_body["posts"]] == [post["id"]]
    listed_post = list_body["posts"][0]
    assert listed_post["owner"]["display_name"] == "Morgan Owner"
    assert listed_post["request_counts"] == {
        "total_count": 1,
        "pending_count": 0,
        "confirmed_count": 0,
        "waitlisted_count": 0,
        "terminal_count": 1,
    }

    detail_response = client.get(f"/admin/need-a-sub/{post['id']}")

    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert detail["post"]["id"] == post["id"]
    assert detail["post"]["post_status"] == "removed"
    assert detail["post"]["address_line_1"] == "123 Test Ave"
    assert detail["post"]["remove_reason"] == "Removed for support review."
    assert detail["owner"]["display_name"] == "Morgan Owner"
    assert len(detail["post"]["positions"]) == 2
    assert detail["request_total_count"] == 1
    assert detail["request_offset"] == 0
    assert detail["request_limit"] == 50
    assert len(detail["requests"]) == 1
    assert detail["requests"][0]["requester"]["display_name"] == "Riley Sub"
    assert detail["requests"][0]["request_status"] == "canceled_by_owner"
    assert [row["new_status"] for row in detail["requests"][0]["status_history"]] == [
        "pending",
        "confirmed",
        "canceled_by_owner",
    ]
    assert [row["new_status"] for row in detail["post_status_history"]] == [
        "active",
        "removed",
    ]
    assert any(
        action["action_type"] == "remove_sub_post"
        and action["reason"] == "Removed for support review."
        for action in detail["audit_actions"]
    )
    assert detail["audit_total_count"] == 1
    assert detail["audit_offset"] == 0
    assert detail["audit_limit"] == 50


def test_admin_need_a_sub_search_hides_email_from_moderator(
    client: TestClient,
):
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    owner = create_user(
        client,
        first_name="Private",
        last_name="Owner",
        email=f"private-owner-{unique_suffix()}@example.com",
    )
    post = create_sub_post(client, owner["id"], team_name="Email Hidden Subs")

    authenticate_as(moderator["id"])
    moderator_response = client.get(
        "/admin/need-a-sub",
        params={"query": owner["email"]},
    )

    authenticate_as(admin["id"])
    admin_response = client.get(
        "/admin/need-a-sub",
        params={"query": owner["email"]},
    )

    assert moderator_response.status_code == 200, moderator_response.text
    assert moderator_response.json()["total_count"] == 0
    assert moderator_response.json()["posts"] == []
    assert admin_response.status_code == 200, admin_response.text
    assert admin_response.json()["total_count"] == 1
    assert [item["id"] for item in admin_response.json()["posts"]] == [post["id"]]


def test_admin_need_a_sub_list_and_detail_are_paginated(
    client: TestClient,
):
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    first_owner = create_user(client)
    second_owner = create_user(client)
    first_post = create_sub_post(client, first_owner["id"], team_name="First Page FC")
    create_sub_post(client, second_owner["id"], team_name="Second Page FC")
    first_requester = create_user(client)
    second_requester = create_user(client)

    for requester, position in (
        (first_requester, first_post["positions"][0]),
        (second_requester, first_post["positions"][1]),
    ):
        authenticate_as(requester["id"])
        response = client.post(
            f"/need-a-sub/posts/{first_post['id']}/requests",
            json={"sub_post_position_id": position["id"]},
        )
        assert response.status_code == 201, response.text

    with SessionLocal() as db:
        db.add_all(
            [
                AdminAction(
                    id=uuid4(),
                    admin_user_id=UUID(moderator["id"]),
                    action_type="remove_sub_post",
                    target_sub_post_id=UUID(first_post["id"]),
                    reason="First support audit row.",
                ),
                AdminAction(
                    id=uuid4(),
                    admin_user_id=UUID(moderator["id"]),
                    action_type="remove_sub_post",
                    target_sub_post_id=UUID(first_post["id"]),
                    reason="Second support audit row.",
                ),
            ]
        )
        db.commit()

    authenticate_as(moderator["id"])
    list_response = client.get(
        "/admin/need-a-sub",
        params={"limit": 1, "offset": 1},
    )
    detail_response = client.get(
        f"/admin/need-a-sub/{first_post['id']}",
        params={
            "request_limit": 1,
            "request_offset": 1,
            "audit_limit": 1,
            "audit_offset": 1,
        },
    )

    assert list_response.status_code == 200, list_response.text
    assert list_response.json()["total_count"] == 2
    assert list_response.json()["offset"] == 1
    assert list_response.json()["limit"] == 1
    assert len(list_response.json()["posts"]) == 1

    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert detail["request_total_count"] == 2
    assert detail["request_offset"] == 1
    assert detail["request_limit"] == 1
    assert len(detail["requests"]) == 1
    assert detail["audit_total_count"] == 2
    assert detail["audit_offset"] == 1
    assert detail["audit_limit"] == 1
    assert len(detail["audit_actions"]) == 1


def test_admin_need_a_sub_reads_expire_due_posts_and_requests(
    client: TestClient,
):
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    owner = create_user(client)
    requester = create_user(client)
    post = create_sub_post(client, owner["id"], team_name="Expired Support FC")

    authenticate_as(requester["id"])
    request_response = client.post(
        f"/need-a-sub/posts/{post['id']}/requests",
        json={"sub_post_position_id": post["positions"][0]["id"]},
    )
    assert request_response.status_code == 201, request_response.text

    past_start = datetime.now(UTC) - timedelta(hours=2)
    with SessionLocal() as db:
        stored_post = db.get(SubPost, UUID(post["id"]))
        assert stored_post is not None
        stored_post.starts_at = past_start
        stored_post.ends_at = past_start + timedelta(hours=1)
        stored_post.starts_on_local = past_start.date()
        stored_post.expires_at = past_start
        db.commit()

    authenticate_as(moderator["id"])
    list_response = client.get(
        "/admin/need-a-sub",
        params={"query": post["id"]},
    )
    detail_response = client.get(f"/admin/need-a-sub/{post['id']}")

    assert list_response.status_code == 200, list_response.text
    listed_post = list_response.json()["posts"][0]
    assert listed_post["post_status"] == "expired"
    assert listed_post["request_counts"]["pending_count"] == 0
    assert listed_post["request_counts"]["terminal_count"] == 1

    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert detail["post"]["post_status"] == "expired"
    assert detail["requests"][0]["request_status"] == "expired"
    assert detail["requests"][0]["expired_at"] is not None
    assert detail["post_status_history"][-1]["new_status"] == "expired"


def test_admin_need_a_sub_read_requires_permission_and_returns_404(
    client: TestClient,
):
    regular_user = create_user(client)
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")

    authenticate_as(regular_user["id"])
    list_response = client.get("/admin/need-a-sub")
    detail_response = client.get(
        "/admin/need-a-sub/00000000-0000-4000-8000-000000000001"
    )

    assert list_response.status_code == 403, list_response.text
    assert detail_response.status_code == 403, detail_response.text

    authenticate_as(moderator["id"])
    missing_response = client.get(
        "/admin/need-a-sub/00000000-0000-4000-8000-000000000001"
    )

    assert missing_response.status_code == 404, missing_response.text
    assert missing_response.json()["detail"] == "Need a Sub post not found."


def test_admin_need_a_sub_removal_notifies_and_preserves_support_history(
    client: TestClient,
):
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    owner = create_user(client)
    requester = create_user(client)
    terminal_requester = create_user(client)
    post = create_sub_post(client, owner["id"], team_name="Removal Test FC")

    authenticate_as(requester["id"])
    request_response = client.post(
        f"/need-a-sub/posts/{post['id']}/requests",
        json={"sub_post_position_id": post["positions"][0]["id"]},
    )
    assert request_response.status_code == 201, request_response.text
    request = request_response.json()

    authenticate_as(owner["id"])
    accept_response = client.patch(
        f"/need-a-sub/requests/{request['id']}/accept"
    )
    assert accept_response.status_code == 200, accept_response.text

    authenticate_as(terminal_requester["id"])
    terminal_request_response = client.post(
        f"/need-a-sub/posts/{post['id']}/requests",
        json={"sub_post_position_id": post["positions"][1]["id"]},
    )
    assert terminal_request_response.status_code == 201, terminal_request_response.text
    terminal_request = terminal_request_response.json()

    authenticate_as(owner["id"])
    decline_response = client.patch(
        f"/need-a-sub/requests/{terminal_request['id']}/decline",
        json={"reason": "Not a fit for this post."},
    )
    assert decline_response.status_code == 200, decline_response.text

    chat_response = client.post(f"/need-a-sub/posts/{post['id']}/chat", json={})
    assert chat_response.status_code == 200, chat_response.text
    chat = chat_response.json()
    message_response = client.post(
        f"/need-a-sub/posts/{post['id']}/chat/messages",
        json={
            "chat_id": chat["id"],
            "message_body": "Removal notification cleanup test.",
        },
    )
    assert message_response.status_code == 201, message_response.text

    authenticate_as(moderator["id"])
    remove_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/remove",
        json={
            "remove_reason": "Unsafe content reported to support.",
            "idempotency_key": f"remove-sub-post-{unique_suffix()}",
        },
    )

    assert remove_response.status_code == 200, remove_response.text
    assert remove_response.json()["post_status"] == "removed"
    assert remove_response.json()["remove_reason"] == (
        "Unsafe content reported to support."
    )
    assert remove_response.json()["removed_by_user_id"] == moderator["id"]
    removed_at = remove_response.json()["removed_at"]

    public_list_response = client.get("/need-a-sub/posts")
    public_detail_response = client.get(f"/need-a-sub/posts/{post['id']}")

    assert public_list_response.status_code == 200, public_list_response.text
    assert post["id"] not in {
        item["id"] for item in public_list_response.json()
    }
    assert public_detail_response.status_code == 404, public_detail_response.text

    for recipient in (owner, requester):
        authenticate_as(recipient["id"])
        notifications_response = client.get(
            "/notifications/me",
            params={"notification_domain": "need_a_sub"},
        )
        assert notifications_response.status_code == 200, notifications_response.text
        removal_notification = next(
            notification
            for notification in notifications_response.json()
            if notification["notification_type"] == "sub_post_removed"
        )
        assert removal_notification["title"] == "Post removed"
        assert removal_notification["summary"] == (
            "This Need a Sub post was removed."
        )
        assert removal_notification["body"] == (
            "This Need a Sub post was removed by Pickup Lane."
        )
        assert removal_notification["action_key"] is None
        assert removal_notification["action"] is None
        assert removal_notification["event_at"] == removed_at

        if recipient["id"] == requester["id"]:
            chat_notification = next(
                notification
                for notification in notifications_response.json()
                if notification["notification_type"] == "sub_chat_message"
            )
            assert chat_notification["is_read"] is True
            assert chat_notification["read_at"] == removed_at
            assert chat_notification["aggregate_count"] is None

    authenticate_as(terminal_requester["id"])
    terminal_notifications_response = client.get(
        "/notifications/me",
        params={"notification_domain": "need_a_sub"},
    )
    assert terminal_notifications_response.status_code == 200
    assert "sub_post_removed" not in {
        notification["notification_type"]
        for notification in terminal_notifications_response.json()
    }

    authenticate_as(moderator["id"])
    detail_response = client.get(f"/admin/need-a-sub/{post['id']}")

    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert detail["post"]["post_status"] == "removed"
    assert detail["post"]["remove_reason"] == "Unsafe content reported to support."
    requests_by_id = {item["id"]: item for item in detail["requests"]}
    assert requests_by_id[request["id"]]["request_status"] == "canceled_by_owner"
    assert requests_by_id[request["id"]]["status_history"][-1]["change_source"] == (
        "admin"
    )
    assert requests_by_id[terminal_request["id"]]["request_status"] == "declined"
    assert detail["post_status_history"][-1]["new_status"] == "removed"
    assert detail["post_status_history"][-1]["change_source"] == "admin"
    assert any(
        action["action_type"] == "remove_sub_post"
        and action["reason"] == "Unsafe content reported to support."
        for action in detail["audit_actions"]
    )


def test_admin_need_a_sub_chat_moderation_retains_rows_and_redacts_audit(
    client: TestClient,
):
    moderator = create_user(client)
    set_user_role(moderator["id"], "moderator")
    owner = create_user(client, first_name="Chat", last_name="Owner")
    requester = create_user(client, first_name="Chat", last_name="Player")
    regular_user = create_user(client)
    post = create_sub_post(client, owner["id"], team_name="Chat Review FC")

    authenticate_as(requester["id"])
    request_response = client.post(
        f"/need-a-sub/posts/{post['id']}/requests",
        json={"sub_post_position_id": post["positions"][0]["id"]},
    )
    assert request_response.status_code == 201, request_response.text

    authenticate_as(owner["id"])
    accept_response = client.patch(
        f"/need-a-sub/requests/{request_response.json()['id']}/accept"
    )
    assert accept_response.status_code == 200, accept_response.text
    chat_response = client.post(f"/need-a-sub/posts/{post['id']}/chat", json={})
    assert chat_response.status_code == 200, chat_response.text
    chat_id = chat_response.json()["id"]

    hidden_text = "Unsafe message that must not enter audit metadata."
    removed_text = "Second unsafe message retained only for support."
    hidden_message_response = client.post(
        f"/need-a-sub/posts/{post['id']}/chat/messages",
        json={"chat_id": chat_id, "message_body": hidden_text},
    )
    removed_message_response = client.post(
        f"/need-a-sub/posts/{post['id']}/chat/messages",
        json={"chat_id": chat_id, "message_body": removed_text},
    )
    assert hidden_message_response.status_code == 201, hidden_message_response.text
    assert removed_message_response.status_code == 201, removed_message_response.text
    hidden_message = hidden_message_response.json()
    removed_message = removed_message_response.json()

    authenticate_as(moderator["id"])
    chat_history_response = client.get(
        f"/admin/need-a-sub/{post['id']}/chat",
        params={"offset": 0, "limit": 1},
    )
    assert chat_history_response.status_code == 200, chat_history_response.text
    chat_history = chat_history_response.json()
    assert chat_history["total_message_count"] == 2
    assert chat_history["offset"] == 0
    assert chat_history["limit"] == 1
    assert [message["id"] for message in chat_history["messages"]] == [
        removed_message["id"]
    ]
    older_history_response = client.get(
        f"/admin/need-a-sub/{post['id']}/chat",
        params={"offset": 1, "limit": 1},
    )
    assert older_history_response.status_code == 200, older_history_response.text
    assert older_history_response.json()["offset"] == 1
    assert [
        message["id"] for message in older_history_response.json()["messages"]
    ] == [hidden_message["id"]]

    hide_payload = {
        "reason": "Hide unsafe scoped chat content.",
        "idempotency_key": "admin-sub-chat-hide-test",
    }
    hide_response = client.post(
        (
            f"/admin/need-a-sub/{post['id']}/chat/messages/"
            f"{hidden_message['id']}/hide"
        ),
        json=hide_payload,
    )
    assert hide_response.status_code == 200, hide_response.text
    assert hide_response.json()["message"]["moderation_status"] == "hidden_by_admin"
    assert hide_response.json()["message"]["message_body"] == hidden_text
    assert hide_response.json()["idempotent_replay"] is False

    hide_replay_response = client.post(
        (
            f"/admin/need-a-sub/{post['id']}/chat/messages/"
            f"{hidden_message['id']}/hide"
        ),
        json=hide_payload,
    )
    assert hide_replay_response.status_code == 200, hide_replay_response.text
    assert hide_replay_response.json()["idempotent_replay"] is True
    assert (
        hide_replay_response.json()["audit_action_id"]
        == hide_response.json()["audit_action_id"]
    )
    hide_conflict_response = client.post(
        (
            f"/admin/need-a-sub/{post['id']}/chat/messages/"
            f"{hidden_message['id']}/hide"
        ),
        json={
            **hide_payload,
            "reason": "A different moderation request.",
        },
    )
    assert hide_conflict_response.status_code == 409, hide_conflict_response.text

    authenticate_as(requester["id"])
    requester_notifications_response = client.get(
        "/notifications/me",
        params={"notification_domain": "need_a_sub"},
    )
    assert (
        requester_notifications_response.status_code == 200
    ), requester_notifications_response.text
    chat_notification = next(
        notification
        for notification in requester_notifications_response.json()
        if notification["notification_type"] == "sub_chat_message"
    )
    assert chat_notification["is_read"] is False
    assert chat_notification["aggregate_count"] == 1
    assert (
        chat_notification["related_sub_post_chat_message_id"]
        == removed_message["id"]
    )

    authenticate_as(moderator["id"])
    remove_payload = {
        "reason": "Remove severe scoped chat content.",
        "idempotency_key": "admin-sub-chat-remove-test",
    }
    remove_response = client.post(
        (
            f"/admin/need-a-sub/{post['id']}/chat/messages/"
            f"{removed_message['id']}/remove"
        ),
        json=remove_payload,
    )
    assert remove_response.status_code == 200, remove_response.text
    assert remove_response.json()["message"]["moderation_status"] == "removed_by_admin"
    assert remove_response.json()["message"]["message_body"] == removed_text
    assert remove_response.json()["idempotent_replay"] is False

    remove_replay_response = client.post(
        (
            f"/admin/need-a-sub/{post['id']}/chat/messages/"
            f"{removed_message['id']}/remove"
        ),
        json=remove_payload,
    )
    assert remove_replay_response.status_code == 200, remove_replay_response.text
    assert remove_replay_response.json()["idempotent_replay"] is True

    history_after_response = client.get(f"/admin/need-a-sub/{post['id']}/chat")
    assert history_after_response.status_code == 200, history_after_response.text
    messages_by_id = {
        message["id"]: message for message in history_after_response.json()["messages"]
    }
    assert messages_by_id[hidden_message["id"]]["message_body"] == hidden_text
    assert messages_by_id[hidden_message["id"]]["moderation_status"] == (
        "hidden_by_admin"
    )
    assert messages_by_id[removed_message["id"]]["message_body"] == removed_text
    assert messages_by_id[removed_message["id"]]["moderation_status"] == (
        "removed_by_admin"
    )

    authenticate_as(owner["id"])
    member_messages_response = client.get(
        f"/need-a-sub/posts/{post['id']}/chat/messages"
    )
    assert member_messages_response.status_code == 200, member_messages_response.text
    assert member_messages_response.json() == []

    authenticate_as(requester["id"])
    requester_notifications_response = client.get(
        "/notifications/me",
        params={"notification_domain": "need_a_sub"},
    )
    assert (
        requester_notifications_response.status_code == 200
    ), requester_notifications_response.text
    chat_notification = next(
        notification
        for notification in requester_notifications_response.json()
        if notification["notification_type"] == "sub_chat_message"
    )
    assert chat_notification["is_read"] is True
    assert chat_notification["read_at"] is not None
    assert chat_notification["aggregate_count"] is None

    authenticate_as(moderator["id"])
    audit_response = client.get(
        "/admin/actions",
        params={"target_sub_post_id": post["id"]},
    )
    assert audit_response.status_code == 200, audit_response.text
    moderation_actions = [
        action
        for action in audit_response.json()
        if action["action_type"] in {"hide_chat_message", "remove_chat_message"}
    ]
    assert {action["action_type"] for action in moderation_actions} == {
        "hide_chat_message",
        "remove_chat_message",
    }
    for action in moderation_actions:
        assert action["target_sub_chat_message_id"] in {
            hidden_message["id"],
            removed_message["id"],
        }
        assert "message_body" not in str(action["metadata"])
        assert hidden_text not in str(action["metadata"])
        assert removed_text not in str(action["metadata"])
        assert action["metadata"]["source"] == "admin_need_a_sub_chat"

    authenticate_as(owner["id"])
    cancel_response = client.patch(
        f"/need-a-sub/posts/{post['id']}/cancel",
        json={"cancel_reason": "Lifecycle status test."},
    )
    assert cancel_response.status_code == 200, cancel_response.text

    authenticate_as(moderator["id"])
    closed_chat_response = client.get(f"/admin/need-a-sub/{post['id']}/chat")
    assert closed_chat_response.status_code == 200, closed_chat_response.text
    assert closed_chat_response.json()["chat_status"] == "closed"
    assert closed_chat_response.json()["closed_at"] == cancel_response.json()[
        "canceled_at"
    ]

    authenticate_as(regular_user["id"])
    denied_history_response = client.get(f"/admin/need-a-sub/{post['id']}/chat")
    denied_moderation_response = client.post(
        (
            f"/admin/need-a-sub/{post['id']}/chat/messages/"
            f"{hidden_message['id']}/remove"
        ),
        json={
            "reason": "Should not run.",
            "idempotency_key": "denied-admin-sub-chat-test",
        },
    )
    assert denied_history_response.status_code == 403, denied_history_response.text
    assert denied_moderation_response.status_code == 403, denied_moderation_response.text
