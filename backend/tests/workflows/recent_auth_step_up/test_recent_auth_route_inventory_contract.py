from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi.routing import APIRoute

pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.suite_type("ordinary"),
]

MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
RECENT_AUTH_DEPENDENCIES = {
    "require_recent_app_user",
    "require_recent_active_user",
    "require_recent_active_admin",
}


@dataclass(frozen=True)
class FrozenRecentAuthRoute:
    action_id: str
    dependency: str
    actor: str


FROZEN_RECENT_AUTH_ROUTE_MATRIX: dict[tuple[str, str], FrozenRecentAuthRoute] = {
    ("DELETE", "/auth/account"): FrozenRecentAuthRoute(
        "self_account_delete",
        "require_recent_app_user",
        "current_user",
    ),
    ("DELETE", "/games/{game_id}"): FrozenRecentAuthRoute(
        "admin_game_soft_delete",
        "require_recent_active_admin",
        "admin",
    ),
    ("DELETE", "/user-payment-methods/{payment_method_id}"): FrozenRecentAuthRoute(
        "saved_payment_method_detach",
        "require_recent_active_user",
        "current_user",
    ),
    ("DELETE", "/venues/{venue_id}"): FrozenRecentAuthRoute(
        "admin_venue_soft_delete",
        "require_recent_active_admin",
        "admin",
    ),
    ("PATCH", "/admin/users/{user_id}/role"): FrozenRecentAuthRoute(
        "admin_user_role_change",
        "require_recent_active_admin",
        "admin",
    ),
    ("PATCH", "/payment-events/{payment_event_id}"): FrozenRecentAuthRoute(
        "admin_payment_event_repair",
        "require_recent_active_admin",
        "admin",
    ),
    (
        "PATCH",
        "/user-payment-methods/{payment_method_id}/default",
    ): FrozenRecentAuthRoute(
        "saved_payment_method_default_change",
        "require_recent_active_user",
        "current_user",
    ),
    ("POST", "/admin/community-games/{game_id}/cancel"): FrozenRecentAuthRoute(
        "admin_community_game_cancellation",
        "require_recent_active_admin",
        "admin",
    ),
    ("POST", "/admin/game-credits/issue"): FrozenRecentAuthRoute(
        "admin_game_credit_issue",
        "require_recent_active_admin",
        "admin",
    ),
    ("POST", "/admin/game-credits/{game_credit_id}/reverse"): FrozenRecentAuthRoute(
        "admin_game_credit_reverse",
        "require_recent_active_admin",
        "admin",
    ),
    ("POST", "/admin/money/financial-outcomes"): FrozenRecentAuthRoute(
        "admin_financial_outcome_create",
        "require_recent_active_admin",
        "admin",
    ),
    ("POST", "/admin/money/issues/{money_issue_id}/resolve"): FrozenRecentAuthRoute(
        "admin_money_issue_resolve",
        "require_recent_active_admin",
        "admin",
    ),
    (
        "POST",
        "/admin/money/issues/{money_issue_id}/retry-credit",
    ): FrozenRecentAuthRoute(
        "admin_money_issue_retry_credit",
        "require_recent_active_admin",
        "admin",
    ),
    ("POST", "/admin/money/refunds/{refund_id}/reconcile"): FrozenRecentAuthRoute(
        "admin_refund_reconcile",
        "require_recent_active_admin",
        "admin",
    ),
    ("POST", "/admin/money/refunds/{refund_id}/retry"): FrozenRecentAuthRoute(
        "admin_refund_retry",
        "require_recent_active_admin",
        "admin",
    ),
    ("POST", "/admin/need-a-sub/{post_id}/remove"): FrozenRecentAuthRoute(
        "admin_need_a_sub_post_removal",
        "require_recent_active_admin",
        "admin",
    ),
    ("POST", "/admin/official-games/{game_id}/cancel"): FrozenRecentAuthRoute(
        "official_game_cancel_execute",
        "require_recent_active_admin",
        "admin",
    ),
    (
        "POST",
        "/admin/official-games/{game_id}/participants/{participant_id}/remove",
    ): FrozenRecentAuthRoute(
        "official_game_player_removal_execute",
        "require_recent_active_admin",
        "admin",
    ),
    ("POST", "/admin/platform-notices"): FrozenRecentAuthRoute(
        "platform_notice_create",
        "require_recent_active_admin",
        "admin",
    ),
    ("POST", "/admin/platform-notices/{notice_id}/cancel"): FrozenRecentAuthRoute(
        "platform_notice_cancel",
        "require_recent_active_admin",
        "admin",
    ),
    ("POST", "/admin/users/{user_id}/delete"): FrozenRecentAuthRoute(
        "admin_user_delete",
        "require_recent_active_admin",
        "admin",
    ),
    ("POST", "/admin/users/{user_id}/restrict-hosting"): FrozenRecentAuthRoute(
        "admin_user_restrict_hosting",
        "require_recent_active_admin",
        "admin",
    ),
    ("POST", "/admin/users/{user_id}/restore-hosting"): FrozenRecentAuthRoute(
        "admin_user_restore_hosting",
        "require_recent_active_admin",
        "admin",
    ),
    ("POST", "/admin/users/{user_id}/suspend"): FrozenRecentAuthRoute(
        "admin_user_suspend",
        "require_recent_active_admin",
        "admin",
    ),
    ("POST", "/admin/users/{user_id}/unsuspend"): FrozenRecentAuthRoute(
        "admin_user_unsuspend",
        "require_recent_active_admin",
        "admin",
    ),
}

