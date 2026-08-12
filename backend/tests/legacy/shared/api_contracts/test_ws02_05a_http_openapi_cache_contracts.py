from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
import uuid

from fastapi import status
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest

import backend.main as main_module
from backend.main import create_app
from backend.observability.correlation import CORRELATION_ID_HEADER
from backend.observability.pagination_contracts import (
    PAGINATION_CONTRACTS,
    PAGINATION_HANDOFFS,
    pagination_contract_keys,
    pagination_handoff_keys,
)
from backend.observability.request_body_limits import (
    UNSUPPORTED_CONTENT_ENCODING_CODE,
    UNSUPPORTED_MEDIA_TYPE_CODE,
)
from backend.routes import stripe_webhook_routes
from backend.services import auth_service
from backend.settings import AppEnvironment, BackendSettings


pytestmark = pytest.mark.no_db_cleanup

ALLOWED_HOST = "api.example.test"
ALLOWED_ORIGIN = "https://frontend.example"
UNUSED_DATABASE_SETTING = "unused-by-ws02-05a-contract-tests"


def runtime_settings(
    *,
    app_env: AppEnvironment = AppEnvironment.TEST,
    enable_api_docs: bool = True,
    enable_db_health: bool = True,
) -> BackendSettings:
    return BackendSettings(
        app_env=app_env,
        database_url=SecretStr(UNUSED_DATABASE_SETTING),
        allowed_hosts=(ALLOWED_HOST, "testserver"),
        cors_allowed_origins=(ALLOWED_ORIGIN,),
        enable_api_docs=enable_api_docs,
        enable_db_health=enable_db_health,
        enable_stripe_payments=False,
    )


def build_app(**settings_overrides):
    return create_app(settings=runtime_settings(**settings_overrides))


def host_headers() -> dict[str, str]:
    return {"Host": ALLOWED_HOST}


def origin_headers() -> dict[str, str]:
    return {"Host": ALLOWED_HOST, "Origin": ALLOWED_ORIGIN}


def synthetic_admin_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        role="admin",
        account_status="active",
        updated_at=datetime(2026, 1, 1),
    )


def assert_stable_error(response, *, status_code: int, code: str) -> dict:
    assert response.status_code == status_code, response.text
    body = response.json()
    assert body["code"] == code
    assert isinstance(body["message"], str)
    assert body["message"]
    assert "detail" in body
    assert body["correlation_id"] == response.headers[CORRELATION_ID_HEADER]
    uuid.UUID(body["correlation_id"])
    return body


