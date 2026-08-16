from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi.routing import APIRoute
from pydantic import BaseModel

from backend.schemas.admin_community_schema import (
    AdminCommunityGameEnforcementActionCreate,
    AdminCommunityGameHidePaymentTextCreate,
    AdminCommunityGameReviewFlagCreate,
)
from backend.schemas.admin_official_game_schema import (
    AdminOfficialGameCancelExecute,
    AdminOfficialGameCreate,
    AdminOfficialGameHostAssign,
    AdminOfficialGameHostRemovalExecute,
    AdminOfficialGamePlayerAdd,
    AdminOfficialGamePlayerRemovalExecute,
    AdminOfficialGameUpdate,
)
from backend.schemas.community_game_detail_schema import (
    CommunityGameDetailCreate,
    CommunityGameDetailHostUpsert,
    CommunityGameDetailUpdate,
)
from backend.schemas.community_game_publish_schema import CommunityGamePublishCreate
from backend.schemas.game_schema import (
    GameBookingGuestAddCreate,
    GameCancelCreate,
    GameGuestAddCreate,
    GameGuestRemoveCreate,
    GameHostEdit,
    GameJoinCreate,
    GameLeaveCreate,
    GameUpdate,
)

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

ACTIVE_ADMIN_DEPENDENCY = "backend.services.auth_service.require_active_admin"
RECENT_ACTIVE_ADMIN_DEPENDENCY = (
    "backend.services.auth_service.require_recent_active_admin"
)
VERIFIED_USER_DEPENDENCY = "backend.services.auth_service.require_verified_user"
GENERIC_PROTECTED_GAME_FIELDS = {
    "game_type",
    "payment_collection_type",
    "publish_status",
    "game_status",
    "public_visibility_status",
    "join_enforcement_status",
    "venue_name_snapshot",
    "address_snapshot",
    "city_snapshot",
    "state_snapshot",
    "neighborhood_snapshot",
    "host_user_id",
    "created_by_user_id",
    "starts_on_local",
    "sport_type",
    "currency",
    "minimum_age",
    "host_guest_max",
    "policy_mode",
    "custom_cancellation_text",
    "published_at",
    "cancelled_at",
    "cancelled_by_user_id",
    "cancellation_source",
    "cancel_reason",
    "completed_at",
    "completed_by_user_id",
    "created_at",
    "updated_at",
    "deleted_at",
}


@dataclass(frozen=True)
class SpecializedRouteSpec:
    method: str
    path: str
    body_model: type[BaseModel]
    required_dependency: str
    deliberately_owned_fields: frozenset[str] = frozenset()

    @property
    def id(self) -> str:
        return f"{self.method} {self.path}"


SPECIALIZED_ROUTE_SPECS = (
    SpecializedRouteSpec(
        "POST",
        "/community-games/publish",
        CommunityGamePublishCreate,
        VERIFIED_USER_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "PATCH",
        "/games/{game_id}/host-edit",
        GameHostEdit,
        VERIFIED_USER_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "POST",
        "/games/{game_id}/join",
        GameJoinCreate,
        VERIFIED_USER_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "POST",
        "/games/{game_id}/leave",
        GameLeaveCreate,
        VERIFIED_USER_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "POST",
        "/games/{game_id}/booking-guests/add",
        GameBookingGuestAddCreate,
        VERIFIED_USER_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "POST",
        "/games/{game_id}/guests/add",
        GameGuestAddCreate,
        VERIFIED_USER_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "POST",
        "/games/{game_id}/guests/remove",
        GameGuestRemoveCreate,
        VERIFIED_USER_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "POST",
        "/games/{game_id}/cancel",
        GameCancelCreate,
        VERIFIED_USER_DEPENDENCY,
        frozenset({"cancel_reason"}),
    ),
    SpecializedRouteSpec(
        "POST",
        "/admin/official-games",
        AdminOfficialGameCreate,
        ACTIVE_ADMIN_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "PATCH",
        "/admin/official-games/{game_id}",
        AdminOfficialGameUpdate,
        ACTIVE_ADMIN_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "POST",
        "/admin/official-games/{game_id}/cancel",
        AdminOfficialGameCancelExecute,
        RECENT_ACTIVE_ADMIN_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "POST",
        "/admin/official-games/{game_id}/host",
        AdminOfficialGameHostAssign,
        ACTIVE_ADMIN_DEPENDENCY,
        frozenset({"host_user_id"}),
    ),
    SpecializedRouteSpec(
        "POST",
        "/admin/official-games/{game_id}/host/remove",
        AdminOfficialGameHostRemovalExecute,
        ACTIVE_ADMIN_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "POST",
        "/admin/official-games/{game_id}/players",
        AdminOfficialGamePlayerAdd,
        ACTIVE_ADMIN_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "POST",
        "/admin/official-games/{game_id}/participants/{participant_id}/remove",
        AdminOfficialGamePlayerRemovalExecute,
        ACTIVE_ADMIN_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "POST",
        "/community-game-details",
        CommunityGameDetailCreate,
        ACTIVE_ADMIN_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "PUT",
        "/community-game-details/games/{game_id}/host-edit",
        CommunityGameDetailHostUpsert,
        VERIFIED_USER_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "PATCH",
        "/community-game-details/{community_game_detail_id}",
        CommunityGameDetailUpdate,
        ACTIVE_ADMIN_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "POST",
        "/admin/community-games/{game_id}/hide-payment-text",
        AdminCommunityGameHidePaymentTextCreate,
        ACTIVE_ADMIN_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "POST",
        "/admin/community-games/{game_id}/restore-payment-text",
        AdminCommunityGameHidePaymentTextCreate,
        ACTIVE_ADMIN_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "POST",
        "/admin/community-games/{game_id}/hide",
        AdminCommunityGameEnforcementActionCreate,
        ACTIVE_ADMIN_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "POST",
        "/admin/community-games/{game_id}/restore",
        AdminCommunityGameEnforcementActionCreate,
        ACTIVE_ADMIN_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "POST",
        "/admin/community-games/{game_id}/pause-joining",
        AdminCommunityGameEnforcementActionCreate,
        ACTIVE_ADMIN_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "POST",
        "/admin/community-games/{game_id}/resume-joining",
        AdminCommunityGameEnforcementActionCreate,
        ACTIVE_ADMIN_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "POST",
        "/admin/community-games/{game_id}/cancel",
        AdminCommunityGameEnforcementActionCreate,
        ACTIVE_ADMIN_DEPENDENCY,
    ),
    SpecializedRouteSpec(
        "POST",
        "/admin/community-games/{game_id}/flag-for-review",
        AdminCommunityGameReviewFlagCreate,
        ACTIVE_ADMIN_DEPENDENCY,
    ),
)


