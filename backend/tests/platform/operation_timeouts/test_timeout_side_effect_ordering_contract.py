from __future__ import annotations

import ast
import inspect
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.observability.timeouts import DependencyMutationTimeoutUnknownError

_REPO_ROOT = Path(__file__).resolve().parents[4]


@dataclass
class _RecordingSession:
    added: list[object]
    added_many: list[object]
    refreshed: list[object]
    flush_calls: int = 0
    commit_calls: int = 0
    rollback_calls: int = 0

    def add(self, value: object) -> None:
        self.added.append(value)

    def add_all(self, values) -> None:
        self.added_many.extend(values)

    def flush(self) -> None:
        self.flush_calls += 1

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1

    def refresh(self, value: object) -> None:
        self.refreshed.append(value)


def _stripe_timeout(operation: str) -> DependencyMutationTimeoutUnknownError:
    return DependencyMutationTimeoutUnknownError(
        provider_kind="stripe",
        operation=operation,
    )


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _count(db: Session, model: type[object]) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _saved_card_user():
    from backend.models import User

    unique = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-04c1-card-user-{unique}",
        role="player",
        email=f"ws02-04c1-card-{unique}@example.invalid",
        first_name="Timeout",
        last_name="Card",
        account_status="active",
        hosting_status="eligible",
        stripe_customer_id="cus_ws02_04c1",
    )


def _saved_payment_method(user, index: int):
    from backend.models import UserPaymentMethod

    return UserPaymentMethod(
        id=uuid.uuid4(),
        user_id=user.id,
        stripe_customer_id=user.stripe_customer_id,
        stripe_payment_method_id=f"pm_ws02_04c1_existing_{index}",
        card_fingerprint=f"ws02-04c1-fingerprint-{index}",
        card_brand="visa",
        card_last4=f"{index:04d}"[-4:],
        exp_month=12,
        exp_year=2035,
        method_status="active",
        is_default=(index == 1),
    )


@pytest.mark.requirement("WS02-04C1-R8")
@pytest.mark.no_db_cleanup
def test_checkout_payment_timeout_preserves_checkpoint_and_propagates_unknown_provider_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import Payment
    from backend.schemas.checkout_schema import GameCheckoutPaymentIntentCreate
    import backend.services.checkout_service as checkout_service
    from backend.services.game_credit_service import GameCreditApplication

    game_id = uuid.uuid4()
    current_user = SimpleNamespace(
        id=uuid.uuid4(),
        stripe_customer_id="cus_ws02_04c1_checkout",
    )
    db_game = SimpleNamespace(
        id=game_id,
        currency="USD",
        price_per_player_cents=1200,
        total_spots=12,
    )
    saved_payment_method = SimpleNamespace(
        stripe_payment_method_id="pm_ws02_04c1_saved"
    )
    db = _RecordingSession(added=[], added_many=[], refreshed=[])
    provider_create_calls: list[dict[str, object]] = []
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
    monkeypatch.setattr(
        checkout_service,
        "build_booking_participants",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        checkout_service,
        "get_user_display_name",
        lambda current_user: "Synthetic Checkout User",
    )
    monkeypatch.setattr(
        checkout_service,
        "sync_game_capacity_status",
        lambda *args, **kwargs: None,
    )

    def create_payment_intent(**kwargs):
        provider_create_calls.append(kwargs)
        raise _stripe_timeout("stripe.payment_intent.create")

    def confirm_payment_intent(payment_intent_id: str, **kwargs):
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
                payment_method_id=uuid.uuid4(),
            ),
            current_user,
        )

    staged_payments = [value for value in db.added if isinstance(value, Payment)]
    assert exc_info.value.operation == "stripe.payment_intent.create"
    assert len(provider_create_calls) == 1
    assert provider_confirm_calls == []
    assert db.flush_calls == 1
    assert db.commit_calls == 1
    assert db.rollback_calls == 0
    assert len(staged_payments) == 1
    assert staged_payments[0].payment_status == "requires_payment_method"
    assert staged_payments[0].provider_payment_intent_id is None
    assert staged_payments[0].provider_charge_id is None
    assert staged_payments[0].payment_status not in {"failed", "succeeded"}


