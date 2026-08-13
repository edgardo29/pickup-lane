from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

pytestmark = pytest.mark.suite_type("ordinary")


@dataclass
class _StripeFake:
    retrieved_setup_intents: list[str]
    retrieved_payment_methods: list[str]
    detached_payment_methods: list[str]
    default_payment_methods: list[str]


def _user() -> User:
    from backend.models import User

    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-04b1-card-user-{uuid.uuid4()}",
        role="player",
        email=f"ws02-04b1-card-{uuid.uuid4()}@example.invalid",
        first_name="Card",
        last_name="User",
        account_status="active",
        hosting_status="eligible",
        stripe_customer_id="cus_ws02_04b1",
    )


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _payment_method(
    user: User,
    index: int,
    *,
    status: str = "active",
    is_default: bool = False,
) -> UserPaymentMethod:
    from backend.models import UserPaymentMethod

    return UserPaymentMethod(
        id=uuid.uuid4(),
        user_id=user.id,
        stripe_customer_id=user.stripe_customer_id or "cus_ws02_04b1",
        stripe_payment_method_id=f"pm_existing_{index}",
        card_fingerprint=f"fingerprint-{index}",
        card_brand="visa",
        card_last4=f"{index:04d}"[-4:],
        exp_month=12,
        exp_year=2035,
        method_status=status,
        is_default=is_default,
        detached_at=datetime.now(timezone.utc) if status == "detached" else None,
    )


def _count(db: Session, model: type[object]) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _install_stripe_fake(monkeypatch: pytest.MonkeyPatch) -> _StripeFake:
    from backend.services import payment_method_service
    from backend.services.stripe_service import StripePaymentMethodCardResult, StripeSetupIntentResult

    fake = _StripeFake([], [], [], [])

    def retrieve_setup_intent(setup_intent_id: str) -> StripeSetupIntentResult:
        fake.retrieved_setup_intents.append(setup_intent_id)
        suffix = setup_intent_id.rsplit("_", 1)[-1]
        return StripeSetupIntentResult(
            id=setup_intent_id,
            client_secret=None,
            status="succeeded",
            customer_id="cus_ws02_04b1",
            payment_method_id=f"pm_new_{suffix}",
        )

    def retrieve_payment_method(payment_method_id: str) -> StripePaymentMethodCardResult:
        fake.retrieved_payment_methods.append(payment_method_id)
        suffix = payment_method_id.rsplit("_", 1)[-1]
        return StripePaymentMethodCardResult(
            id=payment_method_id,
            customer_id="cus_ws02_04b1",
            card_fingerprint=f"new-fingerprint-{suffix}",
            card_brand="visa",
            card_last4="4242",
            exp_month=12,
            exp_year=2035,
        )

    def detach_payment_method(payment_method_id: str) -> None:
        fake.detached_payment_methods.append(payment_method_id)

    def set_customer_default_payment_method(*, customer_id: str, payment_method_id: str) -> None:
        assert customer_id == "cus_ws02_04b1"
        fake.default_payment_methods.append(payment_method_id)

    monkeypatch.setattr(payment_method_service, "stripe_payments_enabled", lambda: True)
    monkeypatch.setattr(payment_method_service, "retrieve_setup_intent", retrieve_setup_intent)
    monkeypatch.setattr(payment_method_service, "retrieve_payment_method", retrieve_payment_method)
    monkeypatch.setattr(payment_method_service, "detach_payment_method", detach_payment_method)
    monkeypatch.setattr(payment_method_service, "set_customer_default_payment_method", set_customer_default_payment_method)
    return fake


@pytest.mark.requirement("WS02-04B1-R6")
def test_saved_card_serial_cap_counts_only_active_local_rows_and_rejects_sixth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import UserPaymentMethod
    from backend.services.payment_method_service import count_active_payment_methods, sync_saved_payment_method

    fake = _install_stripe_fake(monkeypatch)
    with _session() as db:
        user = _user()
        db.add(user)
        db.add_all([_payment_method(user, index, is_default=(index == 1)) for index in range(1, 5)])
        db.add(_payment_method(user, 50, status="detached"))
        db.add(_payment_method(user, 51, status="expired"))
        db.commit()

        assert count_active_payment_methods(db, user.id) == 4

        fifth = sync_saved_payment_method(
            db,
            user,
            setup_intent_id="seti_5",
            set_as_default=False,
        )

        assert fifth.method_status == "active"
        assert count_active_payment_methods(db, user.id) == 5
        assert _count(db, UserPaymentMethod) == 7

        with pytest.raises(HTTPException) as exc_info:
            sync_saved_payment_method(
                db,
                user,
                setup_intent_id="seti_6",
                set_as_default=False,
            )
        db.rollback()

        assert exc_info.value.status_code == 400
        assert count_active_payment_methods(db, user.id) == 5
        assert _count(db, UserPaymentMethod) == 7
        assert fake.retrieved_setup_intents == ["seti_5", "seti_6"]
        assert fake.retrieved_payment_methods == ["pm_new_5", "pm_new_6"]
        assert fake.detached_payment_methods == ["pm_new_6"]
        assert fake.default_payment_methods == []
