from __future__ import annotations

import ast
import uuid
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from backend.observability.timeouts import DependencyReadTimeoutError
from backend.schemas.venue_image_schema import VenueImageUploadCreate
from backend.services import (
    app_check_middleware,
    chat_rate_limit_service,
    content_moderation_finding_service,
    game_service,
    moderation_signal_service,
    moderation_surfacing_service,
    official_game_query_service,
    venue_image_service,
)
from backend.services.app_check_middleware import AppCheckEvent
from backend.services.app_check_service import AppCheckVerificationOutcome
from backend.services.r2_storage_service import (
    R2ObjectNotFoundError,
    R2StorageConfigError,
    R2StorageError,
)

pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.requirement("WS09-01A"),
]

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _capture(monkeypatch: pytest.MonkeyPatch, module) -> list[tuple[object, ...]]:
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(module, "emit_event", lambda *args: calls.append(args) or True)
    return calls


@pytest.mark.parametrize(
    ("outcome", "severity", "code"),
    [
        (AppCheckVerificationOutcome.VALID, "info", None),
        (AppCheckVerificationOutcome.MISSING, "warning", "APP_CHECK.REQUIRED"),
        (AppCheckVerificationOutcome.INVALID, "warning", "APP_CHECK.INVALID"),
        (
            AppCheckVerificationOutcome.PROVIDER_UNAVAILABLE,
            "warning",
            "APP_CHECK.UNAVAILABLE",
        ),
    ],
)
def test_app_check_inventory_has_exact_fixed_mappings(
    monkeypatch: pytest.MonkeyPatch,
    outcome: AppCheckVerificationOutcome,
    severity: str,
    code: str | None,
) -> None:
    calls = _capture(monkeypatch, app_check_middleware)
    event = AppCheckEvent(
        route_template="/games/{game_id}",
        route_family="game_details",
        operation="app_check.enforce",
        outcome=outcome,
        stable_error_code=code,
    )

    app_check_middleware.record_app_check_event(event, Mock())

    fields = {
        "provider_kind": "firebase",
        "operation": "app_check.enforce",
        "resource_kind": "game_details",
        "result": outcome.value,
        "labels": {"route_template": "/games/{game_id}"},
    }
    if code is not None:
        fields["stable_error_code"] = code
    assert calls == [("app_check.request", severity, fields)]


@pytest.mark.parametrize(
    ("result", "severity", "code"),
    [
        ("allowed", "info", None),
        ("rejected", "warning", "API.RATE_LIMITED"),
        ("store_error", "error", "CHAT.RATE_LIMIT_STORE_ERROR"),
    ],
)
def test_chat_rate_limit_inventory_has_exact_fixed_mappings(
    monkeypatch: pytest.MonkeyPatch,
    result: str,
    severity: str,
    code: str | None,
) -> None:
    calls = _capture(monkeypatch, chat_rate_limit_service)

    chat_rate_limit_service._log_rate_limit_event(
        limiter_category="game_chat",
        result=result,
        occurred_at=Mock(),
        stable_error_code=code,
    )

    fields = {
        "actor_kind": "authenticated_user",
        "operation": "chat_rate_limit.check",
        "resource_kind": "game_chat",
        "result": result,
        "labels": {"outcome": result, "route_template": "/chat-messages"},
    }
    if code is not None:
        fields["stable_error_code"] = code
    assert calls == [("chat.rate_limit", severity, fields)]


def test_content_finding_reconciliation_failure_rolls_back_before_exact_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _capture(monkeypatch, content_moderation_finding_service)
    db = Mock()
    monkeypatch.setattr(
        content_moderation_finding_service,
        "reconcile_content_moderation_findings",
        Mock(side_effect=RuntimeError("private-canary")),
    )

    content_moderation_finding_service.run_content_moderation_finding_reconciliation_safely(
        db,
        target_data={"target_game_id": uuid.uuid4()},
        scan_result=Mock(),
    )

    db.rollback.assert_called_once_with()
    assert calls == [
        (
            "moderation.finding_reconciliation_failed",
            "error",
            {
                "operation": "moderation.finding.reconcile",
                "resource_kind": "moderation_finding",
                "result": "failed",
                "stable_error_code": "MODERATION.FINDING_RECONCILIATION_FAILED",
            },
        )
    ]