RECENT_AUTH_REQUIRED_ADMIN_MUTATIONS = {
    key
    for key, route in FROZEN_RECENT_AUTH_ROUTE_MATRIX.items()
    if route.actor == "admin"
}

RECENT_AUTH_NOT_REQUIRED_ADMIN_MUTATIONS: dict[tuple[str, str], str] = {
    ("PATCH", "/admin/official-games/{game_id}"): "routine official-game edit",
    ("PATCH", "/admin/venue-images/{venue_image_id}"): "venue-image update",
    (
        "PATCH",
        "/community-game-details/{community_game_detail_id}",
    ): "staff community detail update",
    (
        "POST",
        "/admin/community-games/{game_id}/chat/messages/{message_id}/remove",
    ): "routine community chat moderation",
    (
        "POST",
        "/admin/community-games/{game_id}/chat/messages/{message_id}/restore",
    ): "routine community chat moderation",
    (
        "POST",
        "/admin/community-games/{game_id}/chat/messages/{message_id}/review",
    ): "routine community chat moderation",
    (
        "POST",
        "/admin/community-games/{game_id}/flag-for-review",
    ): "review workflow creation",
    ("POST", "/admin/community-games/{game_id}/hide"): "reversible moderation",
    (
        "POST",
        "/admin/community-games/{game_id}/hide-payment-text",
    ): "reversible payment-text moderation",
    (
        "POST",
        "/admin/community-games/{game_id}/pause-joining",
    ): "reversible joining moderation",
    ("POST", "/admin/community-games/{game_id}/restore"): "reversible moderation",
    (
        "POST",
        "/admin/community-games/{game_id}/restore-payment-text",
    ): "reversible payment-text moderation",
    (
        "POST",
        "/admin/community-games/{game_id}/resume-joining",
    ): "reversible joining moderation",
    (
        "POST",
        "/admin/need-a-sub/{post_id}/chat/messages/{message_id}/remove",
    ): "routine Need-a-Sub chat moderation",
    (
        "POST",
        "/admin/need-a-sub/{post_id}/chat/messages/{message_id}/restore",
    ): "routine Need-a-Sub chat moderation",
    (
        "POST",
        "/admin/need-a-sub/{post_id}/chat/messages/{message_id}/review",
    ): "routine Need-a-Sub chat moderation",
    ("POST", "/admin/need-a-sub/{post_id}/hide"): "reversible Need-a-Sub moderation",
    (
        "POST",
        "/admin/need-a-sub/{post_id}/restore",
    ): "reversible Need-a-Sub moderation",
    ("POST", "/admin/official-games"): "official-game creation",
    (
        "POST",
        "/admin/official-games/{game_id}/cancel-preview",
    ): "official-game cancellation preview",
    (
        "POST",
        "/admin/official-games/{game_id}/chat/messages/{message_id}/remove",
    ): "routine official-game chat moderation",
    (
        "POST",
        "/admin/official-games/{game_id}/chat/messages/{message_id}/restore",
    ): "routine official-game chat moderation",
    (
        "POST",
        "/admin/official-games/{game_id}/chat/messages/{message_id}/review",
    ): "routine official-game chat moderation",
    ("POST", "/admin/official-games/{game_id}/host"): "host assignment",
    ("POST", "/admin/official-games/{game_id}/host/remove"): "host removal",
    (
        "POST",
        "/admin/official-games/{game_id}/participants/{participant_id}/remove-preview",
    ): "official-player removal preview",
    ("POST", "/admin/official-games/{game_id}/players"): "roster add",
    (
        "POST",
        "/admin/review-cases/{review_case_id}/assignment",
    ): "review case assignment",
    ("POST", "/admin/review-cases/{review_case_id}/close"): "review case close",
    (
        "POST",
        "/admin/review-cases/{review_case_id}/merge",
    ): "review case merge",
    ("POST", "/admin/review-cases/{review_case_id}/notes"): "review note",
    (
        "POST",
        "/admin/review-cases/{review_case_id}/reopen",
    ): "review case reopen",
    (
        "POST",
        "/admin/support-flags/{support_flag_id}/resolve",
    ): "support flag resolve",
    ("POST", "/admin/users/{user_id}/delete-preview"): "account deletion preview",
    (
        "POST",
        "/admin/users/{user_id}/hosting-restriction-preview",
    ): "hosting restriction preview",
    (
        "POST",
        "/admin/users/{user_id}/suspension-preview",
    ): "account suspension preview",
    (
        "POST",
        "/admin/venue-images/{venue_image_id}/complete",
    ): "venue-image upload completion",
    (
        "POST",
        "/admin/venues/{venue_id}/images/upload-url",
    ): "venue-image upload authorization",
    ("POST", "/community-game-details"): "staff community detail creation",
    ("POST", "/games"): "generic admin game creation",
    ("PATCH", "/games/{game_id}"): "generic admin game edit",
}