@pytest.mark.requirement("WS02-04C1-R8")
@pytest.mark.no_db_cleanup
def test_refund_timeout_branches_preserve_processing_unknown_handoff() -> None:
    import backend.services.admin_financial_outcome_service as admin_financial_outcome_service
    import backend.services.game_cancellation_service as game_cancellation_service
    import backend.services.official_game_player_removal_service as official_game_player_removal_service
    import backend.services.stripe_webhook_service as stripe_webhook_service

    timeout_sources = {
        "publish_fee": inspect.getsource(
            admin_financial_outcome_service.apply_refund_outcome
        ),
        "cancellation": inspect.getsource(
            game_cancellation_service.create_official_cancellation_refunds
        ),
        "late_payment": inspect.getsource(
            stripe_webhook_service.create_late_payment_refund_if_needed
        ),
        "admin_removal": inspect.getsource(
            official_game_player_removal_service.execute_admin_removal_refunds
        ),
    }

    for source in timeout_sources.values():
        assert "except DependencyMutationTimeoutUnknownError:" in source
        assert "processing" in source
    assert '"unknown"' in timeout_sources["publish_fee"]
    for key in ("cancellation", "late_payment", "admin_removal"):
        assert "stripe_refund_timeout_unknown" in timeout_sources[key]


@pytest.mark.requirement("WS02-04C1-R8")
@pytest.mark.no_db_cleanup
def test_firebase_account_deletion_timeout_records_support_unknown_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.schemas.auth_schema import AuthDeleteAccountRequest
    import backend.services.account_deletion_service as account_deletion_service

    user = SimpleNamespace(
        id=uuid.uuid4(),
        role="player",
        account_status="active",
        deleted_at=None,
        auth_user_id="firebase-ws02-04c1-delete",
        updated_at=None,
    )
    db = _RecordingSession(added=[], added_many=[], refreshed=[])
    partial_failure_calls: list[dict[str, object]] = []
    delete_calls: list[str] = []

    monkeypatch.setattr(
        account_deletion_service,
        "get_authenticated_user_from_token",
        lambda authorization, db: user,
    )
    monkeypatch.setattr(
        account_deletion_service,
        "lock_user_and_active_admins_for_account_removal",
        lambda db, *, user_id: (user, 1),
    )

    def delete_firebase_user(auth_user_id: str) -> None:
        delete_calls.append(auth_user_id)
        raise DependencyMutationTimeoutUnknownError(
            provider_kind="firebase",
            operation="firebase.user.delete",
        )

    def record_partial_failure(db, **kwargs) -> None:
        partial_failure_calls.append(kwargs)

    monkeypatch.setattr(
        account_deletion_service,
        "delete_firebase_user",
        delete_firebase_user,
    )
    monkeypatch.setattr(
        account_deletion_service,
        "record_account_delete_partial_failure",
        record_partial_failure,
    )

    with pytest.raises(DependencyMutationTimeoutUnknownError) as exc_info:
        account_deletion_service.delete_account_workflow(
            AuthDeleteAccountRequest(confirmation="DELETE"),
            "Bearer synthetic-user-token",
            db,
        )

    assert exc_info.value.operation == "firebase.user.delete"
    assert delete_calls == ["firebase-ws02-04c1-delete"]
    assert db.commit_calls == 1
    assert db.rollback_calls == 0
    assert user.account_status == "pending_deletion"
    assert user.auth_user_id == "firebase-ws02-04c1-delete"
    assert partial_failure_calls == [
        {
            "user_id": user.id,
            "created_by_user_id": user.id,
            "clear_auth_link": False,
            "metadata": {
                "auth_identity_deleted": "unknown",
                "app_cleanup_completed": False,
                "failure_type": "firebase_delete_outcome_unknown",
            },
            "summary": (
                "Firebase deletion timed out, and account deletion requires "
                "support follow-up."
            ),
        }
    ]


