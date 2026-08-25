from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from backend.observability.timeouts import DependencyMutationTimeoutUnknownError

pytestmark = pytest.mark.no_db_cleanup


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self.value = value

    def one(self) -> object:
        return self.value

    def all(self) -> list[object]:
        if isinstance(self.value, list):
            return self.value
        return [self.value]


@dataclass
class _RecordingSession:
    added: list[object]
    added_many: list[object]
    deleted: list[object] = field(default_factory=list)
    scalar_values: list[object | None] = field(default_factory=list)
    commit_calls: int = 0
    flush_calls: int = 0
    rollback_calls: int = 0
    commit_failures: set[int] = field(default_factory=set)

    def add(self, value: object) -> None:
        self.added.append(value)

    def add_all(self, values) -> None:
        self.added_many.extend(values)

    def flush(self) -> None:
        self.flush_calls += 1

    def commit(self) -> None:
        self.commit_calls += 1
        if self.commit_calls in self.commit_failures:
            raise SQLAlchemyError(f"commit {self.commit_calls} failed")

    def rollback(self) -> None:
        self.rollback_calls += 1

    def refresh(self, value: object) -> None:
        del value

    def delete(self, value: object) -> None:
        self.deleted.append(value)

    def get(self, model, ident):
        del model
        for value in reversed(self.added):
            if getattr(value, "id", None) == ident:
                return value
        return None

    def scalar(self, statement):
        del statement
        if self.scalar_values:
            return self.scalar_values.pop(0)
        return None

    def scalars(self, statement):
        entity = statement.column_descriptions[0].get("entity")
        for value in reversed(self.added):
            if isinstance(value, entity):
                return _ScalarResult(value)
        raise AssertionError(f"no scalar result for {entity}")


def _stripe_timeout(operation: str) -> DependencyMutationTimeoutUnknownError:
    return DependencyMutationTimeoutUnknownError(
        provider_kind="stripe",
        operation=operation,
    )


@pytest.mark.requirement("WS04-02A-R2", "WS04-02A-R3", "WS04-02A-R4")
def test_checkout_create_timeout_leaves_committed_local_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import Payment
    from backend.schemas.checkout_schema import GameCheckoutPaymentIntentCreate
    import backend.services.checkout_service as checkout_service
    from backend.services.game_credit_service import GameCreditApplication

    game_id = uuid.uuid4()
    current_user = SimpleNamespace(
        id=uuid.uuid4(),
        stripe_customer_id="cus_ws04_02a_checkout",
    )
    db_game = SimpleNamespace(
        id=game_id,
        currency="USD",
        price_per_player_cents=1200,
        total_spots=12,
    )
    saved_payment_method = SimpleNamespace(
        id=uuid.uuid4(),
        stripe_payment_method_id="pm_ws04_02a_saved",
    )
    db = _RecordingSession(added=[], added_many=[])
    provider_create_events: list[tuple[str, int]] = []
    provider_confirm_calls: list[str] = []

    monkeypatch.setattr(
        checkout_service,
        "validate_checkout_return_url",
        lambda return_url, *, game_id: return_url,
    )
    monkeypatch.setattr(
        checkout_service,
        "get_locked_active_game_or_404",
        lambda db, game_id: db_game,
    )
    monkeypatch.setattr(checkout_service, "require_checkout_game_open", lambda *args: None)
    monkeypatch.setattr(checkout_service, "require_stripe_payments_enabled", lambda: None)
    monkeypatch.setattr(checkout_service, "expire_stale_pending_checkouts", lambda *args: None)
    monkeypatch.setattr(checkout_service, "get_reusable_pending_checkout", lambda *args, **kwargs: None)
    monkeypatch.setattr(checkout_service, "get_existing_active_participant", lambda *args: None)
    monkeypatch.setattr(checkout_service, "get_existing_active_waitlist_entry", lambda *args: None)
    monkeypatch.setattr(checkout_service, "count_roster_players", lambda *args, **kwargs: 0)
    monkeypatch.setattr(checkout_service, "validate_guest_count", lambda game, guest_count: guest_count)
    monkeypatch.setattr(
        checkout_service,
        "calculate_user_game_credit_application",
        lambda *args, **kwargs: GameCreditApplication(
            available_credit_cents=0,
            credit_applied_cents=0,
            minimum_charge_adjustment_cents=0,
            final_amount_due_cents=1200,
            stripe_amount_cents=1200,
            payment_required=True,
        ),
    )
    monkeypatch.setattr(checkout_service, "get_stripe_currency", lambda: "USD")
    monkeypatch.setattr(
        checkout_service,
        "get_current_user_saved_payment_method_for_checkout",
        lambda *args, **kwargs: saved_payment_method,
    )
    monkeypatch.setattr(checkout_service, "build_booking_participants", lambda *args, **kwargs: [])
    monkeypatch.setattr(checkout_service, "get_user_display_name", lambda current_user: "Checkpoint User")
    monkeypatch.setattr(checkout_service, "sync_game_capacity_status", lambda *args, **kwargs: None)

    def create_payment_intent(**kwargs):
        provider_create_events.append((kwargs["idempotency_key"], db.commit_calls))
        raise _stripe_timeout("stripe.payment_intent.create")

    def confirm_payment_intent(payment_intent_id: str, **kwargs):
        del kwargs
        provider_confirm_calls.append(payment_intent_id)
        raise AssertionError("checkout must not confirm after create timeout")

    monkeypatch.setattr(checkout_service, "create_payment_intent", create_payment_intent)
    monkeypatch.setattr(checkout_service, "confirm_payment_intent", confirm_payment_intent)

    with pytest.raises(DependencyMutationTimeoutUnknownError) as exc_info:
        checkout_service.create_game_checkout_payment_intent_workflow(
            db,
            game_id,
            GameCheckoutPaymentIntentCreate(
                guest_count=0,
                payment_method_id=saved_payment_method.id,
            ),
            current_user,
        )

    staged_payments = [value for value in db.added if isinstance(value, Payment)]
    assert exc_info.value.operation == "stripe.payment_intent.create"
    assert len(staged_payments) == 1
    assert provider_create_events == [(staged_payments[0].idempotency_key, 1)]
    assert provider_confirm_calls == []
    assert db.commit_calls == 1
    assert db.rollback_calls == 0
    assert staged_payments[0].provider_payment_intent_id is None
    assert staged_payments[0].payment_status == "requires_payment_method"


