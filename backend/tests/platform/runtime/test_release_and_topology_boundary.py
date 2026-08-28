from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import textwrap
from pathlib import Path
from typing import Mapping

import pytest

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SYNTHETIC_DATABASE_URL = "postgresql+psycopg://127.0.0.1:5432/pickup_lane_test_db"
_BASE_RELEASE_ENV = {
    "APP_ENV": "test",
    "DATABASE_URL": _SYNTHETIC_DATABASE_URL,
    "INBOX_TOKEN_SECRET": "synthetic-independent-runtime-token",
    "ALLOWED_HOSTS": "testserver,localhost,127.0.0.1",
    "CORS_ALLOWED_ORIGINS": "http://testserver",
    "ENABLE_API_DOCS": "false",
    "ENABLE_DB_HEALTH": "false",
    "ENABLE_STRIPE_PAYMENTS": "false",
}
_RELEASE_ENV_NAMES = (
    "PICKUP_LANE_RELEASE",
    "RELEASE_IDENTITY",
    "SOURCE_REVISION",
    "GITHUB_SHA",
    "RENDER_GIT_COMMIT",
    "VERCEL_GIT_COMMIT_SHA",
)
_RUNTIME_MANIFEST_EXACT_NAMES = frozenset(
    {
        "app.json",
        "fly.toml",
        "gunicorn.conf.py",
        "heroku.yml",
        "nixpacks.toml",
        "railway.json",
        "render.yaml",
        "render.yml",
        "runtime.txt",
        "uvicorn.conf.py",
    }
)
_POOL_BUDGET_ENV_NAMES = frozenset(
    {
        "DATABASE_MAX_OVERFLOW",
        "DATABASE_POOL_SIZE",
        "SQLALCHEMY_MAX_OVERFLOW",
        "SQLALCHEMY_POOL_SIZE",
    }
)
_WORKER_SCHEDULER_CALLS = frozenset(
    {
        "ArqRedis",
        "AsyncIOScheduler",
        "BackgroundScheduler",
        "BlockingScheduler",
        "Celery",
        "CronScheduler",
        "Huey",
        "RedisHuey",
        "Scheduler",
        "Worker",
    }
)
_SOURCE_EXCLUDED_PARTS = frozenset(
    {
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "alembic",
        "generated",
        "legacy",
        "site-packages",
        "tests",
    }
)
_COMPOSE_FILE_RE = re.compile(r"(?:docker-)?compose(?:[-.][a-z0-9_-]+)?\.ya?ml$")
_KUBERNETES_WORKLOAD_RE = re.compile(
    r"(?ms)^\s*apiVersion\s*:\s*.+?^\s*kind\s*:\s*(Deployment|StatefulSet|DaemonSet|Job|CronJob)\s*$"
)
_TOPOLOGY_VALUE_PATTERNS = (
    ("WEB_CONCURRENCY", re.compile(r"\bWEB_CONCURRENCY\b\s*(?:[:=]|=)\s*['\"]?\d+\b")),
    ("UVICORN_WORKERS", re.compile(r"\bUVICORN_WORKERS\b\s*(?:[:=]|=)\s*['\"]?\d+\b")),
    ("GUNICORN_WORKERS", re.compile(r"\bGUNICORN_WORKERS\b\s*(?:[:=]|=)\s*['\"]?\d+\b")),
    ("process_count", re.compile(r"\b(?:process_count|processCount|processes)\b\s*[:=]\s*['\"]?\d+\b")),
    ("worker_count", re.compile(r"\b(?:worker_count|workerCount|workers)\b\s*[:=]\s*['\"]?\d+\b")),
    ("instance_count", re.compile(r"\b(?:instance_count|instanceCount|instances)\b\s*[:=]\s*['\"]?\d+\b")),
    ("replicas", re.compile(r"\b(?:replicas|minReplicas|maxReplicas|replicaCount)\b\s*:\s*\d+\b")),
    ("workers flag", re.compile(r"(?:--workers(?:=|\s+|[\"']?\s*,\s*[\"']?)|\s-w\s*)\d+\b")),
    ("worker concurrency", re.compile(r"\b(?:worker_concurrency|workerConcurrency|concurrency)\b\s*[:=]\s*['\"]?\d+\b")),
)
_WORKER_SCHEDULER_COMMAND_PATTERNS = (
    ("celery worker", re.compile(r"\bcelery\b[^\n]*(?:\bworker\b|\bbeat\b)")),
    ("rq worker", re.compile(r"\brq\b[^\n]*(?:\bworker\b|\bscheduler\b)")),
    ("dramatiq", re.compile(r"\bdramatiq\b")),
    ("arq", re.compile(r"\barq\b")),
    ("huey", re.compile(r"\bhuey(?:_consumer)?\b")),
    ("apscheduler", re.compile(r"\bapscheduler\b|\bAPScheduler\b")),
)


