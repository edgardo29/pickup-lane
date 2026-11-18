import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import (
    GameCheckoutGuestPaymentIntentCreate,
    GameCheckoutPaymentIntentCreate,
    GameCheckoutPaymentIntentRead,
    GameCheckoutQuoteRead,
    GameCheckoutStatusRead,
)
from backend.services.auth_service import require_active_user, require_verified_user
from backend.services.checkout_service import (
    create_game_checkout_payment_intent_workflow,
    create_guest_checkout_payment_intent_workflow,
    get_game_checkout_quote_workflow,
    get_game_checkout_status_workflow,
)

router = APIRouter(prefix="/checkout", tags=["checkout"])


# The price, the player's credit, and the amount due for a proposed party.
@router.get(
    "/games/{game_id}/quote",
    response_model=GameCheckoutQuoteRead,
    status_code=status.HTTP_200_OK,
)
def get_game_checkout_quote(
    game_id: uuid.UUID,
    response: Response,
    guest_count: int = Query(default=0, ge=0, le=2),
    add_guests: bool = False,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> GameCheckoutQuoteRead:
    response.headers["Cache-Control"] = "no-store"
    return get_game_checkout_quote_workflow(
        db,
        game_id,
        current_user,
        guest_count=guest_count,
        add_guests=add_guests,
    )


@router.post(
    "/games/{game_id}/payment-intent",
    response_model=GameCheckoutPaymentIntentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_game_checkout_payment_intent(
    game_id: uuid.UUID,
    checkout_request: GameCheckoutPaymentIntentCreate,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
) -> GameCheckoutPaymentIntentRead:
    return create_game_checkout_payment_intent_workflow(
        db,
        game_id,
        checkout_request,
        current_user,
    )


# Guests added to the player's confirmed booking in a paid official game.
@router.post(
    "/games/{game_id}/guest-payment-intent",
    response_model=GameCheckoutPaymentIntentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_guest_checkout_payment_intent(
    game_id: uuid.UUID,
    checkout_request: GameCheckoutGuestPaymentIntentCreate,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
) -> GameCheckoutPaymentIntentRead:
    return create_guest_checkout_payment_intent_workflow(
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
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> GameCheckoutStatusRead:
    return get_game_checkout_status_workflow(db, booking_id, current_user)