@pytest.mark.requirement("WS04-02A-R2", "WS04-02A-R4", "WS04-02A-R5")
def test_checkout_provider_success_then_local_recording_failure_is_honest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import Payment
    from backend.schemas.checkout_schema import GameCheckoutPaymentIntentCreate
    import backend.services.checkout_service as checkout_service
    from backend.services.game_credit_service import GameCreditApplication

    game_id = uuid.uuid4()
    current_user = SimpleNamespace(
        id=uuid.uuid4(),
        stripe_customer_id="cus_ws04_02a_checkout",
    )
    db_game = SimpleNamespace(
        id=game_id,
        currency="USD",
        price_per_player_cents=1200,
        total_spots=12,
    )
    saved_payment_method = SimpleNamespace(
        id=uuid.uuid4(),
        stripe_payment_method_id="pm_ws04_02a_saved",
    )
    db = _RecordingSession(
        added=[],
        added_many=[],
        commit_failures={2},
    )
    provider_create_events: list[tuple[str, int]] = []
    provider_confirm_calls: list[str] = []

    monkeypatch.setattr(
        checkout_service,
        "validate_checkout_return_url",
        lambda return_url, *, game_id: return_url,
    )
    monkeypatch.setattr(
        checkout_service,
        "get_locked_active_game_or_404",
        lambda db, game_id: db_game,
    )
    monkeypatch.setattr(checkout_service, "require_checkout_game_open", lambda *args: None)
    monkeypatch.setattr(checkout_service, "require_stripe_payments_enabled", lambda: None)
    monkeypatch.setattr(checkout_service, "expire_stale_pending_checkouts", lambda *args: None)
    monkeypatch.setattr(checkout_service, "get_reusable_pending_checkout", lambda *args, **kwargs: None)
    monkeypatch.setattr(checkout_service, "get_existing_active_participant", lambda *args: None)
    monkeypatch.setattr(checkout_service, "get_existing_active_waitlist_entry", lambda *args: None)
    monkeypatch.setattr(checkout_service, "count_roster_players", lambda *args, **kwargs: 0)
    monkeypatch.setattr(checkout_service, "validate_guest_count", lambda game, guest_count: guest_count)
    monkeypatch.setattr(
        checkout_service,
        "calculate_user_game_credit_application",
        lambda *args, **kwargs: GameCreditApplication(
            available_credit_cents=0,
            credit_applied_cents=0,
            minimum_charge_adjustment_cents=0,
            final_amount_due_cents=1200,
            stripe_amount_cents=1200,
            payment_required=True,
        ),
    )
    monkeypatch.setattr(checkout_service, "get_stripe_currency", lambda: "USD")
    monkeypatch.setattr(
        checkout_service,
        "get_current_user_saved_payment_method_for_checkout",
        lambda *args, **kwargs: saved_payment_method,
    )
    monkeypatch.setattr(checkout_service, "build_booking_participants", lambda *args, **kwargs: [])
    monkeypatch.setattr(checkout_service, "get_user_display_name", lambda current_user: "Checkpoint User")
    monkeypatch.setattr(checkout_service, "sync_game_capacity_status", lambda *args, **kwargs: None)

    def create_payment_intent(**kwargs):
        provider_create_events.append((kwargs["idempotency_key"], db.commit_calls))
        return SimpleNamespace(
            id="pi_ws04_02a_checkout_recording_failed",
            latest_charge_id="ch_ws04_02a_checkout_recording_failed",
            status="requires_action",
            client_secret="pi_secret_ws04_02a",
        )

    def confirm_payment_intent(payment_intent_id: str, **kwargs):
        del kwargs
        provider_confirm_calls.append(payment_intent_id)
        raise AssertionError("checkout must not confirm before provider result records")

    monkeypatch.setattr(checkout_service, "create_payment_intent", create_payment_intent)
    monkeypatch.setattr(checkout_service, "confirm_payment_intent", confirm_payment_intent)

    with pytest.raises(HTTPException) as exc_info:
        checkout_service.create_game_checkout_payment_intent_workflow(
            db,
            game_id,
            GameCheckoutPaymentIntentCreate(
                guest_count=0,
                payment_method_id=saved_payment_method.id,
            ),
            current_user,
        )

    staged_payments = [value for value in db.added if isinstance(value, Payment)]
    assert exc_info.value.status_code == 409
    assert "Stripe created this payment intent" in exc_info.value.detail
    assert "could not create this payment intent" not in exc_info.value.detail
    assert provider_create_events == [(staged_payments[0].idempotency_key, 1)]
    assert provider_confirm_calls == []
    assert db.commit_calls == 2
    assert db.rollback_calls == 1