def _settings_env(**overrides: str | None) -> dict[str, str]:
    env = dict(_BASE_RELEASE_ENV)
    env["DATABASE_URL"] = os.environ.get("DATABASE_URL") or _SYNTHETIC_DATABASE_URL
    for name in _RELEASE_ENV_NAMES:
        env.pop(name, None)
    for name, value in overrides.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return env


def _build_settings(**overrides: str | None):
    from backend.settings import build_settings

    return build_settings(_settings_env(**overrides), load_dotenv_file=False)


def _assert_settings_rejected(
    *,
    mentions: tuple[str, ...],
    does_not_echo: tuple[str, ...] = (),
    **overrides: str | None,
) -> str:
    from backend.settings import SettingsError

    with pytest.raises(SettingsError) as exc_info:
        _build_settings(**overrides)

    message = str(exc_info.value)
    for fragment in mentions:
        assert fragment in message
    for private_value in does_not_echo:
        assert private_value not in message
    return message


def _import_main(monkeypatch: pytest.MonkeyPatch):
    for name, value in _settings_env(PICKUP_LANE_RELEASE="release-stability-before").items():
        monkeypatch.setenv(name, value)

    from backend.settings import reset_settings_cache

    reset_settings_cache()

    import backend.main as main_module

    return main_module


def _tracked_files() -> tuple[Path, ...]:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "-z"],
        cwd=_REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return tuple(
        _REPO_ROOT / raw_path
        for raw_path in completed.stdout.split("\0")
        if raw_path
    )


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


def _tracked_text_sources() -> dict[str, str]:
    sources: dict[str, str] = {}
    for path in _tracked_files():
        relative = path.relative_to(_REPO_ROOT).as_posix()
        if _tracked_runtime_path_ignored(relative):
            continue
        try:
            sources[relative] = path.read_text()
        except UnicodeDecodeError:
            continue
    return sources


def _tracked_runtime_path_ignored(relative_path: str) -> bool:
    parts = tuple(Path(relative_path).parts)
    return any(part in _SOURCE_EXCLUDED_PARTS for part in parts)


def _is_backend_python_source(relative_path: str) -> bool:
    parts = tuple(Path(relative_path).parts)
    return (
        len(parts) >= 2
        and parts[0] == "backend"
        and relative_path.endswith(".py")
        and not _tracked_runtime_path_ignored(relative_path)
    )


def _is_backend_runtime_config_source(relative_path: str) -> bool:
    if _tracked_runtime_path_ignored(relative_path):
        return False
    parts = tuple(Path(relative_path).parts)
    return relative_path in {
        "backend/.env.example",
        "backend/database.py",
        "backend/settings.py",
    } or (
        len(parts) >= 2
        and parts[0] == "backend"
        and parts[1] in {"config", "deploy", "deployment", "infra", "infrastructure", "runtime"}
    )


def _classify_backend_runtime_artifact(relative_path: str, source: str) -> str | None:
    parts = tuple(part.lower() for part in Path(relative_path).parts)
    if not parts or parts[0] == "frontend" or _tracked_runtime_path_ignored(relative_path):
        return None

    name = parts[-1]
    suffix = Path(relative_path).suffix.lower()
    if name == "vercel.json":
        return None
    if name in _RUNTIME_MANIFEST_EXACT_NAMES and (
        name != "app.json" or _app_json_is_runtime_config(source)
    ):
        return "runtime manifest"
    if name == "procfile" or name.startswith("procfile."):
        return "process manifest"
    if name == "dockerfile" or name.startswith("dockerfile."):
        return "container manifest"
    if _COMPOSE_FILE_RE.fullmatch(name):
        return "compose manifest"
    if name.endswith(".service"):
        return "systemd service"
    if name in {"supervisor.conf", "supervisord.conf"} or name.startswith("supervisord."):
        return "process supervisor config"
    if suffix in {".yaml", ".yml"} and _looks_like_backend_kubernetes_workload(
        parts,
        source,
    ):
        return "kubernetes workload"
    if suffix in {".yaml", ".yml"} and _looks_like_backend_helm_template(parts, source):
        return "helm workload template"
    if _is_recognized_backend_runtime_path(parts) and suffix in {
        ".json",
        ".toml",
        ".yaml",
        ".yml",
    } and _looks_like_machine_runtime_config(source):
        return "backend runtime config"
    return None


