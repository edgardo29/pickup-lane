import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import case, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    CommunityGameDetail,
    CommunityPublishAttempt,
    Game,
    GameParticipant,
    HostPublishEntitlement,
    HostPublishFee,
    Payment,
    User,
    Venue,
)
from backend.schemas.community_publish_attempt_schema import (
    CommunityPublishAttemptStatusRead,
)
from backend.schemas.community_game_publish_schema import (
    CommunityGamePublishCreate,
    CommunityGamePublishRead,
)
from backend.services.auth_service import user_is_active_admin
from backend.services.game_rules import (
    build_game_conflict_detail,
    get_default_host_guest_max,
    normalize_game_lifecycle_fields,
    validate_game_business_rules,
)
from backend.services.hosting_access_service import (
    require_community_publish_hosting_access,
)
from backend.services.moderation_surfacing_service import surface_community_game_text
from backend.services.payment_method_service import (
    get_current_user_saved_payment_method_for_checkout,
)
from backend.services.payment_rules import COLLECTED_PAYMENT_STATUSES
from backend.services.stripe_service import (
    StripeConfigError,
    confirm_payment_intent,
    create_payment_intent,
    get_stripe_currency,
    map_payment_intent_status,
)
from backend.services.user_service import get_user_display_name
from backend.services.venue_service import find_matching_active_venue

COMMUNITY_PUBLISH_FEE_CENTS = 499
FIRST_FREE_WAIVER_REASON = "first_game_free"
ADMIN_COMP_WAIVER_REASON = "admin_comp"
COMMUNITY_PUBLISH_ATTEMPT_EXPIRATION_MINUTES = 30
ACTIVE_PUBLISH_ATTEMPT_STATUSES = {
    "requires_payment_method",
    "requires_action",
    "processing",
}
ABANDONED_PUBLISH_ATTEMPT_STATUSES = {
    "requires_payment_method",
    "requires_action",
}
TERMINAL_PUBLISH_ATTEMPT_STATUSES = {
    "succeeded",
    "failed",
    "cancelled",
    "expired",
}


def get_verified_community_host_or_404(db: Session, user_id: uuid.UUID) -> User:
    db_user = db.scalar(
        select(User).where(User.id == user_id).with_for_update()
    )

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host user not found.",
        )

    if db_user.account_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active account required.",
        )

    if db_user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verify your email before publishing.",
        )

    require_community_publish_hosting_access(db_user)
    return db_user


def build_address_snapshot(venue: dict[str, object]) -> str:
    state_line = " ".join(
        value
        for value in [
            str(venue["state"]).strip(),
            str(venue["postal_code"]).strip(),
        ]
        if value
    )
    city_line = ", ".join(
        value for value in [str(venue["city"]).strip(), state_line] if value
    )
    return ", ".join(
        value for value in [str(venue["address_line_1"]).strip(), city_line] if value
    )


def get_or_create_approved_venue(
    db: Session,
    *,
    host_user_id: uuid.UUID,
    venue_data: dict[str, object],
) -> Venue:
    matching_venue = find_matching_active_venue(
        db,
        name=venue_data["name"],
        address_line_1=venue_data["address_line_1"],
        city=venue_data["city"],
        state=venue_data["state"],
        postal_code=venue_data["postal_code"],
        country_code=venue_data["country_code"],
        neighborhood=venue_data.get("neighborhood"),
    )

    if matching_venue is not None:
        return matching_venue

    new_venue = Venue(
        id=uuid.uuid4(),
        name=venue_data["name"],
        address_line_1=venue_data["address_line_1"],
        city=venue_data["city"],
        state=venue_data["state"],
        postal_code=venue_data["postal_code"],
        country_code=venue_data["country_code"],
        neighborhood=venue_data.get("neighborhood"),
        venue_status="approved",
        created_by_user_id=host_user_id,
        approved_by_user_id=host_user_id,
        approved_at=datetime.now(timezone.utc),
        is_active=True,
    )
    db.add(new_venue)
    db.flush()
    return new_venue


