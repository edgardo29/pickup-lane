"""Source-owned HTTP contract metadata derived from FastAPI routes."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from re import Pattern

from fastapi import status
from fastapi.routing import APIRoute


PRIVATE_AUTH_DEPENDENCIES = frozenset(
    {
        "get_current_app_user",
        "require_active_admin",
        "require_active_user",
    }
)
OPTIONAL_AUTH_DEPENDENCIES = frozenset({"get_optional_current_app_user"})
DATABASE_DEPENDENCY_NAME = "get_db"
PROVIDER_WEBHOOK_PATHS = frozenset({"/stripe/webhook"})


@dataclass(frozen=True)
class RouteMatch:
    """A method/path matcher built from FastAPI route metadata."""

    path: str
    methods: frozenset[str]
    path_regex: Pattern[str]

    def matches(self, *, method: str, path: str) -> bool:
        return method.upper() in self.methods and bool(self.path_regex.match(path))


def iter_api_routes(routes: Iterable[object]) -> tuple[APIRoute, ...]:
    return tuple(route for route in routes if isinstance(route, APIRoute))


def route_dependency_names(route: APIRoute) -> frozenset[str]:
    names: set[str] = set()
    _collect_dependency_names(route.dependant.dependencies, names)
    return frozenset(names)


def route_is_private(route: APIRoute) -> bool:
    if route.path.startswith("/admin"):
        return True
    return bool(route_dependency_names(route) & PRIVATE_AUTH_DEPENDENCIES)


def route_has_optional_auth(route: APIRoute) -> bool:
    return bool(route_dependency_names(route) & OPTIONAL_AUTH_DEPENDENCIES)


def route_uses_database(route: APIRoute) -> bool:
    return DATABASE_DEPENDENCY_NAME in route_dependency_names(route)


def route_is_tombstone(route: APIRoute) -> bool:
    return route.status_code == status.HTTP_410_GONE


def route_has_request_body(route: APIRoute) -> bool:
    return bool(route.dependant.body_params)


def route_is_provider_webhook(route: APIRoute) -> bool:
    return route.path in PROVIDER_WEBHOOK_PATHS


def route_match(route: APIRoute) -> RouteMatch:
    return RouteMatch(
        path=route.path,
        methods=frozenset(method.upper() for method in route.methods or ()),
        path_regex=route.path_regex,
    )


def private_route_matches(routes: Iterable[object]) -> tuple[RouteMatch, ...]:
    return tuple(route_match(route) for route in iter_api_routes(routes) if route_is_private(route))


def _collect_dependency_names(dependencies, names: set[str]) -> None:
    for dependency in dependencies:
        call = getattr(dependency, "call", None)
        call_name = getattr(call, "__name__", "")
        if call_name:
            names.add(call_name)
        _collect_dependency_names(getattr(dependency, "dependencies", ()), names)
