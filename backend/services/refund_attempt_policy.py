"""Authoritative reduction and terminal proof for immutable refund attempts."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Refund, RefundEvent

TERMINAL_REFUND_STATUSES = frozenset({"succeeded", "failed", "cancelled"})
UNSUCCESSFUL_REFUND_STATUSES = frozenset({"failed", "cancelled"})
AUTHORITATIVE_PROVIDER_EVENT_TYPES = frozenset(
    {"provider_result_recorded", "reconciliation_checked"}
)


@dataclass(frozen=True)
class RefundAttemptEvidence:
    status: str
    amount_cents: int
    currency: str
    request_key: str | None
    provider: str | None
    provider_refund_id: str | None
    provider_charge_id: str | None
    identity_consistent: bool


def refund_attempt_identity_matches_refund(
    refund: Refund,
    *,
    attempt_number: int,
    attempt: RefundAttemptEvidence,
) -> bool:
    """Validate an immutable attempt snapshot against its owning Refund."""
    expected_request_key = (
        f"refund:{refund.id}:attempt:{attempt_number}"
        if attempt_number > 0
        else None
    )
    return bool(
        attempt.identity_consistent
        and attempt.amount_cents > 0
        and attempt.currency == refund.currency
        and attempt.request_key == expected_request_key
        and attempt.provider == refund.provider
        and attempt.provider_charge_id == refund.provider_charge_id
        and (
            attempt_number != refund.current_attempt_number
            or (
                attempt.amount_cents == refund.amount_cents
                and attempt.provider_refund_id == refund.provider_refund_id
            )
        )
    )


def refund_event_has_authoritative_provider_observation(
    event: RefundEvent,
) -> bool:
    """Return whether an event carries a validated provider status identity."""
    return (
        event.event_type in AUTHORITATIVE_PROVIDER_EVENT_TYPES
        and event.provider == "stripe"
        and event.provider_refund_id is not None
        and event.provider_status
        in {"processing", "succeeded", "failed", "cancelled"}
        and event.new_refund_status == event.provider_status
    )


def refund_event_has_authoritative_attempt_status(event: RefundEvent) -> bool:
    """Return whether an event can prove an immutable attempt state.

    Provider observations must carry matching normalized provider and refund
    statuses. Local terminal evidence is accepted only when the writer records
    the explicit fact that no provider call started. Other local status events
    remain audit history and cannot prove that an attempt is incapable of later
    returning value.
    """
    new_status = event.new_refund_status
    if new_status is None:
        return False
    if event.event_type in AUTHORITATIVE_PROVIDER_EVENT_TYPES:
        return (
            refund_event_has_authoritative_provider_observation(event)
            and event.provider_status in TERMINAL_REFUND_STATUSES
        )
    return (
        event.event_type == "local_status_changed"
        and new_status in UNSUCCESSFUL_REFUND_STATUSES
        and event.provider_refund_id is None
        and event.provider_status is None
        and (event.event_metadata or {}).get("provider_call_started") is False
    )


def reduce_refund_attempt_status(
    current_status: str | None,
    observed_status: str | None,
) -> str | None:
    """Reduce one status-bearing observation without regressing settled truth."""
    if observed_status is None:
        return current_status
    if current_status == "succeeded":
        return current_status
    if current_status in {"failed", "cancelled"}:
        return "succeeded" if observed_status == "succeeded" else current_status
    return observed_status


def reduce_refund_attempt_events(
    events: Iterable[RefundEvent],
) -> dict[int, str]:
    """Return states reduced only from authoritative attempt evidence."""
    states: dict[int, str] = {}
    for event in events:
        if not refund_event_has_authoritative_attempt_status(event):
            continue
        reduced = reduce_refund_attempt_status(
            states.get(event.attempt_number), event.new_refund_status
        )
        if reduced is not None:
            states[event.attempt_number] = reduced
    return states


def reduce_refund_attempt_evidence(
    events: Iterable[RefundEvent],
) -> dict[int, RefundAttemptEvidence]:
    """Reduce authoritative status plus its immutable attempt snapshot."""
    evidence: dict[int, RefundAttemptEvidence] = {}
    for event in events:
        provider_observation = refund_event_has_authoritative_provider_observation(
            event
        )
        terminal_observation = refund_event_has_authoritative_attempt_status(event)
        if not provider_observation and not terminal_observation:
            continue
        prior = evidence.get(event.attempt_number)
        status = prior.status if prior is not None else "processing"
        if terminal_observation:
            status = reduce_refund_attempt_status(status, event.new_refund_status)
        if status is None:
            continue
        snapshot = (
            event.attempt_amount_cents,
            event.attempt_currency,
            event.attempt_request_key,
            event.provider,
            event.provider_refund_id,
            event.provider_charge_id,
        )
        prior_snapshot = (
            prior.amount_cents,
            prior.currency,
            prior.request_key,
            prior.provider,
            prior.provider_refund_id,
            prior.provider_charge_id,
        ) if prior is not None else snapshot
        evidence[event.attempt_number] = RefundAttemptEvidence(
            status=status,
            # A conflicting success must never understate potentially returned cash.
            amount_cents=max(
                event.attempt_amount_cents,
                prior.amount_cents if prior is not None else 0,
            ),
            currency=event.attempt_currency,
            request_key=event.attempt_request_key,
            provider=event.provider,
            provider_refund_id=event.provider_refund_id,
            provider_charge_id=event.provider_charge_id,
            identity_consistent=(
                (prior.identity_consistent if prior is not None else True)
                and prior_snapshot == snapshot
            ),
        )
    return evidence


def canonical_provider_attempt_event(
    events: Iterable[RefundEvent],
    *,
    attempt_number: int,
) -> RefundEvent | None:
    """Return the canonical provider observation for one consistent attempt."""
    rows = tuple(events)
    attempt = reduce_refund_attempt_evidence(rows).get(attempt_number)
    if (
        attempt is None
        or not attempt.identity_consistent
        or attempt.provider_refund_id is None
    ):
        return None
    for event in rows:
        if (
            event.attempt_number == attempt_number
            and refund_event_has_authoritative_provider_observation(event)
            and event.attempt_amount_cents == attempt.amount_cents
            and event.attempt_currency == attempt.currency
            and event.attempt_request_key == attempt.request_key
            and event.provider == attempt.provider
            and event.provider_refund_id == attempt.provider_refund_id
            and event.provider_charge_id == attempt.provider_charge_id
        ):
            return event
    return None


def refund_attempt_evidence_for_refunds(
    db: Session,
    refund_ids: Iterable,
) -> dict[object, dict[int, RefundAttemptEvidence]]:
    ids = tuple(dict.fromkeys(refund_ids))
    if not ids:
        return {}
    events = db.scalars(
        select(RefundEvent)
        .where(RefundEvent.refund_id.in_(ids))
        .order_by(
            RefundEvent.refund_id.asc(),
            RefundEvent.attempt_number.asc(),
            RefundEvent.occurred_at.asc(),
            RefundEvent.id.asc(),
        )
    ).all()
    grouped: dict[object, list[RefundEvent]] = {refund_id: [] for refund_id in ids}
    for event in events:
        grouped.setdefault(event.refund_id, []).append(event)
    return {
        refund_id: reduce_refund_attempt_evidence(refund_events)
        for refund_id, refund_events in grouped.items()
    }


def expected_refund_attempt_numbers(
    refund: Refund,
    evidence: dict[int, RefundAttemptEvidence] | None = None,
) -> set[int]:
    """Return every attempt number whose outcome must be proved."""
    known = evidence or {}
    if refund.current_attempt_number == 0:
        return {0}
    first_attempt = 0 if 0 in known else 1
    return set(range(first_attempt, refund.current_attempt_number + 1))


def authoritative_succeeded_amount_for_refunds(
    db: Session,
    refunds: Iterable[Refund],
) -> int:
    rows = tuple(refunds)
    evidence = refund_attempt_evidence_for_refunds(db, (row.id for row in rows))
    return sum(
        attempt.amount_cents
        for row in rows
        for attempt_number, attempt in evidence.get(row.id, {}).items()
        if attempt.status == "succeeded"
        and refund_attempt_identity_matches_refund(
            row,
            attempt_number=attempt_number,
            attempt=attempt,
        )
    )


def refund_attempt_statuses(db: Session, refund_id) -> dict[int, str]:
    events = db.scalars(
        select(RefundEvent)
        .where(RefundEvent.refund_id == refund_id)
        .order_by(
            RefundEvent.attempt_number.asc(),
            RefundEvent.occurred_at.asc(),
            RefundEvent.id.asc(),
        )
    ).all()
    return reduce_refund_attempt_events(events)


def refund_has_only_terminal_attempts(db: Session, refund: Refund) -> bool:
    """Prove every started attempt has an absorbing terminal observation."""
    if (
        refund.refund_status not in {"failed", "cancelled"}
        or refund.provider_status in {"processing", "unknown"}
        or refund.automatic_mutation_blocked_reason is not None
    ):
        return False
    return refund_expected_attempts_are_terminal(db, refund)


def refund_expected_attempts_are_terminal(db: Session, refund: Refund) -> bool:
    """Prove complete, identity-consistent terminal coverage for a Refund."""
    statuses = refund_attempt_statuses(db, refund.id)
    evidence = refund_attempt_evidence_for_refunds(db, (refund.id,)).get(
        refund.id, {}
    )
    expected_attempts = expected_refund_attempt_numbers(refund, evidence)
    if set(statuses) != expected_attempts:
        return False
    return all(
        status in TERMINAL_REFUND_STATUSES
        and refund_attempt_identity_matches_refund(
            refund,
            attempt_number=attempt_number,
            attempt=evidence[attempt_number],
        )
        for attempt_number, status in statuses.items()
    )


def refund_has_only_unsuccessful_attempts(db: Session, refund: Refund) -> bool:
    """Prove every expected attempt is terminal and returned no cash."""
    if not refund_has_only_terminal_attempts(db, refund):
        return False
    return all(
        status in UNSUCCESSFUL_REFUND_STATUSES
        for status in refund_attempt_statuses(db, refund.id).values()
    )
