#!/usr/bin/env python3
from __future__ import annotations

import ast
import configparser
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


TESTS_ROOT = Path(__file__).resolve().parent
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

from support.traceability import validate_traceability_manifest_path


BUILTIN_MARKERS = {
    "filterwarnings",
    "parametrize",
    "skip",
    "skipif",
    "usefixtures",
    "xfail",
}
RETAINED_MARKERS = {
    "db",
    "concurrency",
    "migration",
    "provider_integration",
    "slow",
    "no_db_cleanup",
}
OWNERSHIP_MARKERS = {
    "admin",
    "auth",
    "bookings",
    "games",
    "moderation",
    "pages",
    "payments",
    "shared",
    "users",
}
MANIFEST_NAMES = {"testing_manifest.yaml", "testing_manifest.yml"}


Severity = Literal["failure", "review", "info"]
State = Literal["PASS", "FAIL", "USAGE_ERROR", "INTERNAL_ERROR"]


@dataclass(frozen=True)
class Issue:
    rule_id: str
    severity: Severity
    message: str
    location: str | None = None


@dataclass
class CheckResult:
    target: str
    issues: list[Issue] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)
    forced_state: State | None = None

    def add_issue(
        self,
        rule_id: str,
        severity: Severity,
        message: str,
        location: str | None = None,
    ) -> None:
        self.issues.append(Issue(rule_id, severity, message, location))

    @property
    def state(self) -> State:
        if self.forced_state is not None:
            return self.forced_state
        if any(issue.severity == "failure" for issue in self.issues):
            return "FAIL"
        return "PASS"

    @property
    def exit_code(self) -> int:
        return {
            "PASS": 0,
            "FAIL": 1,
            "USAGE_ERROR": 3,
            "INTERNAL_ERROR": 4,
        }[self.state]


@dataclass(frozen=True)
class ScanTarget:
    repo_root: Path
    tests_root: Path
    path: Path
    relative_path: Path


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        result = run_checker(argv)
    except Exception as exc:  # noqa: BLE001 - top-level guard for checker bugs.
        target = " ".join(argv) or "backend/tests"
        result = CheckResult(target=target, forced_state="INTERNAL_ERROR")
        result.add_issue("INTERNAL", "failure", f"checker internal error: {exc}")
    print(render_report(result))
    return result.exit_code


def run_checker(argv: list[str] | None = None, *, cwd: Path | None = None) -> CheckResult:
    argv = list(argv or [])
    target, usage_error = resolve_target(argv, cwd=cwd)
    if usage_error is not None:
        return usage_error
    assert target is not None

    result = CheckResult(target=str(target.relative_path))
    _check_pytest_config(target.repo_root, result)
    _check_python_files(target, result)
    _check_support_dependency_direction(target, result)
    _check_traceability(target, result)

    result.checked.extend(
        [
            "pytest strict marker registration",
            "test-file marker usage and skip/xfail policy",
            "test-support dependency direction",
            "lightweight traceability manifests where present",
        ]
    )
    return result


def resolve_target(argv: list[str], *, cwd: Path | None = None) -> tuple[ScanTarget | None, CheckResult | None]:
    cwd = (cwd or Path.cwd()).resolve()
    repo_root = _find_repo_root(cwd)
    tests_root = repo_root / "backend" / "tests"

    if any(arg in {"--runtime", "--mutations"} for arg in argv):
        result = CheckResult(target=" ".join(argv), forced_state="USAGE_ERROR")
        result.add_issue(
            "CLI001",
            "failure",
            "runtime and mutation execution were removed from the backend architecture checker",
        )
        return None, result
    if any(arg.startswith("--") for arg in argv):
        result = CheckResult(target=" ".join(argv), forced_state="USAGE_ERROR")
        result.add_issue("CLI002", "failure", f"unsupported option: {' '.join(argv)}")
        return None, result
    if len(argv) > 1:
        result = CheckResult(target=" ".join(argv), forced_state="USAGE_ERROR")
        result.add_issue("CLI003", "failure", "zero or one target path is allowed")
        return None, result

    raw = Path(argv[0]) if argv else Path("backend/tests")
    if raw.is_absolute():
        path = raw.resolve()
    else:
        from_repo = (repo_root / raw).resolve()
        from_tests = (tests_root / raw).resolve()
        path = from_repo if from_repo.exists() else from_tests

    try:
        relative_path = path.relative_to(tests_root)
    except ValueError:
        result = CheckResult(target=str(raw), forced_state="USAGE_ERROR")
        result.add_issue("TGT001", "failure", "target must resolve under backend/tests")
        return None, result

    if "__pycache__" in relative_path.parts:
        result = CheckResult(target=str(raw), forced_state="USAGE_ERROR")
        result.add_issue("TGT002", "failure", "__pycache__ targets are not checkable")
        return None, result
    if not path.exists():
        result = CheckResult(target=str(raw), forced_state="USAGE_ERROR")
        result.add_issue("TGT003", "failure", "target does not exist")
        return None, result

    return (
        ScanTarget(
            repo_root=repo_root,
            tests_root=tests_root,
            path=path,
            relative_path=relative_path if str(relative_path) != "." else Path("backend/tests"),
        ),
        None,
    )