def get_or_create_first_free_entitlement(
    db: Session,
    *,
    host_user_id: uuid.UUID,
) -> HostPublishEntitlement:
    entitlement = db.scalars(
        select(HostPublishEntitlement)
        .where(
            HostPublishEntitlement.host_user_id == host_user_id,
            HostPublishEntitlement.entitlement_type == "first_free",
        )
        .with_for_update()
        .limit(1)
    ).first()
    if entitlement is not None:
        return entitlement

    entitlement = HostPublishEntitlement(
        id=uuid.uuid4(),
        host_user_id=host_user_id,
        entitlement_type="first_free",
        status="available",
        source="system",
    )
    db.add(entitlement)
    db.flush()
    return entitlement


def get_available_publish_entitlement(
    db: Session,
    *,
    host_user_id: uuid.UUID,
) -> HostPublishEntitlement | None:
    get_or_create_first_free_entitlement(db, host_user_id=host_user_id)
    return db.scalars(
        select(HostPublishEntitlement)
        .where(
            HostPublishEntitlement.host_user_id == host_user_id,
            HostPublishEntitlement.status == "available",
        )
        .order_by(
            case(
                (HostPublishEntitlement.entitlement_type == "first_free", 0),
                else_=1,
            ),
            HostPublishEntitlement.created_at.asc(),
            HostPublishEntitlement.id.asc(),
        )
        .with_for_update()
        .limit(1)
    ).first()


def get_entitlement_waiver_reason(entitlement: HostPublishEntitlement) -> str:
    if entitlement.entitlement_type == "first_free":
        return FIRST_FREE_WAIVER_REASON

    return ADMIN_COMP_WAIVER_REASON


def build_game_data(
    publish_data: CommunityGamePublishCreate,
    venue: Venue,
    host_user_id: uuid.UUID,
) -> dict[str, object]:
    return {
        "game_type": "community",
        "payment_collection_type": (
            "external_host" if publish_data.price_per_player_cents > 0 else "none"
        ),
        "publish_status": "published",
        "game_status": "active",
        "public_visibility_status": "visible",
        "join_enforcement_status": "open",
        "title": f"{venue.name} {publish_data.format_label}",
        "description": publish_data.game_notes,
        "venue_id": venue.id,
        "venue_name_snapshot": venue.name,
        "address_snapshot": build_address_snapshot(publish_data.venue.model_dump()),
        "city_snapshot": venue.city,
        "state_snapshot": venue.state,
        "neighborhood_snapshot": venue.neighborhood,
        "host_user_id": host_user_id,
        "created_by_user_id": host_user_id,
        "starts_at": publish_data.starts_at,
        "ends_at": publish_data.ends_at,
        "timezone": publish_data.timezone,
        "sport_type": "soccer",
        "format_label": publish_data.format_label,
        "game_player_group": publish_data.game_player_group,
        "skill_level": publish_data.skill_level,
        "environment_type": publish_data.environment_type,
        "total_spots": publish_data.total_spots,
        "price_per_player_cents": publish_data.price_per_player_cents,
        "currency": "USD",
        "minimum_age": 18,
        "allow_guests": True,
        "max_guests_per_booking": 2,
        "host_guest_max": get_default_host_guest_max(publish_data.format_label),
        "waitlist_enabled": True,
        "is_chat_enabled": True,
        "policy_mode": "custom_hosted",
        "custom_rules_text": publish_data.custom_rules_text,
        "custom_cancellation_text": None,
        "game_notes": publish_data.game_notes,
        "parking_notes": publish_data.parking_notes,
        "published_at": None,
        "cancelled_at": None,
        "cancelled_by_user_id": None,
        "cancellation_source": None,
        "cancel_reason": None,
        "completed_at": None,
        "completed_by_user_id": None,
    }


