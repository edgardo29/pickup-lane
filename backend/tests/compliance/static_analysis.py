from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .contracts import Contract
from .report import CheckResult
from .targeting import Target


BANNED_VAGUE_TEST_NAMES = {
    "test_game",
    "test_games",
    "test_error",
    "test_endpoint_works",
    "test_works",
    "test_case_1",
    "test_case_2",
    "test_api",
}

NETWORK_NAMES = {
    "requests.get",
    "requests.post",
    "requests.put",
    "requests.patch",
    "requests.delete",
    "httpx.get",
    "httpx.post",
    "urllib.request.urlopen",
    "stripe.",
}
BUILTIN_MARKERS = {
    "parametrize",
    "skip",
    "skipif",
    "xfail",
    "usefixtures",
    "filterwarnings",
}


@dataclass(frozen=True)
class TestNode:
    ref: str
    file: Path
    name: str
    ast_node: ast.FunctionDef | ast.AsyncFunctionDef
    class_name: str | None = None


@dataclass
class StaticIndex:
    tests: dict[str, TestNode] = field(default_factory=dict)
    module_trees: dict[Path, ast.Module] = field(default_factory=dict)
    fixture_names: set[str] = field(default_factory=set)


def collect_tests(target: Target) -> tuple[StaticIndex, CheckResult]:
    result = CheckResult(target=str(target.relative_path), scope=target.scope)  # type: ignore[arg-type]
    index = StaticIndex()
    for path in target.files:
        tree = _parse_file(path, result)
        if tree is None:
            continue
        index.module_trees[path] = tree
        for test in _collect_test_nodes(path, tree):
            index.tests[test.ref] = test
    index.fixture_names.update(_collect_conftest_fixtures(target))
    return index, result


def analyze_static(target: Target, contract: Contract, index: StaticIndex) -> CheckResult:
    result = CheckResult(target=str(target.relative_path), scope=target.scope)  # type: ignore[arg-type]
    for path, tree in index.module_trees.items():
        _check_imports(path, tree, target, index, result)
        _check_markers(path, tree, target, result)
        _check_dependency_overrides(path, tree, result)
        _check_fixtures(path, tree, contract, result)
        _check_module_state(path, tree, result)
        for test in [node for node in index.tests.values() if node.file == path]:
            _check_test_name(test, result)
            _check_exceptions(test, contract, result)
            _check_time_calls(test, contract, result)
            _check_assertions(test, contract, result)
            _check_parametrize(test, contract, result)
            _check_mocks_and_network(test, contract, result)
    _check_support_helper_modules(target, index, result)
    return result


def _parse_file(path: Path, result: CheckResult) -> ast.Module | None:
    try:
        return ast.parse(path.read_text())
    except SyntaxError as exc:
        result.add_issue("STA001", "failure", f"could not parse test file: {exc}", str(path))
        return None


def _collect_test_nodes(path: Path, tree: ast.Module) -> list[TestNode]:
    tests: list[TestNode] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            tests.append(TestNode(ref=f"{path.name}::{node.name}", file=path, name=node.name, ast_node=node))
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test_"):
                    tests.append(
                        TestNode(
                            ref=f"{path.name}::{node.name}::{child.name}",
                            file=path,
                            name=child.name,
                            ast_node=child,
                            class_name=node.name,
                        )
                    )
    return tests


def _collect_conftest_fixtures(target: Target) -> set[str]:
    names: set[str] = set()
    for path in (target.tests_root / "conftest.py", target.contract_dir / "conftest.py"):
        if not path.exists():
            continue
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _has_fixture_decorator(node.decorator_list):
                names.add(node.name)
            if isinstance(node, ast.Assign) and _is_fixture_registration(node.value):
                for assignment_target in node.targets:
                    if isinstance(assignment_target, ast.Name):
                        names.add(assignment_target.id)
    return names


def _has_fixture_decorator(decorators: list[ast.expr]) -> bool:
    return any(_decorator_name(decorator).endswith("fixture") for decorator in decorators)