def _app_json_is_runtime_config(source: str) -> bool:
    try:
        parsed = json.loads(source)
    except json.JSONDecodeError:
        return False
    return isinstance(parsed, dict) and bool(
        {"buildpacks", "env", "formation", "scripts", "stack"} & set(parsed)
    )


def _looks_like_backend_kubernetes_workload(parts: tuple[str, ...], source: str) -> bool:
    path_text = "/".join(parts)
    if "backend" not in path_text and "api" not in parts:
        return False
    if not ({"k8s", "kubernetes", "deploy", "deployment", "infra", "infrastructure"} & set(parts)):
        return False
    return bool(_KUBERNETES_WORKLOAD_RE.search(source))


def _looks_like_backend_helm_template(parts: tuple[str, ...], source: str) -> bool:
    if "frontend" in parts:
        return False
    if not ({"helm", "charts"} & set(parts)) or "templates" not in parts:
        return False
    return "backend" in "/".join(parts) and bool(_KUBERNETES_WORKLOAD_RE.search(source))


def _is_recognized_backend_runtime_path(parts: tuple[str, ...]) -> bool:
    return len(parts) >= 2 and parts[0] == "backend" and parts[1] in {
        "deploy",
        "deployment",
        "infra",
        "infrastructure",
        "runtime",
    }


def _looks_like_machine_runtime_config(source: str) -> bool:
    return (
        bool(_KUBERNETES_WORKLOAD_RE.search(source))
        or any(pattern.search(source) for _, pattern in _TOPOLOGY_VALUE_PATTERNS)
        or any(pattern.search(source) for _, pattern in _WORKER_SCHEDULER_COMMAND_PATTERNS)
        or bool(re.search(r"\b(?:command|cmd|envVars|image|services|startCommand)\b\s*:", source))
    )


def _imported_create_engine_aliases(tree: ast.Module) -> tuple[set[str], set[str]]:
    direct_names: set[str] = set()
    module_names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module in {"sqlalchemy", "sqlalchemy.engine"}:
            for alias in node.names:
                if alias.name == "create_engine":
                    direct_names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "sqlalchemy":
                    module_names.add(alias.asname or "sqlalchemy")
    return direct_names, module_names


def _is_create_engine_call(
    node: ast.AST,
    *,
    direct_names: set[str],
    module_names: set[str],
) -> bool:
    if not isinstance(node, ast.Call):
        return False
    call_name = _call_name(node.func)
    if call_name in direct_names:
        return True
    parts = call_name.split(".")
    return len(parts) >= 2 and parts[0] in module_names and parts[-1] == "create_engine"


def _python_source_findings(relative_path: str, source: str) -> dict[str, list[str]]:
    findings = {
        "worker_scheduler_config": [],
        "topology_values": [],
        "pool_budget_values": [],
    }
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = _call_name(node.func)
            terminal_name = call_name.split(".")[-1]
            if terminal_name in _WORKER_SCHEDULER_CALLS:
                findings["worker_scheduler_config"].append(
                    f"{relative_path}:python call {terminal_name}"
                )
            if terminal_name == "run" and call_name.split(".")[0] in {"uvicorn", "gunicorn"}:
                if any(keyword.arg == "workers" for keyword in node.keywords):
                    findings["topology_values"].append(f"{relative_path}:workers keyword")
    findings["pool_budget_values"].extend(
        f"{relative_path}:{name}"
        for name in sorted(_POOL_BUDGET_ENV_NAMES)
        if re.search(rf"\b{name}\b", source)
    )
    return findings


def _text_machine_config_findings(relative_path: str, source: str) -> dict[str, list[str]]:
    findings = {
        "worker_scheduler_config": [],
        "topology_values": [],
        "pool_budget_values": [],
    }
    for name, pattern in _WORKER_SCHEDULER_COMMAND_PATTERNS:
        if pattern.search(source):
            findings["worker_scheduler_config"].append(f"{relative_path}:{name}")
    for name, pattern in _TOPOLOGY_VALUE_PATTERNS:
        if pattern.search(source):
            findings["topology_values"].append(f"{relative_path}:{name}")
    findings["pool_budget_values"].extend(
        f"{relative_path}:{name}"
        for name in sorted(_POOL_BUDGET_ENV_NAMES)
        if re.search(rf"\b{name}\b", source)
    )
    return findings


