"""Precomputed Firebase App Check route policy."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Pattern

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import Mount


class AppCheckPolicyError(RuntimeError):
    """Raised when a registered API route is not classified."""


class AppCheckRouteDisposition(str, Enum):
    INCLUDED = "included"
    EXCLUDED = "excluded"


@dataclass(frozen=True)
class AppCheckRoutePolicyEntry:
    methods: frozenset[str]
    route_template: str
    path_regex: Pattern[str]
    disposition: AppCheckRouteDisposition
    route_family: str

    def matches_path(self, path: str) -> bool:
        return bool(self.path_regex.match(path))

    def matches(self, *, method: str, path: str) -> bool:
        return method.upper() in self.methods and self.matches_path(path)


@dataclass(frozen=True)
class AppCheckRouteMatch:
    route_template: str
    disposition: AppCheckRouteDisposition
    route_family: str

    @property
    def applies(self) -> bool:
        return self.disposition is AppCheckRouteDisposition.INCLUDED


@dataclass(frozen=True)
class AppCheckRoutePolicy:
    entries: tuple[AppCheckRoutePolicyEntry, ...]

    def match(self, *, method: str, path: str) -> AppCheckRouteMatch | None:
        normalized_method = method.upper()
        if normalized_method == "OPTIONS":
            return None

        for entry in self.entries:
            if entry.matches(method=normalized_method, path=path):
                return AppCheckRouteMatch(
                    route_template=entry.route_template,
                    disposition=entry.disposition,
                    route_family=entry.route_family,
                )

        return None

    def included_route_templates(self) -> frozenset[str]:
        return frozenset(
            entry.route_template
            for entry in self.entries
            if entry.disposition is AppCheckRouteDisposition.INCLUDED
        )

    def excluded_route_templates(self) -> frozenset[str]:
        return frozenset(
            entry.route_template
            for entry in self.entries
            if entry.disposition is AppCheckRouteDisposition.EXCLUDED
        )


INFRASTRUCTURE_ROUTE_TEMPLATES = frozenset({"/", "/live", "/ready", "/db-health"})
DOCUMENTATION_ROUTE_TEMPLATES = frozenset({"/docs", "/redoc", "/openapi.json"})
PROVIDER_CALLBACK_ROUTE_TEMPLATES = frozenset({"/stripe/webhook"})
_BODYLESS_METHODS = frozenset({"HEAD", "OPTIONS"})
_NON_API_MOUNT_TEMPLATES = frozenset({"/static"})

SUPPORTED_BROWSER_API_ROUTE_TAGS = frozenset(
    {
        "admin",
        "admin_actions",
        "admin_community_games",
        "admin_game_credits",
        "admin_game_images",
        "admin_lookups",
        "admin_money",
        "admin_need_a_sub",
        "admin_notifications",
        "admin_official_games",
        "admin_rejected_attempts",
        "admin_review_cases",
        "admin_users",
        "admin_venue_images",
        "auth",
        "booking_policy_acceptances",
        "booking_status_history",
        "bookings",
        "chat_messages",
        "checkout",
        "community_game_details",
        "community_games",
        "game_chats",
        "game_credits",
        "game_images",
        "game_participants",
        "game_status_history",
        "games",
        "host_publish_fees",
        "inbox",
        "my_games",
        "need_a_sub_positions",
        "need_a_sub_post_status_history",
        "need_a_sub_posts",
        "need_a_sub_request_status_history",
        "need_a_sub_requests",
        "notifications",
        "participant_status_history",
        "payment_events",
        "payments",
        "platform_notices",
        "policy_acceptances",
        "policy_documents",
        "refunds",
        "support_flags",
        "user-payment-methods",
        "user-settings",
        "user_stats",
        "users",
        "venue_approval_requests",
        "venue_images",
        "venues",
        "waitlist_entries",
    }
)


def build_app_check_route_policy(app: FastAPI) -> AppCheckRoutePolicy:
    entries: list[AppCheckRoutePolicyEntry] = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            entries.append(_classify_api_route(route))
        elif isinstance(route, Mount):
            _classify_mount(route)
    return AppCheckRoutePolicy(tuple(entries))


def _classify_api_route(route: APIRoute) -> AppCheckRoutePolicyEntry:
    methods = frozenset(
        method.upper()
        for method in route.methods or ()
        if method.upper() not in _BODYLESS_METHODS
    )
    if not methods:
        raise AppCheckPolicyError(
            f"Registered route has no classifiable methods: {route.path}"
        )

    disposition, route_family = _route_disposition(route)
    return AppCheckRoutePolicyEntry(
        methods=methods,
        route_template=route.path,
        path_regex=route.path_regex,
        disposition=disposition,
        route_family=route_family,
    )


def _route_disposition(
    route: APIRoute,
) -> tuple[AppCheckRouteDisposition, str]:
    if route.path in INFRASTRUCTURE_ROUTE_TEMPLATES:
        return AppCheckRouteDisposition.EXCLUDED, "infrastructure"
    if _is_documentation_route(route.path):
        return AppCheckRouteDisposition.EXCLUDED, "infrastructure"
    if route.path in PROVIDER_CALLBACK_ROUTE_TEMPLATES:
        return AppCheckRouteDisposition.EXCLUDED, "provider_callback"

    tags = _route_tags(route)
    if tags and tags <= SUPPORTED_BROWSER_API_ROUTE_TAGS:
        return AppCheckRouteDisposition.INCLUDED, _route_family(tags)

    raise AppCheckPolicyError(f"Unclassified API route: {route.path}")


def _route_tags(route: APIRoute) -> frozenset[str]:
    return frozenset(tag for tag in route.tags if isinstance(tag, str) and tag)


def _route_family(tags: Iterable[str]) -> str:
    ordered = sorted(tags)
    if not ordered:
        raise AppCheckPolicyError("Included App Check route requires a route tag")
    normalized = re.sub(r"[^a-z0-9_]+", "_", ordered[0].lower()).strip("_")
    if not normalized:
        raise AppCheckPolicyError("Included App Check route requires a bounded tag")
    return f"api.{normalized}"


def _is_documentation_route(path: str) -> bool:
    return path in DOCUMENTATION_ROUTE_TEMPLATES or any(
        path.startswith(f"{template}/") for template in DOCUMENTATION_ROUTE_TEMPLATES
    )


def _classify_mount(route: Mount) -> None:
    if route.path in _NON_API_MOUNT_TEMPLATES:
        return
    if route.path.startswith("/"):
        raise AppCheckPolicyError(f"Unclassified non-API mount: {route.path}")