def _is_fixture_registration(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and _decorator_name(node.func).endswith("fixture")


def _check_imports(path: Path, tree: ast.Module, target: Target, index: StaticIndex, result: CheckResult) -> None:
    del path
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports_from_conftest = module.endswith("conftest") or (node.level > 0 and module == "conftest")
            if imports_from_conftest:
                imported = {alias.name for alias in node.names}
                fixtures = imported & index.fixture_names
                utilities = imported - fixtures
                if fixtures:
                    result.add_issue("STA003", "failure", f"imports fixture(s) from conftest.py: {sorted(fixtures)}")
                if utilities:
                    result.add_issue("STA003", "review", f"imports non-fixture utility from conftest.py; review required: {sorted(utilities)}")
            if module.endswith("helpers") or module in {"backend.tests.helpers", "tests.helpers"}:
                if target.is_legacy:
                    result.add_issue("STA004", "review", "legacy file imports backend/tests/helpers.py; confirm legacy exception")
                else:
                    result.add_issue("STA004", "failure", "new structured tests must not import backend/tests/helpers.py")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {"backend.tests.helpers", "tests.helpers"}:
                    if target.is_legacy:
                        result.add_issue("STA004", "review", "legacy file imports backend/tests/helpers.py; confirm legacy exception")
                    else:
                        result.add_issue("STA004", "failure", "new structured tests must not import backend/tests/helpers.py")


def _check_markers(path: Path, tree: ast.Module, target: Target, result: CheckResult) -> None:
    del path, target
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for decorator in node.decorator_list:
            name = _decorator_name(decorator)
            if name.endswith("pytest.mark.xfail") or name.endswith("mark.xfail"):
                strict = _keyword_value(decorator, "strict")
                if strict is not True:
                    result.add_issue("STA020", "failure", "xfail markers must be strict=True")
                reason = _keyword_value(decorator, "reason")
                if not isinstance(reason, str) or not reason.strip():
                    result.add_issue("STA020", "failure", "xfail markers require a documented reason")
            if name.endswith("pytest.mark.skip") or name.endswith("mark.skip"):
                reason = _keyword_value(decorator, "reason")
                if not isinstance(reason, str) or not reason.strip():
                    result.add_issue("STA020", "failure", "skip markers require a documented reason")
            marker = _custom_marker_name(decorator)
            if marker:
                result.add_issue("STA014", "review", f"custom pytest marker used by target: {marker}")


def _check_dependency_overrides(path: Path, tree: ast.Module, result: CheckResult) -> None:
    del path
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        assigns_override = any(_is_dependency_override_assignment(child) for child in ast.walk(node))
        if not assigns_override:
            continue
        resets_override = any(_is_dependency_override_reset(child) for child in ast.walk(node))
        if not resets_override:
            result.add_issue("STA012", "failure", "FastAPI dependency override is not reset in the same test/helper scope", node.name)


def _check_fixtures(path: Path, tree: ast.Module, contract: Contract, result: CheckResult) -> None:
    del path
    confirmed_flags = _confirmed_review_kinds(contract)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _has_fixture_decorator(node.decorator_list):
            for decorator in node.decorator_list:
                if _decorator_name(decorator).endswith("fixture"):
                    autouse = _keyword_value(decorator, "autouse")
                    scope = _keyword_value(decorator, "scope")
                    if autouse is True or (isinstance(scope, str) and scope not in {"function", ""}):
                        if "broad_fixture" not in confirmed_flags:
                            result.add_issue("STA016", "blocker", f"fixture {node.name} uses autouse or broad scope without confirmed review")
                        else:
                            result.add_issue("STA016", "review", f"fixture {node.name} broad scope/autouse was human-confirmed")


def _check_module_state(path: Path, tree: ast.Module, result: CheckResult) -> None:
    del path
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if isinstance(node.value, (ast.List, ast.Dict, ast.Set)):
                result.add_issue("STA019", "review", "module-level mutable state may affect determinism")
            if _call_name(node.value).startswith("random."):
                result.add_issue("STA019", "review", "module-level random value requires controlled uniqueness")


def _check_test_name(test: TestNode, result: CheckResult) -> None:
    if test.name in BANNED_VAGUE_TEST_NAMES:
        result.add_issue("STA002", "failure", f"vague test name: {test.ref}", test.ref)


def _check_exceptions(test: TestNode, contract: Contract, result: CheckResult) -> None:
    confirmed_broad_exception = _test_has_review_kind(contract, test.ref, "broad_exception_behavior")
    for node in ast.walk(test.ast_node):
        if isinstance(node, ast.Try):
            for handler in node.handlers:
                if handler.type is None:
                    result.add_issue("STA008", "failure", "bare except around ordinary test execution", test.ref)
                elif _exception_name(handler.type) == "Exception":
                    if confirmed_broad_exception:
                        result.add_issue("STA008", "review", "broad exception behavior was human-confirmed", test.ref)
                    else:
                        result.add_issue("STA008", "failure", "except Exception around ordinary test execution", test.ref)
        if isinstance(node, ast.Call) and _call_name(node.func).endswith("pytest.raises"):
            args = [_exception_name(arg) for arg in node.args]
            if "IntegrityError" in args and _test_declares_constraint(contract, test.ref):
                if not _test_has_call(test.ast_node, {"assert_constraint_failure"}):
                    result.add_issue("STA007", "failure", "constraint test uses generic IntegrityError without constraint evidence helper", test.ref)


def _check_time_calls(test: TestNode, contract: Contract, result: CheckResult) -> None:
    has_time_contract = _test_has_time_boundary(contract, test.ref) or _test_has_clock_control(contract, test.ref)
    for node in ast.walk(test.ast_node):
        call_name = _call_name(node)
        if call_name in {"time.sleep", "sleep"}:
            result.add_issue("STA009", "failure", "sleep() is not allowed for expiration or timing tests", test.ref)
        if call_name in {"datetime.now", "datetime.utcnow", "date.today"}:
            if not has_time_contract:
                result.add_issue("STA009", "blocker", "wall-clock call requires a time boundary or clock-control contract", test.ref)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if _looks_like_fixed_future_timestamp(node.value) and not has_time_contract:
                result.add_issue("STA010", "review", "fixed future-looking timestamp requires review", test.ref)


def _check_assertions(test: TestNode, contract: Contract, result: CheckResult) -> None:
    del contract
    assert_nodes = [node for node in ast.walk(test.ast_node) if isinstance(node, ast.Assert)]
    for assert_node in assert_nodes:
        if _is_weak_assertion(assert_node.test):
            result.add_issue("STA006", "failure", "weak assertion pattern detected", test.ref)
    if _test_looks_like_mutation(test) and assert_nodes and all(_assertion_is_status_only(node.test) for node in assert_nodes):
        result.add_issue("STA005", "review", "mutation-looking test appears to assert only response status", test.ref)


def _check_parametrize(test: TestNode, contract: Contract, result: CheckResult) -> None:
    has_parametrize = any("parametrize" in _decorator_name(decorator) for decorator in test.ast_node.decorator_list)
    if has_parametrize and not _test_has_review_kind(contract, test.ref, "parametrization_shape"):
        result.add_issue("STA015", "review", "parametrized test should have same setup/action/rule/assertion shape confirmed", test.ref)


def _check_mocks_and_network(test: TestNode, contract: Contract, result: CheckResult) -> None:
    for node in ast.walk(test.ast_node):
        call_name = _call_name(node)
        if call_name in {"monkeypatch.setattr", "mocker.patch", "patch"}:
            if not _test_has_review_kind(contract, test.ref, "mock_boundary"):
                result.add_issue("STA013", "blocker", "mock boundary requires contract review justification", test.ref)
        if any(call_name.startswith(name) for name in NETWORK_NAMES):
            if not _test_has_review_kind(contract, test.ref, "external_service_mocked"):
                result.add_issue("STA011", "failure", "direct network or external-provider call detected", test.ref)


def _check_support_helper_modules(target: Target, index: StaticIndex, result: CheckResult) -> None:
    for path in _reachable_support_modules(target, index, result):
        tree = _parse_file(path, result)
        if tree is None:
            continue
        if path.name == "factories.py":
            for node in ast.walk(tree):
                if isinstance(node, ast.Assert):
                    result.add_issue("STA017", "failure", "pure factories must not contain assertions", str(path))
                if isinstance(node, ast.Call) and _looks_like_http_call(_call_name(node)):
                    result.add_issue("STA017", "failure", "pure factories must not perform HTTP requests", str(path))
        elif path.name == "api_helpers.py":
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and "factor" in node.name:
                    result.add_issue("STA018", "failure", "API helpers must not be named factories", str(path))
                if isinstance(node, ast.Assert):
                    result.add_issue("STA018", "review", "API helper assertion requires review that it only proves setup success", str(path))


def _reachable_support_modules(target: Target, index: StaticIndex, result: CheckResult) -> list[Path]:
    support_dir = (target.tests_root / "support").resolve()
    seeds: list[Path] = []

    for tree in list(_applicable_conftest_trees(target, result)) + list(index.module_trees.values()):
        seeds.extend(_support_import_paths(tree, support_dir))

    seen: set[Path] = set()
    ordered: list[Path] = []
    queue = list(dict.fromkeys(path for path in seeds if path.exists()))
    while queue:
        path = queue.pop(0).resolve()
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
        tree = _parse_file(path, result)
        if tree is None:
            continue
        for imported in _support_import_paths(tree, support_dir):
            if imported.exists() and imported.resolve() not in seen:
                queue.append(imported)

    return ordered


def _applicable_conftest_trees(target: Target, result: CheckResult) -> list[ast.Module]:
    trees: list[ast.Module] = []
    for path in (target.tests_root / "conftest.py", target.contract_dir / "conftest.py"):
        if not path.exists():
            continue
        tree = _parse_file(path, result)
        if tree is not None:
            trees.append(tree)
    return trees


def _support_import_paths(tree: ast.Module, support_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                path = _support_module_path(alias.name, support_dir)
                if path is not None:
                    paths.append(path)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            path = _support_module_path(module, support_dir)
            if path is not None:
                paths.append(path)
            elif module in {"backend.tests.support", "tests.support"}:
                for alias in node.names:
                    child_path = support_dir / f"{alias.name}.py"
                    paths.append(child_path)
    return paths


def _support_module_path(module: str, support_dir: Path) -> Path | None:
    prefixes = ("backend.tests.support.", "tests.support.")
    for prefix in prefixes:
        if module.startswith(prefix):
            relative = module.removeprefix(prefix).split(".")
            return support_dir.joinpath(*relative).with_suffix(".py")
    return None


def _decorator_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return _call_name(node)


def _call_name(node: ast.AST | None) -> str:
    if node is None:
        return ""
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _custom_marker_name(node: ast.AST) -> str | None:
    name = _decorator_name(node)
    marker_prefixes = ("pytest.mark.", "mark.")
    for prefix in marker_prefixes:
        if name.startswith(prefix):
            marker = name.removeprefix(prefix).split(".", 1)[0]
            if marker and marker not in BUILTIN_MARKERS:
                return marker
    return None


def _keyword_value(node: ast.AST, keyword_name: str) -> Any:
    if not isinstance(node, ast.Call):
        return None
    for keyword in node.keywords:
        if keyword.arg == keyword_name:
            try:
                return ast.literal_eval(keyword.value)
            except Exception:
                return None
    return None


def _is_dependency_override_assignment(node: ast.AST) -> bool:
    if not isinstance(node, ast.Assign):
        return False
    return any(_target_mentions_dependency_overrides(target) for target in node.targets)


def _target_mentions_dependency_overrides(node: ast.AST) -> bool:
    if isinstance(node, ast.Subscript):
        return _call_name(node.value).endswith("dependency_overrides")
    return _call_name(node).endswith("dependency_overrides")


def _is_dependency_override_reset(node: ast.AST) -> bool:
    if isinstance(node, ast.Delete):
        return any(_target_mentions_dependency_overrides(target) for target in node.targets)
    if isinstance(node, ast.Call):
        name = _call_name(node)
        return name.endswith("dependency_overrides.clear") or name.endswith("dependency_overrides.pop")
    if isinstance(node, ast.Assign):
        return any(_target_mentions_dependency_overrides(target) for target in node.targets) and isinstance(node.value, ast.Dict) and not node.value.keys
    return False


def _exception_name(node: ast.AST) -> str:
    return _call_name(node)


def _test_has_call(test: ast.AST, names: set[str]) -> bool:
    return any(isinstance(node, ast.Call) and _call_name(node.func) in names for node in ast.walk(test))


def _is_weak_assertion(node: ast.AST) -> bool:
    if isinstance(node, ast.Compare):
        left = _call_name(node.left)
        if left.endswith("status_code") and any(isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)) for op in node.ops):
            return True
    if isinstance(node, ast.Call) and _call_name(node.func).endswith("json"):
        return True
    return False