def _runtime_topology_findings_from_sources(
    sources: Mapping[str, str],
) -> dict[str, list[str]]:
    findings: dict[str, list[str]] = {
        "deployment_artifacts": [],
        "worker_scheduler_config": [],
        "topology_values": [],
        "pool_budget_values": [],
    }
    for relative_path, source in sorted(sources.items()):
        if _tracked_runtime_path_ignored(relative_path):
            continue
        artifact_kind = _classify_backend_runtime_artifact(relative_path, source)
        if artifact_kind is not None:
            findings["deployment_artifacts"].append(f"{relative_path}:{artifact_kind}")
            text_findings = _text_machine_config_findings(relative_path, source)
            for key, values in text_findings.items():
                findings[key].extend(values)
        if _is_backend_runtime_config_source(relative_path):
            text_findings = _text_machine_config_findings(relative_path, source)
            for key, values in text_findings.items():
                findings[key].extend(values)
        if _is_backend_python_source(relative_path):
            source_findings = _python_source_findings(relative_path, source)
            for key, values in source_findings.items():
                findings[key].extend(values)
    for key, values in findings.items():
        findings[key] = sorted(set(values))
    return findings


def _runtime_topology_findings() -> dict[str, list[str]]:
    return _runtime_topology_findings_from_sources(_tracked_text_sources())


@pytest.mark.requirement("WS02-02-R7")
def test_release_identity_uses_safe_fallback_when_metadata_is_absent() -> None:
    from backend.settings import DEFAULT_RELEASE_IDENTITY

    settings = _build_settings()

    assert settings.release_identity == DEFAULT_RELEASE_IDENTITY


@pytest.mark.requirement("WS02-02-R7")
def test_safe_generic_release_label_is_accepted() -> None:
    settings = _build_settings(PICKUP_LANE_RELEASE="release-2026-08-12")

    assert settings.release_identity == "release-2026-08-12"


@pytest.mark.requirement("WS02-02-R7")
@pytest.mark.parametrize(
    ("env_name", "raw_revision", "expected"),
    [
        ("SOURCE_REVISION", "A" * 40, "a" * 40),
        ("GITHUB_SHA", "B" * 64, "b" * 64),
    ],
)
def test_full_source_revision_values_are_accepted_and_normalized(
    env_name: str,
    raw_revision: str,
    expected: str,
) -> None:
    settings = _build_settings(**{env_name: raw_revision})

    assert settings.release_identity == expected


@pytest.mark.requirement("WS02-02-R7")
def test_short_source_revision_is_rejected_without_echoing_value() -> None:
    short_revision = "abc1234"

    _assert_settings_rejected(
        SOURCE_REVISION=short_revision,
        mentions=("SOURCE_REVISION", "full Git commit SHA"),
        does_not_echo=(short_revision,),
    )


@pytest.mark.requirement("WS02-02-R7")
def test_blank_release_label_is_ignored_but_whitespace_padded_label_is_rejected() -> None:
    from backend.settings import DEFAULT_RELEASE_IDENTITY

    blank_settings = _build_settings(PICKUP_LANE_RELEASE="")

    assert blank_settings.release_identity == DEFAULT_RELEASE_IDENTITY

    _assert_settings_rejected(
        PICKUP_LANE_RELEASE=" release-with-padding ",
        mentions=("PICKUP_LANE_RELEASE", "whitespace"),
        does_not_echo=("release-with-padding",),
    )


@pytest.mark.requirement("WS02-02-R7")
@pytest.mark.parametrize(
    ("value", "mentions"),
    [
        ("https://release.example.invalid/build", ("PICKUP_LANE_RELEASE",)),
        ("folder/release-artifact", ("PICKUP_LANE_RELEASE", "path-like")),
        ("sk_test_syntheticReleaseSecret", ("PICKUP_LANE_RELEASE", "sensitive")),
    ],
)
def test_unsafe_release_labels_are_rejected_without_unsafe_echo(
    value: str,
    mentions: tuple[str, ...],
) -> None:
    _assert_settings_rejected(
        PICKUP_LANE_RELEASE=value,
        mentions=mentions,
        does_not_echo=(value,),
    )


