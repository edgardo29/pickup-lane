"""Source-owned HTTP contract metadata derived from FastAPI routes."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from re import Pattern

from fastapi import status
from fastapi.routing import APIRoute
from starlette.datastructures import Headers, MutableHeaders
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import PlainTextResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

NO_STORE_CACHE_CONTROL = "no-store"
PRIVATE_NO_STORE_CACHE_CONTROL = "private, no-store"
API_REFERRER_POLICY = "no-referrer"
CONTENT_TYPE_OPTIONS = "nosniff"

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


def apply_api_security_headers(
    headers: MutableHeaders,
    *,
    cache_control: str = NO_STORE_CACHE_CONTROL,
) -> None:
    """Apply the API response header contract to normal and outer errors."""

    headers.setdefault("X-Content-Type-Options", CONTENT_TYPE_OPTIONS)
    headers.setdefault("Referrer-Policy", API_REFERRER_POLICY)
    headers.setdefault("Cache-Control", cache_control)


class ApplicationCORSMiddleware(CORSMiddleware):
    """Keep denied preflights from advertising any CORS permissions."""

    def preflight_response(self, request_headers: Headers) -> Response:
        response = super().preflight_response(request_headers)
        if response.status_code != 200:
            for name in tuple(response.headers):
                if name.lower().startswith("access-control-"):
                    del response.headers[name]
        return response


@dataclass(frozen=True)
class RouteMatch:
    """A method/path matcher built from FastAPI route metadata."""

    path: str
    methods: frozenset[str]
    path_regex: Pattern[str]

    def matches(self, *, method: str, path: str) -> bool:
        return method.upper() in self.methods and bool(self.path_regex.match(path))


class RoutePreflightMethodMiddleware:
    """Reject preflights whose requested method is absent from a matching API route."""

    def __init__(self, app: ASGIApp, *, routes: tuple[RouteMatch, ...]) -> None:
        self.app = app
        self._routes = routes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("method") == "OPTIONS":
            headers = Headers(scope=scope)
            requested_method = headers.get("access-control-request-method")
            if headers.get("origin") and requested_method:
                path = str(scope.get("path") or "")
                path_matches = tuple(
                    route for route in self._routes if route.path_regex.match(path)
                )
                if path_matches and not any(
                    route.matches(method=requested_method, path=path)
                    for route in path_matches
                ):
                    response = PlainTextResponse(
                        "Disallowed CORS method", status_code=400
                    )
                    await response(scope, receive, send)
                    return

        await self.app(scope, receive, send)


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
    return tuple(
        route_match(route)
        for route in iter_api_routes(routes)
        if route_is_private(route)
    )


def _collect_dependency_names(dependencies, names: set[str]) -> None:
    for dependency in dependencies:
        call = getattr(dependency, "call", None)
        call_name = getattr(call, "__name__", "")
        if call_name:
            names.add(call_name)
        _collect_dependency_names(getattr(dependency, "dependencies", ()), names)
