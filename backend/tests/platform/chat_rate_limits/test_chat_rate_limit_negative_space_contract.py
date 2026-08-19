from __future__ import annotations

import ast
import inspect
import os
from pathlib import Path

import pytest

os.environ.setdefault("APP_ENV", "test")
if not os.getenv("DATABASE_URL"):
    pytest.skip(
        "DATABASE_URL is required for backend integration tests.",
        allow_module_level=True,
    )

from backend.models import ChatMessage, SubPostChatMessage
from backend.services import chat_rate_limit_service, game_chat_service, sub_post_chat_service

pytestmark = pytest.mark.suite_type("ordinary")

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BACKEND_ROOT = _REPO_ROOT / "backend"


def _python_sources_under(path: Path) -> list[Path]:
    return [
        source
        for source in path.rglob("*.py")
        if "tests/legacy" not in source.as_posix()
        and "__pycache__" not in source.as_posix()
    ]


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts: list[str] = []
        current: ast.AST = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


def _route_decorators(path: Path) -> list[tuple[str, str]]:
    tree = ast.parse(path.read_text())
    routes: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            method = _call_name(decorator.func).split(".")[-1]
            if method not in {"get", "post", "patch", "put", "delete"}:
                continue
            path_value = ""
            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                path_value = str(decorator.args[0].value)
            routes.append((method, path_value))
    return routes


@pytest.mark.requirement("WS02-04C3A-R9")
def test_single_shared_limiter_owner_and_current_send_routes_are_the_only_authenticated_insert_owners() -> None:
    game_source = inspect.getsource(game_chat_service)
    sub_source = inspect.getsource(sub_post_chat_service)
    limiter_source = inspect.getsource(chat_rate_limit_service)

    assert "def enforce_visible_text_chat_rate_limit" in limiter_source
    assert "pg_advisory_xact_lock" in limiter_source
    assert "limiter_category" in limiter_source
    assert "chat_id" in limiter_source
    assert "sender_user_id" in limiter_source

    assert 'limiter_category="game_chat"' in game_source
    assert 'limiter_category="need_a_sub_chat"' in sub_source
    assert "validate_sender_rate_limit" in inspect.getsource(game_chat_service.create_chat_message_record)
    assert "validate_sender_rate_limit" in inspect.getsource(
        sub_post_chat_service.create_sub_post_chat_message_workflow
    )

    production_insert_sources: list[str] = []
    for path in _python_sources_under(_BACKEND_ROOT / "services"):
        text = path.read_text()
        if "ChatMessage(" in text or "SubPostChatMessage(" in text:
            production_insert_sources.append(path.relative_to(_REPO_ROOT).as_posix())

    assert sorted(production_insert_sources) == [
        "backend/services/game_chat_service.py",
        "backend/services/sub_post_chat_service.py",
    ]


@pytest.mark.requirement("WS02-04C3A-R9")
def test_no_duplicate_route_middleware_frontend_memory_redis_or_generic_limiter_replaces_c3a() -> None:
    route_text = "\n".join(path.read_text() for path in (_BACKEND_ROOT / "routes").rglob("*.py"))
    main_text = (_BACKEND_ROOT / "main.py").read_text()
    limiter_text = inspect.getsource(chat_rate_limit_service)
    backend_text = "\n".join(
        path.read_text(errors="ignore")
        for path in _python_sources_under(_BACKEND_ROOT)
        if "/tests/" not in path.as_posix()
    )

    assert "enforce_visible_text_chat_rate_limit" not in route_text
    assert "CHAT_RATE_LIMIT_MAX_VISIBLE_TEXT_MESSAGES" not in route_text
    assert "RateLimitMiddleware" not in main_text
    assert "RequestBodyLimitMiddleware" in main_text
    assert "redis" not in limiter_text.lower()
    assert "in-memory" not in limiter_text.lower()
    assert "provider" not in limiter_text.lower()
    assert "rate_limit" not in " ".join(
        table.name
        for table in ChatMessage.metadata.sorted_tables
        if table.name not in {"chat_messages", "sub_post_chat_messages"}
    )
    assert "localStorage" not in backend_text
    assert "sessionStorage" not in backend_text


@pytest.mark.requirement("WS02-04C3A-R8")
@pytest.mark.requirement("WS02-04C3A-R9")
def test_ordinary_user_routes_do_not_expose_self_remove_restore_visibility_bypass() -> None:
    chat_routes = _route_decorators(_BACKEND_ROOT / "routes" / "chat_message_routes.py")
    sub_routes = _route_decorators(_BACKEND_ROOT / "routes" / "sub_post_routes.py")

    assert chat_routes == [
        ("post", ""),
        ("get", "/{chat_message_id}"),
        ("get", ""),
    ]
    assert ("post", "/{sub_post_id}/chat/messages") in sub_routes
    assert ("get", "/{sub_post_id}/chat/messages") in sub_routes
    for method, route_path in [*chat_routes, *sub_routes]:
        if "chat" not in route_path and route_path != "":
            continue
        assert method in {"get", "post"}
        assert "remove" not in route_path
        assert "restore" not in route_path

    admin_sources = "\n".join(
        (_BACKEND_ROOT / "routes" / file_name).read_text()
        for file_name in (
            "admin_community_routes.py",
            "admin_official_game_routes.py",
            "admin_need_a_sub_routes.py",
        )
    )
    assert "remove" in admin_sources
    assert "restore" in admin_sources


@pytest.mark.requirement("WS02-04C3A-R8")
def test_model_metadata_supports_visible_text_boundary_without_claiming_query_plan_or_migration_proof() -> None:
    game_constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in ChatMessage.__table__.constraints
        if constraint.name is not None
    }
    sub_constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in SubPostChatMessage.__table__.constraints
        if constraint.name is not None
    }
    game_indexes = {index.name for index in ChatMessage.__table__.indexes}
    sub_indexes = {index.name for index in SubPostChatMessage.__table__.indexes}

    assert "message_type IN ('text', 'system', 'pinned_update')" in game_constraints[
        "ck_chat_messages_message_type"
    ]
    assert "message_type IN ('text')" in sub_constraints[
        "ck_sub_post_chat_messages_message_type"
    ]
    assert "visibility_status IN ('visible', 'removed')" in game_constraints[
        "ck_chat_messages_visibility_status"
    ]
    assert "visibility_status IN ('visible', 'removed')" in sub_constraints[
        "ck_sub_post_chat_messages_visibility_status"
    ]
    assert "ix_chat_messages_chat_id_created_at" in game_indexes
    assert "ix_chat_messages_chat_id_visibility_status" in game_indexes
    assert "ix_sub_post_chat_messages_chat_id_created_at" in sub_indexes
    assert "ix_sub_post_chat_messages_chat_id_visibility_status" in sub_indexes


@pytest.mark.requirement("WS02-04C3A-R10")
def test_c3a_event_source_has_no_sensitive_or_high_cardinality_runtime_fields() -> None:
    source = inspect.getsource(chat_rate_limit_service._log_rate_limit_event)

    assert 'event_name="chat.rate_limit"' in source
    assert 'actor_kind="authenticated_user"' in source
    assert 'operation="chat_rate_limit.check"' in source
    assert "resource_kind=limiter_category" in source
    assert 'labels={"outcome": result, "route_template": _route_template(limiter_category)}' in source
    for forbidden in (
        "user_id",
        "chat_id",
        "game_id",
        "sub_post_id",
        "ip",
        "email",
        "message_body",
        "token",
        "provider",
        "exception",
        "sql",
    ):
        assert forbidden not in source.lower()