@pytest.mark.requirement("WS02-02-R7")
def test_health_response_exposes_only_captured_concise_release_identity(monkeypatch) -> None:
    main_module = _import_main(monkeypatch)

    def ready_probe() -> bool:
        return True

    monkeypatch.setattr(main_module, "check_database_connection", ready_probe)

    from fastapi.testclient import TestClient

    app = main_module.create_app(_build_settings(PICKUP_LANE_RELEASE="release-visible-safe"))
    with TestClient(app) as client:
        live_response = client.get("/live")
        ready_response = client.get("/ready")

    assert live_response.json() == {"status": "live", "release": "release-visible-safe"}
    assert ready_response.json() == {"status": "ready", "release": "release-visible-safe"}
    assert set(live_response.json()) == {"status", "release"}
    assert set(ready_response.json()) == {"status", "release"}
    for response in (live_response, ready_response):
        body = response.text
        for forbidden_fragment in (
            "DATABASE_URL",
            "INBOX_TOKEN_SECRET",
            "FIREBASE",
            "STRIPE",
            "R2_",
            "testserver",
            "pickup_lane_test_db",
        ):
            assert forbidden_fragment not in body


@pytest.mark.requirement("WS02-02-R7")
def test_app_release_identity_is_stable_after_ambient_environment_mutation(
    monkeypatch,
) -> None:
    main_module = _import_main(monkeypatch)

    def ready_probe() -> bool:
        return True

    monkeypatch.setattr(main_module, "check_database_connection", ready_probe)

    from fastapi.testclient import TestClient

    app = main_module.create_app(_build_settings(PICKUP_LANE_RELEASE="release-captured"))
    monkeypatch.setenv("PICKUP_LANE_RELEASE", "release-mutated-after-construction")
    monkeypatch.setenv("SOURCE_REVISION", "C" * 40)

    with TestClient(app) as client:
        live_response = client.get("/live")
        ready_response = client.get("/ready")

    assert live_response.json()["release"] == "release-captured"
    assert ready_response.json()["release"] == "release-captured"


@pytest.mark.requirement("WS02-02-R8")
def test_no_tracked_backend_runtime_manifest_defines_production_topology() -> None:
    findings = _runtime_topology_findings()

    assert findings["deployment_artifacts"] == []


@pytest.mark.requirement("WS02-02-R8")
def test_backend_source_has_no_worker_or_scheduler_runtime_configuration() -> None:
    findings = _runtime_topology_findings()

    assert findings["worker_scheduler_config"] == []


@pytest.mark.requirement("WS02-02-R8")
def test_ws05_01a_portable_worker_command_is_not_final_runtime_topology() -> None:
    command_path = _REPO_ROOT / "backend" / "scripts" / "durable_worker.py"
    source = command_path.read_text()

    assert "def main(" in source
    assert "python -m backend.scripts.durable_worker" in source
    assert "Celery" not in source
    assert "rq worker" not in source
    assert "Redis" not in source
    assert "--workers" not in source
    assert "autoscaling" not in source.lower()


@pytest.mark.requirement("WS02-02-R8")
def test_no_approved_numeric_runtime_topology_or_pool_budget_is_tracked() -> None:
    findings = _runtime_topology_findings()

    assert findings["topology_values"] == []
    assert findings["pool_budget_values"] == []


@pytest.mark.requirement("WS02-02-R8")
def test_ws02_02_metadata_keeps_deployment_runtime_configuration_deferred() -> None:
    declaration_path = _REPO_ROOT / "backend" / "tests" / "support" / "requirements" / "ws02_02.json"
    raw = json.loads(declaration_path.read_text())
    declarations = {entry["id"]: entry for entry in raw["requirements"]}

    assert declarations["WS02-02-R8"] == {
        "id": "WS02-02-R8",
        "owning_pass": "WS02-02",
        "source_controls": ["API-M03", "OPS-001", "DBP-01", "FDN-04"],
        "state": "required",
        "scope": "platform/runtime",
    }
    r10 = declarations["WS02-02-R10"]
    assert r10["state"] == "deferred"
    assert r10["scope"] == "planning"
    assert isinstance(r10["reason"], str) and r10["reason"].strip()
    for unsafe_fragment in ("postgresql://", "postgresql+", "Bearer ", "sk_", "whsec_", "/Users/"):
        assert unsafe_fragment not in r10["reason"]


