"""Provider-independent bounded JSON logging for API and worker processes."""

from __future__ import annotations

import logging
import sys
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from backend.observability.correlation import optional_correlation_context
from backend.observability.events import EventEnvelope

APPLICATION_LOGGER_NAME = "pickup_lane.events"
_HANDLER_TAG = "pickup_lane_structured_handler"
_FRAMEWORK_HANDLER_TAG = "pickup_lane_framework_handler"
_RUNTIME_FIELDS = frozenset(
    {
        "actor_kind",
        "attempt_count",
        "http_method",
        "http_status_code",
        "labels",
        "maximum_attempts",
        "operation",
        "provider_kind",
        "resource_kind",
        "result",
        "stable_error_code",
    }
)
_SEVERITY_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}
_transport_result: ContextVar[bool | None] = ContextVar(
    "pickup_lane_transport_result",
    default=None,
)
_submitted_payload: ContextVar[str | None] = ContextVar(
    "pickup_lane_submitted_payload",
    default=None,
)


class _EnvironmentSetting(Protocol):
    value: str


class LoggingSettings(Protocol):
    app_env: _EnvironmentSetting
    release_identity: str


class SafeJsonHandler(logging.Handler):
    """Write only prevalidated JSON records and never invoke logging diagnostics."""

    pickup_lane_handler_tag = _HANDLER_TAG

    def emit(self, record: logging.LogRecord) -> None:
        try:
            authorized_payload = _submitted_payload.get()
            if (
                authorized_payload is None
                or record.args
                or record.exc_info
                or not isinstance(record.msg, str)
                or record.msg != authorized_payload
            ):
                _transport_result.set(False)
                return
            stream = sys.stdout
            stream.write(record.msg + "\n")
            stream.flush()
            _transport_result.set(True)
        except Exception:  # noqa: BLE001 - logging cannot change product behavior.
            _transport_result.set(False)
            return

    def handleError(self, record: logging.LogRecord) -> None:
        del record


class _DropHandler(logging.Handler):
    pickup_lane_handler_tag = _FRAMEWORK_HANDLER_TAG

    def emit(self, record: logging.LogRecord) -> None:
        del record

    def handleError(self, record: logging.LogRecord) -> None:
        del record


class _FrameworkHandler(logging.Handler):
    pickup_lane_handler_tag = _FRAMEWORK_HANDLER_TAG

    def __init__(self, emitter: RuntimeEventEmitter) -> None:
        super().__init__(level=logging.WARNING)
        self._emitter = emitter

    def emit(self, record: logging.LogRecord) -> None:
        try:
            severity = _severity_for_level(record.levelno)
            self._emitter.emit(
                "runtime.framework",
                severity,
                {
                    "operation": "uvicorn.runtime",
                    "result": "runtime_record",
                },
            )
        except Exception:  # noqa: BLE001 - framework logging must be non-throwing.
            return

    def handleError(self, record: logging.LogRecord) -> None:
        del record


@dataclass(frozen=True)
class RuntimeEventEmitter:
    source_identity: str
    environment: str
    release: str

    def __post_init__(self) -> None:
        if self.source_identity not in {"api", "worker"}:
            raise ValueError("Runtime source identity is not supported.")
        if not isinstance(self.environment, str) or not isinstance(self.release, str):
            raise TypeError("Runtime environment and release must be text.")
        EventEnvelope(
            event_name="logging.bootstrap",
            occurred_at=datetime.now(timezone.utc),
            severity="info",
            source_identity=self.source_identity,
            environment=self.environment,
            release=self.release,
        )

    def emit(
        self,
        event_name: object,
        severity: object,
        fields: object,
    ) -> bool:
        return self._emit_owned(event_name, severity, fields)

    def _emit_owned(
        self,
        event_name: object,
        severity: object,
        fields: object,
        *,
        correlation_id: str | None = None,
        resource_id: str | None = None,
    ) -> bool:
        try:
            if not isinstance(event_name, str) or not isinstance(severity, str):
                raise TypeError("event identity must be text")
            level = _SEVERITY_LEVELS[severity]
            if not isinstance(fields, Mapping):
                raise TypeError("event fields must be a mapping")
            unsupported = set(fields) - _RUNTIME_FIELDS
            if unsupported:
                raise ValueError("event fields contain unsupported keys")
            envelope = EventEnvelope(
                event_name=event_name,
                occurred_at=datetime.now(timezone.utc),
                severity=severity,
                source_identity=self.source_identity,
                environment=self.environment,
                release=self.release,
                correlation_id=correlation_id,
                resource_id=resource_id,
                **dict(fields),
            )
        except Exception:  # noqa: BLE001 - rejection content is deliberately opaque.
            return self._emit_rejection()

        try:
            payload = envelope.to_json()
        except Exception:  # noqa: BLE001 - serialization failure cannot recurse.
            return False

        return _submit_json(level, payload)

    def _emit_rejection(self) -> bool:
        try:
            envelope = EventEnvelope(
                event_name="logging.event_rejected",
                occurred_at=datetime.now(timezone.utc),
                severity="warning",
                source_identity=self.source_identity,
                environment=self.environment,
                release=self.release,
            )
            return _submit_json(logging.WARNING, envelope.to_json())
        except Exception:  # noqa: BLE001 - no recursive rejection path.
            return False