@pytest.mark.requirement("WS04-02A-R2", "WS04-02A-R4", "WS04-02A-R5")
def test_community_publish_create_timeout_keeps_attempt_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import CommunityPublishAttempt, Payment
    import backend.services.community_game_publish_service as publish_service

    payment_method_id = uuid.uuid4()
    host = SimpleNamespace(
        id=uuid.uuid4(),
        stripe_customer_id="cus_ws04_02a_publish",
    )
    publish_request = SimpleNamespace(
        payment_method_id=payment_method_id,
        model_dump=lambda mode="json": {"source": "ws04-02a", "mode": mode},
    )
    saved_payment_method = SimpleNamespace(id=payment_method_id)
    db = _RecordingSession(added=[], added_many=[])
    provider_create_events: list[tuple[str, int]] = []

    monkeypatch.setattr(publish_service, "get_stripe_currency", lambda: "USD")
    monkeypatch.setattr(
        publish_service,
        "get_current_user_saved_payment_method_for_checkout",
        lambda *args, **kwargs: saved_payment_method,
    )

    def create_payment_intent(**kwargs):
        provider_create_events.append((kwargs["idempotency_key"], db.commit_calls))
        raise _stripe_timeout("stripe.payment_intent.create")

    monkeypatch.setattr(publish_service, "create_payment_intent", create_payment_intent)

    with pytest.raises(DependencyMutationTimeoutUnknownError) as exc_info:
        publish_service.create_paid_publish_attempt(
            db,
            publish_request=publish_request,
            host=host,
            starts_on_local=date(2035, 5, 2),
            now=datetime.now(timezone.utc),
        )

    staged_attempts = {
        value.id: value
        for value in db.added
        if isinstance(value, CommunityPublishAttempt)
    }
    staged_payments = [value for value in db.added if isinstance(value, Payment)]
    assert exc_info.value.operation == "stripe.payment_intent.create"
    assert len(staged_attempts) == 1
    assert len(staged_payments) == 1
    staged_attempt = next(iter(staged_attempts.values()))
    assert staged_attempt.payment_id == staged_payments[0].id
    assert provider_create_events == [(staged_payments[0].idempotency_key, 1)]
    assert db.commit_calls == 1
    assert db.rollback_calls == 0
    assert staged_payments[0].provider_payment_intent_id is None
    assert staged_attempt.attempt_status == "requires_payment_method"


@pytest.mark.requirement("WS04-02A-R2", "WS04-02A-R4", "WS04-02A-R5")
def test_community_publish_provider_success_then_local_recording_failure_is_honest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import CommunityPublishAttempt, Payment
    import backend.services.community_game_publish_service as publish_service

    payment_method_id = uuid.uuid4()
    host = SimpleNamespace(
        id=uuid.uuid4(),
        stripe_customer_id="cus_ws04_02a_publish",
    )
    publish_request = SimpleNamespace(
        payment_method_id=payment_method_id,
        model_dump=lambda mode="json": {"source": "ws04-02a", "mode": mode},
    )
    saved_payment_method = SimpleNamespace(
        id=payment_method_id,
        stripe_payment_method_id="pm_ws04_02a_publish",
    )
    db = _RecordingSession(
        added=[],
        added_many=[],
        commit_failures={2},
    )
    provider_create_events: list[tuple[str, int]] = []
    provider_confirm_calls: list[str] = []

    monkeypatch.setattr(publish_service, "get_stripe_currency", lambda: "USD")
    monkeypatch.setattr(
        publish_service,
        "get_current_user_saved_payment_method_for_checkout",
        lambda *args, **kwargs: saved_payment_method,
    )

    def create_payment_intent(**kwargs):
        provider_create_events.append((kwargs["idempotency_key"], db.commit_calls))
        return SimpleNamespace(
            id="pi_ws04_02a_publish_recording_failed",
            latest_charge_id="ch_ws04_02a_publish_recording_failed",
            status="requires_payment_method",
            client_secret="pi_secret_ws04_02a_publish",
        )

    def confirm_payment_intent(payment_intent_id: str, **kwargs):
        del kwargs
        provider_confirm_calls.append(payment_intent_id)
        raise AssertionError("publish must not confirm before provider result records")

    monkeypatch.setattr(publish_service, "create_payment_intent", create_payment_intent)
    monkeypatch.setattr(publish_service, "confirm_payment_intent", confirm_payment_intent)

    with pytest.raises(HTTPException) as exc_info:
        publish_service.create_paid_publish_attempt(
            db,
            publish_request=publish_request,
            host=host,
            starts_on_local=date(2035, 5, 2),
            now=datetime.now(timezone.utc),
        )

    staged_attempts = [
        value for value in db.added if isinstance(value, CommunityPublishAttempt)
    ]
    staged_payments = [value for value in db.added if isinstance(value, Payment)]
    assert exc_info.value.status_code == 409
    assert "Stripe created this publish fee payment intent" in exc_info.value.detail
    assert "could not create this publish fee payment" not in exc_info.value.detail
    assert provider_create_events == [(staged_payments[0].idempotency_key, 1)]
    assert provider_confirm_calls == []
    assert db.commit_calls == 2
    assert db.rollback_calls == 1
    assert staged_attempts[0].payment_id == staged_payments[0].id