@pytest.mark.parametrize(
    ("error", "result", "code"),
    [
        (
            IntegrityError("statement", {}, RuntimeError("private-canary")),
            "integrity_error",
            "MODERATION.SURFACING_INTEGRITY",
        ),
        (RuntimeError("private-canary"), "failed", "MODERATION.SURFACING_FAILED"),
    ],
)
def test_moderation_surfacing_failures_preserve_distinct_exact_mappings(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    result: str,
    code: str,
) -> None:
    calls = _capture(monkeypatch, moderation_signal_service)
    db = Mock()
    monkeypatch.setattr(
        moderation_signal_service,
        "surface_moderation_findings",
        Mock(side_effect=error),
    )

    moderation_signal_service.run_moderation_surfacing_safely(
        db,
        target_type="game_chat_message",
        target_data={"target_game_id": uuid.uuid4()},
        findings=[],
        scanned_field_hashes={},
    )

    db.rollback.assert_called_once_with()
    assert calls == [
        (
            "moderation.surfacing_failed",
            "error",
            {
                "operation": "moderation.surfacing.persist",
                "resource_kind": "moderation_signal",
                "result": result,
                "stable_error_code": code,
            },
        )
    ]


@pytest.mark.parametrize(
    ("function_name", "argument_name", "operation", "resource", "code"),
    [
        (
            "surface_community_game_text",
            "game_id",
            "moderation.community_game.reconcile",
            "community_game",
            "MODERATION.COMMUNITY_GAME_RECONCILIATION_FAILED",
        ),
        (
            "surface_need_a_sub_post_text",
            "sub_post_id",
            "moderation.need_a_sub.reconcile",
            "need_a_sub",
            "MODERATION.NEED_A_SUB_RECONCILIATION_FAILED",
        ),
    ],
)
def test_saved_content_reconciliation_catches_have_distinct_exact_mappings(
    monkeypatch: pytest.MonkeyPatch,
    function_name: str,
    argument_name: str,
    operation: str,
    resource: str,
    code: str,
) -> None:
    calls = _capture(monkeypatch, moderation_surfacing_service)
    db = Mock()
    db.scalar.side_effect = RuntimeError("private-canary")

    getattr(moderation_surfacing_service, function_name)(
        db,
        **{argument_name: uuid.uuid4()},
    )

    db.rollback.assert_called_once_with()
    assert calls == [
        (
            "moderation.reconciliation_failed",
            "error",
            {
                "operation": operation,
                "resource_kind": resource,
                "result": "failed",
                "stable_error_code": code,
            },
        )
    ]


@pytest.mark.parametrize(
    ("operation", "configuration_error", "provider_code", "result", "code"),
    [
        (
            "r2.upload.validate",
            True,
            "STORAGE.UPLOAD_URL_FAILED",
            "configuration_error",
            "STORAGE.CONFIG_UNAVAILABLE",
        ),
        (
            "r2.readiness.check",
            True,
            "STORAGE.CONFIG_UNAVAILABLE",
            "configuration_error",
            "STORAGE.CONFIG_UNAVAILABLE",
        ),
        (
            "r2.upload_url.create",
            False,
            "STORAGE.UPLOAD_URL_FAILED",
            "provider_error",
            "STORAGE.UPLOAD_URL_FAILED",
        ),
        (
            "r2.read_url.create",
            False,
            "STORAGE.READ_URL_FAILED",
            "provider_error",
            "STORAGE.READ_URL_FAILED",
        ),
        (
            "r2.metadata.head",
            False,
            "STORAGE.METADATA_LOOKUP_FAILED",
            "provider_error",
            "STORAGE.METADATA_LOOKUP_FAILED",
        ),
    ],
)
def test_storage_event_helper_has_exact_safe_mapping(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    configuration_error: bool,
    provider_code: str,
    result: str,
    code: str,
) -> None:
    calls = _capture(monkeypatch, venue_image_service)

    venue_image_service._emit_storage_failure(
        operation=operation,
        configuration_error=configuration_error,
        provider_code=provider_code,
    )

    assert calls == [
        (
            "storage.operation_failed",
            "error",
            {
                "provider_kind": "r2",
                "operation": operation,
                "result": result,
                "stable_error_code": code,
            },
        )
    ]


def _upload_request() -> VenueImageUploadCreate:
    return VenueImageUploadCreate(
        file_name="private-file-name.jpg",
        content_type="image/jpeg",
        size_bytes=1024,
        image_role="gallery",
    )


