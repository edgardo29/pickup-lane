"""Test data shared by the F17 Game Checkout tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from backend.tests.conftest import FakeStripe, database_now
from backend.tests.factories import make_game, make_saved_card, make_user


def upcoming_game(db, **overrides):
    """A paid official game two days after the database's current time."""
    values = {"allow_guests": True, "max_guests_per_booking": 2, **overrides}
    return make_game(db, starts_at=database_now(db) + timedelta(days=2), **values)


def paying_player(db, stripe: FakeStripe | None = None, **overrides):
    """A complete player with a Stripe customer and one usable saved card."""
    values = {
        "date_of_birth": datetime(1990, 1, 1, tzinfo=UTC).date(),
        "stripe_customer_id": f"cus_test_{uuid.uuid4().hex[:10]}",
        **overrides,
    }
    user = make_user(db, **values)
    card = make_saved_card(db, user=user)
    if stripe is not None:
        from backend.services.stripe_service import StripePaymentMethodCardResult

        stripe.cards[card.stripe_payment_method_id] = StripePaymentMethodCardResult(
            id=card.stripe_payment_method_id,
            customer_id=user.stripe_customer_id,
            card_fingerprint=card.card_fingerprint,
            card_brand=card.card_brand,
            card_last4=card.card_last4,
            exp_month=card.exp_month,
            exp_year=card.exp_year,
        )
    return user, card