def _iter_api_routes() -> tuple[APIRoute, ...]:
    from backend.main import app

    return tuple(route for route in app.routes if isinstance(route, APIRoute))


def _route_by_method_path(method: str, path: str) -> APIRoute:
    matches = [
        route
        for route in _iter_api_routes()
        if route.path == path and method.upper() in route.methods
    ]
    assert len(matches) == 1, f"{method} {path} should have exactly one route"
    return matches[0]


def _callable_name(callable_object: object) -> str:
    module = getattr(callable_object, "__module__", "")
    name = getattr(callable_object, "__name__", repr(callable_object))
    return f"{module}.{name}" if module else name


def _direct_dependency_call_names(route: APIRoute) -> tuple[str, ...]:
    return tuple(_callable_name(dependency.call) for dependency in route.dependant.dependencies)


def _body_annotation(route: APIRoute) -> object:
    assert route.body_field is not None
    return route.body_field.field_info.annotation


def _resolve_ref(schema: dict[str, object], components: dict[str, object]) -> dict[str, object]:
    ref = schema.get("$ref")
    if isinstance(ref, str):
        name = ref.removeprefix("#/components/schemas/")
        return components[name]
    if "allOf" in schema:
        merged: dict[str, object] = {"properties": {}}
        for item in schema["allOf"]:
            resolved = _resolve_ref(item, components)
            merged["properties"].update(resolved.get("properties", {}))
        return merged
    return schema


def _openapi_request_properties(method: str, path: str) -> set[str]:
    from backend.main import app

    openapi = app.openapi()
    raw_schema = openapi["paths"][path][method.lower()]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    request_schema = _resolve_ref(raw_schema, openapi["components"]["schemas"])
    return set(request_schema.get("properties", {}))


@pytest.mark.requirement("WS02-05B1-R5")
def test_specialized_mutation_routes_bind_purpose_schemas_and_actor_dependencies() -> None:
    for spec in SPECIALIZED_ROUTE_SPECS:
        route = _route_by_method_path(spec.method, spec.path)
        dependency_names = _direct_dependency_call_names(route)

        assert _body_annotation(route) is spec.body_model, spec.id
        assert spec.required_dependency in dependency_names, spec.id


@pytest.mark.requirement("WS02-05B1-R5")
def test_specialized_mutation_body_schemas_forbid_unknown_fields() -> None:
    for spec in SPECIALIZED_ROUTE_SPECS:
        assert spec.body_model.model_config.get("extra") == "forbid", spec.id


@pytest.mark.requirement("WS02-05B1-R5")
def test_dedicated_host_and_user_ids_are_not_generic_game_update_fields() -> None:
    host_user_owners = [
        spec.id
        for spec in SPECIALIZED_ROUTE_SPECS
        if "host_user_id" in spec.body_model.model_fields
    ]
    user_id_owners = [
        spec.id
        for spec in SPECIALIZED_ROUTE_SPECS
        if "user_id" in spec.body_model.model_fields
    ]

    assert "host_user_id" not in GameUpdate.model_fields
    assert host_user_owners == ["POST /admin/official-games/{game_id}/host"]
    assert user_id_owners == ["POST /admin/official-games/{game_id}/players"]


@pytest.mark.requirement("WS02-05B1-R5")
def test_specialized_openapi_request_schemas_do_not_expose_generic_game_bypass_fields() -> None:
    for spec in SPECIALIZED_ROUTE_SPECS:
        properties = _openapi_request_properties(spec.method, spec.path)
        forbidden_properties = (
            properties & GENERIC_PROTECTED_GAME_FIELDS
        ) - spec.deliberately_owned_fields
        assert forbidden_properties == set(), spec.id