def _assertion_is_status_only(node: ast.AST) -> bool:
    if isinstance(node, ast.Compare):
        return _call_name(node.left).endswith("status_code")
    return False


def _test_looks_like_mutation(test: TestNode) -> bool:
    mutating_words = {"create", "update", "delete", "remove", "leave", "join", "cancel", "post", "patch", "put"}
    return any(word in test.name for word in mutating_words)


def _looks_like_fixed_future_timestamp(value: str) -> bool:
    return any(year in value for year in ("2027", "2028", "2029", "2030", "2099"))


def _confirmed_review_kinds(contract: Contract) -> set[str]:
    flags = contract.scoped_data.get("review_flags")
    if not isinstance(flags, list):
        return set()
    return {
        str(flag.get("kind"))
        for flag in flags
        if isinstance(flag, dict) and flag.get("status") == "confirmed"
    }


def _test_has_review_kind(contract: Contract, test_ref: str, kind: str) -> bool:
    flags = contract.scoped_data.get("review_flags")
    if not isinstance(flags, list):
        return False
    return any(
        isinstance(flag, dict)
        and flag.get("kind") == kind
        and flag.get("status") == "confirmed"
        and (flag.get("test_ref") == test_ref or test_ref in flag.get("test_refs", []))
        for flag in flags
    )