def build_game_validation_data(
    publish_data: CommunityGamePublishCreate,
    host_user_id: uuid.UUID,
) -> dict[str, object]:
    venue_payload = publish_data.venue.model_dump()
    return {
        "game_type": "community",
        "payment_collection_type": (
            "external_host" if publish_data.price_per_player_cents > 0 else "none"
        ),
        "publish_status": "published",
        "game_status": "active",
        "public_visibility_status": "visible",
        "join_enforcement_status": "open",
        "title": f"{venue_payload['name']} {publish_data.format_label}",
        "description": publish_data.game_notes,
        "venue_id": uuid.uuid4(),
        "venue_name_snapshot": venue_payload["name"],
        "address_snapshot": build_address_snapshot(venue_payload),
        "city_snapshot": venue_payload["city"],
        "state_snapshot": venue_payload["state"],
        "neighborhood_snapshot": venue_payload.get("neighborhood"),
        "host_user_id": host_user_id,
        "created_by_user_id": host_user_id,
        "starts_at": publish_data.starts_at,
        "ends_at": publish_data.ends_at,
        "timezone": publish_data.timezone,
        "sport_type": "soccer",
        "format_label": publish_data.format_label,
        "game_player_group": publish_data.game_player_group,
        "skill_level": publish_data.skill_level,
        "environment_type": publish_data.environment_type,
        "total_spots": publish_data.total_spots,
        "price_per_player_cents": publish_data.price_per_player_cents,
        "currency": "USD",
        "minimum_age": 18,
        "allow_guests": True,
        "max_guests_per_booking": 2,
        "host_guest_max": get_default_host_guest_max(publish_data.format_label),
        "waitlist_enabled": True,
        "is_chat_enabled": True,
        "policy_mode": "custom_hosted",
        "custom_rules_text": publish_data.custom_rules_text,
        "custom_cancellation_text": None,
        "game_notes": publish_data.game_notes,
        "parking_notes": publish_data.parking_notes,
        "published_at": None,
        "cancelled_at": None,
        "cancelled_by_user_id": None,
        "cancellation_source": None,
        "cancel_reason": None,
        "completed_at": None,
        "completed_by_user_id": None,
    }


def validate_community_publish_payload(
    publish_request: CommunityGamePublishCreate,
    host: User,
) -> dict[str, object]:
    if (
        publish_request.price_per_player_cents > 0
        and len(publish_request.payment_methods_snapshot) == 0
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add at least one host payment method.",
        )

    game_data = normalize_game_lifecycle_fields(
        build_game_validation_data(publish_request, host.id)
    )
    validate_game_business_rules(game_data)
    return game_data


def build_publish_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "ux_games_one_active_community_game_per_host_date" in error_text:
        return build_game_conflict_detail(exc)

    if "ux_host_publish_entitlements_one_first_free_per_host" in error_text:
        return "This host already has a first free publish entitlement."

    if "ux_community_publish_attempts_one_active_paid_per_host_date" in error_text:
        return (
            "You already have a community game publish payment in progress "
            "for this date."
        )

    if "uq_payments_idempotency_key" in error_text:
        return "A payment with this idempotency_key already exists."

    if "uq_community_publish_attempts_payment_id" in error_text:
        return "This publish payment is already attached to an attempt."

    if "uq_community_publish_attempts_created_game_id" in error_text:
        return "This created game is already attached to a publish attempt."

    return error_text