@pytest.mark.requirement("WS04-02A-R2", "WS04-02A-R4", "WS04-02A-R5")
def test_paid_waitlist_auto_promotion_create_timeout_keeps_committed_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import Payment
    import backend.services.game_waitlist_service as waitlist_service

    now = datetime.now(timezone.utc)
    buyer_user_id = uuid.uuid4()
    db = _RecordingSession(added=[], added_many=[])
    db_game = SimpleNamespace(id=uuid.uuid4())
    waitlist_entry = SimpleNamespace(
        id=uuid.uuid4(),
        auto_charge_consent_at=now,
        auto_charge_consent_version="terms-v1",
        authorized_stripe_payment_method_id="pm_ws04_02a_waitlist",
        authorized_amount_cents=1600,
        waitlist_status="active",
        promoted_at=None,
    )
    booking = SimpleNamespace(
        id=uuid.uuid4(),
        buyer_user_id=buyer_user_id,
        total_cents=1600,
        currency="USD",
    )
    booking_participant = SimpleNamespace(id=uuid.uuid4())
    provider_create_events: list[tuple[str, int]] = []
    provider_confirm_calls: list[str] = []

    def create_payment_intent(**kwargs):
        provider_create_events.append((kwargs["idempotency_key"], db.commit_calls))
        raise _stripe_timeout("stripe.payment_intent.create")

    def confirm_payment_intent(payment_intent_id: str, **kwargs):
        del kwargs
        provider_confirm_calls.append(payment_intent_id)
        raise AssertionError("waitlist must not confirm after create timeout")

    monkeypatch.setattr(waitlist_service, "create_payment_intent", create_payment_intent)
    monkeypatch.setattr(waitlist_service, "confirm_payment_intent", confirm_payment_intent)

    status_value, held_spots = waitlist_service.attempt_paid_waitlist_auto_promotion(
        db,
        db_game,
        waitlist_entry,
        booking,
        [booking_participant],
        now,
    )

    staged_payments = {
        value.id: value for value in db.added if isinstance(value, Payment)
    }
    staged_payment = next(iter(staged_payments.values()))
    assert status_value == "processing"
    assert held_spots == 1
    assert len(staged_payments) == 1
    assert provider_create_events == [(staged_payment.idempotency_key, 1)]
    assert provider_confirm_calls == []
    assert db.commit_calls == 2
    assert db.rollback_calls == 0
    assert waitlist_entry.waitlist_status == "payment_processing"
    assert booking.booking_status == "pending_payment"
    assert booking_participant.participant_status == "pending_payment"
    assert staged_payment.provider_payment_intent_id is None
    assert staged_payment.payment_status == "processing"


@pytest.mark.requirement("WS04-02A-R2", "WS04-02A-R4", "WS04-02A-R5")
def test_paid_waitlist_auto_promotion_provider_result_records_before_confirm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import Payment
    import backend.services.game_waitlist_service as waitlist_service

    now = datetime.now(timezone.utc)
    buyer_user_id = uuid.uuid4()
    db = _RecordingSession(added=[], added_many=[], commit_failures={2})
    db_game = SimpleNamespace(id=uuid.uuid4())
    waitlist_entry = SimpleNamespace(
        id=uuid.uuid4(),
        auto_charge_consent_at=now,
        auto_charge_consent_version="terms-v1",
        authorized_stripe_payment_method_id="pm_ws04_02a_waitlist",
        authorized_amount_cents=1600,
        waitlist_status="active",
        promoted_at=None,
    )
    booking = SimpleNamespace(
        id=uuid.uuid4(),
        buyer_user_id=buyer_user_id,
        total_cents=1600,
        currency="USD",
    )
    booking_participant = SimpleNamespace(id=uuid.uuid4())
    provider_create_events: list[tuple[str, int]] = []
    provider_confirm_calls: list[str] = []

    def create_payment_intent(**kwargs):
        provider_create_events.append((kwargs["idempotency_key"], db.commit_calls))
        return SimpleNamespace(
            id="pi_ws04_02a_waitlist_recording_failed",
            latest_charge_id=None,
            status="requires_payment_method",
        )

    def confirm_payment_intent(payment_intent_id: str, **kwargs):
        del kwargs
        provider_confirm_calls.append(payment_intent_id)
        raise AssertionError("waitlist must not confirm before provider result records")

    monkeypatch.setattr(waitlist_service, "create_payment_intent", create_payment_intent)
    monkeypatch.setattr(waitlist_service, "confirm_payment_intent", confirm_payment_intent)

    with pytest.raises(HTTPException) as exc_info:
        waitlist_service.attempt_paid_waitlist_auto_promotion(
            db,
            db_game,
            waitlist_entry,
            booking,
            [booking_participant],
            now,
        )

    staged_payments = {
        value.id: value for value in db.added if isinstance(value, Payment)
    }
    staged_payment = next(iter(staged_payments.values()))
    assert exc_info.value.status_code == 409
    assert "Stripe created or updated this waitlist payment" in exc_info.value.detail
    assert provider_create_events == [(staged_payment.idempotency_key, 1)]
    assert provider_confirm_calls == []
    assert db.commit_calls == 2
    assert db.rollback_calls == 1
    assert staged_payment.provider_payment_intent_id == (
        "pi_ws04_02a_waitlist_recording_failed"
    )


