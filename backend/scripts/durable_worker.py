"""Portable durable-job worker command.

Run with ``python -m backend.scripts.durable_worker``.
"""

from __future__ import annotations

import argparse
import json
import signal
import time
import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from backend.observability.redaction import contains_sensitive_text
from backend.observability.structured_logging import (
    RuntimeEventEmitter,
    build_event_emitter,
    configure_process_logging,
    emit_event,
    prepare_worker_logging,
)
from backend.settings import get_settings


def _canonical_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_operator_string(value: str | None, *, maximum: int) -> str | None:
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= maximum
        or value != value.strip()
        or any(character in value for character in ("\x00", "\n", "\r", "\t"))
        or contains_sensitive_text(value)
    ):
        return "redacted"
    return value


def _safe_event_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    from backend.services.durable_job_service import sanitize_diagnostic_metadata

    try:
        return dict(sorted(sanitize_diagnostic_metadata(metadata).items()))
    except Exception:  # noqa: BLE001 - stored diagnostics must fail closed.
        return {}


def _status_record(summary) -> dict[str, object]:
    return {
        "record_type": "durable_job_status",
        "schema_version": 1,
        "by_status": [
            {"status": status_name, "count": count}
            for status_name, count in sorted(summary.by_status.items())
        ],
        "by_type_version": [
            {"job_type": job_type, "payload_version": version, "count": count}
            for (job_type, version), count in sorted(summary.by_type_version.items())
        ],
        "attempt_counts_by_status": [
            {
                "status": status_name,
                "attempt_counts": [
                    {"attempt_count": attempt, "count": count}
                    for attempt, count in sorted(attempt_counts.items())
                ],
            }
            for status_name, attempt_counts in sorted(
                summary.attempt_counts_by_status.items()
            )
        ],
        "unsupported_type_versions": [
            {"job_type": job_type, "payload_version": version}
            for job_type, version in sorted(summary.unsupported_type_versions)
        ],
        "expired_leases": summary.expired_leases,
        "exhausted_jobs": summary.exhausted_jobs,
        "retry_waiting_jobs": summary.retry_waiting_jobs,
        "oldest_pending_age_seconds": summary.oldest_pending_age_seconds,
        "fairness_protected_jobs": summary.fairness_protected_jobs,
        "worker_heartbeats": [
            {
                "worker_identity": _safe_operator_string(
                    worker.worker_identity,
                    maximum=120,
                ),
                "worker_version": _safe_operator_string(
                    worker.worker_version,
                    maximum=80,
                ),
                "status": worker.status,
                "heartbeat_age_seconds": worker.heartbeat_age_seconds,
                "has_current_job": worker.has_current_job,
            }
            for worker in sorted(
                summary.worker_heartbeats,
                key=lambda item: (item.worker_identity, item.worker_version),
            )
        ],
    }


def _job_record(job_summary) -> dict[str, object]:
    return {
        "record_type": "durable_job_details",
        "schema_version": 1,
        "missing": False,
        "job_type": job_summary.job_type,
        "payload_version": job_summary.payload_version,
        "status": job_summary.status,
        "attempt_count": job_summary.attempt_count,
        "maximum_attempts": job_summary.maximum_attempts,
        "last_safe_error_code": job_summary.last_safe_error_code,
        "recent_events": [
            {
                "occurred_at": _canonical_timestamp(event.occurred_at),
                "event_type": event.event_type,
                "previous_status": event.previous_status,
                "new_status": event.new_status,
                "attempt_count": event.attempt_count,
                "lease_owner": _safe_operator_string(event.lease_owner, maximum=120),
                "safe_error_code": event.safe_error_code,
                "event_metadata": _safe_event_metadata(event.event_metadata),
            }
            for event in job_summary.recent_events
        ],
    }


def _write_json(record: Mapping[str, object]) -> None:
    print(json.dumps(record, separators=(",", ":"), sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    try:
        prepare_worker_logging()
        settings = get_settings()
        event_emitter = build_event_emitter(settings, source_identity="worker")
        configure_process_logging(event_emitter, configure_uvicorn=False)
    except Exception as exc:  # noqa: BLE001 - expose only a fixed bootstrap failure.
        del exc
        raise RuntimeError("Worker logging bootstrap failed.") from None

    return _run_worker(argv, event_emitter)


def _run_worker(
    argv: list[str] | None,
    event_emitter: RuntimeEventEmitter,
) -> int:
    try:
        from backend.database import SessionLocal, check_database_connection
        from backend.services.durable_job_service import (
            DEFAULT_WORKER_VERSION,
            DurableJobQueuePolicy,
            DurableJobRunner,
            backlog_summary,
            inspect_job_history,
        )
        from backend.services.payment_job_service import build_production_job_registry

        parser = argparse.ArgumentParser(
            description="Run the portable Pickup Lane durable-job worker."
        )
        parser.add_argument("--worker-id", default="local-durable-worker")
        parser.add_argument("--worker-version", default=DEFAULT_WORKER_VERSION)
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--status", action="store_true")
        parser.add_argument("--job-id")
        parser.add_argument("--poll-seconds", type=float, default=5.0)
        args = parser.parse_args(argv)

        check_database_connection()
        registry = build_production_job_registry()
        policy = DurableJobQueuePolicy(poll_interval_seconds=args.poll_seconds)

        if args.status:
            inspected_job_id = None
            if args.job_id:
                try:
                    inspected_job_id = uuid.UUID(args.job_id)
                except ValueError:
                    parser.error("--job-id must be a UUID")
            with SessionLocal() as db:
                summary = backlog_summary(db, registry=registry, policy=policy)
                job_summary = (
                    inspect_job_history(db, job_id=inspected_job_id)
                    if inspected_job_id is not None
                    else None
                )
            _write_json(_status_record(summary))
            if inspected_job_id is not None:
                _write_json(
                    {
                        "record_type": "durable_job_details",
                        "schema_version": 1,
                        "missing": True,
                    }
                    if job_summary is None
                    else _job_record(job_summary)
                )
            return 0

        runner = DurableJobRunner(
            session_factory=SessionLocal,
            registry=registry,
            worker_identity=args.worker_id,
            worker_version=args.worker_version,
            policy=policy,
            event_emitter=event_emitter,
        )

        def request_shutdown(signum, frame) -> None:
            del signum, frame
            runner.request_shutdown()

        signal.signal(signal.SIGINT, request_shutdown)
        signal.signal(signal.SIGTERM, request_shutdown)

        try:
            while True:
                outcome = runner.process_once()
                if outcome == "shutdown":
                    return 0
                if args.once:
                    return 0
                time.sleep(policy.poll_interval_seconds)
        finally:
            runner.mark_stopped()
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001 - the worker boundary must not print a traceback.
        emit_event(
            "durable_worker.failure",
            "error",
            {
                "operation": "durable_worker.run",
                "result": "failed",
                "stable_error_code": "WORKER.UNEXPECTED_FAILURE",
            },
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