def create_published_community_game_records(
    db: Session,
    publish_request: CommunityGamePublishCreate,
    host: User,
    *,
    now: datetime,
    payment: Payment | None = None,
    entitlement: HostPublishEntitlement | None = None,
) -> tuple[Game, HostPublishFee]:
    venue_data = publish_request.venue.model_dump()
    venue = get_or_create_approved_venue(
        db,
        host_user_id=host.id,
        venue_data=venue_data,
    )
    game_data = normalize_game_lifecycle_fields(
        build_game_data(publish_request, venue, host.id)
    )
    validate_game_business_rules(game_data)

    game_id = uuid.uuid4()
    new_game = Game(id=game_id, **game_data)

    db.add(new_game)
    db.flush()

    db.add(
        GameParticipant(
            id=uuid.uuid4(),
            game_id=game_id,
            participant_type="host",
            user_id=host.id,
            display_name_snapshot=get_user_display_name(host, fallback="Host"),
            participant_status="confirmed",
            attendance_status="unknown",
            cancellation_type="none",
            price_cents=0,
            currency="USD",
            roster_order=1,
            confirmed_at=datetime.now(timezone.utc),
        )
    )

    db.add(
        CommunityGameDetail(
            id=uuid.uuid4(),
            game_id=game_id,
            payment_methods_snapshot=publish_request.payment_methods_snapshot,
            payment_instructions_snapshot=(
                publish_request.payment_instructions_snapshot
            ),
        )
    )

    if payment is not None:
        payment.game_id = game_id
        payment.updated_at = now
        db.add(payment)

    host_publish_fee = HostPublishFee(
        id=uuid.uuid4(),
        game_id=game_id,
        host_user_id=host.id,
        payment_id=payment.id if payment is not None else None,
        amount_cents=0 if payment is None else payment.amount_cents,
        currency="USD" if payment is None else payment.currency,
        fee_status="waived" if payment is None else "paid",
        waiver_reason=(
            get_entitlement_waiver_reason(entitlement)
            if payment is None and entitlement is not None
            else "none"
        ),
        paid_at=payment.paid_at if payment is not None else None,
    )
    db.add(host_publish_fee)
    db.flush()

    if entitlement is not None:
        entitlement.status = "used"
        entitlement.reserved_by_attempt_id = None
        entitlement.used_by_game_id = game_id
        entitlement.used_by_host_publish_fee_id = host_publish_fee.id
        entitlement.used_at = entitlement.used_at or now
        entitlement.updated_at = now
        db.add(entitlement)

    return new_game, host_publish_fee


def expire_abandoned_community_publish_attempts(
    db: Session,
    *,
    host_user_id: uuid.UUID,
    now: datetime,
) -> list[CommunityPublishAttempt]:
    attempts = list(
        db.scalars(
            select(CommunityPublishAttempt)
            .where(
                CommunityPublishAttempt.host_user_id == host_user_id,
                CommunityPublishAttempt.attempt_status.in_(
                    ABANDONED_PUBLISH_ATTEMPT_STATUSES
                ),
                CommunityPublishAttempt.expires_at.is_not(None),
                CommunityPublishAttempt.expires_at <= now,
            )
            .with_for_update()
        ).all()
    )
    if not attempts:
        return []

    attempt_ids = [attempt.id for attempt in attempts]
    payments = {
        payment.id: payment
        for payment in db.scalars(
            select(Payment)
            .where(
                Payment.id.in_(
                    [
                        attempt.payment_id
                        for attempt in attempts
                        if attempt.payment_id is not None
                    ]
                )
            )
            .with_for_update()
        ).all()
    }
    entitlements = list(
        db.scalars(
            select(HostPublishEntitlement)
            .where(HostPublishEntitlement.reserved_by_attempt_id.in_(attempt_ids))
            .with_for_update()
        ).all()
    )

    for attempt in attempts:
        attempt.attempt_status = "expired"
        attempt.failure_code = attempt.failure_code or "publish_attempt_expired"
        attempt.failure_message = (
            attempt.failure_message
            or "Community publish attempt expired before payment confirmation."
        )
        attempt.updated_at = now
        db.add(attempt)

        payment = payments.get(attempt.payment_id)
        if (
            payment is not None
            and payment.payment_status not in COLLECTED_PAYMENT_STATUSES
        ):
            payment.payment_status = "canceled"
            payment.failure_code = payment.failure_code or "publish_attempt_expired"
            payment.failure_message = (
                payment.failure_message
                or "Community publish attempt expired before payment confirmation."
            )
            payment.failure_reason = payment.failure_reason or "publish_attempt_expired"
            payment.updated_at = now
            db.add(payment)

    for entitlement in entitlements:
        if entitlement.status == "reserved":
            entitlement.status = "available"
            entitlement.reserved_by_attempt_id = None
            entitlement.updated_at = now
            db.add(entitlement)

    db.flush()
    return attempts