@pytest.mark.requirement("WS04-02A-R2", "WS04-02A-R4", "WS04-02A-R5")
def test_saved_card_sync_default_provider_success_local_failure_is_honest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.payment_method_service as payment_service

    current_user = SimpleNamespace(
        id=uuid.uuid4(),
        stripe_customer_id="cus_ws04_02a_saved_card",
    )
    db = _RecordingSession(added=[], added_many=[], commit_failures={1})
    provider_default_updates: list[tuple[str, str]] = []

    monkeypatch.setattr(payment_service, "require_stripe_payments_enabled", lambda: None)
    monkeypatch.setattr(
        payment_service,
        "retrieve_setup_intent",
        lambda setup_intent_id: SimpleNamespace(
            id=setup_intent_id,
            customer_id=current_user.stripe_customer_id,
            status="succeeded",
            payment_method_id="pm_ws04_02a_sync",
        ),
    )
    monkeypatch.setattr(
        payment_service,
        "retrieve_payment_method",
        lambda payment_method_id: SimpleNamespace(
            id=payment_method_id,
            customer_id=current_user.stripe_customer_id,
            card_fingerprint="card_ws04_02a_sync",
            card_brand="visa",
            card_last4="4242",
            exp_month=12,
            exp_year=2035,
        ),
    )
    monkeypatch.setattr(payment_service, "count_active_payment_methods", lambda *args: 0)
    monkeypatch.setattr(payment_service, "unset_other_active_defaults", lambda *args: None)

    def set_customer_default_payment_method(**kwargs):
        provider_default_updates.append(
            (kwargs["customer_id"], kwargs["payment_method_id"])
        )

    monkeypatch.setattr(
        payment_service,
        "set_customer_default_payment_method",
        set_customer_default_payment_method,
    )

    with pytest.raises(HTTPException) as exc_info:
        payment_service.sync_saved_payment_method(
            db,
            current_user,
            setup_intent_id="seti_ws04_02a_sync",
            set_as_default=True,
        )

    assert exc_info.value.status_code == 409
    assert "Stripe updated the default payment method" in exc_info.value.detail
    assert provider_default_updates == [
        (current_user.stripe_customer_id, "pm_ws04_02a_sync")
    ]
    assert db.commit_calls == 1
    assert db.rollback_calls == 1


@pytest.mark.requirement("WS04-02A-R2", "WS04-02A-R4", "WS04-02A-R5")
def test_saved_card_default_provider_success_local_failure_is_honest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.payment_method_service as payment_service

    payment_method = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        stripe_payment_method_id="pm_ws04_02a_default",
        method_status="active",
        is_default=False,
    )
    current_user = SimpleNamespace(
        id=payment_method.user_id,
        stripe_customer_id="cus_ws04_02a_default",
    )
    db = _RecordingSession(added=[], added_many=[], commit_failures={1})
    provider_default_updates: list[tuple[str, str]] = []

    monkeypatch.setattr(
        payment_service,
        "get_owned_payment_method_or_404",
        lambda *args: payment_method,
    )
    monkeypatch.setattr(payment_service, "unset_other_active_defaults", lambda *args: None)

    def set_customer_default_payment_method(**kwargs):
        provider_default_updates.append(
            (kwargs["customer_id"], kwargs["payment_method_id"])
        )

    monkeypatch.setattr(
        payment_service,
        "set_customer_default_payment_method",
        set_customer_default_payment_method,
    )

    with pytest.raises(HTTPException) as exc_info:
        payment_service.set_default_saved_payment_method(
            db,
            current_user,
            payment_method.id,
        )

    assert exc_info.value.status_code == 409
    assert "Stripe updated the default payment method" in exc_info.value.detail
    assert provider_default_updates == [
        (current_user.stripe_customer_id, payment_method.stripe_payment_method_id)
    ]
    assert db.commit_calls == 1
    assert db.rollback_calls == 1


