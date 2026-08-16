from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import get_args, get_origin

import pytest
from fastapi.routing import APIRoute

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

HTTP_RESPONSE_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})
NO_RESPONSE_MODEL = "None"

B2_OWNED_MINIMIZED = "B2-owned and already minimized"
B2_OWNED_CONTRADICTORY = "B2-owned and contradictory to frozen contract"
ADMIN_INTERNAL_PROVIDER_EXCEPTION = "explicit admin/internal/provider exception"
LATER_OWNER_NON_B2 = "later-owner/non-B2 scope"

FROZEN_CLASSIFICATION_CATEGORIES = {
    B2_OWNED_MINIMIZED,
    B2_OWNED_CONTRADICTORY,
    ADMIN_INTERNAL_PROVIDER_EXCEPTION,
    LATER_OWNER_NON_B2,
}

VAGUE_CLASSIFICATION_REASONS = {"out of scope", "admin", "fine", "legacy"}


@dataclass(frozen=True)
class RouteSurface:
    method: str
    path: str
    endpoint: str
    name: str
    response_model_name: str
    status_code: int
    response_class_name: str
    return_annotation_name: str


@dataclass(frozen=True)
class RouteClassification:
    category: str
    reason: str
    expected_status_code: int
    expected_response_model_name: str


PLATFORM_PROBE_REASON = (
    "Platform/runtime probe returns a tiny operational status payload; "
    "platform runtime owners prove health behavior rather than B2 response "
    "minimization."
)
ROOT_OPERATIONAL_REASON = (
    "Root operational smoke response returns a fixed availability message and "
    "does not expose product, provider, storage, or audience-specific fields."
)
NO_CONTENT_AUTH_REASON = (
    "No-content account cleanup endpoint returns HTTP 204 with no payload to "
    "minimize; WS03/auth owners prove account lifecycle behavior."
)
RETIRED_TOMBSTONE_REASON = (
    "Retired mutation tombstone returns only the standardized 410 error body; "
    "WS02-05A and route-lifecycle owners prove tombstone behavior."
)
ADMIN_OPERATIONAL_DICT_REASON = (
    "Active-admin upload readiness check returns a tiny bool capability "
    "dictionary and no image/provider object data; WS06 owns storage runtime."
)
PROVIDER_WEBHOOK_REASON = (
    "Provider webhook acknowledgement is provider-ingress behavior returning "
    "a small processing result; payment/provider owners prove lifecycle correctness."
)