def _test_declares_constraint(contract: Contract, test_ref: str) -> bool:
    constraints = contract.scoped_data.get("constraints")
    if not isinstance(constraints, list):
        return False
    return any(isinstance(entry, dict) and entry.get("test_ref") == test_ref for entry in constraints)


def _test_has_time_boundary(contract: Contract, test_ref: str) -> bool:
    boundaries = contract.scoped_data.get("time_boundaries")
    if not isinstance(boundaries, list):
        return False
    return any(
        isinstance(entry, dict) and test_ref in _contract_entry_refs(entry)
        for entry in boundaries
    )


def _test_has_clock_control(contract: Contract, test_ref: str) -> bool:
    controls = contract.scoped_data.get("clock_controls")
    if not isinstance(controls, list):
        return False
    return any(
        isinstance(entry, dict) and test_ref in _contract_entry_refs(entry)
        for entry in controls
    )


def _contract_entry_refs(entry: dict[str, Any]) -> set[str]:
    refs = set()
    if isinstance(entry.get("test_ref"), str):
        refs.add(entry["test_ref"])
    if isinstance(entry.get("test_refs"), list):
        refs.update(ref for ref in entry["test_refs"] if isinstance(ref, str))
    return refs


def _looks_like_http_call(call_name: str) -> bool:
    if any(call_name.startswith(name) for name in NETWORK_NAMES):
        return True
    return call_name.endswith((".get", ".post", ".put", ".patch", ".delete"))
