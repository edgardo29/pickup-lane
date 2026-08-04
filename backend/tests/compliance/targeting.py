from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .report import CheckResult


@dataclass(frozen=True)
class Target:
    repo_root: Path
    tests_root: Path
    path: Path
    relative_path: Path
    scope: str
    contract_dir: Path
    files: tuple[Path, ...]
    is_legacy: bool


_BROAD_TARGETS = {
    Path("."),
    Path("backend/tests"),
    Path("pages"),
    Path("shared"),
    Path("support"),
    Path("legacy"),
}
_IGNORED_LEAF_DIR_NAMES = {"__pycache__"}


def resolve_target(argv_targets: list[str], cwd: Path | None = None) -> tuple[Target | None, CheckResult | None]:
    cwd = (cwd or Path.cwd()).resolve()
    repo_root = _find_repo_root(cwd)
    tests_root = repo_root / "backend" / "tests"
    raw_target = " ".join(argv_targets) if argv_targets else ""

    if len(argv_targets) != 1:
        result = CheckResult(target=raw_target or "<missing>", scope=None)
        result.forced_state = "USAGE_ERROR"
        result.add_issue("TGT001", "failure", "exactly one target path is required")
        return None, result

    target_text = argv_targets[0]
    raw_path = Path(target_text)
    if raw_path == Path("."):
        result = CheckResult(target=target_text, scope=None)
        result.forced_state = "USAGE_ERROR"
        result.add_issue("TGT003", "failure", f"broad target is not allowed: {target_text}")
        return None, result
    if raw_path.is_absolute():
        target_path = raw_path.resolve()
    else:
        candidate_from_repo = (repo_root / raw_path).resolve()
        candidate_from_tests = (tests_root / raw_path).resolve()
        target_path = candidate_from_repo if candidate_from_repo.exists() else candidate_from_tests

    try:
        relative_path = target_path.relative_to(tests_root)
    except ValueError:
        result = CheckResult(target=target_text, scope=None)
        result.forced_state = "USAGE_ERROR"
        result.add_issue("TGT002", "failure", "target must resolve under backend/tests")
        return None, result

    normalized = relative_path if str(relative_path) != "." else Path(".")
    if normalized == Path("legacy"):
        result = CheckResult(target=target_text, scope=None)
        result.forced_state = "USAGE_ERROR"
        result.add_issue("TGT008", "failure", "broad legacy target is not allowed")
        return None, result
    if normalized in _BROAD_TARGETS or Path("backend/tests") / normalized in _BROAD_TARGETS:
        result = CheckResult(target=target_text, scope=None)
        result.forced_state = "USAGE_ERROR"
        result.add_issue("TGT003", "failure", f"broad target is not allowed: {target_text}")
        return None, result

    if "support" in normalized.parts:
        result = CheckResult(target=target_text, scope=None)
        result.forced_state = "USAGE_ERROR"
        result.add_issue("TGT005", "failure", "support targets are not checkable")
        return None, result

    if not target_path.exists():
        result = CheckResult(target=target_text, scope=None)
        result.forced_state = "USAGE_ERROR"
        result.add_issue("TGT004", "failure", "target does not exist")
        return None, result

    is_legacy = normalized.parts[:1] == ("legacy",)

    if target_path.is_file():
        if target_path.name == "conftest.py" or target_path.name.startswith("_") or target_path.name in {"helpers.py", "__init__.py"}:
            result = CheckResult(target=target_text, scope=None)
            result.forced_state = "USAGE_ERROR"
            result.add_issue("TGT006", "failure", "target must be a concrete test_*.py file")
            return None, result
        if not target_path.name.startswith("test_") or target_path.suffix != ".py":
            result = CheckResult(target=target_text, scope=None)
            result.forced_state = "USAGE_ERROR"
            result.add_issue("TGT006", "failure", "target must be a concrete test_*.py file")
            return None, result
        if normalized.parts[:1] not in {("pages",), ("shared",), ("legacy",)}:
            result = CheckResult(target=target_text, scope=None)
            result.forced_state = "USAGE_ERROR"
            result.add_issue("TGT004", "failure", "test file target must belong to pages, shared, or legacy")
            return None, result
        return (
            Target(
                repo_root=repo_root,
                tests_root=tests_root,
                path=target_path,
                relative_path=normalized,
                scope="file",
                contract_dir=target_path.parent,
                files=(target_path,),
                is_legacy=is_legacy,
            ),
            None,
        )

    if target_path.is_dir():
        if normalized.parts[:1] == ("legacy",) and len(normalized.parts) == 1:
            result = CheckResult(target=target_text, scope=None)
            result.forced_state = "USAGE_ERROR"
            result.add_issue("TGT008", "failure", "broad legacy target is not allowed")
            return None, result
        if normalized.parts[:1] not in {("pages",), ("shared",), ("legacy",)}:
            result = CheckResult(target=target_text, scope=None)
            result.forced_state = "USAGE_ERROR"
            result.add_issue("TGT004", "failure", "directory target must belong to pages, shared, or legacy")
            return None, result
        if any(
            child.is_dir()
            for child in target_path.iterdir()
            if not _is_ignored_leaf_child(child)
        ):
            result = CheckResult(target=target_text, scope=None)
            result.forced_state = "USAGE_ERROR"
            result.add_issue("TGT004", "failure", "directory target must be a leaf directory")
            return None, result
        files = tuple(sorted(target_path.glob("test_*.py")))
        if not files and not (target_path / "_backend_test_contract.py").exists():
            result = CheckResult(target=target_text, scope=None)
            result.forced_state = "USAGE_ERROR"
            result.add_issue("TGT007", "failure", "directory target must contain test files or a contract")
            return None, result
        return (
            Target(
                repo_root=repo_root,
                tests_root=tests_root,
                path=target_path,
                relative_path=normalized,
                scope="directory",
                contract_dir=target_path,
                files=files,
                is_legacy=is_legacy,
            ),
            None,
        )

    result = CheckResult(target=target_text, scope=None)
    result.forced_state = "USAGE_ERROR"
    result.add_issue("TGT004", "failure", "target must be a file or directory")
    return None, result


def _find_repo_root(cwd: Path) -> Path:
    current = cwd
    for candidate in (current, *current.parents):
        if (candidate / "backend" / "tests").exists():
            return candidate
    return cwd


def _is_ignored_leaf_child(path: Path) -> bool:
    return path.name.startswith(".") or path.name in _IGNORED_LEAF_DIR_NAMES