@pytest.mark.requirement("WS02-02-R8")
def test_runtime_classifier_detects_common_backend_deployment_artifacts() -> None:
    sources = {
        "deploy/render.yaml": "services:\n  - type: web\n    name: pickup-lane-backend\n",
        "backend/Procfile.backend": "web: gunicorn backend.main:app -w 4\n",
        "backend/Dockerfile.production": (
            'FROM python:3.12\nCMD ["uvicorn", "backend.main:app", "--workers", "2"]\n'
        ),
        "infra/kubernetes/backend-deployment.yaml": textwrap.dedent(
            """
            apiVersion: apps/v1
            kind: Deployment
            metadata:
              name: pickup-lane-backend
            spec:
              replicas: 2
            """
        ),
    }

    findings = _runtime_topology_findings_from_sources(sources)

    assert findings["deployment_artifacts"] == [
        "backend/Dockerfile.production:container manifest",
        "backend/Procfile.backend:process manifest",
        "deploy/render.yaml:runtime manifest",
        "infra/kubernetes/backend-deployment.yaml:kubernetes workload",
    ]
    assert "backend/Dockerfile.production:workers flag" in findings["topology_values"]
    assert "backend/Procfile.backend:workers flag" in findings["topology_values"]
    assert "infra/kubernetes/backend-deployment.yaml:replicas" in findings["topology_values"]


@pytest.mark.requirement("WS02-02-R8")
def test_runtime_classifier_detects_worker_scheduler_and_runtime_env_config() -> None:
    sources = {
        "backend/.env.example": "WEB_CONCURRENCY=2\n",
        "backend/worker.py": "from celery import Celery\ncelery_app = Celery('pickup')\n",
        "backend/scheduler.py": textwrap.dedent(
            """
            from apscheduler.schedulers.background import BackgroundScheduler

            scheduler = BackgroundScheduler()
            scheduler.start()
            """
        ),
        "backend/Procfile": "worker: rq worker default\nscheduler: celery -A backend.worker beat\n",
    }

    findings = _runtime_topology_findings_from_sources(sources)

    assert findings["deployment_artifacts"] == ["backend/Procfile:process manifest"]
    assert findings["worker_scheduler_config"] == [
        "backend/Procfile:celery worker",
        "backend/Procfile:rq worker",
        "backend/scheduler.py:python call BackgroundScheduler",
        "backend/worker.py:python call Celery",
    ]
    assert findings["topology_values"] == ["backend/.env.example:WEB_CONCURRENCY"]


@pytest.mark.requirement("WS02-02-R8")
def test_pool_budget_detector_ignores_application_pool_settings() -> None:
    sources = {
        "backend/database.py": textwrap.dedent(
            """
            from sqlalchemy import create_engine as make_engine
            import sqlalchemy as sa

            engine = make_engine("postgresql://synthetic", pool_size=5, max_overflow=2)
            replica_engine = sa.create_engine("postgresql://synthetic", pool_size=3)
            """
        ),
        "backend/settings.py": "BACKEND_ENVIRONMENT_VARIABLES = {'DB_POOL_SIZE', 'DATABASE_MAX_OVERFLOW'}\n",
    }

    findings = _runtime_topology_findings_from_sources(sources)

    assert findings["pool_budget_values"] == [
        "backend/settings.py:DATABASE_MAX_OVERFLOW",
    ]


@pytest.mark.requirement("WS02-02-R8")
def test_runtime_classifier_ignores_frontend_prose_tests_legacy_and_placeholders() -> None:
    sources = {
        "frontend/vercel.json": '{"rewrites": [{"source": "/api/(.*)", "destination": "..."}]}',
        "docs/production-readiness/planning/runtime-notes.md": (
            "The worker process count and connection budget formula remain unresolved."
        ),
        "docs/production-readiness/governance/release-rollback-record-template.md": (
            "| Provider deployment linkage | [sanitized provider evidence reference or unavailable] |"
        ),
        "backend/tests/platform/runtime/test_fake.py": "WEB_CONCURRENCY=9\n",
        "backend/legacy/render.yaml": "services:\n  - type: web\n    envVars:\n      WEB_CONCURRENCY: 9\n",
        "backend/settings.py": (
            "DB_POOL_WAIT_TIMEOUT_SECONDS = 2\n"
            "DB_STATEMENT_TIMEOUT_MILLISECONDS = 12000\n"
            "DB_LOCK_TIMEOUT_MILLISECONDS = 2000\n"
        ),
        "backend/runtime/placeholders.yml": "replicas: TBD\nWEB_CONCURRENCY: unknown\n",
    }

    findings = _runtime_topology_findings_from_sources(sources)

    assert findings == {
        "deployment_artifacts": [],
        "worker_scheduler_config": [],
        "topology_values": [],
        "pool_budget_values": [],
    }
