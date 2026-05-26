import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, UserPaymentMethod
from backend.routes.auth_routes import get_current_app_user
from backend.routes.user_routes import build_conflict_detail
from backend.schemas import (
    UserPaymentMethodRead,
    UserPaymentMethodSetupIntentCreate,
    UserPaymentMethodSetupIntentRead,
    UserPaymentMethodSyncCreate,
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
)

router = APIRouter(prefix="/user-payment-methods", tags=["user-payment-methods"])

ACTIVE_METHOD_STATUS = "active"
DETACHED_METHOD_STATUS = "detached"
MAX_ACTIVE_PAYMENT_METHODS = 5


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
            detail=build_conflict_detail(exc),
        ) from exc

    return current_user.stripe_customer_id


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


def unset_other_active_defaults(
    db: Session,
    user_id: uuid.UUID,
    *,
    keep_payment_method_id: uuid.UUID | None = None,
) -> None:
    existing_defaults = db.scalars(
        select(UserPaymentMethod).where(
            UserPaymentMethod.user_id == user_id,
            UserPaymentMethod.method_status == ACTIVE_METHOD_STATUS,
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
                UserPaymentMethod.method_status == ACTIVE_METHOD_STATUS,
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
        UserPaymentMethod.method_status == ACTIVE_METHOD_STATUS,
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
    except Exception:
        pass


@router.get(
    "",
    response_model=list[UserPaymentMethodRead],
    status_code=status.HTTP_200_OK,
)
def list_current_user_payment_methods(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> list[UserPaymentMethod]:
    statement = select(UserPaymentMethod).where(
        UserPaymentMethod.user_id == current_user.id
    )

    if not include_inactive:
        statement = statement.where(
            UserPaymentMethod.method_status == ACTIVE_METHOD_STATUS
        )

    payment_methods = db.scalars(
        statement.order_by(
            UserPaymentMethod.created_at.asc(),
            UserPaymentMethod.id.asc(),
        )
    ).all()
    return list(payment_methods)


@router.post(
    "/setup-intent",
    response_model=UserPaymentMethodSetupIntentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_current_user_payment_method_setup_intent(
    setup_request: UserPaymentMethodSetupIntentCreate,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> UserPaymentMethodSetupIntentRead:
    stripe_customer_id = ensure_stripe_customer_id(db, current_user)

    try:
        setup_intent = create_setup_intent(
            customer_id=stripe_customer_id,
            idempotency_key=(
                f"user:{current_user.id}:payment_method_setup:{uuid.uuid4()}"
            ),
            metadata={
                "user_id": str(current_user.id),
                "set_as_default": setup_request.set_as_default,
            },
        )
    except StripeConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe could not create this setup intent.",
        ) from exc

    if not setup_intent.client_secret:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe did not return a client secret for this setup intent.",
        )

    return UserPaymentMethodSetupIntentRead(client_secret=setup_intent.client_secret)


@router.post(
    "/sync",
    response_model=UserPaymentMethodRead,
    status_code=status.HTTP_201_CREATED,
)
def sync_current_user_payment_method(
    sync_request: UserPaymentMethodSyncCreate,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> UserPaymentMethod:
    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Create a Stripe customer before syncing a payment method.",
        )

    try:
        setup_intent = retrieve_setup_intent(sync_request.setup_intent_id)
    except StripeConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe could not retrieve this setup intent.",
        ) from exc

    if setup_intent.customer_id != current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This setup intent does not belong to the current user.",
        )

    if setup_intent.status != "succeeded" or not setup_intent.payment_method_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This setup intent has not completed with a payment method.",
        )

    try:
        stripe_payment_method = retrieve_payment_method(
            setup_intent.payment_method_id
        )
    except StripeConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe could not retrieve this payment method.",
        ) from exc

    if stripe_payment_method.customer_id != current_user.stripe_customer_id:
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
        and existing_card.method_status == ACTIVE_METHOD_STATUS
    ):
        if existing_card.stripe_payment_method_id != stripe_payment_method.id:
            detach_unpersisted_payment_method(stripe_payment_method.id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This card is already saved.",
        )

    active_payment_method_count = count_active_payment_methods(db, current_user.id)
    if active_payment_method_count >= MAX_ACTIVE_PAYMENT_METHODS:
        detach_unpersisted_payment_method(stripe_payment_method.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You can save up to {MAX_ACTIVE_PAYMENT_METHODS} active cards.",
        )

    should_default = (
        active_payment_method_count == 0 or sync_request.set_as_default
    )
    if should_default:
        try:
            set_customer_default_payment_method(
                customer_id=current_user.stripe_customer_id,
                payment_method_id=stripe_payment_method.id,
            )
        except StripeConfigError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Stripe could not set this default payment method.",
            ) from exc
        unset_other_active_defaults(db, current_user.id)
        db.flush()

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
            method_status=ACTIVE_METHOD_STATUS,
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
        payment_method.method_status = ACTIVE_METHOD_STATUS
        payment_method.is_default = should_default
        payment_method.detached_at = None
        payment_method.updated_at = now

    try:
        db.add(payment_method)
        db.commit()
        db.refresh(payment_method)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_payment_method_conflict_detail(exc),
        ) from exc

    return payment_method