def test_explicit_non_json_media_type_on_json_body_route_returns_415():
    app = build_app()

    with TestClient(app) as client:
        response = client.patch(
            "/users/me",
            content=b"{}",
            headers={
                **origin_headers(),
                "Content-Type": "text/plain",
            },
        )

    body = assert_stable_error(
        response,
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        code=UNSUPPORTED_MEDIA_TYPE_CODE,
    )
    assert body["message"] == "Unsupported media type."
    assert response.headers["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN
    assert response.headers["Cache-Control"] == "private, no-store"
    assert "text/plain" not in response.text


def test_json_charset_and_missing_content_type_preserve_compatibility():
    app = build_app()

    with TestClient(app) as client:
        charset_response = client.patch(
            "/users/me",
            content=b"{}",
            headers={
                **host_headers(),
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        missing_type_response = client.patch(
            "/users/me",
            content=b"{}",
            headers=host_headers(),
        )

    assert charset_response.status_code != status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert missing_type_response.status_code != status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert charset_response.json()["code"] != UNSUPPORTED_MEDIA_TYPE_CODE
    assert missing_type_response.json()["code"] != UNSUPPORTED_MEDIA_TYPE_CODE


def test_malformed_json_remains_existing_stable_422_behavior():
    app = build_app()

    with TestClient(app) as client:
        response = client.patch(
            "/users/me",
            content=b"{malformed",
            headers={**host_headers(), "Content-Type": "application/json"},
        )

    assert response.status_code != status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert response.json()["code"] in {
        "API.MALFORMED_JSON",
        "AUTH.UNAUTHENTICATED",
    }


def test_existing_unsupported_content_encoding_contract_is_unchanged():
    app = build_app()

    with TestClient(app) as client:
        response = client.patch(
            "/users/me",
            content=b"compressed-body",
            headers={
                **host_headers(),
                "Content-Encoding": "gzip",
                "Content-Type": "application/json",
            },
        )

    body = assert_stable_error(
        response,
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        code=UNSUPPORTED_CONTENT_ENCODING_CODE,
    )
    assert body["message"] == "Unsupported content encoding."


def test_raw_stripe_webhook_media_behavior_remains_special(monkeypatch):
    app = build_app()

    def fake_construct_webhook_event(payload: bytes, stripe_signature: str):
        del payload, stripe_signature
        return {"id": "evt_synthetic", "type": "synthetic.event", "data": {}}

    def fake_record_and_process_stripe_webhook_event(db, stripe_event):
        del db, stripe_event
        return {"status": "processed"}

    monkeypatch.setattr(
        stripe_webhook_routes,
        "construct_webhook_event",
        fake_construct_webhook_event,
    )
    monkeypatch.setattr(
        stripe_webhook_routes,
        "record_and_process_stripe_webhook_event",
        fake_record_and_process_stripe_webhook_event,
    )

    with TestClient(app) as client:
        response = client.post(
            "/stripe/webhook",
            content=b'{"type":"synthetic.event"}',
            headers={
                **host_headers(),
                "Content-Type": "text/plain",
                "Stripe-Signature": "synthetic-signature",
            },
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "processed"}


def test_bodyless_tombstones_do_not_start_parsing_media_type():
    app = build_app()
    app.dependency_overrides[auth_service.require_active_admin] = synthetic_admin_user

    try:
        with TestClient(app) as client:
            response = client.post(
                "/bookings",
                content=b"not-json",
                headers={
                    **host_headers(),
                    "Content-Type": "text/plain",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert_stable_error(
        response,
        status_code=status.HTTP_410_GONE,
        code="API.HTTP_ERROR",
    )
    assert UNSUPPORTED_MEDIA_TYPE_CODE not in response.text


def test_framework_owned_405_contract_keeps_allow_header_and_security():
    app = build_app()

    with TestClient(app) as client:
        response = client.put("/live", headers=origin_headers())

    body = assert_stable_error(
        response,
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        code="API.METHOD_NOT_ALLOWED",
    )
    assert body["detail"] == "Method Not Allowed"
    assert "GET" in response.headers["Allow"]
    assert response.headers["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_private_and_public_json_cache_policies_are_source_owned():
    app = build_app()
    app.dependency_overrides[auth_service.require_active_admin] = synthetic_admin_user

    try:
        with TestClient(app) as client:
            private_response = client.get("/admin/me", headers=host_headers())
            public_response = client.get("/", headers=host_headers())
    finally:
        app.dependency_overrides.clear()

    assert private_response.status_code == status.HTTP_200_OK
    assert private_response.headers["Cache-Control"] == "private, no-store"
    assert public_response.status_code == status.HTTP_200_OK
    assert public_response.headers["Cache-Control"] == "no-store"


def test_docs_openapi_environment_policy_is_preserved(monkeypatch):
    monkeypatch.setattr(main_module, "check_database_connection", lambda: True)
    local_app = build_app(app_env=AppEnvironment.LOCAL, enable_api_docs=True)
    production_app = build_app(
        app_env=AppEnvironment.PRODUCTION,
        enable_api_docs=False,
        enable_db_health=False,
    )

    with TestClient(local_app) as local_client:
        docs_response = local_client.get("/docs", headers=host_headers())
        redoc_response = local_client.get("/redoc", headers=host_headers())
        schema_response = local_client.get("/openapi.json", headers=host_headers())

    with TestClient(production_app) as production_client:
        production_docs = production_client.get("/docs", headers=host_headers())
        production_redoc = production_client.get("/redoc", headers=host_headers())
        production_schema = production_client.get("/openapi.json", headers=host_headers())

    assert docs_response.status_code == status.HTTP_200_OK
    assert redoc_response.status_code == status.HTTP_200_OK
    assert schema_response.status_code == status.HTTP_200_OK
    assert production_docs.status_code == status.HTTP_404_NOT_FOUND
    assert production_redoc.status_code == status.HTTP_404_NOT_FOUND
    assert production_schema.status_code == status.HTTP_404_NOT_FOUND


def test_openapi_shared_error_components_and_common_statuses_are_documented():
    schema = build_app().openapi()
    components = schema["components"]["schemas"]

    assert "PublicErrorResponse" in components
    assert "ValidationErrorResponse" in components
    assert "detail" in components["PublicErrorResponse"]["properties"]

    users_me_patch = schema["paths"]["/users/me"]["patch"]["responses"]
    assert set(users_me_patch) >= {"401", "403", "405", "409", "413", "415", "422", "503"}

    admin_me_get = schema["paths"]["/admin/me"]["get"]["responses"]
    assert set(admin_me_get) >= {"401", "403", "405"}

    chat_create = schema["paths"]["/chat-messages"]["post"]["responses"]
    assert "429" in chat_create

    ready = schema["paths"]["/ready"]["get"]["responses"]
    assert "503" in ready


def test_openapi_tombstones_are_deprecated_bodyless_410_operations():
    schema = build_app().openapi()
    operation = schema["paths"]["/bookings"]["post"]

    assert operation["deprecated"] is True
    assert "requestBody" not in operation
    assert "410" in operation["responses"]
    assert operation["responses"]["410"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/PublicErrorResponse",
    }


def test_openapi_request_body_media_types_remain_correct():
    schema = build_app().openapi()

    users_me_patch = schema["paths"]["/users/me"]["patch"]
    content = users_me_patch["requestBody"]["content"]
    assert set(content) == {"application/json"}

    webhook = schema["paths"]["/stripe/webhook"]["post"]
    assert "requestBody" not in webhook

    tombstone = schema["paths"]["/bookings"]["post"]
    assert "requestBody" not in tombstone


def test_openapi_operation_ids_are_unique_and_method_paths_are_not_duplicated():
    schema = build_app().openapi()
    operation_ids: list[str] = []
    method_paths: set[tuple[str, str]] = set()

    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            method_path = (method.upper(), path)
            assert method_path not in method_paths
            method_paths.add(method_path)
            operation_ids.append(operation["operationId"])

    assert len(operation_ids) == len(set(operation_ids))


def test_pagination_inventory_covers_all_current_collection_candidates():
    app = build_app()
    current_candidates = _current_collection_route_keys(app.routes)
    registered_candidates = pagination_contract_keys() | pagination_handoff_keys()

    assert current_candidates == registered_candidates
    assert pagination_contract_keys().isdisjoint(pagination_handoff_keys())
    assert len(PAGINATION_HANDOFFS) > 0


def test_pagination_contract_route_limits_match_route_metadata():
    route_map = {
        ("GET", route.path): route
        for route in build_app().routes
        if isinstance(route, APIRoute) and "GET" in (route.methods or set())
    }

    for contract in PAGINATION_CONTRACTS:
        route = route_map[contract.key]
        query_params = {param.name: param for param in route.dependant.query_params}

        if contract.limit_default is not None:
            assert "limit" in query_params, contract.key
            assert query_params["limit"].default == contract.limit_default

        if contract.limit_max is not None and "route" in contract.max_owner:
            assert _query_le(query_params["limit"]) == contract.limit_max

        if contract.next_cursor:
            assert any("cursor" in name for name in query_params), contract.key

        if contract.offset_param is not None:
            offset_param = query_params[contract.offset_param]
            assert _query_ge(offset_param) == 0


def _current_collection_route_keys(routes) -> frozenset[tuple[str, str]]:
    candidates: set[tuple[str, str]] = set()
    for route in routes:
        if not isinstance(route, APIRoute) or "GET" not in (route.methods or set()):
            continue
        query_params = {param.name: param for param in route.dependant.query_params}
        response_model = str(route.response_model)
        if _is_collection_route(response_model, query_params):
            candidates.add(("GET", route.path))
    return frozenset(candidates)


def _is_collection_route(response_model: str, query_params: dict) -> bool:
    return (
        "list[" in response_model
        or "List" in response_model
        or "Page" in response_model
        or "ListRead" in response_model
        or "ListResponse" in response_model
        or "limit" in query_params
        or "cursor" in query_params
        or "offset" in query_params
    )


def _query_le(param) -> int | None:
    for metadata in param.field_info.metadata:
        value = getattr(metadata, "le", None)
        if value is not None:
            return value
    return None


def _query_ge(param) -> int | None:
    for metadata in param.field_info.metadata:
        value = getattr(metadata, "ge", None)
        if value is not None:
            return value
    return None
