import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import (
    GameCheckoutPaymentIntentCreate,
    GameCheckoutPaymentIntentRead,
    GameCheckoutStatusRead,
)
from backend.services.auth_service import get_current_app_user
from backend.services.checkout_service import (
    create_game_checkout_payment_intent_workflow,
    get_game_checkout_status_workflow,
)

router = APIRouter(prefix="/checkout", tags=["checkout"])


@router.post(
    "/games/{game_id}/payment-intent",
    response_model=GameCheckoutPaymentIntentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_game_checkout_payment_intent(
    game_id: uuid.UUID,
    checkout_request: GameCheckoutPaymentIntentCreate,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> GameCheckoutPaymentIntentRead:
    return create_game_checkout_payment_intent_workflow(
        db,
        game_id,
        checkout_request,
        current_user,
    )


@router.get(
    "/bookings/{booking_id}/status",
    response_model=GameCheckoutStatusRead,
    status_code=status.HTTP_200_OK,
)
def get_game_checkout_status(
    booking_id: uuid.UUID,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> GameCheckoutStatusRead:
    return get_game_checkout_status_workflow(db, booking_id, current_user)