MINIMIZED_SCHEMA_PROHIBITIONS = {
    "GameDetailRead": {
        "created_by_user_id",
        "sport_type",
        "policy_mode",
        "published_at",
        "cancelled_by_user_id",
        "cancellation_source",
        "completed_by_user_id",
        "created_at",
        "updated_at",
        "deleted_at",
    },
    "GameCardRead": {
        "created_by_user_id",
        "sport_type",
        "policy_mode",
        "published_at",
        "cancelled_by_user_id",
        "cancellation_source",
        "completed_by_user_id",
        "created_at",
        "updated_at",
        "deleted_at",
        "description",
        "address_snapshot",
        "host_user_id",
        "host_guest_max",
        "custom_rules_text",
        "custom_cancellation_text",
        "game_notes",
        "parking_notes",
    },
    "MyGameCardRead": {
        "created_by_user_id",
        "sport_type",
        "policy_mode",
        "published_at",
        "cancelled_by_user_id",
        "cancellation_source",
        "completed_by_user_id",
        "created_at",
        "updated_at",
        "deleted_at",
        "host_user_id",
        "host_guest_max",
        "game_notes",
        "parking_notes",
    },
    "PublicGameParticipantRead": {
        "guest_name",
        "guest_email",
        "guest_phone",
        "attendance_status",
        "price_cents",
        "currency",
        "checked_in_at",
        "marked_attendance_by_user_id",
        "attendance_decided_at",
        "attendance_notes",
        "created_at",
        "updated_at",
    },
    "SelfUserRead": {"auth_user_id", "created_at", "updated_at", "deleted_at"},
    "GameCheckoutPaymentIntentRead": {
        "provider",
        "provider_payment_intent_id",
        "provider_charge_id",
        "provider_event_id",
        "raw_payload",
        "payload",
        "idempotency_key",
        "reconciliation_status",
        "failure_code",
        "failure_message",
        "metadata",
        "payment_metadata",
        "processing_error",
    },
    "GameCheckoutStatusRead": {
        "client_secret",
        "stripe_status",
        "provider",
        "provider_payment_intent_id",
        "provider_charge_id",
        "provider_event_id",
        "raw_payload",
        "payload",
        "idempotency_key",
        "reconciliation_status",
        "failure_code",
        "failure_message",
        "metadata",
        "payment_metadata",
        "processing_error",
    },
    "PaymentSummaryRead": {
        "provider",
        "provider_payment_intent_id",
        "provider_charge_id",
        "idempotency_key",
        "failure_code",
        "failure_message",
        "metadata",
        "updated_at",
    },
    "UserPaymentMethodRead": {
        "stripe_customer_id",
        "stripe_payment_method_id",
        "card_fingerprint",
        "client_secret",
    },
    "UserPaymentMethodSetupIntentRead": {
        "id",
        "user_id",
        "stripe_customer_id",
        "stripe_payment_method_id",
        "card_fingerprint",
        "card_brand",
        "card_last4",
        "method_status",
        "is_default",
        "created_at",
        "updated_at",
        "detached_at",
    },
    "RefundSummaryRead": {
        "origin_workflow",
        "provider",
        "provider_refund_id",
        "provider_charge_id",
        "provider_status",
        "provider_status_observed_at",
        "requested_by_user_id",
        "approved_by_user_id",
        "updated_at",
    },
    "PaymentEventRead": {"raw_payload", "payload"},
    "GameImagePublicRead": {
        "uploaded_by_user_id",
        "image_status",
        "created_at",
        "updated_at",
        "deleted_at",
    },
    "VenueImagePublicRead": {
        "uploaded_by_user_id",
        "storage_provider",
        "storage_object_key",
        "storage_bucket",
        "storage_account_id",
        "content_type",
        "size_bytes",
        "etag",
        "image_status",
        "upload_requested_at",
        "upload_completed_at",
        "created_at",
        "updated_at",
        "deleted_at",
    },
    "ChatMessageParticipantRead": {
        "visibility_status",
        "review_status",
        "reviewed_by_user_id",
        "removed_by_user_id",
        "removed_source",
        "restored_by_user_id",
        "detections",
    },
    "SubPostChatMessageParticipantRead": {
        "visibility_status",
        "review_status",
        "reviewed_by_user_id",
        "removed_by_user_id",
        "removed_source",
        "restored_by_user_id",
        "detections",
    },
    "PolicyDocumentPublicRead": {
        "is_active",
        "retired_at",
        "created_at",
        "updated_at",
    },
}

B2_ROUTE_MODELS = {
    ("GET", "/games/{game_id}"): "GameDetailRead",
    ("GET", "/games"): "list[GameDetailRead]",
    ("GET", "/games/browse"): "GameCardListRead",
    ("GET", "/my-games"): "MyGamesListRead",
    ("GET", "/games/{game_id}/participants"): "list[PublicGameParticipantRead]",
    ("GET", "/game-participants/me"): "list[PublicGameParticipantRead]",
    ("POST", "/games/{game_id}/cancel"): "GameDetailRead",
    ("PATCH", "/games/{game_id}/host-edit"): "GameDetailRead",
    ("GET", "/auth/me"): "SelfUserRead",
    ("POST", "/auth/sync-user"): "SelfUserRead",
    ("DELETE", "/auth/account"): "SelfUserRead",
    ("GET", "/users/me"): "SelfUserRead",
    ("PATCH", "/users/me"): "SelfUserRead",
    ("POST", "/checkout/games/{game_id}/payment-intent"): (
        "GameCheckoutPaymentIntentRead"
    ),
    ("GET", "/checkout/bookings/{booking_id}/status"): "GameCheckoutStatusRead",
    ("GET", "/payments"): "list[PaymentSummaryRead]",
    ("GET", "/payments/{payment_id}"): "PaymentSummaryRead",
    ("GET", "/refunds"): "list[RefundSummaryRead]",
    ("GET", "/refunds/{refund_id}"): "RefundSummaryRead",
    ("GET", "/payment-events"): "list[PaymentEventRead]",
    ("GET", "/payment-events/{payment_event_id}"): "PaymentEventRead",
    ("GET", "/user-payment-methods"): "list[UserPaymentMethodRead]",
    ("POST", "/user-payment-methods/setup-intent"): (
        "UserPaymentMethodSetupIntentRead"
    ),
    ("POST", "/user-payment-methods/sync"): "UserPaymentMethodRead",
    ("GET", "/user-payment-methods/{payment_method_id}"): "UserPaymentMethodRead",
    ("PATCH", "/user-payment-methods/{payment_method_id}/default"): (
        "UserPaymentMethodRead"
    ),
    ("DELETE", "/user-payment-methods/{payment_method_id}"): "UserPaymentMethodRead",
    ("GET", "/game-images"): "list[GameImagePublicRead]",
    ("GET", "/game-images/{game_image_id}"): "GameImagePublicRead",
    ("GET", "/venue-images"): "list[VenueImagePublicRead]",
    ("GET", "/chat-messages"): "list[ChatMessageParticipantRead]",
    ("GET", "/chat-messages/{chat_message_id}"): "ChatMessageParticipantRead",
    ("GET", "/need-a-sub/posts/{sub_post_id}/chat/messages"): (
        "list[SubPostChatMessageParticipantRead]"
    ),
    ("POST", "/need-a-sub/posts/{sub_post_id}/chat/messages"): (
        "SubPostChatMessageParticipantRead"
    ),
    ("GET", "/policy-documents"): "list[PolicyDocumentPublicRead]",
    ("GET", "/policy-documents/{policy_document_id}"): "PolicyDocumentPublicRead",
}