@router.get(
    "/{payment_method_id}",
    response_model=UserPaymentMethodRead,
    status_code=status.HTTP_200_OK,
)
def get_current_user_payment_method(
    payment_method_id: uuid.UUID,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> UserPaymentMethod:
    return get_owned_payment_method_or_404(db, payment_method_id, current_user)


@router.patch(
    "/{payment_method_id}/default",
    response_model=UserPaymentMethodRead,
    status_code=status.HTTP_200_OK,
)
def set_current_user_default_payment_method(
    payment_method_id: uuid.UUID,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> UserPaymentMethod:
    payment_method = get_owned_payment_method_or_404(
        db, payment_method_id, current_user
    )
    if payment_method.method_status != ACTIVE_METHOD_STATUS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active payment methods can be made default.",
        )

    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This user does not have a Stripe customer.",
        )

    try:
        set_customer_default_payment_method(
            customer_id=current_user.stripe_customer_id,
            payment_method_id=payment_method.stripe_payment_method_id,
        )
    except StripeConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe could not set this default payment method.",
        ) from exc

    unset_other_active_defaults(db, current_user.id)
    db.flush()

    payment_method.is_default = True
    payment_method.updated_at = datetime.now(timezone.utc)

    try:
        db.add(payment_method)
        db.commit()
        db.refresh(payment_method)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_payment_method_conflict_detail(exc),
        ) from exc

    return payment_method


@router.delete(
    "/{payment_method_id}",
    response_model=UserPaymentMethodRead,
    status_code=status.HTTP_200_OK,
)
def detach_current_user_payment_method(
    payment_method_id: uuid.UUID,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> UserPaymentMethod:
    payment_method = get_owned_payment_method_or_404(
        db, payment_method_id, current_user
    )
    if payment_method.method_status == DETACHED_METHOD_STATUS:
        return payment_method

    try:
        detach_payment_method(payment_method.stripe_payment_method_id)
    except StripeConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe could not detach this payment method.",
        ) from exc

    now = datetime.now(timezone.utc)
    was_default = bool(payment_method.is_default)
    payment_method.method_status = DETACHED_METHOD_STATUS
    payment_method.is_default = False
    payment_method.detached_at = now
    payment_method.updated_at = now
    db.add(payment_method)
    db.flush()
    next_default_payment_method: UserPaymentMethod | None = None

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

        try:
            if next_default_payment_method is not None and stripe_customer_id:
                set_customer_default_payment_method(
                    customer_id=stripe_customer_id,
                    payment_method_id=next_default_payment_method.stripe_payment_method_id,
                )
            elif stripe_customer_id:
                clear_customer_default_payment_method(
                    customer_id=stripe_customer_id,
                )
        except StripeConfigError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Stripe could not update the default payment method.",
            ) from exc

        if next_default_payment_method is not None:
            next_default_payment_method.is_default = True
            next_default_payment_method.updated_at = now
            db.add(next_default_payment_method)

    try:
        db.add(payment_method)
        db.commit()
        db.refresh(payment_method)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_payment_method_conflict_detail(exc),
        ) from exc

    return payment_method
