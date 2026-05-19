import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    CommunityGameDetail,
    Game,
    GameParticipant,
    HostPublishFee,
    Payment,
    User,
    Venue,
)
from backend.routes.game_routes import (
    build_game_conflict_detail,
    get_default_host_guest_max,
    normalize_game_lifecycle_fields,
    validate_game_business_rules,
)
from backend.routes.venue_routes import find_matching_active_venue
from backend.schemas import CommunityGamePublishCreate, CommunityGamePublishRead

router = APIRouter(prefix="/community-games", tags=["community_games"])

COMMUNITY_PUBLISH_FEE_CENTS = 499
FIRST_FREE_WAIVER_REASON = "first_game_free"


def get_active_host_or_404(db: Session, user_id: uuid.UUID) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host user not found.",
        )

    if db_user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verify your email before publishing.",
        )

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


def host_has_used_first_free_publish(db: Session, host_user_id: uuid.UUID) -> bool:
    statement = (
        select(HostPublishFee.id)
        .where(
            HostPublishFee.host_user_id == host_user_id,
            HostPublishFee.waiver_reason == FIRST_FREE_WAIVER_REASON,
        )
        .limit(1)
    )
    return db.scalar(statement) is not None


def build_game_data(
    publish_data: CommunityGamePublishCreate,
    venue: Venue,
) -> dict[str, object]:
    return {
        "game_type": "community",
        "payment_collection_type": (
            "external_host"
            if publish_data.price_per_player_cents > 0
            else "none"
        ),
        "publish_status": "published",
        "game_status": "scheduled",
        "title": f"{venue.name} {publish_data.format_label}",
        "description": publish_data.game_notes,
        "venue_id": venue.id,
        "venue_name_snapshot": venue.name,
        "address_snapshot": build_address_snapshot(publish_data.venue.model_dump()),
        "city_snapshot": venue.city,
        "state_snapshot": venue.state,
        "neighborhood_snapshot": venue.neighborhood,
        "host_user_id": publish_data.host_user_id,
        "created_by_user_id": publish_data.host_user_id,
        "starts_at": publish_data.starts_at,
        "ends_at": publish_data.ends_at,
        "timezone": publish_data.timezone,
        "sport_type": "soccer",
        "format_label": publish_data.format_label,
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
        "custom_rules_text": None,
        "custom_cancellation_text": None,
        "game_notes": publish_data.game_notes,
        "parking_notes": publish_data.parking_notes,
        "published_at": None,
        "cancelled_at": None,
        "cancelled_by_user_id": None,
        "cancel_reason": None,
        "completed_at": None,
        "completed_by_user_id": None,
    }


def build_host_display_name(host: User) -> str:
    full_name = f"{host.first_name or ''} {host.last_name or ''}".strip()
    return full_name or host.email or "Host"


def build_publish_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "ux_games_one_active_community_game_per_host_date" in error_text:
        return build_game_conflict_detail(exc)

    if "ux_host_publish_fees_one_first_free_per_host" in error_text:
        return "This host has already used their first free game."

    if "uq_payments_idempotency_key" in error_text:
        return "A payment with this idempotency_key already exists."

    return error_text


@router.post(
    "/publish",
    response_model=CommunityGamePublishRead,
    status_code=status.HTTP_201_CREATED,
)
def publish_community_game(
    publish_request: CommunityGamePublishCreate,
    db: Session = Depends(get_db),
) -> CommunityGamePublishRead:
    host = get_active_host_or_404(db, publish_request.host_user_id)

    if (
        publish_request.price_per_player_cents > 0
        and len(publish_request.payment_methods_snapshot) == 0
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add at least one host payment method.",
        )

    venue_data = publish_request.venue.model_dump()
    venue = get_or_create_approved_venue(
        db,
        host_user_id=publish_request.host_user_id,
        venue_data=venue_data,
    )
    game_data = normalize_game_lifecycle_fields(build_game_data(publish_request, venue))
    validate_game_business_rules(game_data)

    game_id = uuid.uuid4()
    new_game = Game(id=game_id, **game_data)

    try:
        db.add(new_game)
        db.flush()

        db.add(
            GameParticipant(
                id=uuid.uuid4(),
                game_id=game_id,
                participant_type="host",
                user_id=publish_request.host_user_id,
                display_name_snapshot=build_host_display_name(host),
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

        first_publish_is_free = not host_has_used_first_free_publish(
            db,
            publish_request.host_user_id,
        )
        payment = None
        if not first_publish_is_free:
            payment = Payment(
                id=uuid.uuid4(),
                payer_user_id=publish_request.host_user_id,
                game_id=game_id,
                payment_type="community_publish_fee",
                provider="stripe",
                provider_payment_intent_id=f"pi_demo_community_publish_fee_{game_id}",
                provider_charge_id=f"ch_demo_community_publish_fee_{game_id}",
                idempotency_key=(
                    f"community-publish-fee:{game_id}:{publish_request.host_user_id}"
                ),
                amount_cents=COMMUNITY_PUBLISH_FEE_CENTS,
                currency="USD",
                payment_status="succeeded",
                paid_at=datetime.now(timezone.utc),
                payment_metadata={
                    "source": "community_game_publish",
                    "payment_method_id": (
                        str(publish_request.payment_method_id)
                        if publish_request.payment_method_id
                        else None
                    ),
                },
            )
            db.add(payment)

        db.add(
            HostPublishFee(
                id=uuid.uuid4(),
                game_id=game_id,
                host_user_id=publish_request.host_user_id,
                payment_id=payment.id if payment is not None else None,
                amount_cents=(
                    0 if first_publish_is_free else COMMUNITY_PUBLISH_FEE_CENTS
                ),
                currency="USD",
                fee_status="waived" if first_publish_is_free else "paid",
                waiver_reason=(
                    FIRST_FREE_WAIVER_REASON if first_publish_is_free else "none"
                ),
                paid_at=payment.paid_at if payment is not None else None,
            )
        )
        db.commit()
        db.refresh(new_game)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_publish_conflict_detail(exc),
        ) from exc

    return CommunityGamePublishRead(game=new_game)