def map_paid_publish_confirmation_status(stripe_status: str) -> tuple[str, str, str]:
    internal_status = map_payment_intent_status(stripe_status)
    if internal_status == "succeeded":
        return "processing", "processing", "processing"

    if internal_status == "requires_action":
        return "requires_action", "requires_action", "requires_action"

    if internal_status == "processing":
        return "processing", "processing", "processing"

    if internal_status == "requires_payment_method":
        return "failed", "failed", "failed"

    if internal_status == "canceled":
        return "failed", "cancelled", "canceled"

    return "processing", "processing", "processing"


def build_publish_attempt_response(
    *,
    attempt: CommunityPublishAttempt,
    payment: Payment | None,
    game: Game | None = None,
    client_secret: str | None = None,
    stripe_status: str | None = None,
) -> CommunityGamePublishRead:
    if attempt.attempt_status == "succeeded":
        response_status = "published"
    elif attempt.attempt_status == "requires_action":
        response_status = "requires_action"
    elif attempt.attempt_status in {"failed", "cancelled", "expired"}:
        response_status = "failed"
    else:
        response_status = "processing"

    return CommunityGamePublishRead(
        status=response_status,
        game=game,
        attempt_id=attempt.id,
        payment_id=attempt.payment_id,
        attempt_status=attempt.attempt_status,
        payment_status=payment.payment_status if payment is not None else None,
        stripe_status=stripe_status or (
            payment.payment_status if payment is not None else None
        ),
        client_secret=client_secret,
        created_game_id=attempt.created_game_id,
        error_message=attempt.failure_message,
    )


def build_attempt_status_response(
    *,
    attempt: CommunityPublishAttempt,
    payment: Payment | None,
    game: Game | None = None,
) -> CommunityPublishAttemptStatusRead:
    publish_response = build_publish_attempt_response(
        attempt=attempt,
        payment=payment,
        game=game,
    )
    return CommunityPublishAttemptStatusRead(
        status=publish_response.status,
        attempt_id=attempt.id,
        payment_id=attempt.payment_id,
        attempt_status=attempt.attempt_status,
        payment_status=publish_response.payment_status,
        stripe_status=publish_response.stripe_status,
        client_secret=None,
        created_game_id=attempt.created_game_id,
        game=game,
        error_message=attempt.failure_message,
    )