@pytest.mark.requirement("WS04-02A-R2", "WS04-02A-R4", "WS04-02A-R5")
def test_saved_card_detach_provider_success_local_failure_is_honest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.payment_method_service as payment_service

    payment_method = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        stripe_customer_id="cus_ws04_02a_detach",
        stripe_payment_method_id="pm_ws04_02a_detach",
        method_status="active",
        is_default=False,
    )
    current_user = SimpleNamespace(
        id=payment_method.user_id,
        stripe_customer_id=payment_method.stripe_customer_id,
    )
    db = _RecordingSession(added=[], added_many=[], commit_failures={1})
    provider_detaches: list[str] = []

    monkeypatch.setattr(
        payment_service,
        "get_owned_payment_method_or_404",
        lambda *args: payment_method,
    )

    def detach_payment_method(payment_method_id: str):
        provider_detaches.append(payment_method_id)

    monkeypatch.setattr(payment_service, "detach_payment_method", detach_payment_method)

    with pytest.raises(HTTPException) as exc_info:
        payment_service.detach_saved_payment_method(
            db,
            current_user,
            payment_method.id,
        )

    assert exc_info.value.status_code == 409
    assert "Stripe detached this payment method" in exc_info.value.detail
    assert provider_detaches == [payment_method.stripe_payment_method_id]
    assert db.commit_calls == 1
    assert db.rollback_calls == 1


@pytest.mark.requirement("WS04-02A-R2", "WS04-02A-R4", "WS04-02A-R5")
def test_admin_refund_retry_timeout_preserves_committed_retry_intent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.admin_money_refund_service as refund_service
    from backend.schemas.admin_money_refund_schema import AdminMoneyRefundRetryCreate

    db = _RecordingSession(added=[], added_many=[])
    refund_id = uuid.uuid4()
    payment_id = uuid.uuid4()
    admin_user = SimpleNamespace(id=uuid.uuid4())
    refund = SimpleNamespace(
        id=refund_id,
        payment_id=payment_id,
        booking_id=None,
        host_publish_fee_id=None,
        participant_id=None,
        amount_cents=500,
        currency="USD",
    )
    payment = SimpleNamespace(
        id=payment_id,
        payer_user_id=uuid.uuid4(),
        booking_id=uuid.uuid4(),
        provider_charge_id="ch_ws04_02a_retry",
        amount_cents=500,
        currency="USD",
    )
    admin_action = SimpleNamespace(id=uuid.uuid4())
    provider_events: list[tuple[str, int]] = []

    monkeypatch.setattr(refund_service, "get_existing_retry_action", lambda *args, **kwargs: None)
    monkeypatch.setattr(refund_service, "get_refund_for_retry_or_404", lambda *args, **kwargs: refund)
    monkeypatch.setattr(refund_service, "get_payment_for_retry_or_404", lambda *args, **kwargs: payment)
    monkeypatch.setattr(refund_service, "get_booking_for_retry", lambda *args, **kwargs: None)
    monkeypatch.setattr(refund_service, "get_host_publish_fee_for_retry", lambda *args, **kwargs: None)
    monkeypatch.setattr(refund_service, "validate_refund_retry", lambda *args, **kwargs: None)
    monkeypatch.setattr(refund_service, "refund_audit_snapshot", lambda refund: {"status": "failed"})
    monkeypatch.setattr(refund_service, "refund_audit_metadata", lambda *args, **kwargs: {"source": "admin_money_refund_retry"})
    monkeypatch.setattr(refund_service, "record_admin_action", lambda *args, **kwargs: admin_action)

    def create_stripe_refund(**kwargs):
        provider_events.append((kwargs["idempotency_key"], db.commit_calls))
        raise _stripe_timeout("stripe.refund.create")

    monkeypatch.setattr(refund_service, "create_stripe_refund", create_stripe_refund)

    with pytest.raises(DependencyMutationTimeoutUnknownError) as exc_info:
        refund_service.retry_admin_money_refund(
            db,
            admin_user=admin_user,
            refund_id=refund_id,
            payload=AdminMoneyRefundRetryCreate(
                reason="retry timeout boundary",
                idempotency_key="ws04-02a-admin-refund",
            ),
        )

    assert exc_info.value.operation == "stripe.refund.create"
    assert provider_events == [("ws04-02a-admin-refund", 1)]
    assert db.flush_calls == 1
    assert db.commit_calls == 1
    assert db.rollback_calls == 0


