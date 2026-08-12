from __future__ import annotations

from fastapi import status
from fastapi.testclient import TestClient

from backend.tests.helpers import create_game, create_user, create_venue
from backend.tests.support.auth import authenticate_optional_as


def schema_properties(openapi_schema: dict, component_name: str) -> set[str]:
    return set(openapi_schema["components"]["schemas"][component_name]["properties"])


def response_schema(openapi_schema: dict, path: str, method: str) -> dict:
    return openapi_schema["paths"][path][method]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]


def response_component(openapi_schema: dict, path: str, method: str) -> str:
    schema = response_schema(openapi_schema, path, method)
    if "$ref" in schema:
        return schema["$ref"].rsplit("/", 1)[-1]
    if "items" in schema:
        return schema["items"]["$ref"].rsplit("/", 1)[-1]
    raise AssertionError(f"{method.upper()} {path} does not reference a component")


def assert_has_fields(fields: set[str], expected_fields: set[str]) -> None:
    assert expected_fields <= fields


def assert_omits_fields(fields: set[str], omitted_fields: set[str]) -> None:
    assert not fields.intersection(omitted_fields)


def test_game_detail_route_uses_minimized_detail_contract(client: TestClient) -> None:
    openapi_schema = client.get("/openapi.json").json()
    fields = schema_properties(openapi_schema, "GameDetailRead")

    assert response_component(openapi_schema, "/games/{game_id}", "get") == "GameDetailRead"
    assert response_component(openapi_schema, "/games", "get") == "GameDetailRead"
    assert_has_fields(
        fields,
        {
            "id",
            "title",
            "venue_id",
            "venue_name_snapshot",
            "address_snapshot",
            "city_snapshot",
            "state_snapshot",
            "starts_at",
            "ends_at",
            "starts_on_local",
            "format_label",
            "total_spots",
            "price_per_player_cents",
            "currency",
            "allow_guests",
            "max_guests_per_booking",
            "is_chat_enabled",
        },
    )
    assert_omits_fields(
        fields,
        {
            "created_by_user_id",
            "cancelled_by_user_id",
            "cancellation_source",
            "completed_at",
            "completed_by_user_id",
            "created_at",
            "deleted_at",
            "policy_mode",
            "published_at",
            "sport_type",
            "updated_at",
        },
    )


def test_signed_out_game_detail_masks_host_only_fields(client: TestClient) -> None:
    host = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        game_type="community",
        host_user_id=host["id"],
        host_guest_max=4,
        price_per_player_cents=0,
    )

    signed_out_response = client.get(f"/games/{game['id']}")

    assert signed_out_response.status_code == status.HTTP_200_OK
    signed_out_body = signed_out_response.json()
    assert signed_out_body["host_user_id"] is None
    assert signed_out_body["host_guest_max"] == 0
    assert "created_by_user_id" not in signed_out_body
    assert "policy_mode" not in signed_out_body
    assert "deleted_at" not in signed_out_body

    authenticate_optional_as(host["id"], target_app=client.app)
    host_response = client.get(f"/games/{game['id']}")

    assert host_response.status_code == status.HTTP_200_OK
    host_body = host_response.json()
    assert host_body["host_user_id"] == host["id"]
    assert host_body["host_guest_max"] == 4


def test_user_routes_use_self_and_admin_contracts(client: TestClient) -> None:
    openapi_schema = client.get("/openapi.json").json()
    self_fields = schema_properties(openapi_schema, "SelfUserRead")
    admin_fields = schema_properties(openapi_schema, "AdminUserRead")

    assert response_component(openapi_schema, "/auth/me", "get") == "SelfUserRead"
    assert response_component(openapi_schema, "/auth/sync-user", "post") == "SelfUserRead"
    assert response_component(openapi_schema, "/auth/account", "delete") == "SelfUserRead"
    assert response_component(openapi_schema, "/users/me", "get") == "SelfUserRead"
    assert response_component(openapi_schema, "/users/me", "patch") == "SelfUserRead"
    assert response_component(openapi_schema, "/users", "get") == "AdminUserRead"
    assert response_component(openapi_schema, "/users/{user_id}", "get") == "AdminUserRead"
    assert_has_fields(
        self_fields,
        {
            "id",
            "role",
            "email",
            "email_verified_at",
            "phone",
            "first_name",
            "last_name",
            "date_of_birth",
            "profile_photo_url",
            "home_city",
            "home_state",
            "account_status",
            "hosting_status",
            "member_since",
        },
    )
    assert_omits_fields(self_fields, {"auth_user_id", "created_at", "updated_at", "deleted_at"})
    assert_has_fields(admin_fields, {"auth_user_id", "created_at", "updated_at", "deleted_at"})