def _assert_storage_call(
    calls: list[tuple[object, ...]],
    *,
    operation: str,
    result: str,
    code: str,
) -> None:
    assert calls == [
        (
            "storage.operation_failed",
            "error",
            {
                "provider_kind": "r2",
                "operation": operation,
                "result": result,
                "stable_error_code": code,
            },
        )
    ]
    serialized = repr(calls)
    for prohibited in (
        "private-file-name",
        "private-object-key",
        "private-provider-response",
        "private-bucket",
        "private-account",
    ):
        assert prohibited not in serialized


def test_validate_upload_request_config_failure_emits_at_actual_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _capture(monkeypatch, venue_image_service)
    monkeypatch.setattr(
        venue_image_service,
        "get_r2_storage_config",
        Mock(side_effect=R2StorageConfigError("private-provider-response")),
    )

    with pytest.raises(HTTPException) as exc_info:
        venue_image_service.validate_upload_request(_upload_request())

    assert exc_info.value.status_code == 503
    _assert_storage_call(
        calls,
        operation="r2.upload.validate",
        result="configuration_error",
        code="STORAGE.CONFIG_UNAVAILABLE",
    )


def test_upload_readiness_config_failure_emits_at_actual_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _capture(monkeypatch, venue_image_service)
    monkeypatch.setattr(
        venue_image_service,
        "get_r2_storage_config",
        Mock(side_effect=R2StorageConfigError("private-provider-response")),
    )

    with pytest.raises(HTTPException) as exc_info:
        venue_image_service.check_venue_image_upload_readiness(Mock())

    assert exc_info.value.status_code == 503
    _assert_storage_call(
        calls,
        operation="r2.readiness.check",
        result="configuration_error",
        code="STORAGE.CONFIG_UNAVAILABLE",
    )


def test_create_upload_direct_config_failure_emits_at_actual_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _capture(monkeypatch, venue_image_service)
    monkeypatch.setattr(venue_image_service, "get_active_venue_or_404", Mock())
    monkeypatch.setattr(venue_image_service, "validate_upload_request", Mock())
    monkeypatch.setattr(venue_image_service, "validate_selected_image_capacity", Mock())
    monkeypatch.setattr(
        venue_image_service,
        "get_r2_storage_config",
        Mock(side_effect=R2StorageConfigError("private-provider-response")),
    )

    with pytest.raises(HTTPException) as exc_info:
        venue_image_service.create_venue_image_upload(
            Mock(),
            venue_id=uuid.uuid4(),
            upload_request=_upload_request(),
            current_admin=Mock(id=uuid.uuid4()),
        )

    assert exc_info.value.status_code == 503
    _assert_storage_call(
        calls,
        operation="r2.upload_url.create",
        result="configuration_error",
        code="STORAGE.CONFIG_UNAVAILABLE",
    )


@pytest.mark.parametrize(
    ("failure", "result", "code", "status_code"),
    [
        (
            R2StorageConfigError("private-provider-response"),
            "configuration_error",
            "STORAGE.CONFIG_UNAVAILABLE",
            503,
        ),
        (
            R2StorageError("private-provider-response"),
            "provider_error",
            "STORAGE.UPLOAD_URL_FAILED",
            502,
        ),
    ],
)
def test_create_upload_ticket_failures_emit_at_actual_boundary(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    result: str,
    code: str,
    status_code: int,
) -> None:
    calls = _capture(monkeypatch, venue_image_service)
    monkeypatch.setattr(venue_image_service, "get_active_venue_or_404", Mock())
    monkeypatch.setattr(venue_image_service, "validate_upload_request", Mock())
    monkeypatch.setattr(venue_image_service, "validate_selected_image_capacity", Mock())
    monkeypatch.setattr(
        venue_image_service,
        "get_r2_storage_config",
        Mock(bucket_name="private-bucket", account_id="private-account"),
    )
    monkeypatch.setattr(
        venue_image_service,
        "create_object_upload_url",
        Mock(side_effect=failure),
    )

    with pytest.raises(HTTPException) as exc_info:
        venue_image_service.create_venue_image_upload(
            Mock(),
            venue_id=uuid.uuid4(),
            upload_request=_upload_request(),
            current_admin=Mock(id=uuid.uuid4()),
        )

    assert exc_info.value.status_code == status_code
    _assert_storage_call(
        calls,
        operation="r2.upload_url.create",
        result=result,
        code=code,
    )