RETIRED_OR_NON_EXECUTING_ADMIN_MUTATIONS: dict[tuple[str, str], str] = {
    ("DELETE", "/admin/official-games/{game_id}/host"): "retired direct host delete",
    (
        "DELETE",
        "/admin/official-games/{game_id}/participants/{participant_id}",
    ): "retired direct participant delete",
    ("DELETE", "/users/{user_id}"): "disabled generic user mutation",
    (
        "PATCH",
        "/booking-policy-acceptances/{booking_policy_acceptance_id}",
    ): "retired scaffold",
    ("PATCH", "/booking-status-history/{history_id}"): "retired scaffold",
    ("PATCH", "/bookings/{booking_id}"): "retired scaffold",
    ("PATCH", "/game-chats/{game_chat_id}"): "retired scaffold",
    ("PATCH", "/game-images/{game_image_id}"): "retired scaffold",
    ("PATCH", "/game-participants/{participant_id}"): "retired scaffold",
    ("PATCH", "/game-status-history/{history_id}"): "retired scaffold",
    ("PATCH", "/host-publish-fees/{host_publish_fee_id}"): "retired scaffold",
    ("PATCH", "/need-a-sub/posts/{sub_post_id}/remove"): "retired duplicate removal",
    ("PATCH", "/notifications/{notification_id}"): "retired scaffold",
    ("PATCH", "/participant-status-history/{history_id}"): "retired scaffold",
    ("PATCH", "/payments/{payment_id}"): "retired scaffold",
    ("PATCH", "/policy-acceptances/{policy_acceptance_id}"): "retired scaffold",
    ("PATCH", "/policy-documents/{policy_document_id}"): "retired scaffold",
    ("PATCH", "/refunds/{refund_id}"): "retired scaffold",
    ("PATCH", "/user-settings/{user_id}"): "retired scaffold",
    ("PATCH", "/user-stats/{user_id}"): "retired scaffold",
    ("PATCH", "/users/{user_id}"): "disabled generic user mutation",
    (
        "PATCH",
        "/venue-approval-requests/{venue_approval_request_id}",
    ): "retired scaffold",
    ("PATCH", "/venues/{venue_id}"): "retired scaffold",
    ("PATCH", "/waitlist-entries/{waitlist_entry_id}"): "retired scaffold",
    ("POST", "/admin/actions"): "retired direct audit-action creation",
    ("POST", "/admin/actions/{admin_action_id}/notes"): "retired audit notes",
    ("POST", "/booking-policy-acceptances"): "retired scaffold",
    ("POST", "/booking-status-history"): "retired scaffold",
    ("POST", "/bookings"): "retired scaffold",
    ("POST", "/game-chats"): "retired scaffold",
    ("POST", "/game-images"): "retired scaffold",
    ("POST", "/game-participants"): "retired scaffold",
    ("POST", "/game-status-history"): "retired scaffold",
    ("POST", "/host-publish-fees"): "retired scaffold",
    ("POST", "/notifications"): "retired scaffold",
    ("POST", "/participant-status-history"): "retired scaffold",
    ("POST", "/payment-events"): "retired provider-event creation",
    ("POST", "/payments"): "retired scaffold",
    ("POST", "/policy-acceptances"): "retired scaffold",
    ("POST", "/policy-documents"): "retired scaffold",
    ("POST", "/refunds"): "retired scaffold",
    ("POST", "/user-settings"): "retired scaffold",
    ("POST", "/user-stats"): "retired scaffold",
    ("POST", "/users"): "disabled generic user mutation",
    ("POST", "/venue-approval-requests"): "retired scaffold",
    ("POST", "/venues"): "retired scaffold",
    ("POST", "/waitlist-entries"): "retired scaffold",
}