def create_paid_publish_attempt(
    db: Session,
    *,
    publish_request: CommunityGamePublishCreate,
    host: User,
    starts_on_local,
    now: datetime,
) -> CommunityGamePublishRead:
    if publish_request.payment_method_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose a saved card before publishing.",
        )

    try:
        currency = get_stripe_currency()
    except StripeConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    expires_at = now + timedelta(
        minutes=COMMUNITY_PUBLISH_ATTEMPT_EXPIRATION_MINUTES
    )
    saved_payment_method = get_current_user_saved_payment_method_for_checkout(
        db,
        publish_request.payment_method_id,
        host,
        now=now,
    )
    if saved_payment_method is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose a saved card before publishing.",
        )

    attempt_id = uuid.uuid4()
    payment_id = uuid.uuid4()
    publish_payload = publish_request.model_dump(mode="json")
    attempt = CommunityPublishAttempt(
        id=attempt_id,
        host_user_id=host.id,
        payment_id=None,
        created_game_id=None,
        attempt_status="requires_payment_method",
        publish_payload=publish_payload,
        payment_method_id=saved_payment_method.id,
        starts_on_local=starts_on_local,
        amount_cents=COMMUNITY_PUBLISH_FEE_CENTS,
        currency=currency,
        failure_code=None,
        failure_message=None,
        expires_at=expires_at,
    )
    payment = Payment(
        id=payment_id,
        payer_user_id=host.id,
        game_id=None,
        booking_id=None,
        payment_type="community_publish_fee",
        provider="stripe",
        provider_payment_intent_id=None,
        provider_charge_id=None,
        idempotency_key=f"community-publish-fee:{attempt_id}:{payment_id}",
        amount_cents=COMMUNITY_PUBLISH_FEE_CENTS,
        currency=currency,
        payment_status="requires_payment_method",
        paid_at=None,
        failure_code=None,
        failure_message=None,
        failure_reason=None,
        payment_metadata={
            "source": "community_publish_fee",
            "host_user_id": str(host.id),
            "community_publish_attempt_id": str(attempt_id),
            "payment_id": str(payment_id),
            "amount_cents": COMMUNITY_PUBLISH_FEE_CENTS,
            "payment_method_id": str(saved_payment_method.id),
        },
    )

    try:
        db.add(attempt)
        db.add(payment)
        db.flush()
        attempt.payment_id = payment.id
        db.add(attempt)
        db.flush()

        payment_intent = create_payment_intent(
            amount_cents=payment.amount_cents,
            currency=payment.currency,
            idempotency_key=payment.idempotency_key,
            metadata={
                "source": "community_publish_fee",
                "host_user_id": str(host.id),
                "community_publish_attempt_id": str(attempt.id),
                "payment_id": str(payment.id),
                "amount_cents": str(payment.amount_cents),
            },
            customer_id=host.stripe_customer_id,
        )
        payment.provider_payment_intent_id = payment_intent.id
        payment.provider_charge_id = payment_intent.latest_charge_id
        payment.updated_at = now
        db.add(payment)
        db.commit()
        db.refresh(attempt)
        db.refresh(payment)
    except StripeConfigError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_publish_conflict_detail(exc),
        ) from exc
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe could not create this publish fee payment.",
        ) from exc

    confirm_client_secret = payment_intent.client_secret
    stripe_status = payment_intent.status
    try:
        confirmed_intent = confirm_payment_intent(
            payment.provider_payment_intent_id,
            payment_method_id=saved_payment_method.stripe_payment_method_id,
        )
        confirm_client_secret = confirmed_intent.client_secret
        stripe_status = confirmed_intent.status
    except StripeConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        locked_attempt = db.scalars(
            select(CommunityPublishAttempt)
            .where(CommunityPublishAttempt.id == attempt.id)
            .with_for_update()
        ).one()
        locked_payment = db.scalars(
            select(Payment)
            .where(Payment.id == payment.id)
            .with_for_update()
        ).one()
        if locked_attempt.attempt_status not in TERMINAL_PUBLISH_ATTEMPT_STATUSES:
            locked_attempt.attempt_status = "failed"
            locked_attempt.failure_code = "publish_fee_confirm_failed"
            locked_attempt.failure_message = (
                "Stripe could not confirm this saved payment method."
            )
            locked_attempt.updated_at = datetime.now(timezone.utc)
            locked_payment.payment_status = "failed"
            locked_payment.failure_code = "publish_fee_confirm_failed"
            locked_payment.failure_message = (
                "Stripe could not confirm this saved payment method."
            )
            locked_payment.failure_reason = "publish_fee_confirm_failed"
            locked_payment.updated_at = locked_attempt.updated_at
            db.add(locked_attempt)
            db.add(locked_payment)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe could not confirm this saved payment method.",
        ) from exc

    response_status, attempt_status, payment_status = (
        map_paid_publish_confirmation_status(stripe_status)
    )
    locked_attempt = db.scalars(
        select(CommunityPublishAttempt)
        .where(CommunityPublishAttempt.id == attempt.id)
        .with_for_update()
    ).one()
    locked_payment = db.scalars(
        select(Payment).where(Payment.id == payment.id).with_for_update()
    ).one()
    if locked_attempt.attempt_status != "succeeded":
        locked_attempt.attempt_status = attempt_status
        if attempt_status == "failed":
            failure_code = "publish_fee_payment_failed"
            failure_message = (
                "This saved card could not be charged. Choose another card."
            )
        elif attempt_status == "cancelled":
            failure_code = "publish_fee_payment_canceled"
            failure_message = "This publish fee payment was canceled."
        else:
            failure_code = None
            failure_message = None

        locked_attempt.failure_code = failure_code
        locked_attempt.failure_message = failure_message
        locked_attempt.updated_at = datetime.now(timezone.utc)
        locked_payment.payment_status = payment_status
        locked_payment.provider_charge_id = confirmed_intent.latest_charge_id
        locked_payment.failure_code = failure_code
        locked_payment.failure_message = failure_message
        locked_payment.failure_reason = failure_code
        locked_payment.updated_at = locked_attempt.updated_at
        db.add(locked_attempt)
        db.add(locked_payment)
    db.commit()

    db.refresh(attempt)
    db.refresh(payment)
    if response_status == "failed":
        return build_publish_attempt_response(
            attempt=attempt,
            payment=payment,
            client_secret=None,
            stripe_status=stripe_status,
        )

    return build_publish_attempt_response(
        attempt=attempt,
        payment=payment,
        client_secret=confirm_client_secret,
        stripe_status=stripe_status,
    )