def render_report(result: CheckResult) -> str:
    lines = [
        f"Target: {result.target}",
        f"Result: {result.state}",
        f"Exit code: {result.exit_code}",
        "Meaning: mechanical backend test architecture and safety rules only; no business coverage is validated.",
    ]

    grouped: dict[Severity, list[Issue]] = {"failure": [], "review": [], "info": []}
    for issue in result.issues:
        grouped[issue.severity].append(issue)

    for title, severity in (
        ("Failures", "failure"),
        ("Review Findings", "review"),
        ("Info", "info"),
    ):
        if not grouped[severity]:
            continue
        lines.append("")
        lines.append(f"{title}:")
        for issue in grouped[severity]:
            location = f" [{issue.location}]" if issue.location else ""
            lines.append(f"- {issue.rule_id}{location}: {issue.message}")

    lines.append("")
    lines.append("Rules checked:")
    for item in result.checked or ["None"]:
        lines.append(f"- {item}")

    return "\n".join(lines)


def _find_repo_root(cwd: Path) -> Path:
    for candidate in (cwd, *cwd.parents):
        if (candidate / "backend" / "tests").exists():
            return candidate
    return cwd


def _check_pytest_config(repo_root: Path, result: CheckResult) -> None:
    setup_cfg = repo_root / "backend" / "setup.cfg"
    if not setup_cfg.exists():
        result.add_issue("CFG001", "failure", "backend/setup.cfg is missing")
        return

    parser = configparser.ConfigParser()
    parser.read(setup_cfg)
    if "tool:pytest" not in parser:
        result.add_issue("CFG002", "failure", "backend/setup.cfg lacks [tool:pytest]")
        return

    section = parser["tool:pytest"]
    addopts = section.get("addopts", "")
    if "--strict-markers" not in addopts.split():
        result.add_issue("CFG003", "failure", "pytest addopts must include --strict-markers")

    registered = _registered_markers(section.get("markers", ""))
    missing = sorted(RETAINED_MARKERS - registered)
    if missing:
        result.add_issue("CFG004", "failure", f"missing retained marker registration: {missing}")

    extra = sorted(registered - RETAINED_MARKERS)
    if extra:
        result.add_issue("CFG005", "failure", f"unapproved backend marker registration: {extra}")

    ownership = sorted(registered & OWNERSHIP_MARKERS)
    if ownership:
        result.add_issue("CFG006", "failure", f"ownership markers are not allowed: {ownership}")


def _registered_markers(markers_text: str) -> set[str]:
    markers: set[str] = set()
    for line in markers_text.splitlines():
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue
        name = stripped.split(":", 1)[0].strip()
        if name:
            markers.add(name)
    return markers


def _check_python_files(target: ScanTarget, result: CheckResult) -> None:
    for path in _iter_python_files(target):
        try:
            tree = ast.parse(path.read_text(), filename=str(path))
        except SyntaxError as exc:
            result.add_issue("PY001", "failure", f"Python syntax error: {exc}", _location(path, target))
            continue

        file_markers: set[str] = set()
        for node in ast.walk(tree):
            marker = _marker_name(node)
            if marker is None:
                continue
            file_markers.add(marker)
            if marker in BUILTIN_MARKERS:
                continue
            location = _location(path, target, getattr(node, "lineno", None))
            if marker not in RETAINED_MARKERS:
                result.add_issue("MRK001", "failure", f"unregistered or unapproved pytest marker: {marker}", location)
            if marker in OWNERSHIP_MARKERS:
                result.add_issue("MRK002", "failure", f"ownership marker is not allowed: {marker}", location)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            marker = _marker_name(node.func)
            if marker not in {"skip", "skipif", "xfail"}:
                continue
            location = _location(path, target, getattr(node, "lineno", None))
            reason = _keyword_value(node, "reason")
            if not isinstance(reason, str) or not reason.strip():
                result.add_issue("MRK003", "failure", f"pytest.mark.{marker} requires a reason", location)
            if marker == "xfail" and _keyword_value(node, "strict") is not True:
                result.add_issue("MRK004", "failure", "pytest.mark.xfail requires strict=True", location)

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            for decorator in node.decorator_list:
                marker = _marker_name(decorator)
                if marker not in {"skip", "skipif", "xfail"} or isinstance(decorator, ast.Call):
                    continue
                location = _location(path, target, getattr(decorator, "lineno", None))
                result.add_issue("MRK003", "failure", f"pytest.mark.{marker} requires a reason", location)
                if marker == "xfail":
                    result.add_issue("MRK004", "failure", "pytest.mark.xfail requires strict=True", location)

        if "no_db_cleanup" in file_markers and file_markers & {"db", "concurrency", "migration"}:
            result.add_issue(
                "MRK005",
                "failure",
                "no_db_cleanup must not be combined with database, concurrency, or migration markers",
                _location(path, target),
            )

        if "no_db_cleanup" in file_markers:
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if any(arg.arg == "client" for arg in node.args.args):
                    result.add_issue(
                        "MRK006",
                        "failure",
                        "no_db_cleanup tests must not request the shared client fixture",
                        _location(path, target, node.lineno),
                    )