@pytest.mark.requirement("WS02-04C1-R8")
def test_saved_card_unpersisted_cleanup_timeout_cannot_create_saved_card_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import UserPaymentMethod
    from backend.services import payment_method_service
    from backend.services.stripe_service import (
        StripePaymentMethodCardResult,
        StripeSetupIntentResult,
    )

    detach_calls: list[str] = []

    monkeypatch.setattr(payment_method_service, "stripe_payments_enabled", lambda: True)
    monkeypatch.setattr(
        payment_method_service,
        "retrieve_setup_intent",
        lambda setup_intent_id: StripeSetupIntentResult(
            id=setup_intent_id,
            client_secret=None,
            status="succeeded",
            customer_id="cus_ws02_04c1",
            payment_method_id="pm_ws02_04c1_unpersisted",
        ),
    )
    monkeypatch.setattr(
        payment_method_service,
        "retrieve_payment_method",
        lambda payment_method_id: StripePaymentMethodCardResult(
            id=payment_method_id,
            customer_id="cus_ws02_04c1",
            card_fingerprint="ws02-04c1-new-fingerprint",
            card_brand="visa",
            card_last4="4242",
            exp_month=12,
            exp_year=2035,
        ),
    )

    def detach_payment_method(payment_method_id: str) -> None:
        detach_calls.append(payment_method_id)
        raise _stripe_timeout("stripe.payment_method.detach")

    monkeypatch.setattr(
        payment_method_service,
        "detach_payment_method",
        detach_payment_method,
    )

    with _session() as db:
        user = _saved_card_user()
        db.add(user)
        db.add_all([_saved_payment_method(user, index) for index in range(1, 6)])
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            payment_method_service.sync_saved_payment_method(
                db,
                user,
                setup_intent_id="seti_ws02_04c1_unpersisted",
                set_as_default=False,
            )
        db.rollback()

        assert exc_info.value.status_code == 400
        assert "save up to" in str(exc_info.value.detail)
        assert detach_calls == ["pm_ws02_04c1_unpersisted"]
        assert _count(db, UserPaymentMethod) == 5
        assert (
            db.scalar(
                select(UserPaymentMethod).where(
                    UserPaymentMethod.stripe_payment_method_id
                    == "pm_ws02_04c1_unpersisted"
                )
            )
            is None
        )


@pytest.mark.requirement("WS02-04C1-R8")
@pytest.mark.no_db_cleanup
def test_saved_card_unpersisted_cleanup_timeout_is_best_effort_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.payment_method_service as payment_method_service

    sync_source = inspect.getsource(payment_method_service.sync_saved_payment_method)
    detach_calls: list[str] = []

    def detach_payment_method(payment_method_id: str) -> None:
        detach_calls.append(payment_method_id)
        raise _stripe_timeout("stripe.payment_method.detach")

    monkeypatch.setattr(
        payment_method_service,
        "detach_payment_method",
        detach_payment_method,
    )

    assert payment_method_service.detach_unpersisted_payment_method(
        "pm_ws02_04c1_unpersisted"
    ) is None
    assert detach_calls == ["pm_ws02_04c1_unpersisted"]
    assert "detach_unpersisted_payment_method(stripe_payment_method.id)" in sync_source
    assert "This card is already saved." in sync_source
    assert "You can save up to" in sync_source


@pytest.mark.requirement("WS02-04C1-R2", "WS02-04C1-R8")
@pytest.mark.no_db_cleanup
def test_provider_mutation_retry_policy_preserves_no_blind_replay() -> None:
    import backend.services.provider_retry_policy as retry_policy

    mutation_policies = [
        policy
        for policy in retry_policy.PROVIDER_OPERATION_RETRY_POLICIES
        if policy.provider in {"stripe", "firebase"} and policy.provider_mutation
    ]

    assert mutation_policies
    for policy in mutation_policies:
        assert policy.application_automatic_retry_allowed is False
        assert policy.unknown_outcome_possible is True
        assert policy.current_recovery


@pytest.mark.requirement("WS02-04C1-R7", "WS02-04C1-R8")
@pytest.mark.no_db_cleanup
def test_representative_call_sites_catch_exception_not_base_exception() -> None:
    call_site_paths = [
        "backend/services/checkout_service.py",
        "backend/services/admin_financial_outcome_service.py",
        "backend/services/game_cancellation_service.py",
        "backend/services/stripe_webhook_service.py",
        "backend/services/official_game_player_removal_service.py",
        "backend/services/account_deletion_service.py",
        "backend/services/admin_user_delete_service.py",
        "backend/services/payment_method_service.py",
    ]
    caught_base_exception: list[str] = []
    for relative_path in call_site_paths:
        tree = ast.parse((_REPO_ROOT / relative_path).read_text(), filename=relative_path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if isinstance(node.type, ast.Name) and node.type.id == "BaseException":
                caught_base_exception.append(relative_path)

    assert caught_base_exception == []
