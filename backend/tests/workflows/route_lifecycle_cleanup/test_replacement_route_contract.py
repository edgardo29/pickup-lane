from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import pytest
from fastapi.routing import APIRoute

from backend.tests.workflows.route_lifecycle_cleanup.test_retired_route_registration_contract import (
    RETIRED_MUTATION_ROUTES,
    route_by_method_path,
)

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

REPO_ROOT = Path(__file__).resolve().parents[4]
FRONTEND_ADMIN_API = REPO_ROOT / "frontend" / "src" / "pages" / "admin" / "shared" / "adminApi.js"
FRONTEND_OFFICIAL_GAMES_API = (
    REPO_ROOT
    / "frontend"
    / "src"
    / "pages"
    / "admin"
    / "official-games"
    / "shared"
    / "adminOfficialGamesApi.js"
)
TRUSTED_SUPPORT_FILES = (
    REPO_ROOT / "backend" / "tests" / "conftest.py",
    REPO_ROOT / "backend" / "tests" / "support" / "__init__.py",
    REPO_ROOT / "backend" / "tests" / "support" / "artifacts.py",
    REPO_ROOT / "backend" / "tests" / "support" / "browser_quality.py",
    REPO_ROOT / "backend" / "tests" / "support" / "environment_safety.py",
)
def _call_names(function) -> tuple[str, ...]:
    source = inspect.getsource(function)
    tree = ast.parse(source)
    calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            calls.append(_call_name(node.func))
    return tuple(calls)


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _route(method: str, path: str) -> APIRoute:
    return route_by_method_path(method, path)


def _assert_active_route(method: str, path: str, *, body_expected: bool) -> APIRoute:
    route = _route(method, path)

    assert route.status_code != 410
    assert ("raise_retired_mutation_route" not in _call_names(route.endpoint))
    assert (route.body_field is not None) is body_expected
    return route


def _function_block(source: str, function_name: str) -> str:
    match = re.search(rf"export\s+async\s+function\s+{re.escape(function_name)}\b", source)
    assert match is not None, function_name
    start = match.start()
    body_match = re.search(r"\)\s*\{", source[match.end() :])
    assert body_match is not None, function_name
    brace_start = match.end() + body_match.end() - 1
    depth = 0
    for index in range(brace_start, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"could not find end of {function_name}")


def _path_pattern(path: str) -> re.Pattern[str]:
    escaped = re.escape(path)
    pattern = re.sub(r"\\\{[^}]+\\\}", r"[^/]+", escaped)
    return re.compile(rf"^{pattern}$")


def _joined_string_value(node: ast.JoinedStr) -> str:
    parts = []
    for value in node.values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            parts.append(value.value)
        else:
            parts.append("synthetic")
    return "".join(parts)