CLASSIFIED_RESPONSE_FAMILIES = {
    ("POST", "/checkout/games/{game_id}/payment-intent"): (
        "B2 minimized checkout payment-intent action response."
    ),
    ("GET", "/checkout/bookings/{booking_id}/status"): (
        "B2 minimized checkout status response."
    ),
    ("GET", "/user-payment-methods"): "B2 minimized saved-card display response.",
    ("POST", "/user-payment-methods/setup-intent"): (
        "B2 narrow saved-card setup-intent action response."
    ),
    ("POST", "/user-payment-methods/sync"): "B2 minimized saved-card sync response.",
    ("PATCH", "/user-payment-methods/{payment_method_id}/default"): (
        "B2 minimized saved-card default action response."
    ),
    ("DELETE", "/user-payment-methods/{payment_method_id}"): (
        "B2 minimized saved-card detach action response."
    ),
    ("GET", "/need-a-sub/posts"): "B2 minimized public Need-a-Sub list response.",
    ("GET", "/need-a-sub/posts/mine"): "Owner Need-a-Sub response uses explicit owner schema.",
    ("GET", "/need-a-sub/posts/{sub_post_id}/requests"): (
        "Need-a-Sub owner/requester response uses explicit request schema."
    ),
    ("GET", "/admin/need-a-sub"): "Admin Need-a-Sub response is an admin exception.",
    ("GET", "/admin/official-games"): "Admin official-game response is an admin exception.",
    ("GET", "/admin/community-games"): "Admin community-game response is an admin exception.",
    ("GET", "/admin/money/payments"): "Admin money response is an admin exception.",
    ("GET", "/admin/review-cases"): "Admin review response is an admin exception.",
    ("GET", "/admin/support-flags"): "Support flag response is an admin/support exception.",
    ("GET", "/admin/rejected-attempts"): "Rejected-attempt response is an admin exception.",
    ("GET", "/admin/actions"): "Admin action/audit response is an admin exception.",
    ("GET", "/admin/platform-notices"): "Platform notice response is an admin exception.",
    ("GET", "/admin/notifications"): "Admin notification lookup response is an admin exception.",
    ("GET", "/notifications/me"): "Notification response uses an explicit user schema.",
    ("GET", "/inbox/app-updates"): "Inbox response uses an explicit user schema.",
    ("GET", "/user-settings/me"): "User settings response is an explicit current-user schema.",
    ("GET", "/user-stats/me"): "User stats response is an explicit current-user schema.",
    ("GET", "/waitlist-entries/me"): "Waitlist current-user response uses explicit schema.",
    ("GET", "/bookings/me"): "Booking current-user response uses explicit schema.",
    ("GET", "/game-credits/balance"): "Game credit balance response uses explicit schema.",
}

CLASSIFIED_RAW_OR_OPERATIONAL_EXCEPTIONS = {
    ("POST", "/stripe/webhook"): "Provider webhook returns small provider-owned result dict.",
    ("GET", "/admin/venue-images/upload-readiness"): (
        "Admin operational readiness endpoint returns a small bool dict."
    ),
}

