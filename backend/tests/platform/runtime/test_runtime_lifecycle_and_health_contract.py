from __future__ import annotations

import ast
import asyncio
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, Mapping

import pytest

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BACKEND_ROOT = _REPO_ROOT / "backend"
_SYNTHETIC_DATABASE_URL = "postgresql+psycopg://127.0.0.1:5432/pickup_lane_test_db"
_RUNTIME_RELEASE = "runtime-test-release"
_IGNORED_SOURCE_PARTS = frozenset(
    {
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "generated",
        "legacy",
        "site-packages",
        "tests",
    }
)
_IGNORED_RUNTIME_DIRECTORIES = frozenset({"alembic", "scripts"})
_HEALTH_PATHS = frozenset({"/live", "/ready", "/db-health"})
_ROUTE_DECORATOR_METHODS = frozenset({"get", "post", "put", "patch", "delete", "api_route", "route"})
_ROUTE_REGISTRATION_METHODS = frozenset({"add_api_route"})
_LIFECYCLE_EVENT_NAMES = frozenset({"startup", "shutdown"})


def _active_database_url() -> str:
    return os.environ.get("DATABASE_URL") or _SYNTHETIC_DATABASE_URL


def _settings_env(**overrides: str | None) -> dict[str, str]:
    env = {
        "APP_ENV": "test",
        "DATABASE_URL": _active_database_url(),
        "INBOX_TOKEN_SECRET": "synthetic-independent-runtime-token",
        "ALLOWED_HOSTS": "testserver,localhost,127.0.0.1",
        "CORS_ALLOWED_ORIGINS": "http://testserver",
        "ENABLE_API_DOCS": "false",
        "ENABLE_DB_HEALTH": "false",
        "ENABLE_STRIPE_PAYMENTS": "false",
        "PICKUP_LANE_RELEASE": _RUNTIME_RELEASE,
    }
    for name, value in overrides.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return env


def _runtime_settings(**overrides: str | None):
    from backend.settings import build_settings

    return build_settings(_settings_env(**overrides), load_dotenv_file=False)


def _install_runtime_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    env = _settings_env()
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    from backend.settings import reset_settings_cache

    reset_settings_cache()


def _import_main(monkeypatch: pytest.MonkeyPatch):
    _install_runtime_environment(monkeypatch)
    import backend.main as main_module

    return main_module