def finalize_community_publish_attempt_success(
    db: Session,
    *,
    payment: Payment,
    provider_charge_id: str | None,
    now: datetime,
) -> Game | None:
    attempt = db.scalars(
        select(CommunityPublishAttempt)
        .where(CommunityPublishAttempt.payment_id == payment.id)
        .with_for_update()
        .limit(1)
    ).first()
    if attempt is None:
        raise ValueError("Publish attempt for this payment was not found.")

    if attempt.created_game_id is not None:
        payment_changed = False
        if payment.payment_status != "succeeded":
            payment.payment_status = "succeeded"
            payment.paid_at = payment.paid_at or now
            payment.failure_code = None
            payment.failure_message = None
            payment.failure_reason = None
            payment_changed = True
        if provider_charge_id is not None and payment.provider_charge_id is None:
            payment.provider_charge_id = provider_charge_id
            payment_changed = True
        if payment_changed:
            payment.updated_at = now
            db.add(payment)
        return db.get(Game, attempt.created_game_id)

    if attempt.attempt_status in {"failed", "cancelled", "expired"}:
        raise ValueError("Publish attempt is no longer active.")

    if payment.payment_type != "community_publish_fee":
        raise ValueError("Payment is not a community publish fee.")

    if payment.payer_user_id != attempt.host_user_id:
        raise ValueError("Publish attempt host does not match payment payer.")

    host = db.scalars(
        select(User).where(User.id == attempt.host_user_id).with_for_update()
    ).first()
    if host is None or host.deleted_at is not None:
        raise ValueError("Publish attempt host was not found.")

    publish_request = CommunityGamePublishCreate.model_validate(attempt.publish_payload)
    validate_community_publish_payload(publish_request, host)

    payment.payment_status = "succeeded"
    payment.provider_charge_id = provider_charge_id
    payment.paid_at = payment.paid_at or now
    payment.failure_code = None
    payment.failure_message = None
    payment.failure_reason = None
    payment.updated_at = now
    db.add(payment)

    game, _host_publish_fee = create_published_community_game_records(
        db,
        publish_request,
        host,
        now=now,
        payment=payment,
        entitlement=None,
    )
    attempt.attempt_status = "succeeded"
    attempt.created_game_id = game.id
    attempt.failure_code = None
    attempt.failure_message = None
    attempt.updated_at = now
    db.add(attempt)
    db.flush()
    return game