SUSPICIOUS_ROUTE_CLASSIFICATIONS = {
    ("GET", "/"): RouteClassification(
        LATER_OWNER_NON_B2, ROOT_OPERATIONAL_REASON, 200, NO_RESPONSE_MODEL
    ),
    ("GET", "/live"): RouteClassification(
        LATER_OWNER_NON_B2, PLATFORM_PROBE_REASON, 200, NO_RESPONSE_MODEL
    ),
    ("GET", "/ready"): RouteClassification(
        LATER_OWNER_NON_B2, PLATFORM_PROBE_REASON, 200, NO_RESPONSE_MODEL
    ),
    ("GET", "/db-health"): RouteClassification(
        LATER_OWNER_NON_B2, PLATFORM_PROBE_REASON, 200, NO_RESPONSE_MODEL
    ),
    ("DELETE", "/auth/unfinished-account"): RouteClassification(
        LATER_OWNER_NON_B2, NO_CONTENT_AUTH_REASON, 204, NO_RESPONSE_MODEL
    ),
    ("POST", "/user-settings"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("PATCH", "/user-settings/{user_id}"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("POST", "/user-stats"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("PATCH", "/user-stats/{user_id}"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("POST", "/venues"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("PATCH", "/venues/{venue_id}"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("POST", "/venue-approval-requests"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("PATCH", "/venue-approval-requests/{venue_approval_request_id}"): (
        RouteClassification(
            LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
        )
    ),
    ("POST", "/game-chats"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("PATCH", "/game-chats/{game_chat_id}"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    (
        "DELETE",
        "/admin/official-games/{game_id}/participants/{participant_id}",
    ): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("DELETE", "/admin/official-games/{game_id}/host"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("GET", "/admin/venue-images/upload-readiness"): RouteClassification(
        ADMIN_INTERNAL_PROVIDER_EXCEPTION,
        ADMIN_OPERATIONAL_DICT_REASON,
        200,
        "dict[str, bool]",
    ),
    ("POST", "/game-images"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("PATCH", "/game-images/{game_image_id}"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("POST", "/bookings"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("PATCH", "/bookings/{booking_id}"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("POST", "/booking-status-history"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("PATCH", "/booking-status-history/{history_id}"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("POST", "/booking-policy-acceptances"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    (
        "PATCH",
        "/booking-policy-acceptances/{booking_policy_acceptance_id}",
    ): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("POST", "/game-participants"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("PATCH", "/game-participants/{participant_id}"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("POST", "/game-status-history"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("PATCH", "/game-status-history/{history_id}"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("POST", "/participant-status-history"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("PATCH", "/participant-status-history/{history_id}"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("POST", "/host-publish-fees"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("PATCH", "/host-publish-fees/{host_publish_fee_id}"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("POST", "/notifications"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("GET", "/notifications"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("PATCH", "/notifications/{notification_id}"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("POST", "/admin/actions"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("POST", "/admin/actions/{admin_action_id}/notes"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("POST", "/waitlist-entries"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("PATCH", "/waitlist-entries/{waitlist_entry_id}"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("POST", "/payments"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("PATCH", "/payments/{payment_id}"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("POST", "/payment-events"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("POST", "/policy-documents"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("PATCH", "/policy-documents/{policy_document_id}"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("POST", "/policy-acceptances"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("PATCH", "/policy-acceptances/{policy_acceptance_id}"): (
        RouteClassification(
            LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
        )
    ),
    ("POST", "/refunds"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("PATCH", "/refunds/{refund_id}"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
    ("POST", "/stripe/webhook"): RouteClassification(
        ADMIN_INTERNAL_PROVIDER_EXCEPTION,
        PROVIDER_WEBHOOK_REASON,
        200,
        "dict[str, object]",
    ),
    ("PATCH", "/need-a-sub/posts/{sub_post_id}/remove"): RouteClassification(
        LATER_OWNER_NON_B2, RETIRED_TOMBSTONE_REASON, 410, NO_RESPONSE_MODEL
    ),
}


def _route(method: str, path: str) -> APIRoute:
    from backend.main import app

    for route in app.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


def _model_name(model: object) -> str:
    if model is None:
        return NO_RESPONSE_MODEL
    if model is Any:
        return "Any"

    origin = get_origin(model)
    args = get_args(model)
    if origin is list and args:
        return f"list[{_model_name(args[0])}]"
    if origin is dict:
        if len(args) == 2:
            return f"dict[{_model_name(args[0])}, {_model_name(args[1])}]"
        return "dict"

    return getattr(model, "__name__", repr(model))


def _response_class_name(response_class: object) -> str:
    resolved_response_class = getattr(response_class, "value", response_class)
    return getattr(resolved_response_class, "__name__", repr(resolved_response_class))


def _is_broad_response_contract(model: object) -> bool:
    if model is Any or model is dict:
        return True
    return get_origin(model) is dict


def _route_inventory() -> dict[tuple[str, str], RouteSurface]:
    from backend.main import app

    inventory: dict[tuple[str, str], RouteSurface] = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        endpoint = f"{route.endpoint.__module__}.{route.endpoint.__name__}"
        return_annotation = route.endpoint.__annotations__.get("return")
        surface = RouteSurface(
            method="",
            path=route.path,
            endpoint=endpoint,
            name=route.name,
            response_model_name=_model_name(route.response_model),
            status_code=route.status_code or 200,
            response_class_name=_response_class_name(route.response_class),
            return_annotation_name=_model_name(return_annotation),
        )

        for method in sorted(set(route.methods) & HTTP_RESPONSE_METHODS):
            inventory[(method, route.path)] = RouteSurface(
                method=method,
                path=surface.path,
                endpoint=surface.endpoint,
                name=surface.name,
                response_model_name=surface.response_model_name,
                status_code=surface.status_code,
                response_class_name=surface.response_class_name,
                return_annotation_name=surface.return_annotation_name,
            )

    return inventory


def _suspicious_response_candidates() -> dict[tuple[str, str], RouteSurface]:
    return {
        key: surface
        for key, surface in _route_inventory().items()
        if surface.response_model_name == NO_RESPONSE_MODEL
        or _is_broad_response_contract(_route(key[0], key[1]).response_model)
    }


def _route_debug_lines(
    route_surfaces: dict[tuple[str, str], RouteSurface],
    keys: set[tuple[str, str]],
) -> list[str]:
    return [
        (
            f"{method} {path} status={route_surfaces[(method, path)].status_code} "
            f"model={route_surfaces[(method, path)].response_model_name} "
            f"return={route_surfaces[(method, path)].return_annotation_name} "
            f"endpoint={route_surfaces[(method, path)].endpoint}"
        )
        for method, path in sorted(keys)
    ]


def _component_properties(openapi: dict[str, Any], schema_name: str) -> set[str]:
    schema = openapi["components"]["schemas"][schema_name]
    return set(schema.get("properties", {}))


def _response_schema(
    openapi: dict[str, Any],
    method: str,
    path: str,
    *,
    status_code: str = "200",
) -> dict[str, Any]:
    operation = openapi["paths"][path][method.lower()]
    return operation["responses"][status_code]["content"]["application/json"]["schema"]


def _operation(openapi: dict[str, Any], method: str, path: str) -> dict[str, Any]:
    return openapi["paths"][path][method.lower()]


@pytest.mark.requirement("WS02-05B2-R8")
def test_b2_routes_declare_expected_response_models() -> None:
    for (method, path), expected_model_name in B2_ROUTE_MODELS.items():
        route = _route(method, path)
        assert route.response_model is not None, f"{method} {path} missing response_model"
        assert _model_name(route.response_model) == expected_model_name


@pytest.mark.requirement("WS02-05B2-R8")
def test_openapi_components_publish_minimized_response_shapes() -> None:
    from backend.main import app

    openapi = app.openapi()
    for schema_name, prohibited_fields in MINIMIZED_SCHEMA_PROHIBITIONS.items():
        properties = _component_properties(openapi, schema_name)
        assert prohibited_fields.isdisjoint(properties), schema_name

    game_detail_schema = _response_schema(openapi, "GET", "/games/{game_id}")
    assert game_detail_schema["$ref"].endswith("/GameDetailRead")
    my_games_schema = _response_schema(openapi, "GET", "/my-games")
    assert my_games_schema["$ref"].endswith("/MyGamesListRead")
    my_participants_schema = _response_schema(
        openapi,
        "GET",
        "/game-participants/me",
    )
    assert my_participants_schema["items"]["$ref"].endswith(
        "/PublicGameParticipantRead"
    )
    checkout_intent_schema = _response_schema(
        openapi,
        "POST",
        "/checkout/games/{game_id}/payment-intent",
        status_code="201",
    )
    assert checkout_intent_schema["$ref"].endswith(
        "/GameCheckoutPaymentIntentRead"
    )
    checkout_status_schema = _response_schema(
        openapi,
        "GET",
        "/checkout/bookings/{booking_id}/status",
    )
    assert checkout_status_schema["$ref"].endswith("/GameCheckoutStatusRead")
    payment_list_schema = _response_schema(openapi, "GET", "/payments")
    assert payment_list_schema["items"]["$ref"].endswith("/PaymentSummaryRead")
    setup_intent_schema = _response_schema(
        openapi,
        "POST",
        "/user-payment-methods/setup-intent",
        status_code="201",
    )
    assert setup_intent_schema["$ref"].endswith("/UserPaymentMethodSetupIntentRead")
    payment_method_sync_schema = _response_schema(
        openapi,
        "POST",
        "/user-payment-methods/sync",
        status_code="201",
    )
    assert payment_method_sync_schema["$ref"].endswith("/UserPaymentMethodRead")
    payment_method_default_schema = _response_schema(
        openapi,
        "PATCH",
        "/user-payment-methods/{payment_method_id}/default",
    )
    assert payment_method_default_schema["$ref"].endswith("/UserPaymentMethodRead")
    payment_method_detach_schema = _response_schema(
        openapi,
        "DELETE",
        "/user-payment-methods/{payment_method_id}",
    )
    assert payment_method_detach_schema["$ref"].endswith("/UserPaymentMethodRead")
    sub_chat_schema = _response_schema(
        openapi,
        "GET",
        "/need-a-sub/posts/{sub_post_id}/chat/messages",
    )
    assert sub_chat_schema["items"]["$ref"].endswith(
        "/SubPostChatMessageParticipantRead"
    )

    route_surfaces = _route_inventory()
    for key, classification in SUSPICIOUS_ROUTE_CLASSIFICATIONS.items():
        surface = route_surfaces[key]
        operation = _operation(openapi, key[0], key[1])
        response = operation["responses"][str(surface.status_code)]
        if surface.status_code == 410:
            assert operation.get("deprecated") is True, key
            schema = response["content"]["application/json"]["schema"]
            assert schema["$ref"].endswith("/PublicErrorResponse")
        elif surface.status_code == 204:
            assert "content" not in response, key
        elif classification.expected_response_model_name.startswith("dict["):
            schema = response["content"]["application/json"]["schema"]
            assert schema["type"] == "object", key


@pytest.mark.requirement("WS02-05B2-R8")
def test_negative_space_response_families_are_explicitly_classified() -> None:
    suspicious_candidates = _suspicious_response_candidates()

    gate_c_examples = {
        ("POST", "/venues"),
        ("PATCH", "/venues/{venue_id}"),
        ("POST", "/notifications"),
        ("GET", "/notifications"),
        ("PATCH", "/notifications/{notification_id}"),
    }
    assert gate_c_examples <= set(suspicious_candidates)

    missing_classifications = set(suspicious_candidates) - set(
        SUSPICIOUS_ROUTE_CLASSIFICATIONS
    )
    assert missing_classifications == set(), (
        "Unclassified suspicious response candidates: "
        f"{_route_debug_lines(suspicious_candidates, missing_classifications)}"
    )

    stale_classifications = set(SUSPICIOUS_ROUTE_CLASSIFICATIONS) - set(
        suspicious_candidates
    )
    assert stale_classifications == set(), (
        "Stale suspicious response classifications: "
        f"{sorted(stale_classifications)}"
    )

    contradictory_routes: list[tuple[str, str]] = []
    for key, surface in sorted(suspicious_candidates.items()):
        classification = SUSPICIOUS_ROUTE_CLASSIFICATIONS[key]
        assert classification.category in FROZEN_CLASSIFICATION_CATEGORIES, key
        assert classification.reason.strip(), key
        assert (
            classification.reason.strip().lower()
            not in VAGUE_CLASSIFICATION_REASONS
        ), key
        assert surface.status_code == classification.expected_status_code, key
        assert (
            surface.response_model_name == classification.expected_response_model_name
        ), key

        if classification.category == B2_OWNED_CONTRADICTORY:
            contradictory_routes.append(key)
        if classification.category == B2_OWNED_MINIMIZED:
            assert surface.response_model_name != NO_RESPONSE_MODEL, key
            assert not _is_broad_response_contract(_route(key[0], key[1]).response_model)

    assert contradictory_routes == []

    for (method, path), reason in CLASSIFIED_RESPONSE_FAMILIES.items():
        route = _route(method, path)
        assert route.response_model is not None, reason
        assert _model_name(route.response_model) not in {"Any", "dict", "Dict"}

    for (method, path), reason in CLASSIFIED_RAW_OR_OPERATIONAL_EXCEPTIONS.items():
        route = _route(method, path)
        assert route.response_model in {None, dict[str, object], dict[str, bool]}, reason
        assert route.endpoint.__annotations__.get("return") in {
            dict[str, object],
            dict[str, bool],
        }