@pytest.mark.parametrize(
    "function_name",
    ["build_venue_image_read", "build_public_venue_image_read"],
)
@pytest.mark.parametrize(
    ("failure", "result", "code", "status_code"),
    [
        (
            R2StorageConfigError("private-provider-response"),
            "configuration_error",
            "STORAGE.CONFIG_UNAVAILABLE",
            503,
        ),
        (
            R2StorageError("private-provider-response"),
            "provider_error",
            "STORAGE.READ_URL_FAILED",
            502,
        ),
    ],
)
def test_image_read_url_failures_emit_at_actual_admin_and_public_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    function_name: str,
    failure: Exception,
    result: str,
    code: str,
    status_code: int,
) -> None:
    calls = _capture(monkeypatch, venue_image_service)
    monkeypatch.setattr(
        venue_image_service,
        "create_object_read_url",
        Mock(side_effect=failure),
    )

    with pytest.raises(HTTPException) as exc_info:
        getattr(venue_image_service, function_name)(
            Mock(storage_object_key="private-object-key")
        )

    assert exc_info.value.status_code == status_code
    _assert_storage_call(
        calls,
        operation="r2.read_url.create",
        result=result,
        code=code,
    )


@pytest.mark.parametrize(
    ("failure", "result", "code", "status_code"),
    [
        (
            R2StorageConfigError("private-provider-response"),
            "configuration_error",
            "STORAGE.CONFIG_UNAVAILABLE",
            503,
        ),
        (
            R2StorageError("private-provider-response"),
            "provider_error",
            "STORAGE.METADATA_LOOKUP_FAILED",
            502,
        ),
    ],
)
def test_metadata_failures_emit_at_actual_completion_boundary(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    result: str,
    code: str,
    status_code: int,
) -> None:
    calls = _capture(monkeypatch, venue_image_service)
    monkeypatch.setattr(
        venue_image_service,
        "get_venue_image_or_404",
        Mock(
            return_value=Mock(
                image_status="pending_upload",
                storage_object_key="private-object-key",
            )
        ),
    )
    monkeypatch.setattr(
        venue_image_service,
        "get_object_properties",
        Mock(side_effect=failure),
    )

    with pytest.raises(HTTPException) as exc_info:
        venue_image_service.complete_venue_image_upload(
            Mock(),
            venue_image_id=uuid.uuid4(),
            current_admin=Mock(id=uuid.uuid4()),
        )

    assert exc_info.value.status_code == status_code
    _assert_storage_call(
        calls,
        operation="r2.metadata.head",
        result=result,
        code=code,
    )


@pytest.mark.parametrize(
    "failure",
    [
        R2ObjectNotFoundError("private-provider-response"),
        DependencyReadTimeoutError(provider_kind="r2", operation="r2.metadata.head"),
    ],
)
def test_expected_metadata_not_found_and_timeout_do_not_duplicate_storage_event(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
) -> None:
    calls = _capture(monkeypatch, venue_image_service)
    monkeypatch.setattr(
        venue_image_service,
        "get_venue_image_or_404",
        Mock(
            return_value=Mock(
                image_status="pending_upload",
                storage_object_key="private-object-key",
            )
        ),
    )
    monkeypatch.setattr(
        venue_image_service,
        "get_object_properties",
        Mock(side_effect=failure),
    )

    with pytest.raises((HTTPException, DependencyReadTimeoutError)) as exc_info:
        venue_image_service.complete_venue_image_upload(
            Mock(),
            venue_image_id=uuid.uuid4(),
            current_admin=Mock(id=uuid.uuid4()),
        )

    if isinstance(failure, R2ObjectNotFoundError):
        assert isinstance(exc_info.value, HTTPException)
        assert exc_info.value.status_code == 400
    else:
        assert exc_info.value is failure
    assert calls == []


@pytest.mark.parametrize(
    ("failure", "result", "code"),
    [
        (
            R2StorageConfigError("private-provider-response"),
            "configuration_error",
            "STORAGE.CONFIG_UNAVAILABLE",
        ),
        (
            R2StorageError("private-provider-response"),
            "provider_error",
            "STORAGE.READ_URL_FAILED",
        ),
    ],
)
def test_official_game_best_effort_read_failure_emits_and_returns_none(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    result: str,
    code: str,
) -> None:
    calls = _capture(monkeypatch, official_game_query_service)
    monkeypatch.setattr(
        official_game_query_service,
        "create_object_read_url",
        Mock(side_effect=failure),
    )

    assert (
        official_game_query_service.build_primary_venue_image_url("private-object-key")
        is None
    )
    _assert_storage_call(
        calls,
        operation="r2.read_url.create",
        result=result,
        code=code,
    )


