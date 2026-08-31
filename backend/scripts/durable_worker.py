"""Portable durable-job worker command.

Run with:

    python -m backend.scripts.durable_worker --once

The production registry is shared by every enqueue path and this worker.
"""

from __future__ import annotations

import argparse
import signal
import time
import uuid

from backend.database import SessionLocal, check_database_connection
from backend.services.durable_job_service import (
    DEFAULT_WORKER_VERSION,
    DurableJobQueuePolicy,
    DurableJobRunner,
    backlog_summary,
    inspect_job_history,
)
from backend.services.payment_job_service import build_production_job_registry


def _format_worker_summaries(summary) -> list[dict[str, object]]:
    return [
        {
            "worker_identity": worker.worker_identity,
            "worker_version": worker.worker_version,
            "status": worker.status,
            "heartbeat_age_seconds": worker.heartbeat_age_seconds,
            "has_current_job": worker.has_current_job,
        }
        for worker in summary.worker_heartbeats
    ]


def _format_recent_events(job_summary) -> list[dict[str, object]]:
    return [
        {
            "event_type": event.event_type,
            "previous_status": event.previous_status,
            "new_status": event.new_status,
            "attempt_count": event.attempt_count,
            "lease_owner": event.lease_owner,
            "safe_error_code": event.safe_error_code,
            "event_metadata": dict(event.event_metadata),
        }
        for event in job_summary.recent_events
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the portable Pickup Lane durable-job worker.")
    parser.add_argument("--worker-id", default="local-durable-worker")
    parser.add_argument("--worker-version", default=DEFAULT_WORKER_VERSION)
    parser.add_argument("--once", action="store_true", help="process at most one job and exit")
    parser.add_argument("--status", action="store_true", help="print queue status and exit")
    parser.add_argument("--job-id", help="include safe lifecycle history for one job")
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
        print(
            "durable_jobs "
            f"by_status={dict(summary.by_status)} "
            f"by_type_version={dict(summary.by_type_version)} "
            f"attempts_by_status={dict(summary.attempt_counts_by_status)} "
            f"expired_leases={summary.expired_leases} "
            f"exhausted={summary.exhausted_jobs} "
            f"retry_waiting={summary.retry_waiting_jobs} "
            f"oldest_pending_age_seconds={summary.oldest_pending_age_seconds} "
            f"fairness_protected={summary.fairness_protected_jobs} "
            f"workers={_format_worker_summaries(summary)}"
        )
        if inspected_job_id is not None:
            if job_summary is None:
                print("durable_job_details missing=true")
            else:
                print(
                    "durable_job_details "
                    f"status={job_summary.status} "
                    f"job_type={job_summary.job_type} "
                    f"payload_version={job_summary.payload_version} "
                    f"attempt_count={job_summary.attempt_count} "
                    f"maximum_attempts={job_summary.maximum_attempts} "
                    f"last_safe_error_code={job_summary.last_safe_error_code} "
                    f"recent_events={_format_recent_events(job_summary)}"
                )
        return 0

    runner = DurableJobRunner(
        session_factory=SessionLocal,
        registry=registry,
        worker_identity=args.worker_id,
        worker_version=args.worker_version,
        policy=policy,
    )

    def request_shutdown(signum, frame) -> None:
        del signum, frame
        runner.request_shutdown()

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)

    try:
        while True:
            outcome = runner.process_once()
            print(f"durable_worker outcome={outcome}")
            if outcome == "shutdown":
                return 0
            if args.once:
                return 0
            time.sleep(policy.poll_interval_seconds)
    finally:
        runner.mark_stopped()


if __name__ == "__main__":
    raise SystemExit(main())
