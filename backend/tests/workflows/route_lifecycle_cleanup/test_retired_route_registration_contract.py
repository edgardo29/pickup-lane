from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pytest
from fastapi.routing import APIRoute

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

@dataclass(frozen=True)
class RetiredMutationRoute:
    family: str
    method: str
    path: str
    concrete_path: str
    endpoint_module: str
    endpoint_name: str

    @property
    def key(self) -> tuple[str, str]:
        return self.method, self.path

    @property
    def id(self) -> str:
        return f"{self.method} {self.path}"


_UUID_1 = "00000000-0000-4000-8000-000000000001"
_UUID_2 = "00000000-0000-4000-8000-000000000002"

RETIRED_MUTATION_ROUTES: tuple[RetiredMutationRoute, ...] = (
    RetiredMutationRoute("bookings", "POST", "/bookings", "/bookings", "backend.routes.booking_routes", "create_booking"),
    RetiredMutationRoute("bookings", "PATCH", "/bookings/{booking_id}", f"/bookings/{_UUID_1}", "backend.routes.booking_routes", "update_booking"),
    RetiredMutationRoute("game participants", "POST", "/game-participants", "/game-participants", "backend.routes.game_participant_routes", "create_game_participant"),
    RetiredMutationRoute("game participants", "PATCH", "/game-participants/{participant_id}", f"/game-participants/{_UUID_1}", "backend.routes.game_participant_routes", "update_game_participant"),
    RetiredMutationRoute("waitlist entries", "POST", "/waitlist-entries", "/waitlist-entries", "backend.routes.waitlist_entry_routes", "create_waitlist_entry"),
    RetiredMutationRoute("waitlist entries", "PATCH", "/waitlist-entries/{waitlist_entry_id}", f"/waitlist-entries/{_UUID_1}", "backend.routes.waitlist_entry_routes", "update_waitlist_entry"),
    RetiredMutationRoute("host publish fees", "POST", "/host-publish-fees", "/host-publish-fees", "backend.routes.host_publish_fee_routes", "create_host_publish_fee"),
    RetiredMutationRoute("host publish fees", "PATCH", "/host-publish-fees/{host_publish_fee_id}", f"/host-publish-fees/{_UUID_1}", "backend.routes.host_publish_fee_routes", "update_host_publish_fee"),
    RetiredMutationRoute("venues", "POST", "/venues", "/venues", "backend.routes.venue_routes", "create_venue"),
    RetiredMutationRoute("venues", "PATCH", "/venues/{venue_id}", f"/venues/{_UUID_1}", "backend.routes.venue_routes", "update_venue"),
    RetiredMutationRoute("game images", "POST", "/game-images", "/game-images", "backend.routes.game_image_routes", "create_game_image"),
    RetiredMutationRoute("game images", "PATCH", "/game-images/{game_image_id}", f"/game-images/{_UUID_1}", "backend.routes.game_image_routes", "update_game_image"),
    RetiredMutationRoute("venue approval requests", "POST", "/venue-approval-requests", "/venue-approval-requests", "backend.routes.venue_approval_request_routes", "create_venue_approval_request"),
    RetiredMutationRoute("venue approval requests", "PATCH", "/venue-approval-requests/{venue_approval_request_id}", f"/venue-approval-requests/{_UUID_1}", "backend.routes.venue_approval_request_routes", "update_venue_approval_request"),
    RetiredMutationRoute("user settings", "POST", "/user-settings", "/user-settings", "backend.routes.user_settings_routes", "create_user_settings"),
    RetiredMutationRoute("user settings", "PATCH", "/user-settings/{user_id}", f"/user-settings/{_UUID_1}", "backend.routes.user_settings_routes", "update_user_settings"),
    RetiredMutationRoute("user stats", "POST", "/user-stats", "/user-stats", "backend.routes.user_stats_routes", "create_user_stats"),
    RetiredMutationRoute("user stats", "PATCH", "/user-stats/{user_id}", f"/user-stats/{_UUID_1}", "backend.routes.user_stats_routes", "update_user_stats"),
    RetiredMutationRoute("game chats", "POST", "/game-chats", "/game-chats", "backend.routes.game_chat_routes", "create_game_chat"),
    RetiredMutationRoute("game chats", "PATCH", "/game-chats/{game_chat_id}", f"/game-chats/{_UUID_1}", "backend.routes.game_chat_routes", "update_game_chat"),
    RetiredMutationRoute("admin actions", "POST", "/admin/actions", "/admin/actions", "backend.routes.admin_action_routes", "create_admin_action_route"),
    RetiredMutationRoute("admin actions", "POST", "/admin/actions/{admin_action_id}/notes", f"/admin/actions/{_UUID_1}/notes", "backend.routes.admin_action_routes", "append_admin_action_note_route"),
    RetiredMutationRoute("game status history", "POST", "/game-status-history", "/game-status-history", "backend.routes.game_status_history_routes", "create_game_status_history"),
    RetiredMutationRoute("game status history", "PATCH", "/game-status-history/{history_id}", f"/game-status-history/{_UUID_1}", "backend.routes.game_status_history_routes", "update_game_status_history"),
    RetiredMutationRoute("booking status history", "POST", "/booking-status-history", "/booking-status-history", "backend.routes.booking_status_history_routes", "create_booking_status_history"),
    RetiredMutationRoute("booking status history", "PATCH", "/booking-status-history/{history_id}", f"/booking-status-history/{_UUID_1}", "backend.routes.booking_status_history_routes", "update_booking_status_history"),
    RetiredMutationRoute("participant status history", "POST", "/participant-status-history", "/participant-status-history", "backend.routes.participant_status_history_routes", "create_participant_status_history"),
    RetiredMutationRoute("participant status history", "PATCH", "/participant-status-history/{history_id}", f"/participant-status-history/{_UUID_1}", "backend.routes.participant_status_history_routes", "update_participant_status_history"),
    RetiredMutationRoute("booking-policy acceptances", "POST", "/booking-policy-acceptances", "/booking-policy-acceptances", "backend.routes.booking_policy_acceptance_routes", "create_booking_policy_acceptance"),
    RetiredMutationRoute("booking-policy acceptances", "PATCH", "/booking-policy-acceptances/{booking_policy_acceptance_id}", f"/booking-policy-acceptances/{_UUID_1}", "backend.routes.booking_policy_acceptance_routes", "update_booking_policy_acceptance"),
    RetiredMutationRoute("admin notification writes", "POST", "/notifications", "/notifications", "backend.routes.notification_routes", "create_notification"),
    RetiredMutationRoute("admin notification writes", "PATCH", "/notifications/{notification_id}", f"/notifications/{_UUID_1}", "backend.routes.notification_routes", "update_notification"),
    RetiredMutationRoute("Need-a-Sub duplicate removal", "PATCH", "/need-a-sub/posts/{sub_post_id}/remove", f"/need-a-sub/posts/{_UUID_1}/remove", "backend.routes.sub_post_routes", "remove_need_a_sub_post"),
    RetiredMutationRoute("official-game player removal", "DELETE", "/admin/official-games/{game_id}/participants/{participant_id}", f"/admin/official-games/{_UUID_1}/participants/{_UUID_2}", "backend.routes.admin_official_game_routes", "remove_admin_official_game_player"),
    RetiredMutationRoute("official-game host removal", "DELETE", "/admin/official-games/{game_id}/host", f"/admin/official-games/{_UUID_1}/host", "backend.routes.admin_official_game_routes", "remove_admin_official_game_host"),
)