@pytest.mark.parametrize(
    ("failure", "result", "code"),
    [
        (
            R2StorageConfigError("private-provider-response"),
            "configuration_error",
            "STORAGE.CONFIG_UNAVAILABLE",
        ),
        (
            R2StorageError("private-provider-response"),
            "provider_error",
            "STORAGE.READ_URL_FAILED",
        ),
    ],
)
def test_game_card_best_effort_read_failure_emits_and_preserves_missing_image(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    result: str,
    code: str,
) -> None:
    calls = _capture(monkeypatch, game_service)
    monkeypatch.setattr(
        game_service,
        "create_object_read_url",
        Mock(side_effect=failure),
    )
    monkeypatch.setattr(
        game_service, "build_game_card_display_title", lambda game: "title"
    )
    monkeypatch.setattr(
        game_service, "build_game_card_location_label", lambda game: "place"
    )
    monkeypatch.setattr(
        game_service, "get_game_availability_status", lambda *args, **kwargs: "open"
    )
    monkeypatch.setattr(game_service, "get_game_time_group_key", lambda *args: "12:00")
    monkeypatch.setattr(game_service, "format_game_card_price", lambda *args: "$10")
    monkeypatch.setattr(game_service, "get_join_window_closes_at", lambda game: Mock())
    monkeypatch.setattr(game_service, "GameAvailabilityRead", lambda **kwargs: kwargs)
    monkeypatch.setattr(game_service, "GameCardRead", lambda **kwargs: kwargs)
    game = Mock(total_spots=10, timezone="UTC")

    result_card = game_service.build_game_card_read(
        game,
        participant_count=2,
        primary_game_image_url=None,
        primary_venue_image_object_key="private-object-key",
    )

    assert result_card["primary_image_url"] is None
    _assert_storage_call(
        calls,
        operation="r2.read_url.create",
        result=result,
        code=code,
    )


def test_storage_inventory_is_owned_only_by_request_facing_services() -> None:
    venue_source = (_REPO_ROOT / "backend/services/venue_image_service.py").read_text()
    official_source = (
        _REPO_ROOT / "backend/services/official_game_query_service.py"
    ).read_text()
    game_source = (_REPO_ROOT / "backend/services/game_service.py").read_text()
    adapter_source = (_REPO_ROOT / "backend/services/r2_storage_service.py").read_text()

    for operation in (
        "r2.upload.validate",
        "r2.readiness.check",
        "r2.upload_url.create",
        "r2.read_url.create",
        "r2.metadata.head",
    ):
        assert operation in venue_source
    assert "r2.read_url.create" in official_source
    assert "r2.read_url.create" in game_source
    assert "storage.operation_failed" not in adapter_source
    assert "DependencyReadTimeoutError" in adapter_source
    assert "R2ObjectNotFoundError" in venue_source


def test_complete_in_scope_runtime_population_has_no_parallel_plain_logging() -> None:
    module_paths = (
        "backend/main.py",
        "backend/observability/http_errors.py",
        "backend/services/app_check_middleware.py",
        "backend/services/chat_rate_limit_service.py",
        "backend/services/content_moderation_finding_service.py",
        "backend/services/moderation_signal_service.py",
        "backend/services/moderation_surfacing_service.py",
        "backend/services/venue_image_service.py",
        "backend/services/official_game_query_service.py",
        "backend/services/game_service.py",
        "backend/services/durable_job_service.py",
        "backend/scripts/durable_worker.py",
    )
    event_modules = set(module_paths) - {"backend/main.py"}

    for relative_path in module_paths:
        source = (_REPO_ROOT / relative_path).read_text()
        tree = ast.parse(source, filename=relative_path)
        imported_roots = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported_modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        call_names = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        attribute_calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }

        assert "logging" not in imported_roots
        assert "logging" not in imported_modules
        assert "getLogger" not in attribute_calls
        assert not ({"debug", "info", "warning", "error", "exception"} & call_names)
        if relative_path in event_modules:
            assert "backend.observability.structured_logging" in imported_modules

        print_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "print"
        ]
        if relative_path == "backend/scripts/durable_worker.py":
            assert len(print_calls) == 1
            assert "def _write_json" in source
        else:
            assert print_calls == []
