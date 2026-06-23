import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, UserPaymentMethod
from backend.schemas import (
    UserPaymentMethodRead,
    UserPaymentMethodSetupIntentCreate,
    UserPaymentMethodSetupIntentRead,
    UserPaymentMethodSyncCreate,
)
from backend.services.auth_service import require_active_user
from backend.services.payment_method_service import (
    ACTIVE_PAYMENT_METHOD_STATUS,
    create_saved_payment_method_setup_intent,
    detach_saved_payment_method,
    get_owned_payment_method_or_404,
    set_default_saved_payment_method,
    sync_saved_payment_method,
)

router = APIRouter(prefix="/user-payment-methods", tags=["user-payment-methods"])

ACTIVE_METHOD_STATUS = ACTIVE_PAYMENT_METHOD_STATUS


@router.get(
    "",
    response_model=list[UserPaymentMethodRead],
    status_code=status.HTTP_200_OK,
)
def list_current_user_payment_methods(
    include_inactive: bool = False,
    current_user: User = Depends(require_active_user),
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
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> UserPaymentMethodSetupIntentRead:
    client_secret = create_saved_payment_method_setup_intent(
        db,
        current_user,
        set_as_default=setup_request.set_as_default,
    )
    return UserPaymentMethodSetupIntentRead(client_secret=client_secret)


@router.post(
    "/sync",
    response_model=UserPaymentMethodRead,
    status_code=status.HTTP_201_CREATED,
)
def sync_current_user_payment_method(
    sync_request: UserPaymentMethodSyncCreate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> UserPaymentMethod:
    return sync_saved_payment_method(
        db,
        current_user,
        setup_intent_id=sync_request.setup_intent_id,
        set_as_default=sync_request.set_as_default,
    )


@router.get(
    "/{payment_method_id}",
    response_model=UserPaymentMethodRead,
    status_code=status.HTTP_200_OK,
)
def get_current_user_payment_method(
    payment_method_id: uuid.UUID,
    current_user: User = Depends(require_active_user),
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
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> UserPaymentMethod:
    return set_default_saved_payment_method(db, current_user, payment_method_id)


@router.delete(
    "/{payment_method_id}",
    response_model=UserPaymentMethodRead,
    status_code=status.HTTP_200_OK,
)
def detach_current_user_payment_method(
    payment_method_id: uuid.UUID,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> UserPaymentMethod:
    return detach_saved_payment_method(db, current_user, payment_method_id)
