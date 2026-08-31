"""Saved payment method validation shared by checkout-style flows."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.models import PaymentMethodOperation, User, UserPaymentMethod
from backend.observability.timeouts import PublicTimeoutError
from backend.services.payment_job_service import enqueue_payment_method_reconcile_job
from backend.services.payment_lifecycle_policy import canonical_fingerprint
from backend.services.query_pagination import (
    DEFAULT_COLLECTION_LIMIT,
    MAX_COLLECTION_LIMIT,
    bounded_collection_limit,
    bounded_collection_offset,
)
from backend.services.stripe_service import (
    StripeConfigError,
    clear_customer_default_payment_method,
    create_customer,
    create_setup_intent,
    detach_payment_method,
    retrieve_payment_method,
    retrieve_setup_intent,
    set_customer_default_payment_method,
    stripe_payments_enabled,
)
from backend.services.user_service import build_user_conflict_detail

ACTIVE_PAYMENT_METHOD_STATUS = "active"
DETACHED_PAYMENT_METHOD_STATUS = "detached"
ACTIVE_PAYMENT_METHOD_OPERATION_STATUSES = {"pending", "provider_unknown"}
MAX_ACTIVE_PAYMENT_METHODS = 5
STRIPE_PAYMENTS_DISABLED_DETAIL = "Stripe payments are disabled for this demo."
SAVED_CARD_SYNC_RECORDING_FAILED_DETAIL = (
    "Stripe saved this payment method, but Pickup Lane could not save the "
    "matching local card state. Refresh saved cards or contact support before "
    "retrying."
)
SAVED_CARD_DEFAULT_RECORDING_FAILED_DETAIL = (
    "Stripe updated the default payment method, but Pickup Lane could not save "
    "the matching local card state. Refresh saved cards or contact support "
    "before retrying."
)
SAVED_CARD_DETACH_RECORDING_FAILED_DETAIL = (
    "Stripe detached this payment method, but Pickup Lane could not save the "
    "matching local card state. Refresh saved cards or contact support before "
    "retrying."
)


def begin_payment_method_operation(
    db: Session,
    current_user: User,
    *,
    operation_kind: str,
    idempotency_key: uuid.UUID,
    payment_method_id: uuid.UUID | None = None,
    provider_object_id: str | None = None,
    values: dict[str, object] | None = None,
    allow_active_operation_ids: set[uuid.UUID] | None = None,
) -> PaymentMethodOperation:
    provider_idempotency_key = f"payment-method:{current_user.id}:{idempotency_key}"
    if values is not None and "set_as_default" in values:
        provider_idempotency_key += (
            ":default:1" if bool(values["set_as_default"]) else ":default:0"
        )
    fingerprint = canonical_fingerprint(
        {
            "user_id": str(current_user.id),
            "operation_kind": operation_kind,
            "idempotency_key": str(idempotency_key),
            "payment_method_id": str(payment_method_id) if payment_method_id else None,
            "provider_object_id": provider_object_id,
            **(values or {}),
        }
    )
    operation = db.scalars(
        select(PaymentMethodOperation).where(
            PaymentMethodOperation.provider_idempotency_key
            == provider_idempotency_key
        )
    ).first()
    if operation is not None:
        if operation.request_fingerprint != fingerprint:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency-Key was already used for a different payment-method operation.",
            )
        return operation
    operation = db.scalars(
        select(PaymentMethodOperation).where(
            PaymentMethodOperation.user_id == current_user.id,
            PaymentMethodOperation.operation_kind == operation_kind,
            PaymentMethodOperation.request_fingerprint == fingerprint,
        )
    ).first()
    if operation is not None:
        return operation
    require_no_unresolved_payment_method_operation(
        db,
        current_user,
        allow_operation_ids=allow_active_operation_ids,
    )
    operation = PaymentMethodOperation(
        id=uuid.uuid4(),
        user_id=current_user.id,
        payment_method_id=payment_method_id,
        operation_kind=operation_kind,
        status="pending",
        request_fingerprint=fingerprint,
        provider_idempotency_key=provider_idempotency_key,
        provider_object_id=provider_object_id,
    )
    try:
        db.add(operation)
        db.commit()
        db.refresh(operation)
    except IntegrityError as exc:
        db.rollback()
        operation = db.scalars(
            select(PaymentMethodOperation).where(
                PaymentMethodOperation.provider_idempotency_key
                == provider_idempotency_key
            )
        ).first()
        if operation is None or operation.request_fingerprint != fingerprint:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment-method operation identity conflicts with existing work.",
            ) from exc
    return operation


def get_unresolved_payment_method_operation(
    db: Session,
    current_user: User,
    *,
    allow_operation_ids: set[uuid.UUID] | None = None,
) -> PaymentMethodOperation | None:
    statement = (
        select(PaymentMethodOperation)
        .where(
            PaymentMethodOperation.user_id == current_user.id,
            PaymentMethodOperation.status.in_(ACTIVE_PAYMENT_METHOD_OPERATION_STATUSES),
        )
        .order_by(PaymentMethodOperation.created_at.asc(), PaymentMethodOperation.id.asc())
    )
    if allow_operation_ids:
        statement = statement.where(
            PaymentMethodOperation.id.notin_(allow_operation_ids)
        )
    return db.scalars(statement.limit(1).with_for_update()).first()


def require_no_unresolved_payment_method_operation(
    db: Session,
    current_user: User,
    *,
    allow_operation_ids: set[uuid.UUID] | None = None,
) -> None:
    if (
        get_unresolved_payment_method_operation(
            db,
            current_user,
            allow_operation_ids=allow_operation_ids,
        )
        is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A payment-method operation is still pending. Refresh saved cards "
                "or contact support before starting another card action."
            ),
        )


def payment_method_operation_idempotency_key(
    operation: PaymentMethodOperation,
) -> uuid.UUID:
    parts = operation.provider_idempotency_key.split(":")
    if (
        len(parts) not in {3, 5}
        or parts[0] != "payment-method"
        or parts[1] != str(operation.user_id)
    ):
        raise ValueError("payment-method operation idempotency identity is invalid")
    return uuid.UUID(parts[2])


def payment_method_operation_desired_default(
    operation: PaymentMethodOperation,
) -> bool:
    parts = operation.provider_idempotency_key.split(":")
    if len(parts) != 5 or parts[3] != "default" or parts[4] not in {"0", "1"}:
        raise ValueError("payment-method operation default identity is invalid")
    return parts[4] == "1"


def mark_payment_method_operation_unknown(
    db: Session,
    operation: PaymentMethodOperation,
    error_code: str,
) -> None:
    operation_id = operation.id
    db.rollback()
    operation = db.get(PaymentMethodOperation, operation_id)
    apply_payment_method_operation_unknown(
        db,
        operation,
        error_code,
        enqueue_reconciliation=True,
    )
    db.commit()


def mark_payment_method_operation_failed(
    db: Session,
    operation: PaymentMethodOperation,
    error_code: str,
) -> None:
    operation_id = operation.id
    db.rollback()
    operation = db.get(PaymentMethodOperation, operation_id)
    apply_payment_method_operation_failed(db, operation, error_code)
    db.commit()


def mark_payment_method_operation_succeeded(
    db: Session,
    operation: PaymentMethodOperation,
    *,
    provider_object_id: str | None = None,
    payment_method_id: uuid.UUID | None = None,
) -> None:
    apply_payment_method_operation_succeeded(
        db,
        operation,
        provider_object_id=provider_object_id,
        payment_method_id=payment_method_id,
    )
    db.commit()


def apply_payment_method_operation_unknown(
    db: Session,
    operation: PaymentMethodOperation | None,
    error_code: str,
    *,
    enqueue_reconciliation: bool,
) -> None:
    if operation is None or operation.status in {"succeeded", "failed"}:
        return
    operation.status = "provider_unknown"
    operation.error_code = error_code[:100]
    operation.updated_at = datetime.now(timezone.utc)
    db.add(operation)
    if enqueue_reconciliation:
        enqueue_payment_method_reconcile_job(db, operation.id)


def apply_payment_method_operation_failed(
    db: Session,
    operation: PaymentMethodOperation | None,
    error_code: str,
) -> None:
    if operation is None or operation.status == "succeeded":
        return
    now = datetime.now(timezone.utc)
    operation.status = "failed"
    operation.error_code = error_code[:100]
    operation.resolved_at = now
    operation.updated_at = now
    db.add(operation)


def apply_payment_method_operation_succeeded(
    db: Session,
    operation: PaymentMethodOperation,
    *,
    provider_object_id: str | None = None,
    payment_method_id: uuid.UUID | None = None,
) -> None:
    now = datetime.now(timezone.utc)
    operation.status = "succeeded"
    operation.provider_object_id = provider_object_id or operation.provider_object_id
    operation.payment_method_id = payment_method_id or operation.payment_method_id
    operation.error_code = None
    operation.resolved_at = now
    operation.updated_at = now
    db.add(operation)


def require_payment_method_operation_retryable(
    operation: PaymentMethodOperation,
) -> None:
    if operation.status == "provider_unknown":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This payment-method operation has an unknown provider outcome. "
                "Refresh saved cards or contact support before retrying."
            ),
        )
    if operation.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This payment-method operation already failed. Start a new action.",
        )


def build_user_payment_method_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "uq_user_payment_methods_stripe_payment_method_id" in error_text:
        return "This Stripe payment method is already saved."

    if "ix_user_payment_methods_user_card_fingerprint" in error_text:
        return "This card is already saved."

    if "ix_user_payment_methods_one_active_default_per_user" in error_text:
        return "A user can only have one active default payment method."

    return error_text


def build_customer_name(user: User) -> str | None:
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return name or user.email


def require_stripe_payments_enabled() -> None:
    if not stripe_payments_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=STRIPE_PAYMENTS_DISABLED_DETAIL,
        )


def ensure_stripe_customer_id(db: Session, current_user: User) -> str:
    if current_user.stripe_customer_id:
        return current_user.stripe_customer_id

    try:
        stripe_customer = create_customer(
            email=current_user.email,
            name=build_customer_name(current_user),
            idempotency_key=f"user:{current_user.id}:stripe_customer",
            metadata={"user_id": str(current_user.id)},
        )
    except StripeConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except PublicTimeoutError:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe could not create this customer.",
        ) from exc

    current_user.stripe_customer_id = stripe_customer.id
    current_user.updated_at = datetime.now(timezone.utc)
    db.add(current_user)

    try:
        db.commit()
        db.refresh(current_user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_conflict_detail(exc),
        ) from exc

    return current_user.stripe_customer_id


def create_saved_payment_method_setup_intent(
    db: Session,
    current_user: User,
    *,
    set_as_default: bool,
    idempotency_key: uuid.UUID,
) -> str:
    require_stripe_payments_enabled()
    operation = begin_payment_method_operation(
        db,
        current_user,
        operation_kind="setup_create",
        idempotency_key=idempotency_key,
        values={"set_as_default": set_as_default},
    )
    require_payment_method_operation_retryable(operation)
    try:
        stripe_customer_id = ensure_stripe_customer_id(db, current_user)
    except PublicTimeoutError:
        mark_payment_method_operation_unknown(
            db, operation, "customer_create_timeout_unknown"
        )
        raise
    except HTTPException:
        mark_payment_method_operation_failed(db, operation, "customer_create_failed")
        raise

    try:
        setup_intent = create_setup_intent(
            customer_id=stripe_customer_id,
            idempotency_key=operation.provider_idempotency_key,
            metadata={
                "user_id": str(current_user.id),
                "set_as_default": set_as_default,
            },
        )
    except StripeConfigError as exc:
        mark_payment_method_operation_failed(db, operation, "stripe_not_configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except PublicTimeoutError:
        mark_payment_method_operation_unknown(
            db, operation, "setup_create_timeout_unknown"
        )
        raise
    except Exception as exc:
        mark_payment_method_operation_failed(db, operation, "setup_create_failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe could not create this setup intent.",
        ) from exc

    if not setup_intent.client_secret:
        mark_payment_method_operation_failed(
            db,
            operation,
            "setup_client_secret_missing",
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe did not return a client secret for this setup intent.",
        )

    mark_payment_method_operation_succeeded(
        db,
        operation,
        provider_object_id=setup_intent.id,
    )

    return setup_intent.client_secret


def unset_other_active_defaults(
    db: Session,
    user_id: uuid.UUID,
    *,
    keep_payment_method_id: uuid.UUID | None = None,
) -> None:
    existing_defaults = db.scalars(
        select(UserPaymentMethod).where(
            UserPaymentMethod.user_id == user_id,
            UserPaymentMethod.method_status == ACTIVE_PAYMENT_METHOD_STATUS,
            UserPaymentMethod.is_default.is_(True),
        )
    ).all()

    for payment_method in existing_defaults:
        if payment_method.id == keep_payment_method_id:
            continue

        payment_method.is_default = False
        payment_method.updated_at = datetime.now(timezone.utc)
        db.add(payment_method)


def count_active_payment_methods(db: Session, user_id: uuid.UUID) -> int:
    return len(
        db.scalars(
            select(UserPaymentMethod.id).where(
                UserPaymentMethod.user_id == user_id,
                UserPaymentMethod.method_status == ACTIVE_PAYMENT_METHOD_STATUS,
            )
        ).all()
    )


def list_active_payment_methods(
    db: Session,
    user_id: uuid.UUID,
    *,
    excluding_payment_method_id: uuid.UUID | None = None,
) -> list[UserPaymentMethod]:
    statement = select(UserPaymentMethod).where(
        UserPaymentMethod.user_id == user_id,
        UserPaymentMethod.method_status == ACTIVE_PAYMENT_METHOD_STATUS,
    )

    if excluding_payment_method_id is not None:
        statement = statement.where(
            UserPaymentMethod.id != excluding_payment_method_id
        )

    return list(
        db.scalars(
            statement.order_by(
                UserPaymentMethod.created_at.asc(),
                UserPaymentMethod.id.asc(),
            )
        ).all()
    )


def detach_unpersisted_payment_method(payment_method_id: str) -> None:
    try:
        detach_payment_method(payment_method_id)
    except Exception:  # noqa: BLE001, S110 - best-effort cleanup only
        pass


def get_owned_payment_method_or_404(
    db: Session,
    payment_method_id: uuid.UUID,
    current_user: User,
) -> UserPaymentMethod:
    payment_method = db.get(UserPaymentMethod, payment_method_id)
    if payment_method is None or payment_method.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found.",
        )

    return payment_method


def list_current_user_payment_methods(
    db: Session,
    current_user: User,
    *,
    include_inactive: bool = False,
    limit: int = DEFAULT_COLLECTION_LIMIT,
    offset: int = 0,
) -> list[UserPaymentMethod]:
    statement = select(UserPaymentMethod).where(
        UserPaymentMethod.user_id == current_user.id
    )

    if not include_inactive:
        statement = statement.where(
            UserPaymentMethod.method_status == ACTIVE_PAYMENT_METHOD_STATUS
        )

    payment_methods = db.scalars(
        statement.order_by(
            UserPaymentMethod.created_at.asc(),
            UserPaymentMethod.id.asc(),
        )
        .offset(bounded_collection_offset(offset))
        .limit(bounded_collection_limit(limit, max_limit=MAX_COLLECTION_LIMIT))
    ).all()
    return list(payment_methods)


def sync_saved_payment_method(
    db: Session,
    current_user: User,
    *,
    setup_intent_id: str,
    set_as_default: bool,
    idempotency_key: uuid.UUID,
) -> UserPaymentMethod:
    require_stripe_payments_enabled()
    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Create a Stripe customer before syncing a payment method.",
        )
    operation = begin_payment_method_operation(
        db,
        current_user,
        operation_kind="sync",
        idempotency_key=idempotency_key,
        provider_object_id=setup_intent_id,
        values={"set_as_default": set_as_default},
    )
    require_payment_method_operation_retryable(operation)
    if operation.status == "succeeded" and operation.payment_method_id is not None:
        payment_method = db.get(UserPaymentMethod, operation.payment_method_id)
        if payment_method is not None:
            return payment_method

    try:
        setup_intent = retrieve_setup_intent(setup_intent_id)
    except StripeConfigError as exc:
        mark_payment_method_operation_failed(db, operation, "stripe_not_configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except PublicTimeoutError:
        mark_payment_method_operation_unknown(db, operation, "sync_timeout_unknown")
        raise
    except Exception as exc:
        mark_payment_method_operation_failed(db, operation, "setup_retrieve_failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe could not retrieve this setup intent.",
        ) from exc

    if setup_intent.customer_id != current_user.stripe_customer_id:
        mark_payment_method_operation_failed(db, operation, "setup_owner_mismatch")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This setup intent does not belong to the current user.",
        )

    if setup_intent.status != "succeeded" or not setup_intent.payment_method_id:
        mark_payment_method_operation_failed(db, operation, "setup_not_completed")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This setup intent has not completed with a payment method.",
        )

    try:
        stripe_payment_method = retrieve_payment_method(
            setup_intent.payment_method_id
        )
    except StripeConfigError as exc:
        mark_payment_method_operation_failed(db, operation, "stripe_not_configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except PublicTimeoutError:
        mark_payment_method_operation_unknown(
            db, operation, "payment_method_read_timeout_unknown"
        )
        raise
    except Exception as exc:
        mark_payment_method_operation_failed(db, operation, "payment_method_read_failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe could not retrieve this payment method.",
        ) from exc

    if stripe_payment_method.customer_id != current_user.stripe_customer_id:
        mark_payment_method_operation_failed(db, operation, "payment_method_owner_mismatch")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This payment method does not belong to the current user.",
        )

    existing_payment_method = db.scalar(
        select(UserPaymentMethod).where(
            UserPaymentMethod.stripe_payment_method_id == stripe_payment_method.id
        )
    )
    if (
        existing_payment_method is not None
        and existing_payment_method.user_id != current_user.id
    ):
        mark_payment_method_operation_failed(db, operation, "payment_method_conflict")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This Stripe payment method is already saved.",
        )

    now = datetime.now(timezone.utc)
    existing_card = db.scalar(
        select(UserPaymentMethod).where(
            UserPaymentMethod.user_id == current_user.id,
            UserPaymentMethod.card_fingerprint == stripe_payment_method.card_fingerprint,
        )
    )

    if (
        existing_card is not None
        and existing_card.method_status == ACTIVE_PAYMENT_METHOD_STATUS
    ):
        if existing_card.stripe_payment_method_id != stripe_payment_method.id:
            detach_unpersisted_payment_method(stripe_payment_method.id)
        mark_payment_method_operation_failed(db, operation, "card_already_saved")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This card is already saved.",
        )

    active_payment_method_count = count_active_payment_methods(db, current_user.id)
    if active_payment_method_count >= MAX_ACTIVE_PAYMENT_METHODS:
        detach_unpersisted_payment_method(stripe_payment_method.id)
        mark_payment_method_operation_failed(db, operation, "saved_card_limit")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You can save up to {MAX_ACTIVE_PAYMENT_METHODS} active cards.",
        )

    should_default = active_payment_method_count == 0 or set_as_default
    provider_default_updated = False
    if should_default:
        try:
            set_customer_default_payment_method(
                customer_id=current_user.stripe_customer_id,
                payment_method_id=stripe_payment_method.id,
                idempotency_key=operation.provider_idempotency_key,
            )
            provider_default_updated = True
        except StripeConfigError as exc:
            mark_payment_method_operation_failed(db, operation, "stripe_not_configured")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except PublicTimeoutError:
            mark_payment_method_operation_unknown(
                db, operation, "sync_default_timeout_unknown"
            )
            raise
        except Exception as exc:
            mark_payment_method_operation_failed(
                db, operation, "sync_default_update_failed"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Stripe could not set this default payment method.",
            ) from exc
        try:
            unset_other_active_defaults(db, current_user.id)
            db.flush()
        except SQLAlchemyError as exc:
            mark_payment_method_operation_unknown(
                db, operation, "sync_default_local_recording_failed"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=SAVED_CARD_DEFAULT_RECORDING_FAILED_DETAIL,
            ) from exc

    if existing_card is None:
        payment_method = UserPaymentMethod(
            id=uuid.uuid4(),
            user_id=current_user.id,
            stripe_customer_id=current_user.stripe_customer_id,
            stripe_payment_method_id=stripe_payment_method.id,
            card_fingerprint=stripe_payment_method.card_fingerprint,
            card_brand=stripe_payment_method.card_brand,
            card_last4=stripe_payment_method.card_last4,
            exp_month=stripe_payment_method.exp_month,
            exp_year=stripe_payment_method.exp_year,
            method_status=ACTIVE_PAYMENT_METHOD_STATUS,
            is_default=should_default,
            detached_at=None,
        )
    else:
        payment_method = existing_card
        payment_method.stripe_customer_id = current_user.stripe_customer_id
        payment_method.stripe_payment_method_id = stripe_payment_method.id
        payment_method.card_fingerprint = stripe_payment_method.card_fingerprint
        payment_method.card_brand = stripe_payment_method.card_brand
        payment_method.card_last4 = stripe_payment_method.card_last4
        payment_method.exp_month = stripe_payment_method.exp_month
        payment_method.exp_year = stripe_payment_method.exp_year
        payment_method.method_status = ACTIVE_PAYMENT_METHOD_STATUS
        payment_method.is_default = should_default
        payment_method.detached_at = None
        payment_method.updated_at = now

    try:
        db.add(payment_method)
        db.commit()
        db.refresh(payment_method)
    except IntegrityError as exc:
        if provider_default_updated:
            mark_payment_method_operation_unknown(
                db, operation, "sync_local_recording_failed"
            )
        else:
            db.rollback()
        detail = (
            SAVED_CARD_DEFAULT_RECORDING_FAILED_DETAIL
            if provider_default_updated
            else build_user_payment_method_conflict_detail(exc)
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        ) from exc
    except SQLAlchemyError as exc:
        mark_payment_method_operation_unknown(
            db, operation, "sync_local_recording_failed"
        )
        detail = (
            SAVED_CARD_DEFAULT_RECORDING_FAILED_DETAIL
            if provider_default_updated
            else SAVED_CARD_SYNC_RECORDING_FAILED_DETAIL
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        ) from exc

    mark_payment_method_operation_succeeded(
        db,
        operation,
        provider_object_id=setup_intent_id,
        payment_method_id=payment_method.id,
    )
    return payment_method


def set_default_saved_payment_method(
    db: Session,
    current_user: User,
    payment_method_id: uuid.UUID,
    idempotency_key: uuid.UUID,
) -> UserPaymentMethod:
    payment_method = get_owned_payment_method_or_404(
        db, payment_method_id, current_user
    )
    if payment_method.method_status != ACTIVE_PAYMENT_METHOD_STATUS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active payment methods can be made default.",
        )

    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This user does not have a Stripe customer.",
        )
    require_no_unresolved_payment_method_operation(db, current_user)
    verify_saved_payment_method_with_stripe(
        db,
        payment_method,
        current_user,
        datetime.now(timezone.utc),
    )
    payment_method = get_owned_payment_method_or_404(
        db,
        payment_method_id,
        current_user,
    )
    if payment_method.method_status != ACTIVE_PAYMENT_METHOD_STATUS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active payment methods can be made default.",
        )
    operation = begin_payment_method_operation(
        db,
        current_user,
        operation_kind="set_default",
        idempotency_key=idempotency_key,
        payment_method_id=payment_method.id,
    )
    require_payment_method_operation_retryable(operation)
    if operation.status == "succeeded":
        return payment_method

    provider_default_updated = False
    try:
        set_customer_default_payment_method(
            customer_id=current_user.stripe_customer_id,
            payment_method_id=payment_method.stripe_payment_method_id,
            idempotency_key=operation.provider_idempotency_key,
        )
        provider_default_updated = True
    except StripeConfigError as exc:
        mark_payment_method_operation_failed(db, operation, "stripe_not_configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except PublicTimeoutError:
        mark_payment_method_operation_unknown(
            db, operation, "set_default_timeout_unknown"
        )
        raise
    except Exception as exc:
        mark_payment_method_operation_failed(
            db, operation, "set_default_provider_failed"
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe could not set this default payment method.",
        ) from exc

    try:
        unset_other_active_defaults(db, current_user.id)
        db.flush()
    except SQLAlchemyError as exc:
        mark_payment_method_operation_unknown(
            db, operation, "set_default_local_recording_failed"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=SAVED_CARD_DEFAULT_RECORDING_FAILED_DETAIL,
        ) from exc

    payment_method.is_default = True
    payment_method.updated_at = datetime.now(timezone.utc)

    try:
        db.add(payment_method)
        db.commit()
        db.refresh(payment_method)
    except IntegrityError as exc:
        mark_payment_method_operation_unknown(
            db, operation, "set_default_local_recording_failed"
        )
        detail = (
            SAVED_CARD_DEFAULT_RECORDING_FAILED_DETAIL
            if provider_default_updated
            else build_user_payment_method_conflict_detail(exc)
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        ) from exc
    except SQLAlchemyError as exc:
        mark_payment_method_operation_unknown(
            db, operation, "set_default_local_recording_failed"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=SAVED_CARD_DEFAULT_RECORDING_FAILED_DETAIL,
        ) from exc

    mark_payment_method_operation_succeeded(
        db, operation, payment_method_id=payment_method.id
    )
    return payment_method


def detach_saved_payment_method(
    db: Session,
    current_user: User,
    payment_method_id: uuid.UUID,
    idempotency_key: uuid.UUID,
) -> UserPaymentMethod:
    payment_method = get_owned_payment_method_or_404(
        db, payment_method_id, current_user
    )
    if payment_method.method_status != DETACHED_PAYMENT_METHOD_STATUS:
        require_no_unresolved_payment_method_operation(db, current_user)
        verify_saved_payment_method_with_stripe(
            db,
            payment_method,
            current_user,
            datetime.now(timezone.utc),
        )
        payment_method = get_owned_payment_method_or_404(
            db,
            payment_method_id,
            current_user,
        )
    operation = begin_payment_method_operation(
        db,
        current_user,
        operation_kind="detach",
        idempotency_key=idempotency_key,
        payment_method_id=payment_method.id,
    )
    require_payment_method_operation_retryable(operation)
    if operation.status == "succeeded":
        return payment_method
    if payment_method.method_status == DETACHED_PAYMENT_METHOD_STATUS:
        mark_payment_method_operation_succeeded(
            db, operation, payment_method_id=payment_method.id
        )
        return payment_method

    provider_detached = False
    try:
        detach_payment_method(
            payment_method.stripe_payment_method_id,
            idempotency_key=operation.provider_idempotency_key,
        )
        provider_detached = True
    except StripeConfigError as exc:
        mark_payment_method_operation_failed(db, operation, "stripe_not_configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except PublicTimeoutError:
        mark_payment_method_operation_unknown(db, operation, "detach_timeout_unknown")
        raise
    except Exception as exc:
        mark_payment_method_operation_failed(db, operation, "detach_provider_failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe could not detach this payment method.",
        ) from exc

    now = datetime.now(timezone.utc)
    was_default = bool(payment_method.is_default)
    payment_method.method_status = DETACHED_PAYMENT_METHOD_STATUS
    payment_method.is_default = False
    payment_method.detached_at = now
    payment_method.updated_at = now
    db.add(payment_method)
    try:
        db.flush()
    except SQLAlchemyError as exc:
        mark_payment_method_operation_unknown(
            db, operation, "detach_local_recording_failed"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
                detail=SAVED_CARD_DETACH_RECORDING_FAILED_DETAIL,
        ) from exc
    next_default_payment_method: UserPaymentMethod | None = None
    default_operation: PaymentMethodOperation | None = None

    if was_default:
        stripe_customer_id = (
            current_user.stripe_customer_id or payment_method.stripe_customer_id
        )
        remaining_payment_methods = list_active_payment_methods(
            db,
            current_user.id,
            excluding_payment_method_id=payment_method.id,
        )
        next_default_payment_method = (
            remaining_payment_methods[0] if remaining_payment_methods else None
        )
        default_operation_kind = (
            "set_default" if next_default_payment_method is not None else "clear_default"
        )
        default_operation_key = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"payment-method-operation:{operation.id}:{default_operation_kind}",
        )
        apply_payment_method_operation_succeeded(
            db,
            operation,
            payment_method_id=payment_method.id,
        )
        db.flush()
        default_operation = begin_payment_method_operation(
            db,
            current_user,
            operation_kind=default_operation_kind,
            idempotency_key=default_operation_key,
            payment_method_id=(
                next_default_payment_method.id
                if next_default_payment_method is not None
                else None
            ),
            allow_active_operation_ids={operation.id},
        )
        require_payment_method_operation_retryable(default_operation)
        operation = db.get(PaymentMethodOperation, operation.id)

        try:
            if next_default_payment_method is not None and stripe_customer_id:
                set_customer_default_payment_method(
                    customer_id=stripe_customer_id,
                    payment_method_id=next_default_payment_method.stripe_payment_method_id,
                    idempotency_key=default_operation.provider_idempotency_key,
                )
            elif stripe_customer_id:
                clear_customer_default_payment_method(
                    customer_id=stripe_customer_id,
                    idempotency_key=default_operation.provider_idempotency_key,
                )
        except StripeConfigError as exc:
            if provider_detached:
                mark_payment_method_operation_unknown(
                    db, default_operation, "default_replacement_unknown"
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=SAVED_CARD_DETACH_RECORDING_FAILED_DETAIL,
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except PublicTimeoutError:
            mark_payment_method_operation_unknown(
                db, default_operation, "default_replacement_timeout_unknown"
            )
            raise
        except Exception as exc:
            if provider_detached:
                mark_payment_method_operation_unknown(
                    db, default_operation, "default_replacement_unknown"
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=SAVED_CARD_DETACH_RECORDING_FAILED_DETAIL,
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Stripe could not update the default payment method.",
            ) from exc

        if next_default_payment_method is not None:
            next_default_payment_method.is_default = True
            next_default_payment_method.updated_at = now
            db.add(next_default_payment_method)
        if default_operation is not None:
            apply_payment_method_operation_succeeded(
                db,
                default_operation,
                payment_method_id=(
                    next_default_payment_method.id
                    if next_default_payment_method is not None
                    else None
                ),
            )

    try:
        db.add(payment_method)
        db.commit()
        db.refresh(payment_method)
    except IntegrityError as exc:
        mark_payment_method_operation_unknown(
            db,
            default_operation or operation,
            "detach_local_recording_failed",
        )
        detail = (
            SAVED_CARD_DETACH_RECORDING_FAILED_DETAIL
            if provider_detached
            else build_user_payment_method_conflict_detail(exc)
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        ) from exc
    except SQLAlchemyError as exc:
        mark_payment_method_operation_unknown(
            db,
            default_operation or operation,
            "detach_local_recording_failed",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=SAVED_CARD_DETACH_RECORDING_FAILED_DETAIL,
        ) from exc

    mark_payment_method_operation_succeeded(
        db, operation, payment_method_id=payment_method.id
    )
    return payment_method


def is_saved_payment_method_expired(
    payment_method: UserPaymentMethod,
    now: datetime,
) -> bool:
    return (
        payment_method.exp_year < now.year
        or (
            payment_method.exp_year == now.year
            and payment_method.exp_month < now.month
        )
    )


def get_current_user_saved_payment_method_for_checkout(
    db: Session,
    payment_method_id: uuid.UUID | None,
    current_user: User,
    *,
    now: datetime,
    verify_provider: bool = True,
) -> UserPaymentMethod | None:
    if payment_method_id is None:
        return None

    payment_method = db.get(UserPaymentMethod, payment_method_id)
    if payment_method is None or payment_method.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found.",
        )

    if payment_method.method_status != ACTIVE_PAYMENT_METHOD_STATUS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active payment methods can be used for checkout.",
        )

    if is_saved_payment_method_expired(payment_method, now):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This saved card is expired. Choose another card.",
        )

    if (
        not current_user.stripe_customer_id
        or payment_method.stripe_customer_id != current_user.stripe_customer_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This payment method is not linked to your Stripe customer.",
        )

    if verify_provider:
        verify_saved_payment_method_with_stripe(db, payment_method, current_user, now)

    return payment_method


def verify_saved_payment_method_with_stripe(
    db: Session,
    payment_method: UserPaymentMethod,
    current_user: User,
    now: datetime,
) -> None:
    try:
        stripe_payment_method = retrieve_payment_method(
            payment_method.stripe_payment_method_id
        )
    except StripeConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except PublicTimeoutError:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This saved card could not be verified. Choose another card.",
        ) from exc

    try:
        apply_provider_verified_saved_payment_method(
            db,
            payment_method,
            current_user,
            stripe_payment_method,
            now,
        )
        db.commit()
    except HTTPException:
        db.commit()
        raise


def apply_provider_verified_saved_payment_method(
    db: Session,
    payment_method: UserPaymentMethod,
    current_user: User,
    stripe_payment_method,
    now: datetime,
) -> None:
    if stripe_payment_method.id != payment_method.stripe_payment_method_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This saved card no longer matches the saved provider identity.",
        )

    if (
        stripe_payment_method.customer_id != current_user.stripe_customer_id
        or stripe_payment_method.customer_id != payment_method.stripe_customer_id
    ):
        payment_method.method_status = DETACHED_PAYMENT_METHOD_STATUS
        payment_method.is_default = False
        payment_method.detached_at = now
        payment_method.updated_at = now
        db.add(payment_method)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This saved card is no longer linked to your Stripe customer.",
        )

    if stripe_payment_method.card_fingerprint != payment_method.card_fingerprint:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This saved card no longer matches the saved card details.",
        )

    payment_method.card_brand = stripe_payment_method.card_brand
    payment_method.card_last4 = stripe_payment_method.card_last4
    payment_method.exp_month = stripe_payment_method.exp_month
    payment_method.exp_year = stripe_payment_method.exp_year
    payment_method.updated_at = now
    db.add(payment_method)

    if is_saved_payment_method_expired(payment_method, now):
        payment_method.method_status = "expired"
        payment_method.is_default = False
        payment_method.updated_at = now
        db.add(payment_method)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This saved card is expired. Choose another card.",
        )


def get_locked_payment_method_operation(
    db: Session,
    operation_id: uuid.UUID,
) -> PaymentMethodOperation | None:
    return db.scalars(
        select(PaymentMethodOperation)
        .where(PaymentMethodOperation.id == operation_id)
        .with_for_update()
    ).first()


def _fail_operation(
    db: Session,
    operation: PaymentMethodOperation | None,
    error_code: str,
) -> str:
    apply_payment_method_operation_failed(db, operation, error_code)
    return "failed"


def _unknown_operation(
    db: Session,
    operation: PaymentMethodOperation | None,
    error_code: str,
) -> str:
    apply_payment_method_operation_unknown(
        db,
        operation,
        error_code,
        enqueue_reconciliation=False,
    )
    return "provider_unknown"


def _relock_operation_and_user(
    db: Session,
    operation_id: uuid.UUID,
) -> tuple[PaymentMethodOperation | None, User | None]:
    operation = get_locked_payment_method_operation(db, operation_id)
    user = db.get(User, operation.user_id) if operation is not None else None
    return operation, user


def _reconcile_setup_create(
    db: Session,
    operation: PaymentMethodOperation,
    user: User,
) -> str:
    desired_default = payment_method_operation_desired_default(operation)
    operation_id = operation.id
    customer_id = user.stripe_customer_id
    user_email = user.email
    user_name = build_customer_name(user)
    user_id = user.id
    db.commit()

    try:
        if not customer_id:
            stripe_customer = create_customer(
                email=user_email,
                name=user_name,
                idempotency_key=f"user:{user_id}:stripe_customer",
                metadata={"user_id": str(user_id)},
            )
            customer_id = stripe_customer.id
        setup_intent = create_setup_intent(
            customer_id=customer_id,
            idempotency_key=operation.provider_idempotency_key,
            metadata={
                "user_id": str(user_id),
                "set_as_default": desired_default,
            },
        )
    except StripeConfigError:
        operation, _ = _relock_operation_and_user(db, operation_id)
        return _fail_operation(db, operation, "stripe_not_configured")
    except PublicTimeoutError:
        operation, _ = _relock_operation_and_user(db, operation_id)
        return _unknown_operation(db, operation, "setup_create_timeout_unknown")
    except Exception:  # noqa: BLE001 - durable repair records provider-unknown
        operation, _ = _relock_operation_and_user(db, operation_id)
        return _unknown_operation(db, operation, "setup_create_reconcile_failed")

    operation, user = _relock_operation_and_user(db, operation_id)
    if operation is None:
        return "failed"
    if operation.status in {"succeeded", "failed"}:
        return operation.status
    if user is None:
        return _fail_operation(db, operation, "payment_method_user_unavailable")
    if user.stripe_customer_id and user.stripe_customer_id != customer_id:
        return _fail_operation(db, operation, "payment_method_customer_conflict")
    if not user.stripe_customer_id:
        user.stripe_customer_id = customer_id
        user.updated_at = datetime.now(timezone.utc)
        db.add(user)
    apply_payment_method_operation_succeeded(
        db,
        operation,
        provider_object_id=setup_intent.id,
    )
    return "succeeded"


def _reconcile_sync(
    db: Session,
    operation: PaymentMethodOperation,
    user: User,
) -> str:
    setup_intent_id = operation.provider_object_id
    if not user.stripe_customer_id or not setup_intent_id:
        return _fail_operation(db, operation, "payment_method_operation_invalid")

    desired_default = payment_method_operation_desired_default(operation)
    operation_id = operation.id
    customer_id = user.stripe_customer_id
    db.commit()

    try:
        setup_intent = retrieve_setup_intent(setup_intent_id)
        if (
            setup_intent.customer_id != customer_id
            or setup_intent.status != "succeeded"
            or not setup_intent.payment_method_id
        ):
            operation, _ = _relock_operation_and_user(db, operation_id)
            return _fail_operation(db, operation, "setup_not_completed")
        stripe_payment_method = retrieve_payment_method(setup_intent.payment_method_id)
        if desired_default:
            set_customer_default_payment_method(
                customer_id=customer_id,
                payment_method_id=stripe_payment_method.id,
                idempotency_key=operation.provider_idempotency_key,
            )
    except StripeConfigError:
        operation, _ = _relock_operation_and_user(db, operation_id)
        return _fail_operation(db, operation, "stripe_not_configured")
    except PublicTimeoutError:
        operation, _ = _relock_operation_and_user(db, operation_id)
        return _unknown_operation(db, operation, "sync_timeout_unknown")
    except Exception:  # noqa: BLE001 - durable repair records provider-unknown
        operation, _ = _relock_operation_and_user(db, operation_id)
        return _unknown_operation(db, operation, "sync_reconcile_failed")

    operation, user = _relock_operation_and_user(db, operation_id)
    if operation is None:
        return "failed"
    if operation.status in {"succeeded", "failed"}:
        return operation.status
    if user is None or user.stripe_customer_id != customer_id:
        return _fail_operation(db, operation, "payment_method_user_unavailable")
    if stripe_payment_method.customer_id != customer_id:
        return _fail_operation(db, operation, "payment_method_owner_mismatch")

    existing_payment_method = db.scalar(
        select(UserPaymentMethod).where(
            UserPaymentMethod.stripe_payment_method_id == stripe_payment_method.id
        )
    )
    if (
        existing_payment_method is not None
        and existing_payment_method.user_id != user.id
    ):
        return _fail_operation(db, operation, "payment_method_conflict")

    existing_card = db.scalar(
        select(UserPaymentMethod).where(
            UserPaymentMethod.user_id == user.id,
            UserPaymentMethod.card_fingerprint
            == stripe_payment_method.card_fingerprint,
        )
    )
    if (
        existing_card is not None
        and existing_card.method_status == ACTIVE_PAYMENT_METHOD_STATUS
        and existing_card.stripe_payment_method_id != stripe_payment_method.id
    ):
        return _fail_operation(db, operation, "card_already_saved")

    active_payment_method_count = count_active_payment_methods(db, user.id)
    if (
        existing_card is None
        and active_payment_method_count >= MAX_ACTIVE_PAYMENT_METHODS
    ):
        return _fail_operation(db, operation, "saved_card_limit")

    should_default = active_payment_method_count == 0 or desired_default
    if should_default:
        unset_other_active_defaults(db, user.id)

    now = datetime.now(timezone.utc)
    if existing_card is None:
        payment_method = UserPaymentMethod(
            id=uuid.uuid4(),
            user_id=user.id,
            stripe_customer_id=customer_id,
            stripe_payment_method_id=stripe_payment_method.id,
            card_fingerprint=stripe_payment_method.card_fingerprint,
            card_brand=stripe_payment_method.card_brand,
            card_last4=stripe_payment_method.card_last4,
            exp_month=stripe_payment_method.exp_month,
            exp_year=stripe_payment_method.exp_year,
            method_status=ACTIVE_PAYMENT_METHOD_STATUS,
            is_default=should_default,
            detached_at=None,
        )
    else:
        payment_method = existing_card
        payment_method.stripe_customer_id = customer_id
        payment_method.stripe_payment_method_id = stripe_payment_method.id
        payment_method.card_fingerprint = stripe_payment_method.card_fingerprint
        payment_method.card_brand = stripe_payment_method.card_brand
        payment_method.card_last4 = stripe_payment_method.card_last4
        payment_method.exp_month = stripe_payment_method.exp_month
        payment_method.exp_year = stripe_payment_method.exp_year
        payment_method.method_status = ACTIVE_PAYMENT_METHOD_STATUS
        payment_method.is_default = should_default
        payment_method.detached_at = None
        payment_method.updated_at = now

    db.add(payment_method)
    apply_payment_method_operation_succeeded(
        db,
        operation,
        provider_object_id=setup_intent_id,
        payment_method_id=payment_method.id,
    )
    return "succeeded"


def _reconcile_set_default(
    db: Session,
    operation: PaymentMethodOperation,
    user: User,
) -> str:
    if not user.stripe_customer_id or operation.payment_method_id is None:
        return _fail_operation(db, operation, "payment_method_operation_invalid")

    operation_id = operation.id
    payment_method_id = operation.payment_method_id
    customer_id = user.stripe_customer_id
    payment_method = db.get(UserPaymentMethod, payment_method_id)
    if payment_method is None or payment_method.user_id != user.id:
        return _fail_operation(db, operation, "payment_method_not_found")
    provider_payment_method_id = payment_method.stripe_payment_method_id
    db.commit()

    try:
        stripe_payment_method = retrieve_payment_method(provider_payment_method_id)
        if stripe_payment_method.customer_id != customer_id:
            operation, _ = _relock_operation_and_user(db, operation_id)
            return _fail_operation(db, operation, "payment_method_owner_mismatch")
        set_customer_default_payment_method(
            customer_id=customer_id,
            payment_method_id=provider_payment_method_id,
            idempotency_key=operation.provider_idempotency_key,
        )
    except StripeConfigError:
        operation, _ = _relock_operation_and_user(db, operation_id)
        return _fail_operation(db, operation, "stripe_not_configured")
    except PublicTimeoutError:
        operation, _ = _relock_operation_and_user(db, operation_id)
        return _unknown_operation(db, operation, "set_default_timeout_unknown")
    except Exception:  # noqa: BLE001 - durable repair records provider-unknown
        operation, _ = _relock_operation_and_user(db, operation_id)
        return _unknown_operation(db, operation, "set_default_reconcile_failed")

    operation, user = _relock_operation_and_user(db, operation_id)
    if operation is None:
        return "failed"
    if operation.status in {"succeeded", "failed"}:
        return operation.status
    payment_method = db.scalar(
        select(UserPaymentMethod)
        .where(UserPaymentMethod.id == payment_method_id)
        .with_for_update()
    )
    if user is None or payment_method is None or payment_method.user_id != user.id:
        return _fail_operation(db, operation, "payment_method_not_found")
    try:
        apply_provider_verified_saved_payment_method(
            db,
            payment_method,
            user,
            stripe_payment_method,
            datetime.now(timezone.utc),
        )
    except HTTPException:
        return _fail_operation(db, operation, "payment_method_provider_mismatch")
    unset_other_active_defaults(db, user.id, keep_payment_method_id=payment_method.id)
    payment_method.is_default = True
    payment_method.updated_at = datetime.now(timezone.utc)
    db.add(payment_method)
    apply_payment_method_operation_succeeded(
        db,
        operation,
        payment_method_id=payment_method.id,
    )
    return "succeeded"


def _reconcile_clear_default(
    db: Session,
    operation: PaymentMethodOperation,
    user: User,
) -> str:
    if not user.stripe_customer_id:
        return _fail_operation(db, operation, "payment_method_operation_invalid")

    operation_id = operation.id
    customer_id = user.stripe_customer_id
    user_id = user.id
    db.commit()

    try:
        clear_customer_default_payment_method(
            customer_id=customer_id,
            idempotency_key=operation.provider_idempotency_key,
        )
    except StripeConfigError:
        operation, _ = _relock_operation_and_user(db, operation_id)
        return _fail_operation(db, operation, "stripe_not_configured")
    except PublicTimeoutError:
        operation, _ = _relock_operation_and_user(db, operation_id)
        return _unknown_operation(
            db,
            operation,
            "clear_default_timeout_unknown",
        )
    except Exception:  # noqa: BLE001 - durable repair records provider-unknown
        operation, _ = _relock_operation_and_user(db, operation_id)
        return _unknown_operation(db, operation, "clear_default_reconcile_failed")

    operation, user = _relock_operation_and_user(db, operation_id)
    if operation is None:
        return "failed"
    if operation.status in {"succeeded", "failed"}:
        return operation.status
    if user is None or user.id != user_id or user.stripe_customer_id != customer_id:
        return _fail_operation(db, operation, "payment_method_user_unavailable")

    for payment_method in db.scalars(
        select(UserPaymentMethod)
        .where(
            UserPaymentMethod.user_id == user.id,
            UserPaymentMethod.method_status == ACTIVE_PAYMENT_METHOD_STATUS,
            UserPaymentMethod.is_default.is_(True),
        )
        .with_for_update()
    ).all():
        payment_method.is_default = False
        payment_method.updated_at = datetime.now(timezone.utc)
        db.add(payment_method)

    apply_payment_method_operation_succeeded(db, operation)
    return "succeeded"


def _reconcile_detach(
    db: Session,
    operation: PaymentMethodOperation,
    user: User,
) -> str:
    if operation.payment_method_id is None:
        return _fail_operation(db, operation, "payment_method_operation_invalid")

    operation_id = operation.id
    payment_method_id = operation.payment_method_id
    payment_method = db.get(UserPaymentMethod, payment_method_id)
    if payment_method is None or payment_method.user_id != user.id:
        return _fail_operation(db, operation, "payment_method_not_found")
    provider_payment_method_id = payment_method.stripe_payment_method_id
    customer_id = user.stripe_customer_id or payment_method.stripe_customer_id
    was_default = bool(payment_method.is_default)
    next_default_provider_id = None
    default_provider_idempotency_key = None
    if was_default:
        remaining_payment_methods = list_active_payment_methods(
            db,
            user.id,
            excluding_payment_method_id=payment_method.id,
        )
        if remaining_payment_methods:
            next_default_provider_id = (
                remaining_payment_methods[0].stripe_payment_method_id
            )
        default_operation_kind = (
            "set_default" if next_default_provider_id is not None else "clear_default"
        )
        default_provider_idempotency_key = (
            f"payment-method:{user.id}:"
            f"{uuid.uuid5(uuid.NAMESPACE_URL, f'payment-method-operation:{operation.id}:{default_operation_kind}')}"
        )
    db.commit()

    try:
        stripe_payment_method = retrieve_payment_method(provider_payment_method_id)
        if stripe_payment_method.customer_id != customer_id:
            operation, _ = _relock_operation_and_user(db, operation_id)
            return _fail_operation(db, operation, "payment_method_owner_mismatch")
        detach_payment_method(
            provider_payment_method_id,
            idempotency_key=operation.provider_idempotency_key,
        )
        if customer_id:
            if next_default_provider_id is not None:
                set_customer_default_payment_method(
                    customer_id=customer_id,
                    payment_method_id=next_default_provider_id,
                    idempotency_key=default_provider_idempotency_key,
                )
            else:
                clear_customer_default_payment_method(
                    customer_id=customer_id,
                    idempotency_key=default_provider_idempotency_key,
                )
    except StripeConfigError:
        operation, _ = _relock_operation_and_user(db, operation_id)
        return _fail_operation(db, operation, "stripe_not_configured")
    except PublicTimeoutError:
        operation, _ = _relock_operation_and_user(db, operation_id)
        return _unknown_operation(db, operation, "detach_timeout_unknown")
    except Exception:  # noqa: BLE001 - durable repair records provider-unknown
        operation, _ = _relock_operation_and_user(db, operation_id)
        return _unknown_operation(db, operation, "detach_reconcile_failed")

    operation, user = _relock_operation_and_user(db, operation_id)
    if operation is None:
        return "failed"
    if operation.status in {"succeeded", "failed"}:
        return operation.status
    payment_method = db.scalar(
        select(UserPaymentMethod)
        .where(UserPaymentMethod.id == payment_method_id)
        .with_for_update()
    )
    if user is None or payment_method is None or payment_method.user_id != user.id:
        return _fail_operation(db, operation, "payment_method_not_found")
    now = datetime.now(timezone.utc)
    payment_method.method_status = DETACHED_PAYMENT_METHOD_STATUS
    payment_method.is_default = False
    payment_method.detached_at = payment_method.detached_at or now
    payment_method.updated_at = now
    db.add(payment_method)
    if was_default:
        remaining_payment_methods = list_active_payment_methods(
            db,
            user.id,
            excluding_payment_method_id=payment_method.id,
        )
        next_default_payment_method = (
            remaining_payment_methods[0] if remaining_payment_methods else None
        )
        if next_default_payment_method is not None:
            next_default_payment_method.is_default = True
            next_default_payment_method.updated_at = now
            db.add(next_default_payment_method)
    apply_payment_method_operation_succeeded(
        db,
        operation,
        payment_method_id=payment_method.id,
    )
    return "succeeded"


def reconcile_payment_method_operation(
    db: Session,
    operation_id: uuid.UUID,
) -> str:
    operation = get_locked_payment_method_operation(db, operation_id)
    if operation is None:
        return "failed"
    if operation.status in {"succeeded", "failed"}:
        return operation.status
    user = db.get(User, operation.user_id)
    if user is None or (
        operation.operation_kind != "setup_create" and not user.stripe_customer_id
    ):
        return _fail_operation(db, operation, "payment_method_user_unavailable")

    try:
        payment_method_operation_idempotency_key(operation)
        if operation.operation_kind in {"setup_create", "sync"}:
            payment_method_operation_desired_default(operation)
    except ValueError:
        return _fail_operation(db, operation, "payment_method_operation_invalid")

    if operation.operation_kind == "setup_create":
        return _reconcile_setup_create(db, operation, user)
    if operation.operation_kind == "sync":
        return _reconcile_sync(db, operation, user)
    if operation.operation_kind == "set_default":
        return _reconcile_set_default(db, operation, user)
    if operation.operation_kind == "detach":
        return _reconcile_detach(db, operation, user)
    if operation.operation_kind == "clear_default":
        return _reconcile_clear_default(db, operation, user)

    return _fail_operation(db, operation, "payment_method_operation_invalid")