def _check_support_dependency_direction(target: ScanTarget, result: CheckResult) -> None:
    support_root = target.tests_root / "support"
    if target.path.is_file():
        paths = [target.path] if support_root in target.path.parents else []
    elif target.path == support_root or support_root in target.path.parents:
        paths = list(_iter_python_files(target))
    else:
        paths = [
            path
            for path in _iter_python_files(
                ScanTarget(
                    repo_root=target.repo_root,
                    tests_root=target.tests_root,
                    path=support_root,
                    relative_path=Path("support"),
                )
            )
        ] if support_root.exists() else []

    for path in paths:
        try:
            tree = ast.parse(path.read_text(), filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            imported = _imported_module_name(node)
            if imported is None:
                continue
            if imported.startswith(("backend.tests.pages", "backend.tests.shared", "backend.tests.legacy")):
                result.add_issue(
                    "SUP001",
                    "failure",
                    f"support code must not import from test ownership directories: {imported}",
                    _location(path, target, getattr(node, "lineno", None)),
                )
            if imported.startswith(("pages", "shared", "legacy")):
                result.add_issue(
                    "SUP001",
                    "failure",
                    f"support code must not import from test ownership directories: {imported}",
                    _location(path, target, getattr(node, "lineno", None)),
                )


def _check_traceability(target: ScanTarget, result: CheckResult) -> None:
    for manifest in _iter_named_files(target, MANIFEST_NAMES):
        validation = validate_traceability_manifest_path(manifest)
        for error in validation.errors:
            result.add_issue("TRC001", "failure", error, _location(manifest, target))
        if not (manifest.parent / "TESTING.md").exists():
            result.add_issue(
                "TRC002",
                "failure",
                "testing_manifest.yaml requires sibling TESTING.md",
                _location(manifest, target),
            )

    for testing_doc in _iter_named_files(target, {"TESTING.md"}):
        if not any((testing_doc.parent / name).exists() for name in MANIFEST_NAMES):
            result.add_issue(
                "TRC003",
                "failure",
                "TESTING.md requires sibling testing_manifest.yaml",
                _location(testing_doc, target),
            )


def _iter_python_files(target: ScanTarget) -> tuple[Path, ...]:
    if target.path.is_file():
        return (target.path,) if target.path.suffix == ".py" else ()
    return tuple(
        path
        for path in sorted(target.path.rglob("*.py"))
        if "__pycache__" not in path.parts and not _is_implicit_legacy_scan(path, target)
    )


def _iter_named_files(target: ScanTarget, names: set[str]) -> tuple[Path, ...]:
    if target.path.is_file():
        return (target.path,) if target.path.name in names else ()
    return tuple(
        path
        for path in sorted(target.path.rglob("*"))
        if path.is_file()
        and path.name in names
        and "__pycache__" not in path.parts
        and not _is_implicit_legacy_scan(path, target)
    )


def _is_implicit_legacy_scan(path: Path, target: ScanTarget) -> bool:
    relative = path.relative_to(target.tests_root)
    if target.relative_path.parts[:1] == ("legacy",):
        return False
    return relative.parts[:1] == ("legacy",)


def _marker_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        return _marker_name(node.func)
    if not isinstance(node, ast.Attribute):
        return None

    parts: list[str] = []
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)

    dotted = ".".join(reversed(parts))
    if dotted.startswith("pytest.mark."):
        return dotted.split(".")[2]
    if dotted.startswith("mark."):
        return dotted.split(".")[1]
    return None


def _keyword_value(node: ast.Call, name: str) -> object:
    for keyword in node.keywords:
        if keyword.arg != name:
            continue
        if isinstance(keyword.value, ast.Constant):
            return keyword.value.value
    return None


def _imported_module_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Import):
        return node.names[0].name if node.names else None
    if isinstance(node, ast.ImportFrom):
        module = node.module or ""
        if node.level >= 2:
            return module
        return module
    return None


def _location(path: Path, target: ScanTarget, line_number: int | None = None) -> str:
    relative = path.relative_to(target.tests_root)
    suffix = f":{line_number}" if line_number else ""
    return f"{relative}{suffix}"


if __name__ == "__main__":
    raise SystemExit(main())
