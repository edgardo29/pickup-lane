import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, UserPaymentMethod
from backend.schemas import (
    UserPaymentMethodCreate,
    UserPaymentMethodRead,
    UserPaymentMethodUpdate,
)

router = APIRouter(prefix="/user-payment-methods", tags=["user-payment-methods"])


def build_user_payment_method_conflict_detail(exc: IntegrityError) -> str:
    # Map known payment-method uniqueness issues to clearer API messages so
    # Postman responses are easier to understand during development.
    error_text = str(exc.orig)

    if "uq_user_payment_methods_provider_payment_method_id" in error_text:
        return "A payment method with this provider_payment_method_id already exists."

    if "ix_user_payment_methods_one_active_default_per_user" in error_text:
        return "A user can only have one active default payment method."

    return error_text


def unset_other_active_defaults(
    db: Session, user_id: uuid.UUID, keep_payment_method_id: uuid.UUID | None = None
) -> None:
    # When one payment method becomes the active default, clear that flag from
    # every other active payment method for the same user.
    existing_defaults = db.scalars(
        select(UserPaymentMethod).where(
            UserPaymentMethod.user_id == user_id,
            UserPaymentMethod.is_default.is_(True),
            UserPaymentMethod.is_active.is_(True),
        )
    ).all()

    for payment_method in existing_defaults:
        if payment_method.id == keep_payment_method_id:
            continue

        payment_method.is_default = False
        payment_method.updated_at = datetime.now(timezone.utc)
        db.add(payment_method)


# This route lists a user's saved payment-method references. By default it
# returns only active methods so deactivated records do not show up in the
# normal app flow.
@router.get("", response_model=list[UserPaymentMethodRead], status_code=status.HTTP_200_OK)
def list_user_payment_methods(
    user_id: uuid.UUID, include_inactive: bool = False, db: Session = Depends(get_db)
) -> list[UserPaymentMethod]:
    db_user = db.get(User, user_id)

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    statement = select(UserPaymentMethod).where(UserPaymentMethod.user_id == user_id)

    if not include_inactive:
        statement = statement.where(UserPaymentMethod.is_active.is_(True))

    # Show the most relevant methods first: active before inactive, default
    # before non-default, then older records before newer ones within the same
    # state bucket.
    payment_methods = db.scalars(
        statement.order_by(
            UserPaymentMethod.is_active.desc(),
            UserPaymentMethod.is_default.desc(),
            UserPaymentMethod.created_at.asc(),
        )
    ).all()
    return list(payment_methods)


# This route creates a saved payment-method reference for an existing user.
@router.post(
    "", response_model=UserPaymentMethodRead, status_code=status.HTTP_201_CREATED
)
def create_user_payment_method(
    user_payment_method: UserPaymentMethodCreate, db: Session = Depends(get_db)
) -> UserPaymentMethod:
    db_user = db.get(User, user_payment_method.user_id)

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user_payment_method.is_default and not user_payment_method.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A default payment method must be active.",
        )

    if user_payment_method.is_default:
        unset_other_active_defaults(db, user_payment_method.user_id)

    new_user_payment_method = UserPaymentMethod(
        id=uuid.uuid4(),
        user_id=user_payment_method.user_id,
        provider=user_payment_method.provider,
        provider_payment_method_id=user_payment_method.provider_payment_method_id,
        card_brand=user_payment_method.card_brand,
        card_last4=user_payment_method.card_last4,
        exp_month=user_payment_method.exp_month,
        exp_year=user_payment_method.exp_year,
        is_default=user_payment_method.is_default,
        is_active=user_payment_method.is_active,
    )

    try:
        db.add(new_user_payment_method)
        db.commit()
        db.refresh(new_user_payment_method)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_payment_method_conflict_detail(exc),
        ) from exc

    return new_user_payment_method


# This route fetches a saved payment-method reference by its internal UUID.
@router.get(
    "/{payment_method_id}",
    response_model=UserPaymentMethodRead,
    status_code=status.HTTP_200_OK,
)
def get_user_payment_method(
    payment_method_id: uuid.UUID, db: Session = Depends(get_db)
) -> UserPaymentMethod:
    db_user_payment_method = db.get(UserPaymentMethod, payment_method_id)

    if db_user_payment_method is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User payment method not found.",
        )

    return db_user_payment_method


# This route applies partial updates to an existing saved payment-method
# reference.
@router.patch(
    "/{payment_method_id}",
    response_model=UserPaymentMethodRead,
    status_code=status.HTTP_200_OK,
)
def update_user_payment_method(
    payment_method_id: uuid.UUID,
    user_payment_method_update: UserPaymentMethodUpdate,
    db: Session = Depends(get_db),
) -> UserPaymentMethod:
    db_user_payment_method = db.get(UserPaymentMethod, payment_method_id)

    if db_user_payment_method is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User payment method not found.",
        )

    update_data = user_payment_method_update.model_dump(exclude_unset=True)

    # Deactivation should always clear the default flag so a user cannot have
    # an inactive payment method still marked as default.
    if update_data.get("is_active") is False:
        update_data["is_default"] = False

    effective_is_active = update_data.get("is_active", db_user_payment_method.is_active)
    effective_is_default = update_data.get(
        "is_default", db_user_payment_method.is_default
    )

    if effective_is_default and not effective_is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A default payment method must be active.",
        )

    if effective_is_default:
        unset_other_active_defaults(
            db,
            db_user_payment_method.user_id,
            keep_payment_method_id=db_user_payment_method.id,
        )

    for field_name, field_value in update_data.items():
        setattr(db_user_payment_method, field_name, field_value)

    # Keep updated_at aligned with the latest payment-method change so the
    # record has a trustworthy modification timestamp.
    db_user_payment_method.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_user_payment_method)
        db.commit()
        db.refresh(db_user_payment_method)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_payment_method_conflict_detail(exc),
        ) from exc

    return db_user_payment_method