_active_emitter: ContextVar[RuntimeEventEmitter | None] = ContextVar(
    "pickup_lane_event_emitter",
    default=None,
)
_process_emitter: RuntimeEventEmitter | None = None


def build_event_emitter(
    settings: LoggingSettings,
    *,
    source_identity: str,
) -> RuntimeEventEmitter:
    return RuntimeEventEmitter(
        source_identity=source_identity,
        environment=settings.app_env.value,
        release=settings.release_identity,
    )


@contextmanager
def event_emitter_context(
    emitter: RuntimeEventEmitter,
) -> Iterator[RuntimeEventEmitter]:
    token = _active_emitter.set(emitter)
    try:
        yield emitter
    finally:
        _active_emitter.reset(token)


def emit_event(event_name: object, severity: object, fields: object) -> bool:
    emitter = _active_emitter.get() or _process_emitter
    if emitter is None:
        return False
    return emitter.emit(event_name, severity, fields)


def emit_event_with_correlation(
    emitter: RuntimeEventEmitter,
    correlation_id: str,
    event_name: str,
    severity: str,
    fields: Mapping[str, object],
) -> bool:
    with optional_correlation_context(correlation_id), event_emitter_context(emitter):
        return emitter._emit_owned(
            event_name,
            severity,
            fields,
            correlation_id=correlation_id,
        )


def emit_durable_job_event(
    emitter: RuntimeEventEmitter | None,
    job_id: uuid.UUID,
    severity: str,
    fields: Mapping[str, object],
) -> bool:
    selected_emitter = emitter or _active_emitter.get() or _process_emitter
    if selected_emitter is None:
        return False
    owned_fields = dict(fields)
    owned_fields["resource_kind"] = "durable_job"
    return selected_emitter._emit_owned(
        "durable_job.processed",
        severity,
        owned_fields,
        resource_id=str(job_id),
    )


def prepare_api_logging() -> None:
    """Suppress raw Uvicorn output until validated process metadata is available."""

    global _process_emitter
    _process_emitter = None
    _configure_uvicorn_handler(_DropHandler())


def prepare_worker_logging() -> None:
    """Install the safe application transport before worker-dependent imports."""

    global _process_emitter
    _process_emitter = None
    _configure_application_handler()


def configure_process_logging(
    emitter: RuntimeEventEmitter,
    *,
    configure_uvicorn: bool = True,
) -> None:
    global _process_emitter
    _process_emitter = emitter
    _configure_application_handler()
    if configure_uvicorn:
        _configure_uvicorn_handler(_FrameworkHandler(emitter))


def _configure_application_handler() -> None:
    logger = logging.getLogger(APPLICATION_LOGGER_NAME)
    logger.handlers = [SafeJsonHandler()]
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger.disabled = False


def _configure_uvicorn_handler(handler: logging.Handler) -> None:
    access = logging.getLogger("uvicorn.access")
    access.handlers = []
    access.propagate = False
    access.disabled = True

    parent = logging.getLogger("uvicorn")
    parent.handlers = [handler]
    parent.setLevel(logging.WARNING)
    parent.propagate = False
    parent.disabled = False

    error = logging.getLogger("uvicorn.error")
    error.handlers = []
    error.setLevel(logging.WARNING)
    error.propagate = True
    error.disabled = False


def _submit_json(level: int, payload: str) -> bool:
    result_token = _transport_result.set(None)
    payload_token = _submitted_payload.set(payload)
    try:
        logging.getLogger(APPLICATION_LOGGER_NAME).log(level, payload)
        return _transport_result.get() is True
    except Exception:  # noqa: BLE001 - logging failure must be isolated.
        return False
    finally:
        _submitted_payload.reset(payload_token)
        _transport_result.reset(result_token)


def _severity_for_level(level: int) -> str:
    if level >= logging.CRITICAL:
        return "critical"
    if level >= logging.ERROR:
        return "error"
    return "warning"
