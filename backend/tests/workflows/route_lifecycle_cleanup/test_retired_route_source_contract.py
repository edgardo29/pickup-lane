from __future__ import annotations

import ast
import importlib
import inspect
import textwrap
from collections.abc import Iterable

import pytest

from backend.tests.workflows.route_lifecycle_cleanup.test_retired_route_registration_contract import (
    RETIRED_MUTATION_ROUTES,
    route_by_method_path,
)

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

_BODY_READER_SUFFIXES = (".body", ".json", ".form", ".stream")
_FORBIDDEN_CALL_NAMES = {
    "get_db",
    "SessionLocal",
    "create_engine",
    "sessionmaker",
    "requests.get",
    "requests.post",
    "requests.patch",
    "requests.delete",
    "httpx.get",
    "httpx.post",
    "httpx.patch",
    "httpx.delete",
    "urllib.request.urlopen",
    "socket.create_connection",
}
_ALLOWED_TERMINAL_CALL = "raise_retired_mutation_route"


def _function_node(function) -> ast.FunctionDef:
    source = textwrap.dedent(inspect.getsource(function))
    module = ast.parse(source)
    function_node = next(node for node in module.body if isinstance(node, ast.FunctionDef))
    return function_node


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    return ""


def _body_calls(function) -> tuple[str, ...]:
    function_node = _function_node(function)
    calls: list[str] = []
    for body_node in function_node.body:
        for node in ast.walk(body_node):
            if isinstance(node, ast.Call):
                calls.append(_call_name(node.func))
    return tuple(calls)


def _function_parameters(function) -> Iterable[inspect.Parameter]:
    return inspect.signature(function).parameters.values()


def _local_wrapper_functions(module_name: str) -> dict[str, object]:
    module = importlib.import_module(module_name)
    wrappers = {}
    for name, value in inspect.getmembers(module, inspect.isfunction):
        if getattr(value, "__module__", None) == module_name and name.startswith("_raise_"):
            wrappers[name] = value
    return wrappers


def _assert_no_forbidden_signature(function, route_id: str) -> None:
    for parameter in _function_parameters(function):
        annotation_name = getattr(parameter.annotation, "__name__", "")
        assert annotation_name != "Request", route_id


def _assert_no_forbidden_calls(function, route_id: str, seen: set[object] | None = None) -> None:
    seen = set() if seen is None else seen
    if function in seen:
        return
    seen.add(function)

    wrappers = _local_wrapper_functions(function.__module__)
    for call_name in _body_calls(function):
        assert not call_name.endswith(_BODY_READER_SUFFIXES), f"{route_id}: {call_name}"
        assert call_name not in _FORBIDDEN_CALL_NAMES, f"{route_id}: {call_name}"
        assert not call_name.startswith("stripe."), f"{route_id}: {call_name}"
        assert not call_name.endswith(".connect"), f"{route_id}: {call_name}"
        if call_name in wrappers:
            _assert_no_forbidden_calls(wrappers[call_name], route_id, seen)
            continue
        assert call_name == _ALLOWED_TERMINAL_CALL, f"{route_id}: unexpected call {call_name}"


def _terminates_in_shared_retired_helper(function, seen: set[object] | None = None) -> bool:
    seen = set() if seen is None else seen
    if function in seen:
        return False
    seen.add(function)

    wrappers = _local_wrapper_functions(function.__module__)
    for call_name in _body_calls(function):
        if call_name == _ALLOWED_TERMINAL_CALL:
            return True
        if call_name in wrappers and _terminates_in_shared_retired_helper(wrappers[call_name], seen):
            return True
    return False


@pytest.mark.requirement("WS02-04B2A2B1-R1", "WS02-04B2A2B1-R2")
def test_retired_handlers_have_no_body_db_provider_or_mutation_service_calls() -> None:
    for retired_route in RETIRED_MUTATION_ROUTES:
        route = route_by_method_path(retired_route.method, retired_route.path)

        _assert_no_forbidden_signature(route.endpoint, retired_route.id)
        _assert_no_forbidden_calls(route.endpoint, retired_route.id)


@pytest.mark.requirement("WS02-04B2A2B1-R1", "WS02-04B2A2B1-R2")
def test_retired_handlers_terminate_in_shared_retired_route_mechanism() -> None:
    for retired_route in RETIRED_MUTATION_ROUTES:
        route = route_by_method_path(retired_route.method, retired_route.path)

        assert _terminates_in_shared_retired_helper(route.endpoint), retired_route.id