def _registered_routes() -> dict[tuple[str, str], APIRoute]:
    import backend.main as backend_main

    routes: dict[tuple[str, str], APIRoute] = {}
    for route in backend_main.app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in sorted(route.methods or set()):
            if method in {"HEAD", "OPTIONS"}:
                continue
            routes[(method, route.path_format)] = route
    return routes


def _dependency_call_names(route: APIRoute) -> set[str]:
    names: set[str] = set()

    def walk(dependant) -> None:
        for dependency in dependant.dependencies:
            call = dependency.call
            if call is not None:
                call_name = getattr(call, "__name__", repr(call))
                call_module = getattr(call, "__module__", "")
                names.add(call_name)
                names.add(f"{call_module}.{call_name}")
            walk(dependency)

    walk(route.dependant)
    return names


def _has_dependency(route: APIRoute, dependency_name: str) -> bool:
    return dependency_name in _dependency_call_names(route)


def _has_any_recent_auth_dependency(route: APIRoute) -> bool:
    return any(_has_dependency(route, name) for name in RECENT_AUTH_DEPENDENCIES)


def _admin_access_mutation_routes(
    registered_routes: dict[tuple[str, str], APIRoute],
) -> set[tuple[str, str]]:
    admin_mutations: set[tuple[str, str]] = set()
    for (method, path), route in registered_routes.items():
        if method not in MUTATION_METHODS:
            continue
        dependency_names = _dependency_call_names(route)
        if (
            "require_active_admin" in dependency_names
            or "require_recent_active_admin" in dependency_names
        ):
            admin_mutations.add((method, path))
    return admin_mutations