MUTATION_METHODS = {"POST", "PATCH", "DELETE"}
ACTIVE_ADMIN_DEPENDENCY = "backend.services.auth_service.require_active_admin"
GET_DB_DEPENDENCY = "backend.database.get_db"


def iter_api_routes() -> Iterable[APIRoute]:
    from backend.main import app

    for route in app.routes:
        if isinstance(route, APIRoute):
            yield route


def route_by_method_path(method: str, path: str) -> APIRoute:
    matches = [
        route
        for route in iter_api_routes()
        if route.path == path and method.upper() in route.methods
    ]
    assert len(matches) == 1, f"{method} {path} should have exactly one registration"
    return matches[0]


def callable_name(callable_object: object) -> str:
    module = getattr(callable_object, "__module__", "")
    name = getattr(callable_object, "__name__", repr(callable_object))
    return f"{module}.{name}" if module else name


def direct_dependency_call_names(route: APIRoute) -> tuple[str, ...]:
    return tuple(callable_name(dependency.call) for dependency in route.dependant.dependencies)


@pytest.mark.requirement("WS02-04B2A2B1-R1")
def test_frozen_retired_mutation_inventory_is_exactly_35_routes() -> None:
    keys = [retired_route.key for retired_route in RETIRED_MUTATION_ROUTES]

    assert len(RETIRED_MUTATION_ROUTES) == 35
    assert len(set(keys)) == 35
    assert all(method in MUTATION_METHODS for method, _path in keys)
    assert ("GET", "/notifications") not in keys


@pytest.mark.requirement("WS02-04B2A2B1-R1")
def test_retired_mutation_routes_are_registered_bodyless_auth_guarded_and_no_db() -> None:
    for retired_route in RETIRED_MUTATION_ROUTES:
        route = route_by_method_path(retired_route.method, retired_route.path)
        dependency_names = direct_dependency_call_names(route)

        assert route.endpoint.__module__ == retired_route.endpoint_module, retired_route.id
        assert route.endpoint.__name__ == retired_route.endpoint_name, retired_route.id
        assert route.body_field is None, retired_route.id
        assert ACTIVE_ADMIN_DEPENDENCY in dependency_names, retired_route.id
        assert GET_DB_DEPENDENCY not in dependency_names, retired_route.id


@pytest.mark.requirement("WS02-04B2A2B1-R1")
def test_retired_mutation_routes_have_no_same_method_duplicate_or_slash_alias() -> None:
    for retired_route in RETIRED_MUTATION_ROUTES:
        normalized_path = retired_route.path.rstrip("/")
        aliases = [
            route
            for route in iter_api_routes()
            if retired_route.method in route.methods
            and route.path.rstrip("/") == normalized_path
        ]

        assert [route.path for route in aliases] == [retired_route.path], retired_route.id