def mark_community_publish_attempt_processing(
    db: Session,
    *,
    payment: Payment,
    provider_charge_id: str | None,
    now: datetime,
) -> None:
    attempt = db.scalars(
        select(CommunityPublishAttempt)
        .where(CommunityPublishAttempt.payment_id == payment.id)
        .with_for_update()
        .limit(1)
    ).first()
    if attempt is None:
        raise ValueError("Publish attempt for this payment was not found.")

    if attempt.attempt_status == "succeeded":
        return

    if attempt.attempt_status in TERMINAL_PUBLISH_ATTEMPT_STATUSES:
        raise ValueError("Publish attempt is no longer active.")

    attempt.attempt_status = "processing"
    attempt.updated_at = now
    db.add(attempt)

    if payment.payment_status not in COLLECTED_PAYMENT_STATUSES:
        payment.payment_status = "processing"
        payment.provider_charge_id = provider_charge_id
        payment.updated_at = now
        db.add(payment)


def mark_community_publish_attempt_failed_or_canceled(
    db: Session,
    *,
    payment: Payment,
    provider_charge_id: str | None,
    now: datetime,
    payment_status: str,
    attempt_status: str,
    failure_code: str,
    failure_message: str,
) -> None:
    attempt = db.scalars(
        select(CommunityPublishAttempt)
        .where(CommunityPublishAttempt.payment_id == payment.id)
        .with_for_update()
        .limit(1)
    ).first()
    if attempt is None:
        raise ValueError("Publish attempt for this payment was not found.")

    if attempt.attempt_status in TERMINAL_PUBLISH_ATTEMPT_STATUSES:
        return

    attempt.attempt_status = attempt_status
    attempt.failure_code = failure_code
    attempt.failure_message = failure_message
    attempt.updated_at = now
    db.add(attempt)

    if payment.payment_status not in COLLECTED_PAYMENT_STATUSES:
        payment.payment_status = payment_status
        payment.provider_charge_id = provider_charge_id
        payment.failure_code = failure_code
        payment.failure_message = failure_message
        payment.failure_reason = failure_code
        payment.updated_at = now
        db.add(payment)


def publish_community_game_workflow(
    db: Session,
    publish_request: CommunityGamePublishCreate,
    current_user: User,
) -> CommunityGamePublishRead:
    now = datetime.now(timezone.utc)
    host = get_verified_community_host_or_404(db, current_user.id)
    validated_game_data = validate_community_publish_payload(publish_request, host)
    starts_on_local = validated_game_data["starts_on_local"]
    expire_abandoned_community_publish_attempts(
        db,
        host_user_id=host.id,
        now=now,
    )
    entitlement = get_available_publish_entitlement(db, host_user_id=host.id)

    if entitlement is None:
        return create_paid_publish_attempt(
            db,
            publish_request=publish_request,
            host=host,
            starts_on_local=starts_on_local,
            now=now,
        )

    try:
        game, _host_publish_fee = create_published_community_game_records(
            db,
            publish_request,
            host,
            now=now,
            entitlement=entitlement,
        )
        db.commit()
        db.refresh(game)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_publish_conflict_detail(exc),
        ) from exc

    surface_community_game_text(db, game_id=game.id)
    return CommunityGamePublishRead(status="published", game=game)


def get_community_publish_attempt_status_workflow(
    db: Session,
    attempt_id: uuid.UUID,
    current_user: User,
) -> CommunityPublishAttemptStatusRead:
    attempt = db.scalars(
        select(CommunityPublishAttempt)
        .where(CommunityPublishAttempt.id == attempt_id)
        .limit(1)
    ).first()
    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publish attempt not found.",
        )

    if attempt.host_user_id != current_user.id and not user_is_active_admin(
        current_user
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot view this publish attempt.",
        )

    now = datetime.now(timezone.utc)
    expire_abandoned_community_publish_attempts(
        db,
        host_user_id=attempt.host_user_id,
        now=now,
    )
    db.commit()
    db.refresh(attempt)

    payment = db.get(Payment, attempt.payment_id) if attempt.payment_id else None
    game = db.get(Game, attempt.created_game_id) if attempt.created_game_id else None
    return build_attempt_status_response(attempt=attempt, payment=payment, game=game)