def _stringish_value(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return _joined_string_value(node)
    return None


def _http_method_path_from_call(node: ast.Call, method_name: str) -> tuple[str, str] | None:
    if method_name in {"get", "post", "patch", "put", "delete"}:
        if not node.args:
            return None
        path = _stringish_value(node.args[0])
        return (method_name.upper(), path) if path is not None else None
    if method_name != "request" or len(node.args) < 2:
        return None
    method = _stringish_value(node.args[0])
    path = _stringish_value(node.args[1])
    if method is None or path is None:
        return None
    return method.upper(), path


@pytest.mark.requirement("WS02-04B2A2B1-R3")
def test_need_a_sub_duplicate_removal_is_retired_and_admin_post_is_canonical() -> None:
    retired = _route("PATCH", "/need-a-sub/posts/{sub_post_id}/remove")
    canonical = _assert_active_route("POST", "/admin/need-a-sub/{post_id}/remove", body_expected=True)

    assert retired.status_code == 410
    assert "raise_retired_mutation_route" in _call_names(retired.endpoint)
    assert "remove_need_a_sub_post_by_admin" in _call_names(canonical.endpoint)


@pytest.mark.requirement("WS02-04B2A2B1-R4")
def test_official_game_player_delete_is_retired_and_post_preview_execute_are_canonical() -> None:
    retired = _route("DELETE", "/admin/official-games/{game_id}/participants/{participant_id}")
    preview = _assert_active_route(
        "POST",
        "/admin/official-games/{game_id}/participants/{participant_id}/remove-preview",
        body_expected=False,
    )
    execute = _assert_active_route(
        "POST",
        "/admin/official-games/{game_id}/participants/{participant_id}/remove",
        body_expected=True,
    )

    assert retired.status_code == 410
    assert "raise_retired_mutation_route" in _call_names(retired.endpoint)
    assert "preview_official_game_player_removal" in _call_names(preview.endpoint)
    assert "execute_official_game_player_removal" in _call_names(execute.endpoint)


@pytest.mark.requirement("WS02-04B2A2B1-R5")
def test_official_game_host_delete_is_retired_and_post_remove_is_canonical() -> None:
    retired = _route("DELETE", "/admin/official-games/{game_id}/host")
    canonical = _assert_active_route(
        "POST",
        "/admin/official-games/{game_id}/host/remove",
        body_expected=True,
    )

    assert retired.status_code == 410
    assert "raise_retired_mutation_route" in _call_names(retired.endpoint)
    assert "remove_official_game_host" in _call_names(canonical.endpoint)
    assert canonical.body_field is not None
    assert getattr(canonical.body_field.field_info, "annotation", None).__name__ == (
        "AdminOfficialGameHostRemovalExecute"
    )


@pytest.mark.requirement(
    "WS02-04B2A2B1-R3",
    "WS02-04B2A2B1-R4",
    "WS02-04B2A2B1-R5",
    "WS02-04B2A2B1-R6",
)
def test_frontend_production_callers_use_canonical_replacement_routes() -> None:
    admin_api = FRONTEND_ADMIN_API.read_text()
    official_games_api = FRONTEND_OFFICIAL_GAMES_API.read_text()

    need_a_sub_remove = _function_block(admin_api, "removeAdminNeedASubPost")
    assert "`/admin/need-a-sub/${postId}/remove`" in need_a_sub_remove
    assert "method: 'POST'" in need_a_sub_remove
    assert "/need-a-sub/posts/" not in need_a_sub_remove

    host_remove = _function_block(official_games_api, "removeAdminOfficialGameHost")
    assert "`/admin/official-games/${gameId}/host/remove`" in host_remove
    assert "method: 'POST'" in host_remove
    assert "JSON.stringify({ reason })" in host_remove
    assert "method: 'DELETE'" not in host_remove

    player_preview = _function_block(official_games_api, "previewAdminOfficialGamePlayerRemoval")
    assert "`/admin/official-games/${gameId}/participants/${participantId}/remove-preview`" in player_preview
    assert "method: 'POST'" in player_preview
    assert "method: 'DELETE'" not in player_preview

    player_execute = _function_block(official_games_api, "executeAdminOfficialGamePlayerRemoval")
    assert "`/admin/official-games/${gameId}/participants/${participantId}/remove`" in player_execute
    assert "method: 'POST'" in player_execute
    assert "method: 'DELETE'" not in player_execute


@pytest.mark.requirement("WS02-04B2A2B1-R6")
def test_current_trusted_backend_support_helpers_do_not_setup_through_retired_routes() -> None:
    retired_patterns = {
        (retired_route.method, _path_pattern(retired_route.path)): retired_route.id
        for retired_route in RETIRED_MUTATION_ROUTES
    }
    http_methods = {"get", "post", "patch", "put", "delete", "request"}

    for path in TRUSTED_SUPPORT_FILES:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            call_name = _call_name(node.func)
            method_name = call_name.rsplit(".", 1)[-1]
            if method_name not in http_methods:
                continue
            method_path = _http_method_path_from_call(node, method_name)
            if method_path is None:
                continue
            method, request_path = method_path
            for (retired_method, pattern), route_id in retired_patterns.items():
                assert not (method == retired_method and pattern.fullmatch(request_path)), f"{path}: {route_id}"