@pytest.mark.requirement("WS04-02A-R2", "WS04-02A-R4", "WS04-02A-R5")
def test_admin_refund_retry_provider_success_records_metadata_before_local_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sqlalchemy.exc import IntegrityError

    import backend.services.admin_money_refund_service as refund_service
    from backend.schemas.admin_money_refund_schema import AdminMoneyRefundRetryCreate

    db = _RecordingSession(added=[], added_many=[])
    refund_id = uuid.uuid4()
    payment_id = uuid.uuid4()
    admin_user = SimpleNamespace(id=uuid.uuid4())
    refund = SimpleNamespace(
        id=refund_id,
        payment_id=payment_id,
        booking_id=None,
        host_publish_fee_id=None,
        participant_id=None,
        amount_cents=500,
        currency="USD",
        provider="stripe",
    )
    payment = SimpleNamespace(
        id=payment_id,
        payer_user_id=uuid.uuid4(),
        booking_id=uuid.uuid4(),
        provider_charge_id="ch_ws04_02a_retry",
        amount_cents=500,
        currency="USD",
    )
    admin_action = SimpleNamespace(id=uuid.uuid4(), metadata_=None)
    provider_events: list[tuple[str, int]] = []

    monkeypatch.setattr(refund_service, "get_existing_retry_action", lambda *args, **kwargs: None)
    monkeypatch.setattr(refund_service, "get_refund_for_retry_or_404", lambda *args, **kwargs: refund)
    monkeypatch.setattr(refund_service, "get_payment_for_retry_or_404", lambda *args, **kwargs: payment)
    monkeypatch.setattr(refund_service, "get_booking_for_retry", lambda *args, **kwargs: None)
    monkeypatch.setattr(refund_service, "get_host_publish_fee_for_retry", lambda *args, **kwargs: None)
    monkeypatch.setattr(refund_service, "validate_refund_retry", lambda *args, **kwargs: None)
    monkeypatch.setattr(refund_service, "refund_audit_snapshot", lambda refund: {"status": "failed"})
    monkeypatch.setattr(refund_service, "refund_audit_metadata", lambda *args, **kwargs: {"source": "admin_money_refund_retry"})

    def record_admin_action(*args, **kwargs):
        del args, kwargs
        db.add(admin_action)
        return admin_action

    def create_stripe_refund(**kwargs):
        provider_events.append((kwargs["idempotency_key"], db.commit_calls))
        return SimpleNamespace(
            id="re_ws04_02a_retry_recording_failed",
            status="succeeded",
        )

    def apply_refund_retry_result(**kwargs):
        del kwargs
        raise IntegrityError("stmt", "params", Exception("local result failed"))

    monkeypatch.setattr(refund_service, "record_admin_action", record_admin_action)
    monkeypatch.setattr(refund_service, "create_stripe_refund", create_stripe_refund)
    monkeypatch.setattr(
        refund_service,
        "map_admin_money_retry_refund_status",
        lambda provider_status: provider_status,
    )
    monkeypatch.setattr(
        refund_service,
        "apply_refund_retry_result",
        apply_refund_retry_result,
    )

    with pytest.raises(HTTPException) as exc_info:
        refund_service.retry_admin_money_refund(
            db,
            admin_user=admin_user,
            refund_id=refund_id,
            payload=AdminMoneyRefundRetryCreate(
                reason="retry post-provider failure",
                idempotency_key="ws04-02a-admin-refund",
            ),
        )

    assert exc_info.value.status_code == 409
    assert "Stripe returned a refund result" in exc_info.value.detail
    assert "refund reconciliation before retrying" in exc_info.value.detail
    assert provider_events == [("ws04-02a-admin-refund", 1)]
    provider_result = admin_action.metadata_["provider_result"]
    assert provider_result["provider"] == "stripe"
    assert provider_result["provider_refund_id"] == "re_ws04_02a_retry_recording_failed"
    assert provider_result["provider_status"] == "succeeded"
    assert provider_result["recording_state"] == "pending_local_refund_state"
    assert provider_result["recorded_at"]
    assert db.commit_calls == 2
    assert db.rollback_calls == 1


@pytest.mark.requirement("WS04-02A-R2", "WS04-02A-R4", "WS04-02A-R5")
def test_unfinished_account_cleanup_config_failure_rolls_back_before_support_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.firebase_admin_client import FirebaseAdminConfigError
    import backend.services.auth_account_service as auth_account_service

    db = _RecordingSession(added=[], added_many=[])
    user = SimpleNamespace(id=uuid.uuid4())
    support_records: list[dict[str, object]] = []

    monkeypatch.setattr(
        auth_account_service,
        "get_auth_user_id_from_token",
        lambda authorization: "firebase-ws04-02a",
    )
    monkeypatch.setattr(
        auth_account_service,
        "get_active_user_by_auth_id",
        lambda auth_user_id, db: user,
    )
    monkeypatch.setattr(
        auth_account_service,
        "lock_user_and_active_admins_for_account_removal",
        lambda db, *, user_id: (user, 2),
    )
    monkeypatch.setattr(
        auth_account_service,
        "require_account_removal_preserves_active_admin",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        auth_account_service,
        "hard_delete_incomplete_user",
        lambda user, db: db.delete(user),
    )
    monkeypatch.setattr(
        auth_account_service,
        "delete_firebase_user",
        lambda auth_user_id: (_ for _ in ()).throw(
            FirebaseAdminConfigError("missing Firebase config")
        ),
    )
    monkeypatch.setattr(
        auth_account_service,
        "record_account_delete_partial_failure",
        lambda *args, **kwargs: support_records.append(kwargs),
    )

    with pytest.raises(HTTPException) as exc_info:
        auth_account_service.cleanup_unfinished_account_workflow(
            "Bearer token",
            db,
        )

    assert exc_info.value.status_code == 503
    assert "Firebase could not clean up this sign-up" in exc_info.value.detail
    assert db.deleted == [user]
    assert db.commit_calls == 0
    assert db.rollback_calls == 1
    assert support_records == []


