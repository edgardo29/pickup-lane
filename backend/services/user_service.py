"""Shared user helpers used by user-adjacent routes and services."""

from sqlalchemy.exc import IntegrityError


def build_user_conflict_detail(exc: IntegrityError) -> str:
    # Map known unique-constraint failures to clearer API messages so local
    # API testing returns actionable errors instead of raw database text.
    error_text = str(exc.orig)

    constraint_messages = {
        "uq_users_auth_user_id": "A user with this auth_user_id already exists.",
        "uq_users_email": "A user with this email already exists.",
        "uq_users_phone": "A user with this phone already exists.",
        "uq_users_stripe_customer_id": (
            "A user with this stripe_customer_id already exists."
        ),
    }

    for constraint_name, message in constraint_messages.items():
        if constraint_name in error_text:
            return message

    return error_text