def _assert_pairwise_disjoint(*sets: set[tuple[str, str]]) -> None:
    for index, left in enumerate(sets):
        for right in sets[index + 1 :]:
            assert left.isdisjoint(right), left & right


@pytest.mark.requirement("WS03-03A-R5", "WS03-03A-R11")
def test_recent_auth_policy_matches_frozen_matrix_and_registered_routes() -> None:
    from backend.services.recent_auth_policy import (
        RECENT_AUTH_PROTECTED_ACTIONS,
        RECENT_AUTH_PROTECTED_ROUTE_KEYS,
        RECENT_AUTH_PUBLIC_ERROR_CODE,
    )

    registered_routes = _registered_routes()
    policy_by_key = {
        (action.method, action.route_template): action
        for action in RECENT_AUTH_PROTECTED_ACTIONS
    }
    frozen_keys = set(FROZEN_RECENT_AUTH_ROUTE_MATRIX)

    assert RECENT_AUTH_PUBLIC_ERROR_CODE == "AUTH.RECENT_AUTH_REQUIRED"
    assert len(RECENT_AUTH_PROTECTED_ACTIONS) == 25
    assert len({action.action_id for action in RECENT_AUTH_PROTECTED_ACTIONS}) == 25
    assert set(policy_by_key) == frozen_keys
    assert RECENT_AUTH_PROTECTED_ROUTE_KEYS == frozen_keys

    for route_key, frozen in FROZEN_RECENT_AUTH_ROUTE_MATRIX.items():
        action = policy_by_key[route_key]
        route = registered_routes.get(route_key)

        assert route is not None, f"Missing registered route for {route_key}"
        assert action.action_id == frozen.action_id
        assert action.enforcement_dependency == frozen.dependency
        assert action.actor == frozen.actor
        assert action.recent_auth_required is True
        assert action.frontend_caller.strip()
        assert action.protections
        assert action.provider_mfa_dependency in {
            "deferred_to_ws03_03b",
            "not_required_for_current_user_saved_card_management",
        }
        assert _has_dependency(route, frozen.dependency), (
            f"{route_key} lacks {frozen.dependency}; dependencies were "
            f"{sorted(_dependency_call_names(route))}"
        )

    discovered_recent_routes = {
        route_key
        for route_key, route in registered_routes.items()
        if _has_any_recent_auth_dependency(route)
    }
    assert discovered_recent_routes == frozen_keys


@pytest.mark.requirement("WS03-03A-R5", "WS03-03A-R6", "WS03-03A-R11")
def test_complete_admin_access_mutation_partition_matches_current_routes() -> None:
    registered_routes = _registered_routes()
    discovered_admin_mutations = _admin_access_mutation_routes(registered_routes)
    required = set(RECENT_AUTH_REQUIRED_ADMIN_MUTATIONS)
    not_required = set(RECENT_AUTH_NOT_REQUIRED_ADMIN_MUTATIONS)
    retired = set(RETIRED_OR_NON_EXECUTING_ADMIN_MUTATIONS)

    assert len(required) == 22
    assert len(not_required) == 41
    assert len(retired) == 47
    assert len(discovered_admin_mutations) == 110
    _assert_pairwise_disjoint(required, not_required, retired)
    assert required | not_required | retired == discovered_admin_mutations

    for route_key in required | not_required | retired:
        assert route_key in registered_routes, f"Stale classification: {route_key}"

    for route_key in required:
        route = registered_routes[route_key]
        assert route_key in FROZEN_RECENT_AUTH_ROUTE_MATRIX
        assert _has_dependency(route, "require_recent_active_admin")

    for route_key in not_required:
        route = registered_routes[route_key]
        assert route_key not in FROZEN_RECENT_AUTH_ROUTE_MATRIX
        assert _has_dependency(route, "require_active_admin")
        assert not _has_any_recent_auth_dependency(route), (
            f"{route_key} is intentionally non-recent but has "
            f"{sorted(_dependency_call_names(route))}"
        )

    for route_key in retired:
        route = registered_routes[route_key]
        assert route_key not in FROZEN_RECENT_AUTH_ROUTE_MATRIX
        assert _has_dependency(route, "require_active_admin")
        assert not _has_any_recent_auth_dependency(route), (
            f"{route_key} is retired/non-executing but has recent-auth"
        )


