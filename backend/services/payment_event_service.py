"""Shared payment event helpers for routes and webhook processing."""

from sqlalchemy.exc import IntegrityError


def build_payment_event_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "uq_payment_events_provider_event_id" in error_text:
        return "This provider event has already been recorded."

    if "ck_payment_events_provider" in error_text:
        return "provider must be 'stripe'."

    if "ck_payment_events_processing_status" in error_text:
        return "processing_status must be 'pending', 'processed', 'failed', or 'ignored'."

    if "ck_payment_events_event_type_not_empty" in error_text:
        return "event_type must not be empty."

    return error_text
