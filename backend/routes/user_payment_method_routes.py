# ruff: noqa: B008
import uuid

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, UserPaymentMethod
from backend.schemas import (
    UserPaymentMethodRead,
    UserPaymentMethodSetupIntentCreate,
    UserPaymentMethodSetupIntentRead,
    UserPaymentMethodSyncCreate,
)
from backend.services.auth_service import (
    require_active_user,
    require_recent_active_user,
)
from backend.services.payment_method_service import (
    create_saved_payment_method_setup_intent,
    detach_saved_payment_method,
    get_owned_payment_method_or_404,
    set_default_saved_payment_method,
    sync_saved_payment_method,
)
from backend.services.payment_method_service import (
    list_current_user_payment_methods as list_current_user_payment_methods_workflow,
)
from backend.services.query_pagination import (
    DEFAULT_COLLECTION_LIMIT,
    MAX_COLLECTION_LIMIT,
)

router = APIRouter(prefix="/user-payment-methods", tags=["user-payment-methods"])


@router.get(
    "",
    response_model=list[UserPaymentMethodRead],
    status_code=status.HTTP_200_OK,
)
def list_current_user_payment_methods(
    include_inactive: bool = False,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(
        default=DEFAULT_COLLECTION_LIMIT,
        ge=1,
        le=MAX_COLLECTION_LIMIT,
    ),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[UserPaymentMethod]:
    return list_current_user_payment_methods_workflow(
        db,
        current_user,
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/setup-intent",
    response_model=UserPaymentMethodSetupIntentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_current_user_payment_method_setup_intent(
    setup_request: UserPaymentMethodSetupIntentCreate,
    idempotency_key: uuid.UUID = Header(alias="Idempotency-Key"),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> UserPaymentMethodSetupIntentRead:
    client_secret = create_saved_payment_method_setup_intent(
        db,
        current_user,
        set_as_default=setup_request.set_as_default,
        idempotency_key=idempotency_key,
    )
    return UserPaymentMethodSetupIntentRead(client_secret=client_secret)


@router.post(
    "/sync",
    response_model=UserPaymentMethodRead,
    status_code=status.HTTP_201_CREATED,
)
def sync_current_user_payment_method(
    sync_request: UserPaymentMethodSyncCreate,
    idempotency_key: uuid.UUID = Header(alias="Idempotency-Key"),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> UserPaymentMethod:
    return sync_saved_payment_method(
        db,
        current_user,
        setup_intent_id=sync_request.setup_intent_id,
        set_as_default=sync_request.set_as_default,
        idempotency_key=idempotency_key,
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
    idempotency_key: uuid.UUID = Header(alias="Idempotency-Key"),
    current_user: User = Depends(require_recent_active_user),
    db: Session = Depends(get_db),
) -> UserPaymentMethod:
    return set_default_saved_payment_method(
        db,
        current_user,
        payment_method_id,
        idempotency_key=idempotency_key,
    )


@router.delete(
    "/{payment_method_id}",
    response_model=UserPaymentMethodRead,
    status_code=status.HTTP_200_OK,
)
def detach_current_user_payment_method(
    payment_method_id: uuid.UUID,
    idempotency_key: uuid.UUID = Header(alias="Idempotency-Key"),
    current_user: User = Depends(require_recent_active_user),
    db: Session = Depends(get_db),
) -> UserPaymentMethod:
    return detach_saved_payment_method(
        db,
        current_user,
        payment_method_id,
        idempotency_key=idempotency_key,
    )