@pytest.mark.requirement("WS03-03A-R5", "WS03-03A-R6", "WS03-03A-R11")
def test_admin_route_families_use_action_level_classification_without_wildcards() -> (
    None
):
    family_expectations = {
        "/admin/community-games": 11,
        "/admin/need-a-sub": 6,
        "/admin/official-games": 14,
        "/admin/users": 9,
        "/games": 3,
        "/venues": 3,
        "/payment-events": 2,
    }
    all_classified = (
        set(RECENT_AUTH_REQUIRED_ADMIN_MUTATIONS)
        | set(RECENT_AUTH_NOT_REQUIRED_ADMIN_MUTATIONS)
        | set(RETIRED_OR_NON_EXECUTING_ADMIN_MUTATIONS)
    )

    for prefix, expected_count in family_expectations.items():
        family_routes = {
            route_key for route_key in all_classified if route_key[1].startswith(prefix)
        }
        assert len(family_routes) == expected_count
        assert all(route_key in all_classified for route_key in family_routes)

    assert (
        "POST",
        "/admin/official-games/{game_id}/players",
    ) in RECENT_AUTH_NOT_REQUIRED_ADMIN_MUTATIONS
    assert (
        "POST",
        "/admin/official-games/{game_id}/participants/{participant_id}/remove",
    ) in RECENT_AUTH_REQUIRED_ADMIN_MUTATIONS
    assert (
        "POST",
        "/admin/need-a-sub/{post_id}/remove",
    ) in RECENT_AUTH_REQUIRED_ADMIN_MUTATIONS
    assert (
        "POST",
        "/admin/need-a-sub/{post_id}/hide",
    ) in RECENT_AUTH_NOT_REQUIRED_ADMIN_MUTATIONS


@pytest.mark.requirement("WS03-03A-R5", "WS03-03A-R6", "WS03-03A-R11")
def test_representative_intentionally_non_recent_admin_routes_remain_ordinary() -> None:
    registered_routes = _registered_routes()
    representative_routes = {
        (
            "POST",
            "/admin/community-games/{game_id}/hide",
        ): "community hide remains reversible",
        (
            "POST",
            "/admin/need-a-sub/{post_id}/restore",
        ): "Need-a-Sub restore remains reversible",
        (
            "POST",
            "/admin/official-games/{game_id}/cancel-preview",
        ): "official cancellation preview remains unwrapped",
        (
            "POST",
            "/admin/official-games/{game_id}/participants/{participant_id}/remove-preview",
        ): "official-player removal preview remains unwrapped",
        (
            "POST",
            "/admin/official-games/{game_id}/players",
        ): "official-player add remains intentionally non-recent",
        (
            "POST",
            "/admin/users/{user_id}/hosting-restriction-preview",
        ): "hosting preview remains unwrapped",
        (
            "POST",
            "/admin/venue-images/{venue_image_id}/complete",
        ): "venue-image lifecycle remains later-owner",
    }

    for route_key, classification in representative_routes.items():
        route = registered_routes.get(route_key)
        assert route is not None, f"Missing route for {classification}"
        assert route_key in RECENT_AUTH_NOT_REQUIRED_ADMIN_MUTATIONS
        assert not _has_any_recent_auth_dependency(route), classification
