from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from backend.schemas.game_schema import GameCreate, GameUpdate

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

REPO_ROOT = Path(__file__).resolve().parents[4]
FRONTEND_SOURCE_ROOTS = (
    REPO_ROOT / "frontend" / "src" / "pages" / "create-game",
    REPO_ROOT / "frontend" / "src" / "pages" / "admin" / "official-games",
    REPO_ROOT / "frontend" / "src" / "pages" / "browse-games",
)
GAME_SERVICE = REPO_ROOT / "backend" / "services" / "game_service.py"
TRUSTED_TEST_SCAN_ROOTS = (
    REPO_ROOT / "backend" / "tests" / "conftest.py",
    REPO_ROOT / "backend" / "tests" / "support",
    REPO_ROOT / "backend" / "tests" / "checker",
    REPO_ROOT / "backend" / "tests" / "platform",
    REPO_ROOT / "backend" / "tests" / "workflows",
)
SOURCE_SUFFIXES = {".js", ".jsx", ".ts", ".tsx"}
GENERIC_CREATE_ALLOWED_FIELDS = set(GameCreate.model_fields)
GENERIC_UPDATE_ALLOWED_FIELDS = set(GameUpdate.model_fields)
PROTECTED_CREATE_OVERPOST_FIELDS = {
    "created_by_user_id",
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
PROTECTED_UPDATE_OVERPOST_FIELDS = PROTECTED_CREATE_OVERPOST_FIELDS | {
    "game_type",
    "venue_id",
    "host_user_id",
}
SERVICE_DERIVED_CREATE_FIELDS = {
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
    "created_by_user_id",
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
}


def _source_files(roots: tuple[Path, ...], suffixes: set[str]) -> tuple[Path, ...]:
    paths: list[Path] = []
    for root in roots:
        if root.is_file():
            paths.append(root)
            continue
        paths.extend(path for path in root.rglob("*") if path.is_file() and path.suffix in suffixes)
    return tuple(sorted(paths))


def _python_test_sources() -> tuple[Path, ...]:
    paths: list[Path] = []
    for root in TRUSTED_TEST_SCAN_ROOTS:
        if root.is_file():
            paths.append(root)
            continue
        paths.extend(path for path in root.rglob("*.py") if path.is_file())
    filtered = []
    for path in paths:
        relative_parts = path.relative_to(REPO_ROOT).parts
        if "legacy" in relative_parts:
            continue
        if relative_parts[:4] == (
            "backend",
            "tests",
            "workflows",
            "request_ownership",
        ):
            continue
        filtered.append(path)
    return tuple(sorted(filtered))


def _api_request_calls(source: str) -> tuple[tuple[str, str, str], ...]:
    calls: list[tuple[str, str, str]] = []
    pattern = re.compile(
        r"apiRequest\(\s*(?P<path>`[^`]+`|'[^']+'|\"[^\"]+\")(?P<body>.*?)(?=\n\})",
        re.DOTALL,
    )
    for match in pattern.finditer(source):
        path_literal = match.group("path")
        body = match.group("body")
        method_match = re.search(r"method:\s*['\"](?P<method>[A-Z]+)['\"]", body)
        method = method_match.group("method") if method_match else "GET"
        calls.append((method, path_literal, body))
    return tuple(calls)


def _function_by_name(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function {name} not found")


def _return_dict_keys(function: ast.FunctionDef) -> set[str]:
    for node in ast.walk(function):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
            keys: set[str] = set()
            for key in node.value.keys:
                assert isinstance(key, ast.Constant)
                assert isinstance(key.value, str)
                keys.add(key.value)
            return keys
    raise AssertionError(f"function {function.name} did not return a dict literal")


def _call_name(call: ast.Call) -> str:
    function = call.func
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute):
        return function.attr
    return ""


def _explicit_keyword_names(call: ast.Call) -> set[str]:
    return {keyword.arg for keyword in call.keywords if keyword.arg is not None}


def _string_constant(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _dict_literal_keys(node: ast.AST) -> set[str]:
    if not isinstance(node, ast.Dict):
        return set()
    keys: set[str] = set()
    for key in node.keys:
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            keys.add(key.value)
    return keys


def _generic_game_http_payload_issues(path: Path, tree: ast.AST) -> list[str]:
    issues: list[str] = []
    for call in ast.walk(tree):
        if not isinstance(call, ast.Call):
            continue
        name = _call_name(call)
        if name not in {"post", "patch", "request"}:
            continue

        method = name.upper()
        path_arg_index = 0
        if name == "request":
            if len(call.args) < 2:
                continue
            requested_method = _string_constant(call.args[0])
            if requested_method is None:
                continue
            method = requested_method.upper()
            path_arg_index = 1

        if len(call.args) <= path_arg_index:
            continue
        path_value = _string_constant(call.args[path_arg_index])
        if path_value is None:
            continue

        protected_fields = set()
        if method == "POST" and path_value == "/games":
            protected_fields = PROTECTED_CREATE_OVERPOST_FIELDS
        elif method == "PATCH" and path_value.startswith("/games/") and path_value.count("/") == 2:
            protected_fields = PROTECTED_UPDATE_OVERPOST_FIELDS
        else:
            continue

        for keyword in call.keywords:
            if keyword.arg != "json":
                continue
            unsafe = _dict_literal_keys(keyword.value) & protected_fields
            if unsafe:
                issues.append(f"{path}: {method} {path_value} sends {sorted(unsafe)}")
    return issues


@pytest.mark.requirement("WS02-05B1-R6")
def test_current_frontend_callers_do_not_use_generic_game_write_routes() -> None:
    forbidden_calls: list[str] = []
    for path in _source_files(FRONTEND_SOURCE_ROOTS, SOURCE_SUFFIXES):
        source = path.read_text()
        for method, path_literal, _body in _api_request_calls(source):
            normalized_path = path_literal.strip("'\"`")
            if method == "POST" and normalized_path == "/games":
                forbidden_calls.append(f"{path}: POST {path_literal}")
            if (
                method == "PATCH"
                and normalized_path.startswith("/games/${")
                and "/host-edit" not in normalized_path
            ):
                forbidden_calls.append(f"{path}: PATCH {path_literal}")

    assert forbidden_calls == []


@pytest.mark.requirement("WS02-05B1-R6")
def test_generic_game_service_uses_explicit_mapping_not_request_shaped_orm_bypass() -> None:
    source = GAME_SERVICE.read_text()
    tree = ast.parse(source)
    build_create_data = _function_by_name(tree, "build_game_create_data")
    create_workflow = _function_by_name(tree, "create_game_workflow")
    update_workflow = _function_by_name(tree, "update_game_workflow")

    assert SERVICE_DERIVED_CREATE_FIELDS.issubset(_return_dict_keys(build_create_data))
    assert "created_by_user_id\": admin_user.id" in source
    assert "venue_name_snapshot\": venue.name" in source
    assert "address_snapshot\": build_game_address_snapshot(venue)" in source
    assert "payment_collection_type" in ast.get_source_segment(source, build_create_data)
    assert "normalize_game_lifecycle_fields(game_data)" in source
    assert "update_data = game_update.model_dump(exclude_unset=True)" in source
    assert GENERIC_CREATE_ALLOWED_FIELDS.isdisjoint(PROTECTED_CREATE_OVERPOST_FIELDS)
    assert GENERIC_UPDATE_ALLOWED_FIELDS.isdisjoint(PROTECTED_UPDATE_OVERPOST_FIELDS)

    unsafe_unpack_sources: list[str] = []
    for function in (create_workflow, update_workflow):
        for call in ast.walk(function):
            if not isinstance(call, ast.Call) or _call_name(call) != "Game":
                continue
            for keyword in call.keywords:
                if keyword.arg is not None:
                    continue
                unpacked_source = ast.unparse(keyword.value)
                if unpacked_source in {
                    "request_data",
                    "update_data",
                    "game.model_dump()",
                    "game_update.model_dump()",
                    "game_update.model_dump(exclude_unset=True)",
                }:
                    unsafe_unpack_sources.append(unpacked_source)

    assert unsafe_unpack_sources == []
    assert "**game.model_dump()" not in source
    assert "**game_update.model_dump" not in source


@pytest.mark.requirement("WS02-05B1-R6")
def test_current_trusted_helpers_and_setup_callers_do_not_require_generic_overposting() -> None:
    constructor_issues: list[str] = []
    http_payload_issues: list[str] = []

    for path in _python_test_sources():
        tree = ast.parse(path.read_text())
        http_payload_issues.extend(_generic_game_http_payload_issues(path, tree))
        for call in ast.walk(tree):
            if not isinstance(call, ast.Call):
                continue
            call_name = _call_name(call)
            keyword_names = _explicit_keyword_names(call)
            if call_name == "GameCreate":
                unsafe = keyword_names & PROTECTED_CREATE_OVERPOST_FIELDS
            elif call_name == "GameUpdate":
                unsafe = keyword_names & PROTECTED_UPDATE_OVERPOST_FIELDS
            else:
                continue

            if unsafe:
                constructor_issues.append(
                    f"{path}: {call_name} uses protected fields {sorted(unsafe)}"
                )

    assert constructor_issues == []
    assert http_payload_issues == []