def test_financial_and_provider_event_responses_are_audience_specific(
    client: TestClient,
) -> None:
    openapi_schema = client.get("/openapi.json").json()
    payment_fields = schema_properties(openapi_schema, "PaymentSummaryRead")
    admin_payment_fields = schema_properties(openapi_schema, "AdminPaymentRead")
    refund_fields = schema_properties(openapi_schema, "RefundSummaryRead")
    admin_refund_fields = schema_properties(openapi_schema, "AdminRefundRead")
    payment_event_fields = schema_properties(openapi_schema, "PaymentEventRead")

    assert response_component(openapi_schema, "/payments", "get") == "PaymentSummaryRead"
    assert response_component(
        openapi_schema,
        "/payments/{payment_id}",
        "get",
    ) == "PaymentSummaryRead"
    assert response_component(openapi_schema, "/refunds", "get") == "RefundSummaryRead"
    assert response_component(
        openapi_schema,
        "/refunds/{refund_id}",
        "get",
    ) == "RefundSummaryRead"
    assert_omits_fields(
        payment_fields,
        {
            "failure_code",
            "failure_message",
            "idempotency_key",
            "metadata",
            "provider",
            "provider_charge_id",
            "provider_payment_intent_id",
            "updated_at",
        },
    )
    assert_has_fields(
        admin_payment_fields,
        {"idempotency_key", "provider", "provider_charge_id", "provider_payment_intent_id"},
    )
    assert_omits_fields(
        refund_fields,
        {
            "approved_at",
            "approved_by_user_id",
            "last_refund_event_at",
            "origin_workflow",
            "provider",
            "provider_charge_id",
            "provider_refund_id",
            "provider_status",
            "provider_status_observed_at",
            "requested_by_user_id",
            "updated_at",
        },
    )
    assert_has_fields(
        admin_refund_fields,
        {"provider", "provider_refund_id", "provider_status", "last_refund_event_at"},
    )
    assert "raw_payload" not in payment_event_fields


def test_public_and_admin_image_contracts_are_separated(client: TestClient) -> None:
    openapi_schema = client.get("/openapi.json").json()
    venue_public_fields = schema_properties(openapi_schema, "VenueImagePublicRead")
    venue_admin_fields = schema_properties(openapi_schema, "VenueImageAdminRead")
    game_public_fields = schema_properties(openapi_schema, "GameImagePublicRead")
    game_admin_fields = schema_properties(openapi_schema, "GameImageAdminRead")

    assert response_component(openapi_schema, "/venue-images", "get") == "VenueImagePublicRead"
    assert response_component(
        openapi_schema,
        "/admin/venues/{venue_id}/images",
        "get",
    ) == "VenueImageAdminRead"
    assert response_component(openapi_schema, "/game-images", "get") == "GameImagePublicRead"
    assert response_component(
        openapi_schema,
        "/admin/game-images",
        "get",
    ) == "GameImageAdminRead"
    assert_has_fields(
        venue_public_fields,
        {"id", "venue_id", "image_url", "image_role", "is_primary", "sort_order"},
    )
    assert_omits_fields(
        venue_public_fields,
        {
            "content_type",
            "etag",
            "image_status",
            "size_bytes",
            "storage_account_id",
            "storage_bucket",
            "storage_object_key",
            "storage_provider",
            "upload_completed_at",
            "upload_requested_at",
            "uploaded_by_user_id",
        },
    )
    assert_has_fields(
        venue_admin_fields,
        {"content_type", "image_status", "storage_object_key", "uploaded_by_user_id"},
    )
    assert_omits_fields(
        game_public_fields,
        {"created_at", "deleted_at", "image_status", "updated_at", "uploaded_by_user_id"},
    )
    assert_has_fields(game_admin_fields, {"image_status", "uploaded_by_user_id"})


def test_participant_chat_and_policy_contracts_are_minimized(client: TestClient) -> None:
    openapi_schema = client.get("/openapi.json").json()
    game_chat_fields = schema_properties(openapi_schema, "ChatMessageParticipantRead")
    sub_chat_fields = schema_properties(openapi_schema, "SubPostChatMessageParticipantRead")
    policy_fields = schema_properties(openapi_schema, "PolicyDocumentPublicRead")
    admin_chat_fields = schema_properties(openapi_schema, "AdminChatMessageRead")
    participant_fields = schema_properties(openapi_schema, "PublicGameParticipantRead")

    assert response_component(openapi_schema, "/chat-messages", "get") == (
        "ChatMessageParticipantRead"
    )
    assert response_component(openapi_schema, "/chat-messages/{chat_message_id}", "get") == (
        "ChatMessageParticipantRead"
    )
    assert response_component(
        openapi_schema,
        "/need-a-sub/posts/{sub_post_id}/chat/messages",
        "get",
    ) == "SubPostChatMessageParticipantRead"
    assert response_component(
        openapi_schema,
        "/policy-documents",
        "get",
    ) == "PolicyDocumentPublicRead"
    assert_omits_fields(
        game_chat_fields,
        {
            "pinned_by_user_id",
            "removed_at",
            "removed_by_user_id",
            "removed_source",
            "restored_at",
            "restored_by_user_id",
            "review_status",
            "reviewed_at",
            "reviewed_by_user_id",
            "visibility_status",
        },
    )
    assert_omits_fields(
        sub_chat_fields,
        {
            "removed_at",
            "removed_by_user_id",
            "removed_source",
            "restored_at",
            "restored_by_user_id",
            "review_status",
            "reviewed_at",
            "reviewed_by_user_id",
            "visibility_status",
        },
    )
    assert_has_fields(admin_chat_fields, {"review_status", "visibility_status"})
    assert_omits_fields(
        policy_fields,
        {"created_at", "is_active", "retired_at", "updated_at"},
    )
    assert_omits_fields(
        participant_fields,
        {
            "account_status",
            "auth_user_id",
            "email",
            "email_verified_at",
            "guest_email",
            "guest_phone",
            "phone",
            "profile_photo_url",
        },
    )