def _install_optional_provider_sentinels(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_provider_contact(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("optional provider boundary was contacted")

    import backend.firebase_admin_client as firebase_admin_client
    import backend.services.r2_storage_service as r2_storage_service
    import backend.services.stripe_service as stripe_service

    monkeypatch.setattr(
        firebase_admin_client,
        "initialize_firebase_admin",
        fail_provider_contact,
    )
    monkeypatch.setattr(stripe_service, "get_stripe_module", fail_provider_contact)
    monkeypatch.setattr(stripe_service, "get_stripe_client_pair", fail_provider_contact)
    monkeypatch.setattr(r2_storage_service, "get_r2_client", fail_provider_contact)


def _assert_health_response(response, *, status_value: str, release: str = _RUNTIME_RELEASE) -> None:
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == {"status": status_value, "release": release}


def _runtime_relative_source_allowed(relative_path: str) -> bool:
    parts = tuple(part for part in Path(relative_path).parts if part not in {"."})
    if parts[:1] == ("backend",):
        parts = parts[1:]
    if not parts:
        return False
    if any(part in _IGNORED_SOURCE_PARTS for part in parts):
        return False
    return parts[0] not in _IGNORED_RUNTIME_DIRECTORIES


def _runtime_source_map() -> dict[str, str]:
    sources: dict[str, str] = {}
    for path in _BACKEND_ROOT.rglob("*.py"):
        relative = path.relative_to(_REPO_ROOT).as_posix()
        if _runtime_relative_source_allowed(relative):
            sources[relative] = path.read_text()
    return sources


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


def _imported_fastapi_constructors(tree: ast.Module) -> tuple[set[str], set[str]]:
    direct_names: set[str] = set()
    module_names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module in {"fastapi", "fastapi.applications"}:
            for alias in node.names:
                if alias.name == "FastAPI":
                    direct_names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "fastapi":
                    module_names.add(alias.asname or "fastapi")
    return direct_names, module_names


def _is_fastapi_constructor_call(
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
    return len(parts) >= 2 and parts[0] in module_names and parts[-1] == "FastAPI"


def _assigned_names(target: ast.AST) -> tuple[str, ...]:
    if isinstance(target, ast.Name):
        return (target.id,)
    if isinstance(target, (ast.Tuple, ast.List)):
        names: list[str] = []
        for element in target.elts:
            names.extend(_assigned_names(element))
        return tuple(names)
    return ()


def _function_body_nodes(function: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[ast.AST, ...]:
    nodes: list[ast.AST] = []

    def visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            nodes.append(child)
            visit(child)

    visit(function)
    return tuple(nodes)


def _attribute_root_name(node: ast.AST) -> str | None:
    current = node
    while isinstance(current, ast.Attribute):
        current = current.value
    return current.id if isinstance(current, ast.Name) else None


def _function_fastapi_app_names(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    direct_names: set[str],
    module_names: set[str],
) -> set[str]:
    app_names: set[str] = set()
    for node in _function_body_nodes(function):
        value: ast.AST | None = None
        targets: tuple[str, ...] = ()
        if isinstance(node, ast.Assign):
            value = node.value
            targets = tuple(name for target in node.targets for name in _assigned_names(target))
        elif isinstance(node, ast.AnnAssign):
            value = node.value
            targets = _assigned_names(node.target)
        if value is not None and _is_fastapi_constructor_call(
            value,
            direct_names=direct_names,
            module_names=module_names,
        ):
            app_names.update(targets)
    return app_names


def _function_configures_app(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    app_names: set[str],
) -> bool:
    for node in _function_body_nodes(function):
        if isinstance(node, ast.Attribute) and _attribute_root_name(node) in app_names:
            return True
    return False


def _function_returns_app(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    app_names: set[str],
) -> bool:
    for node in _function_body_nodes(function):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
            if node.value.id in app_names:
                return True
    return False


def _canonical_factory_names(
    tree: ast.Module,
    *,
    direct_names: set[str],
    module_names: set[str],
) -> set[str]:
    factory_names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        app_names = _function_fastapi_app_names(
            node,
            direct_names=direct_names,
            module_names=module_names,
        )
        if app_names and _function_configures_app(node, app_names) and _function_returns_app(node, app_names):
            factory_names.add(node.name)
    return factory_names


def _module_app_assignment_owners(
    relative: str,
    tree: ast.Module,
    factory_names: set[str],
) -> list[str]:
    owners: list[str] = []
    for node in tree.body:
        value: ast.AST | None = None
        targets: tuple[str, ...] = ()
        if isinstance(node, ast.Assign):
            value = node.value
            targets = tuple(name for target in node.targets for name in _assigned_names(target))
        elif isinstance(node, ast.AnnAssign):
            value = node.value
            targets = _assigned_names(node.target)
        if isinstance(value, ast.Call) and _call_name(value.func) in factory_names:
            owners.extend(f"{relative}:{target}" for target in targets)
    return owners


def _literal_first_arg(call: ast.Call) -> str | None:
    if not call.args:
        return None
    first_arg = call.args[0]
    return first_arg.value if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str) else None


def _literal_route_path(call: ast.AST, *, decorator: bool) -> str | None:
    if not isinstance(call, ast.Call):
        return None
    method_name = _call_name(call.func).split(".")[-1]
    if decorator and method_name not in _ROUTE_DECORATOR_METHODS:
        return None
    if not decorator and method_name not in _ROUTE_REGISTRATION_METHODS:
        return None
    return _literal_first_arg(call)


def _lifespan_reference(value: ast.AST) -> str:
    reference = _call_name(value)
    return reference or "<inline lifespan>"


def _route_and_lifecycle_findings(relative: str, tree: ast.Module) -> dict[str, list[str]]:
    findings = {
        "live_route_owners": [],
        "ready_route_owners": [],
        "db_health_route_owners": [],
        "lifespan_owners": [],
        "startup_shutdown_owners": [],
    }
    direct_names, module_names = _imported_fastapi_constructors(tree)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator_node in node.decorator_list:
                route_path = _literal_route_path(decorator_node, decorator=True)
                if route_path == "/live":
                    findings["live_route_owners"].append(f"{relative}:{route_path}")
                elif route_path == "/ready":
                    findings["ready_route_owners"].append(f"{relative}:{route_path}")
                elif route_path == "/db-health":
                    findings["db_health_route_owners"].append(f"{relative}:{route_path}")

                if isinstance(decorator_node, ast.Call):
                    method_name = _call_name(decorator_node.func).split(".")[-1]
                    event_name = _literal_first_arg(decorator_node)
                    if method_name == "on_event" and event_name in _LIFECYCLE_EVENT_NAMES:
                        findings["startup_shutdown_owners"].append(f"{relative}:{event_name}")
        if isinstance(node, ast.Call):
            route_path = _literal_route_path(node, decorator=False)
            if route_path == "/live":
                findings["live_route_owners"].append(f"{relative}:{route_path}")
            elif route_path == "/ready":
                findings["ready_route_owners"].append(f"{relative}:{route_path}")
            elif route_path == "/db-health":
                findings["db_health_route_owners"].append(f"{relative}:{route_path}")

            if _is_fastapi_constructor_call(
                node,
                direct_names=direct_names,
                module_names=module_names,
            ):
                for keyword in node.keywords:
                    if keyword.arg == "lifespan":
                        findings["lifespan_owners"].append(
                            f"{relative}:{_lifespan_reference(keyword.value)}"
                        )
            if _call_name(node.func).split(".")[-1] == "add_event_handler":
                event_name = _literal_first_arg(node)
                if event_name in _LIFECYCLE_EVENT_NAMES:
                    findings["startup_shutdown_owners"].append(f"{relative}:{event_name}")
    return findings


def _app_owner_findings_from_sources(sources: Mapping[str, str]) -> dict[str, list[str]]:
    findings: dict[str, list[str]] = {
        "fastapi_constructor_owners": [],
        "canonical_factory_owners": [],
        "module_app_owners": [],
        "live_route_owners": [],
        "ready_route_owners": [],
        "db_health_route_owners": [],
        "lifespan_owners": [],
        "startup_shutdown_owners": [],
    }
    for relative, source in sorted(sources.items()):
        if not _runtime_relative_source_allowed(relative):
            continue
        tree = ast.parse(source)
        direct_names, module_names = _imported_fastapi_constructors(tree)
        factory_names = _canonical_factory_names(
            tree,
            direct_names=direct_names,
            module_names=module_names,
        )
        for node in ast.walk(tree):
            if _is_fastapi_constructor_call(
                node,
                direct_names=direct_names,
                module_names=module_names,
            ):
                scope = "<module>"
                for candidate in tree.body:
                    if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef)) and node in ast.walk(candidate):
                        scope = candidate.name
                        break
                findings["fastapi_constructor_owners"].append(f"{relative}:{scope}")
        findings["canonical_factory_owners"].extend(f"{relative}:{name}" for name in sorted(factory_names))
        findings["module_app_owners"].extend(
            _module_app_assignment_owners(relative, tree, factory_names)
        )
        route_lifecycle = _route_and_lifecycle_findings(relative, tree)
        for key, values in route_lifecycle.items():
            findings[key].extend(values)
    for key, values in findings.items():
        findings[key] = sorted(values)
    return findings


def _app_owner_findings() -> dict[str, list[str]]:
    return _app_owner_findings_from_sources(_runtime_source_map())


@pytest.mark.requirement("WS02-02-R1")
def test_backend_main_is_the_single_canonical_app_and_health_owner(monkeypatch) -> None:
    main_module = _import_main(monkeypatch)
    app = main_module.create_app(_runtime_settings(ENABLE_DB_HEALTH="true"))
    route_paths = {getattr(route, "path", None) for route in app.routes}
    findings = _app_owner_findings()

    assert callable(main_module.create_app)
    assert main_module.app is not None
    assert getattr(main_module.app.state, "lifecycle_started") is False
    assert {"/", "/live", "/ready", "/db-health"} <= route_paths
    assert findings == {
        "fastapi_constructor_owners": ["backend/main.py:create_app"],
        "canonical_factory_owners": ["backend/main.py:create_app"],
        "module_app_owners": ["backend/main.py:app"],
        "live_route_owners": ["backend/main.py:/live"],
        "ready_route_owners": ["backend/main.py:/ready"],
        "db_health_route_owners": ["backend/main.py:/db-health"],
        "lifespan_owners": ["backend/main.py:lifespan"],
        "startup_shutdown_owners": [],
    }


@pytest.mark.requirement("WS02-02-R1")
def test_app_owner_detector_recognizes_equivalent_fastapi_ownership_forms() -> None:
    sources = {
        "backend/runtime_alias.py": textwrap.dedent(
            """
            from fastapi import FastAPI as API

            def runtime_lifespan(app):
                yield

            def ready():
                return {}

            def build_runtime():
                service = API(lifespan=runtime_lifespan)
                service.state.runtime = "synthetic"

                @service.get("/live")
                def live():
                    return {}

                service.add_api_route("/ready", ready)
                return service

            runtime_application: API = build_runtime()
            """
        ),
        "backend/runtime_module.py": textwrap.dedent(
            """
            import fastapi

            def bound_lifespan(app):
                yield

            def make_runtime():
                api = fastapi.FastAPI(lifespan=bound_lifespan)
                api.state.runtime = "synthetic"

                @api.route("/live")
                def live():
                    return {}

                @api.api_route("/ready")
                def ready():
                    return {}

                return api

            module_runtime = make_runtime()
            """
        ),
        "backend/runtime_module_alias.py": textwrap.dedent(
            """
            import fastapi as fa

            def alias_lifespan(app):
                yield

            def assemble():
                runtime = fa.FastAPI(lifespan=alias_lifespan)
                runtime.state.runtime = "synthetic"
                runtime.add_api_route("/live", lambda: {})
                runtime.add_api_route("/ready", lambda: {})
                return runtime

            asgi_runtime = assemble()
            """
        ),
    }

    findings = _app_owner_findings_from_sources(sources)

    assert findings["fastapi_constructor_owners"] == [
        "backend/runtime_alias.py:build_runtime",
        "backend/runtime_module.py:make_runtime",
        "backend/runtime_module_alias.py:assemble",
    ]
    assert findings["canonical_factory_owners"] == [
        "backend/runtime_alias.py:build_runtime",
        "backend/runtime_module.py:make_runtime",
        "backend/runtime_module_alias.py:assemble",
    ]
    assert findings["module_app_owners"] == [
        "backend/runtime_alias.py:runtime_application",
        "backend/runtime_module.py:module_runtime",
        "backend/runtime_module_alias.py:asgi_runtime",
    ]
    assert findings["live_route_owners"] == [
        "backend/runtime_alias.py:/live",
        "backend/runtime_module.py:/live",
        "backend/runtime_module_alias.py:/live",
    ]
    assert findings["ready_route_owners"] == [
        "backend/runtime_alias.py:/ready",
        "backend/runtime_module.py:/ready",
        "backend/runtime_module_alias.py:/ready",
    ]
    assert findings["lifespan_owners"] == [
        "backend/runtime_alias.py:runtime_lifespan",
        "backend/runtime_module.py:bound_lifespan",
        "backend/runtime_module_alias.py:alias_lifespan",
    ]


@pytest.mark.requirement("WS02-02-R1")
def test_app_owner_detector_recognizes_startup_and_shutdown_event_registration() -> None:
    sources = {
        "backend/runtime_events.py": textwrap.dedent(
            """
            from fastapi import FastAPI

            def startup():
                pass

            def build_runtime():
                runtime = FastAPI()
                runtime.state.runtime = "synthetic"
                runtime.add_event_handler("startup", startup)

                @runtime.on_event("shutdown")
                def shutdown():
                    pass

                return runtime

            runtime_app = build_runtime()
            """
        )
    }

    findings = _app_owner_findings_from_sources(sources)

    assert findings["fastapi_constructor_owners"] == ["backend/runtime_events.py:build_runtime"]
    assert findings["canonical_factory_owners"] == ["backend/runtime_events.py:build_runtime"]
    assert findings["module_app_owners"] == ["backend/runtime_events.py:runtime_app"]
    assert findings["startup_shutdown_owners"] == [
        "backend/runtime_events.py:shutdown",
        "backend/runtime_events.py:startup",
    ]


@pytest.mark.requirement("WS02-02-R1")
def test_app_owner_detector_ignores_non_app_syntax_and_non_runtime_paths() -> None:
    sources = {
        "backend/routes/router_only.py": textwrap.dedent(
            '''
            from fastapi import APIRouter

            router = APIRouter()
            note = "FastAPI('/ready')"

            # @app.get("/live")
            @router.get("/unrelated")
            def unrelated():
                return {}
            '''
        ),
        "backend/tests/fake_runtime.py": "from fastapi import FastAPI\napp = FastAPI()\n",
        "backend/legacy/fake_runtime.py": "from fastapi import FastAPI\napp = FastAPI()\n",
        "backend/.venv/fake_runtime.py": "from fastapi import FastAPI\napp = FastAPI()\n",
        "backend/__pycache__/fake_runtime.py": "from fastapi import FastAPI\napp = FastAPI()\n",
        "backend/generated/fake_runtime.py": "from fastapi import FastAPI\napp = FastAPI()\n",
    }

    findings = _app_owner_findings_from_sources(sources)

    assert findings == {
        "fastapi_constructor_owners": [],
        "canonical_factory_owners": [],
        "module_app_owners": [],
        "live_route_owners": [],
        "ready_route_owners": [],
        "db_health_route_owners": [],
        "lifespan_owners": [],
        "startup_shutdown_owners": [],
    }


@pytest.mark.requirement("WS02-02-R2")
def test_backend_main_import_constructs_app_without_runtime_side_effects() -> None:
    child_code = textwrap.dedent(
        """
        import asyncio
        import importlib
        import socket
        import sys
        import threading

        def forbidden(name):
            raise RuntimeError(f"forbidden runtime side effect: {name}")

        import dotenv

        def no_dotenv(*_args, **_kwargs):
            return False

        dotenv.load_dotenv = no_dotenv
        try:
            import dotenv.main
            dotenv.main.load_dotenv = no_dotenv
        except Exception:
            pass

        socket.socket.connect = lambda self, address: forbidden("socket.connect")
        socket.socket.connect_ex = lambda self, address: forbidden("socket.connect_ex")
        socket.create_connection = lambda address, *args, **kwargs: forbidden("socket.create_connection")

        from sqlalchemy.engine import Engine

        Engine.connect = lambda self, *args, **kwargs: forbidden("sqlalchemy.engine.connect")
        Engine.raw_connection = lambda self, *args, **kwargs: forbidden("sqlalchemy.engine.raw_connection")

        try:
            alembic_command = importlib.import_module("alembic.command")
            for command_name in ("upgrade", "downgrade", "stamp", "revision"):
                setattr(
                    alembic_command,
                    command_name,
                    lambda *args, _command_name=command_name, **kwargs: forbidden(
                        f"alembic.command.{_command_name}"
                    ),
                )
        except ModuleNotFoundError:
            pass

        def patch_function(module_name, attribute_name, side_effect_name):
            try:
                module = importlib.import_module(module_name)
            except ModuleNotFoundError:
                return
            setattr(
                module,
                attribute_name,
                lambda *args, **kwargs: forbidden(side_effect_name),
            )

        patch_function("firebase_admin", "initialize_app", "firebase_admin.initialize_app")
        patch_function(
            "backend.firebase_admin_client",
            "initialize_firebase_admin",
            "backend.firebase_admin_client.initialize_firebase_admin",
        )
        patch_function("boto3", "client", "boto3.client")
        try:
            botocore_session = importlib.import_module("botocore.session")
            botocore_session.Session.create_client = (
                lambda self, *args, **kwargs: forbidden("botocore.session.Session.create_client")
            )
        except ModuleNotFoundError:
            pass
        try:
            stripe = importlib.import_module("stripe")
            stripe.StripeClient = lambda *args, **kwargs: forbidden("stripe.StripeClient")
            stripe.RequestsClient = lambda *args, **kwargs: forbidden("stripe.RequestsClient")
        except ModuleNotFoundError:
            pass

        patch_function("uvicorn", "run", "uvicorn.run")
        threading.Thread.start = lambda self, *args, **kwargs: forbidden("threading.Thread.start")
        asyncio.create_task = lambda *args, **kwargs: forbidden("asyncio.create_task")

        import backend.main as main_module
        from fastapi import FastAPI

        if not isinstance(main_module.app, FastAPI):
            raise RuntimeError("canonical app object was not constructed")
        if getattr(main_module.app.state, "lifecycle_started", None) is not False:
            raise RuntimeError("lifecycle state should be inactive after construction")

        print("WS02_02_IMPORT_OK")
        """
    )
    env = {
        "APP_ENV": "test",
        "DATABASE_URL": _SYNTHETIC_DATABASE_URL,
        "INBOX_TOKEN_SECRET": "synthetic-independent-runtime-token",
        "ENABLE_API_DOCS": "false",
        "ENABLE_DB_HEALTH": "false",
        "ENABLE_STRIPE_PAYMENTS": "false",
        "PYTHONPATH": str(_REPO_ROOT),
        "PATH": os.environ.get("PATH", ""),
    }

    completed = subprocess.run(
        [sys.executable, "-c", child_code],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert completed.returncode == 0, _safe_subprocess_output(completed)
    assert completed.stdout.strip() == "WS02_02_IMPORT_OK"
    assert completed.stderr.strip() == ""


def _safe_subprocess_output(completed: subprocess.CompletedProcess[str]) -> str:
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    return output.replace(_SYNTHETIC_DATABASE_URL, "[REDACTED_DATABASE_URL]")[-2000:]


@pytest.mark.requirement("WS02-02-R3")
def test_lifespan_state_transitions_and_calls_public_dispose_helper(monkeypatch) -> None:
    main_module = _import_main(monkeypatch)
    app = main_module.create_app(_runtime_settings())
    dispose_calls: list[str] = []

    def dispose_database_engine() -> None:
        dispose_calls.append("disposed")

    monkeypatch.setattr(main_module, "dispose_database_engine", dispose_database_engine)

    async def exercise_lifespan() -> None:
        assert app.state.lifecycle_started is False
        async with main_module.lifespan(app):
            assert app.state.lifecycle_started is True
        assert app.state.lifecycle_started is False

    asyncio.run(exercise_lifespan())

    assert dispose_calls == ["disposed"]


@pytest.mark.requirement("WS02-02-R3")
def test_public_dispose_helper_delegates_to_sqlalchemy_engine(monkeypatch) -> None:
    _install_runtime_environment(monkeypatch)
    import backend.database as database_module

    dispose_calls: list[str] = []

    class FakeEngine:
        def dispose(self) -> None:
            dispose_calls.append("engine.dispose")

    monkeypatch.setattr(database_module, "engine", FakeEngine())

    database_module.dispose_database_engine()

    assert dispose_calls == ["engine.dispose"]


@pytest.mark.requirement("WS02-02-R4")
def test_live_uses_lifecycle_state_without_database_or_provider_calls(monkeypatch) -> None:
    main_module = _import_main(monkeypatch)
    _install_optional_provider_sentinels(monkeypatch)
    database_calls: list[str] = []

    def fail_database_probe() -> None:
        database_calls.append("database-called")
        raise AssertionError("liveness must not call database readiness")

    monkeypatch.setattr(main_module, "check_database_connection", fail_database_probe)

    from fastapi.testclient import TestClient

    inactive_app = main_module.create_app(_runtime_settings())
    inactive_client = TestClient(inactive_app)
    try:
        inactive_response = inactive_client.get("/live")
    finally:
        inactive_client.close()

    active_app = main_module.create_app(_runtime_settings())
    with TestClient(active_app) as active_client:
        active_response = active_client.get("/live")

    assert inactive_response.status_code == 503
    _assert_health_response(inactive_response, status_value="not_live")
    assert active_response.status_code == 200
    _assert_health_response(active_response, status_value="live")
    assert database_calls == []


@pytest.mark.requirement("WS02-02-R5")
def test_ready_gates_on_lifecycle_and_database_probe_without_optional_providers(
    monkeypatch,
) -> None:
    main_module = _import_main(monkeypatch)
    _install_optional_provider_sentinels(monkeypatch)
    probe_calls: list[str] = []

    def fail_if_called_while_inactive() -> None:
        probe_calls.append("inactive")
        raise AssertionError("inactive readiness must not call the database probe")

    monkeypatch.setattr(main_module, "check_database_connection", fail_if_called_while_inactive)

    from fastapi.testclient import TestClient

    inactive_app = main_module.create_app(_runtime_settings())
    inactive_client = TestClient(inactive_app)
    try:
        inactive_response = inactive_client.get("/ready")
    finally:
        inactive_client.close()

    assert inactive_response.status_code == 503
    _assert_health_response(inactive_response, status_value="not_ready")
    assert probe_calls == []

    outcomes: list[object] = [
        RuntimeError("synthetic SQL host credential stack provider diagnostic"),
        True,
    ]

    def controlled_probe() -> bool:
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return bool(outcome)

    monkeypatch.setattr(main_module, "check_database_connection", controlled_probe)
    active_app = main_module.create_app(_runtime_settings())

    with TestClient(active_app) as active_client:
        failed_response = active_client.get("/ready")
        recovered_response = active_client.get("/ready")

    assert failed_response.status_code == 503
    _assert_health_response(failed_response, status_value="not_ready")
    for leaked_fragment in (
        "synthetic SQL",
        "credential",
        "stack",
        "provider diagnostic",
    ):
        assert leaked_fragment not in failed_response.text

    assert recovered_response.status_code == 200
    _assert_health_response(recovered_response, status_value="ready")
    assert outcomes == []


@pytest.mark.requirement("WS02-02-R5")
def test_database_connection_helper_uses_dedicated_postgresql_test_database() -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    assert database_url, "DATABASE_URL is required for WS02-02 PostgreSQL helper evidence"

    from backend.tests.support.environment_safety import validate_dedicated_test_database_url

    validate_dedicated_test_database_url(database_url)

    import backend.database as database_module

    assert database_module.check_database_connection() is True


@pytest.mark.requirement("WS02-02-R6")
def test_root_compatibility_is_not_database_backed_or_canonical_readiness(
    monkeypatch,
) -> None:
    main_module = _import_main(monkeypatch)
    _install_optional_provider_sentinels(monkeypatch)
    probe_calls: list[str] = []

    def failed_probe() -> bool:
        probe_calls.append("ready")
        raise RuntimeError("synthetic readiness failure")

    monkeypatch.setattr(main_module, "check_database_connection", failed_probe)

    from fastapi.testclient import TestClient

    app = main_module.create_app(_runtime_settings())
    with TestClient(app) as client:
        root_response = client.get("/")
        ready_response = client.get("/ready")

    assert root_response.status_code == 200
    assert root_response.json() == {"message": "Backend is running"}
    assert root_response.headers["Cache-Control"] == "no-store"
    assert ready_response.status_code == 503
    _assert_health_response(ready_response, status_value="not_ready")
    assert probe_calls == ["ready"]


@pytest.mark.requirement("WS02-02-R6")
def test_db_health_is_settings_controlled_uses_shared_probe_and_hides_diagnostics(
    monkeypatch,
) -> None:
    main_module = _import_main(monkeypatch)
    _install_optional_provider_sentinels(monkeypatch)
    probe_calls: list[str] = []

    from fastapi.testclient import TestClient

    disabled_app = main_module.create_app(_runtime_settings(ENABLE_DB_HEALTH="false"))
    with TestClient(disabled_app) as disabled_client:
        disabled_response = disabled_client.get("/db-health")

    assert disabled_response.status_code == 404

    def successful_probe() -> bool:
        probe_calls.append("success")
        return True

    monkeypatch.setattr(main_module, "check_database_connection", successful_probe)
    enabled_success_app = main_module.create_app(_runtime_settings(ENABLE_DB_HEALTH="true"))
    with TestClient(enabled_success_app) as enabled_client:
        success_response = enabled_client.get("/db-health")

    assert success_response.status_code == 200
    assert success_response.headers["Cache-Control"] == "no-store"
    assert success_response.json() == {"message": "Database connection is working"}

    def failed_probe() -> bool:
        probe_calls.append("failure")
        raise RuntimeError("synthetic PostgreSQL credential host stack detail")

    monkeypatch.setattr(main_module, "check_database_connection", failed_probe)
    enabled_failure_app = main_module.create_app(_runtime_settings(ENABLE_DB_HEALTH="true"))
    with TestClient(enabled_failure_app) as enabled_client:
        failure_response = enabled_client.get("/db-health")

    assert failure_response.status_code == 503
    assert failure_response.headers["Cache-Control"] == "no-store"
    assert failure_response.json() == {"message": "Database connection is unavailable"}
    for leaked_fragment in ("synthetic PostgreSQL", "credential", "host", "stack detail"):
        assert leaked_fragment not in failure_response.text
    assert probe_calls == ["success", "failure"]