@pytest.mark.requirement("WS04-02A-R2", "WS04-02A-R4", "WS04-02A-R5")
def test_unfinished_account_cleanup_timeout_keeps_unknown_outcome_uncommitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.auth_account_service as auth_account_service

    db = _RecordingSession(added=[], added_many=[])
    user = SimpleNamespace(id=uuid.uuid4())
    support_records: list[dict[str, object]] = []

    monkeypatch.setattr(
        auth_account_service,
        "get_auth_user_id_from_token",
        lambda authorization: "firebase-ws04-02a",
    )
    monkeypatch.setattr(
        auth_account_service,
        "get_active_user_by_auth_id",
        lambda auth_user_id, db: user,
    )
    monkeypatch.setattr(
        auth_account_service,
        "lock_user_and_active_admins_for_account_removal",
        lambda db, *, user_id: (user, 2),
    )
    monkeypatch.setattr(
        auth_account_service,
        "require_account_removal_preserves_active_admin",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        auth_account_service,
        "hard_delete_incomplete_user",
        lambda user, db: db.delete(user),
    )
    monkeypatch.setattr(
        auth_account_service,
        "delete_firebase_user",
        lambda auth_user_id: (_ for _ in ()).throw(
            DependencyMutationTimeoutUnknownError(
                provider_kind="firebase",
                operation="firebase.user.delete",
            )
        ),
    )
    monkeypatch.setattr(
        auth_account_service,
        "record_account_delete_partial_failure",
        lambda *args, **kwargs: support_records.append(kwargs),
    )

    with pytest.raises(DependencyMutationTimeoutUnknownError) as exc_info:
        auth_account_service.cleanup_unfinished_account_workflow(
            "Bearer token",
            db,
        )

    assert exc_info.value.operation == "firebase.user.delete"
    assert db.deleted == [user]
    assert db.commit_calls == 0
    assert db.rollback_calls == 1
    assert support_records == []


@pytest.mark.requirement("WS04-02A-R2", "WS04-02A-R4", "WS04-02A-R5")
def test_unfinished_account_cleanup_provider_success_records_support_followup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.auth_account_service as auth_account_service

    user_id = uuid.uuid4()
    db = _RecordingSession(added=[], added_many=[], commit_failures={1})
    user = SimpleNamespace(id=user_id)
    support_records: list[dict[str, object]] = []
    provider_deletes: list[str] = []

    monkeypatch.setattr(
        auth_account_service,
        "get_auth_user_id_from_token",
        lambda authorization: "firebase-ws04-02a",
    )
    monkeypatch.setattr(
        auth_account_service,
        "get_active_user_by_auth_id",
        lambda auth_user_id, db: user,
    )
    monkeypatch.setattr(
        auth_account_service,
        "lock_user_and_active_admins_for_account_removal",
        lambda db, *, user_id: (user, 2),
    )
    monkeypatch.setattr(
        auth_account_service,
        "require_account_removal_preserves_active_admin",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        auth_account_service,
        "hard_delete_incomplete_user",
        lambda user, db: db.delete(user),
    )

    def delete_firebase_user(auth_user_id: str) -> None:
        provider_deletes.append(auth_user_id)

    def record_account_delete_partial_failure(db, **kwargs) -> None:
        support_records.append(kwargs)
        db.commit()

    monkeypatch.setattr(
        auth_account_service,
        "delete_firebase_user",
        delete_firebase_user,
    )
    monkeypatch.setattr(
        auth_account_service,
        "record_account_delete_partial_failure",
        record_account_delete_partial_failure,
    )

    with pytest.raises(HTTPException) as exc_info:
        auth_account_service.cleanup_unfinished_account_workflow(
            "Bearer token",
            db,
        )

    assert exc_info.value.status_code == 503
    assert "support follow-up" in exc_info.value.detail
    assert provider_deletes == ["firebase-ws04-02a"]
    assert db.deleted == [user]
    assert db.commit_calls == 2
    assert db.rollback_calls == 1
    assert support_records[0]["user_id"] == user_id
    assert support_records[0]["created_by_user_id"] == user_id
    assert support_records[0]["metadata"] == {
        "auth_identity_deleted": True,
        "app_cleanup_completed": False,
        "failure_type": "unfinished_account_cleanup_commit_error",
    }


@pytest.mark.requirement("WS04-02A-R2", "WS04-02A-R4", "WS04-02A-R5")
def test_unfinished_account_cleanup_duplicate_provider_delete_can_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.auth_account_service as auth_account_service

    db = _RecordingSession(added=[], added_many=[])
    provider_deletes: list[str] = []
    support_records: list[dict[str, object]] = []

    monkeypatch.setattr(
        auth_account_service,
        "get_auth_user_id_from_token",
        lambda authorization: "firebase-ws04-02a",
    )
    monkeypatch.setattr(
        auth_account_service,
        "get_active_user_by_auth_id",
        lambda auth_user_id, db: None,
    )
    monkeypatch.setattr(
        auth_account_service,
        "delete_firebase_user",
        lambda auth_user_id: provider_deletes.append(auth_user_id),
    )
    monkeypatch.setattr(
        auth_account_service,
        "record_account_delete_partial_failure",
        lambda *args, **kwargs: support_records.append(kwargs),
    )

    auth_account_service.cleanup_unfinished_account_workflow(
        "Bearer token",
        db,
    )

    assert provider_deletes == ["firebase-ws04-02a"]
    assert db.deleted == []
    assert db.commit_calls == 1
    assert db.rollback_calls == 0
    assert support_records == []
