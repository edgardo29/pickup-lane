from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from .report import CheckResult, Scope


TRUSTED_ROOTS = frozenset(
    {
        "domains",
        "workflows",
        "platform",
        "migrations",
        "provider_contract",
        "checker",
    }
)
UNTRUSTED_APPLICATION_ROOTS = frozenset({"pages", "shared"})
HISTORICAL_ROOTS = frozenset({"legacy"})
SUPPORT_ROOTS = frozenset({"support", "compliance"})
IGNORED_DIR_NAMES = frozenset({"__pycache__", ".pytest_cache"})


@dataclass(frozen=True)
class Target:
    repo_root: Path
    tests_root: Path
    path: Path
    relative_path: Path
    scope: Scope
    files: tuple[Path, ...]

    @property
    def display(self) -> str:
        return str(self.relative_path)


def resolve_target(
    *,
    scope: Scope,
    target_text: str | None,
    cwd: Path | None = None,
) -> tuple[Target | None, CheckResult | None]:
    repo_root = _find_repo_root((cwd or Path.cwd()).resolve())
    tests_root = repo_root / "backend" / "tests"

    if scope == "suite" and not target_text:
        requested_path = tests_root
        target_path = tests_root
    elif not target_text:
        return None, _usage(target_text or "<missing>", scope, "target path is required", "TGT001")
    else:
        raw = Path(target_text)
        requested_path = raw if raw.is_absolute() else repo_root / raw
        target_path = requested_path.resolve()
        if not _is_under(target_path, tests_root):
            requested_path = tests_root / raw
            target_path = requested_path.resolve()

    if not _is_under(target_path, tests_root):
        return None, _usage(target_text or str(target_path), scope, "target must resolve under backend/tests", "TGT002")

    if _path_has_symlink_component(requested_path, tests_root):
        return None, _usage(
            target_text or str(target_path),
            scope,
            "trusted test targets must not use symlinked path components",
            "TGT013",
        )

    relative_path = target_path.relative_to(tests_root)
    normalized = relative_path if str(relative_path) != "." else Path(".")
    parts = normalized.parts

    if any(part in HISTORICAL_ROOTS for part in parts):
        return None, _usage(
            target_text or str(normalized),
            scope,
            "historical/out-of-scope tests are excluded from trusted discovery",
            "TGT003",
        )
    if parts and parts[0] in UNTRUSTED_APPLICATION_ROOTS:
        return None, _usage(
            target_text or str(normalized),
            scope,
            "existing backend application tests are not trusted production-readiness evidence",
            "TGT004",
        )
    if parts and parts[0] in SUPPORT_ROOTS:
        return None, _usage(
            target_text or str(normalized),
            scope,
            "support and checker implementation modules are not direct compliance targets",
            "TGT005",
        )

    if scope == "suite":
        if target_path != tests_root:
            return None, _usage(
                target_text or str(normalized),
                scope,
                "suite scope target must be backend/tests or omitted",
                "TGT006",
            )
        files = trusted_test_files(tests_root)
        if not files:
            return None, _usage("backend/tests", scope, "suite scope found no trusted test files", "TGT007")
        return Target(repo_root, tests_root, tests_root, Path("."), scope, files), None

    if not target_path.exists():
        return None, _usage(target_text or str(normalized), scope, "target does not exist", "TGT008")

    if scope == "file":
        if not target_path.is_file() or not _is_test_file(target_path):
            return None, _usage(
                target_text or str(normalized),
                scope,
                "file scope target must be one trusted test_*.py file",
                "TGT009",
            )
        if not _trusted_test_file(requested_path, tests_root):
            return None, _usage(
                target_text or str(normalized),
                scope,
                "file scope target must belong to a trusted testing root",
                "TGT010",
            )
        return Target(repo_root, tests_root, target_path, normalized, scope, (target_path,)), None

    if scope == "domain":
        if not target_path.is_dir():
            return None, _usage(target_text or str(normalized), scope, "domain scope target must be a directory", "TGT011")
        if not parts or parts[0] not in TRUSTED_ROOTS:
            return None, _usage(
                target_text or str(normalized),
                scope,
                "domain scope target must belong to a trusted testing root",
                "TGT010",
            )
        files = tuple(
            sorted(
                path
                for path in target_path.rglob("test_*.py")
                if _trusted_test_file(path, tests_root)
            )
        )
        if not files:
            return None, _usage(target_text or str(normalized), scope, "domain scope found no trusted test files", "TGT007")
        return Target(repo_root, tests_root, target_path, normalized, scope, files), None

    return None, _usage(target_text or "<missing>", scope, f"unsupported scope: {scope}", "TGT012")


def trusted_test_files(tests_root: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for root_name in sorted(TRUSTED_ROOTS):
        root = tests_root / root_name
        if not root.exists() or _path_has_symlink_component(root, tests_root):
            continue
        files.extend(
            path
            for path in root.rglob("test_*.py")
            if _trusted_test_file(path, tests_root)
        )
    return tuple(sorted(files))


def _find_repo_root(cwd: Path) -> Path:
    for candidate in (cwd, *cwd.parents):
        if (candidate / "backend" / "tests").exists():
            return candidate
    return cwd


def _trusted_path(relative_path: Path) -> bool:
    parts = relative_path.parts
    return bool(parts) and parts[0] in TRUSTED_ROOTS and not any(part in HISTORICAL_ROOTS for part in parts)


def _trusted_test_file(path: Path, tests_root: Path) -> bool:
    if not _is_test_file(path) or _is_ignored_path(path):
        return False
    if _path_has_symlink_component(path, tests_root):
        return False
    resolved = path.resolve()
    if not _is_under(resolved, tests_root):
        return False
    return _trusted_path(resolved.relative_to(tests_root))


def _path_has_symlink_component(path: Path, tests_root: Path) -> bool:
    absolute_path = Path(os.path.abspath(path))
    absolute_root = Path(os.path.abspath(tests_root))
    try:
        relative_path = absolute_path.relative_to(absolute_root)
    except ValueError:
        return True
    current = absolute_root
    for part in relative_path.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _is_ignored_path(path: Path) -> bool:
    return any(part in IGNORED_DIR_NAMES for part in path.parts)


def _is_test_file(path: Path) -> bool:
    return path.name.startswith("test_") and path.suffix == ".py"


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _usage(target: str, scope: Scope | None, message: str, rule_id: str) -> CheckResult:
    result = CheckResult(target=target, scope=scope, forced_state="USAGE_ERROR")
    result.add_issue(rule_id, "failure", message)
    return result
