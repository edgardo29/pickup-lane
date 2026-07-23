"""Roster workflow orchestration for game join, leave, and guest changes."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import Booking, Game, GameParticipant, Payment, User
from backend.schemas.game_schema import (
    GameGuestAddCreate,
    GameGuestAddRead,
    GameGuestRemoveCreate,
    GameGuestRemoveRead,
    GameJoinCreate,
    GameJoinRead,
    GameLeaveRead,
)
from backend.services.game_rules import (
    ACTIVE_JOIN_STATUSES,
    HOST_EDITABLE_GAME_STATUSES,
    JOINABLE_GAME_STATUSES,
    REFUND_CUTOFF_HOURS,
    build_game_conflict_detail,
    ensure_timezone,
    game_requires_app_player_payment,
    require_join_ready_user,
    require_community_game_joining_open,
    require_minimum_age,
    require_roster_window_open,
    validate_guest_count,
)
from backend.services.game_service import (
    build_booking_participants,
    count_roster_players,
    get_booking_participants,
    get_existing_active_participant,
    get_existing_active_waitlist_entry,
    get_next_roster_order,
    sync_game_capacity_status,
)
from backend.services.user_service import get_user_display_name
from backend.services.game_waitlist_service import (
    build_waitlist_entry_for_join,
    promote_waitlist_entries,
)


def build_booking(
    db_game: Game,
    joining_user_id: uuid.UUID,
    party_size: int,
    now: datetime,
    *,
    is_confirmed: bool,
) -> Booking:
    subtotal_cents = db_game.price_per_player_cents * party_size
    requires_app_payment = game_requires_app_player_payment(db_game)

    if is_confirmed:
        booking_status = "confirmed"
        payment_status = "paid" if requires_app_payment else "not_required"
    else:
        booking_status = "waitlisted"
        payment_status = "unpaid" if requires_app_payment else "not_required"

    return Booking(
        id=uuid.uuid4(),
        game_id=db_game.id,
        buyer_user_id=joining_user_id,
        booking_status=booking_status,
        payment_status=payment_status,
        participant_count=party_size,
        subtotal_cents=subtotal_cents,
        platform_fee_cents=0,
        discount_cents=0,
        total_cents=subtotal_cents,
        currency=db_game.currency,
        price_per_player_snapshot_cents=db_game.price_per_player_cents,
        platform_fee_snapshot_cents=0,
        booked_at=now if is_confirmed else None,
    )


def create_booking_payment(
    db_game: Game,
    booking: Booking,
    payer_user_id: uuid.UUID,
    now: datetime,
    *,
    source: str,
) -> Payment:
    return Payment(
        id=uuid.uuid4(),
        payer_user_id=payer_user_id,
        booking_id=booking.id,
        game_id=None,
        payment_type="booking",
        provider="stripe",
        provider_payment_intent_id=f"pi_demo_booking_{booking.id}",
        provider_charge_id=f"ch_demo_booking_{booking.id}",
        idempotency_key=f"booking:{booking.id}:succeeded",
        amount_cents=booking.total_cents,
        currency=booking.currency,
        payment_status="succeeded",
        paid_at=now,
        payment_metadata={
            "source": source,
            "game_id": str(db_game.id),
            "demo": True,
        },
    )


def create_booking_guest_add_payment(
    db_game: Game,
    booking: Booking,
    payer_user_id: uuid.UUID,
    added_count: int,
    now: datetime,
) -> Payment:
    payment_id = uuid.uuid4()
    return Payment(
        id=payment_id,
        payer_user_id=payer_user_id,
        booking_id=booking.id,
        game_id=None,
        payment_type="booking",
        provider="stripe",
        provider_payment_intent_id=f"pi_demo_booking_add_guests_{payment_id}",
        provider_charge_id=f"ch_demo_booking_add_guests_{payment_id}",
        idempotency_key=f"booking:{booking.id}:add_guests:{payment_id}:succeeded",
        amount_cents=db_game.price_per_player_cents * added_count,
        currency=booking.currency,
        payment_status="succeeded",
        paid_at=now,
        payment_metadata={
            "source": "booking_guest_add_demo",
            "game_id": str(db_game.id),
            "added_guest_count": added_count,
            "demo": True,
        },
    )


def build_added_booking_guest_participants(
    db_game: Game,
    booking: Booking,
    joining_user_id: uuid.UUID,
    display_name: str,
    guest_count: int,
    current_guest_count: int,
    now: datetime,
    first_roster_order: int,
) -> list[GameParticipant]:
    guests = []
    for index in range(guest_count):
        guest_number = current_guest_count + index + 1
        guests.append(
            GameParticipant(
                id=uuid.uuid4(),
                game_id=db_game.id,
                booking_id=booking.id,
                participant_type="guest",
                user_id=None,
                guest_of_user_id=joining_user_id,
                guest_name=f"Guest {guest_number}",
                display_name_snapshot=f"{display_name} guest {guest_number}",
                participant_status="confirmed",
                attendance_status="unknown",
                cancellation_type="none",
                price_cents=db_game.price_per_player_cents,
                currency=db_game.currency,
                roster_order=first_roster_order + index,
                joined_at=now,
                confirmed_at=now,
            )
        )

    return guests


def build_host_guest_participants(
    db_game: Game,
    host_user_id: uuid.UUID,
    display_name: str,
    guest_count: int,
    now: datetime,
    first_roster_order: int,
) -> list[GameParticipant]:
    return [
        GameParticipant(
            id=uuid.uuid4(),
            game_id=db_game.id,
            booking_id=None,
            participant_type="guest",
            user_id=None,
            guest_of_user_id=host_user_id,
            guest_name=f"Guest {index + 1}",
            display_name_snapshot=f"{display_name} guest {index + 1}",
            participant_status="confirmed",
            attendance_status="unknown",
            cancellation_type="none",
            price_cents=0,
            currency=db_game.currency,
            roster_order=first_roster_order + index,
            joined_at=now,
            confirmed_at=now,
        )
        for index in range(guest_count)
    ]


def is_refund_eligible(starts_at: datetime, now: datetime) -> bool:
    seconds_until_start = (ensure_timezone(starts_at) - now).total_seconds()
    return seconds_until_start >= REFUND_CUTOFF_HOURS * 60 * 60


def join_game_roster_workflow(
    db: Session,
    game_id: uuid.UUID,
    join_request: GameJoinCreate,
    joining_user: User,
) -> GameJoinRead:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    require_join_ready_user(joining_user)
    require_minimum_age(joining_user, db_game.minimum_age)

    if db_game.host_user_id == joining_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hosts are already part of their own game.",
        )

    if db_game.publish_status != "published" or db_game.game_status not in JOINABLE_GAME_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This game is not open for joining.",
        )
    require_community_game_joining_open(db_game)

    now = datetime.now(timezone.utc)
    require_roster_window_open(db_game, now, "Joining is closed for this game.")

    existing_participant = get_existing_active_participant(
        db, db_game.id, joining_user.id
    )
    if existing_participant is not None:
        if existing_participant.participant_status == "waitlisted":
            detail = "You are already on the waitlist for this game."
        else:
            detail = "You already joined this game."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    if get_existing_active_waitlist_entry(db, db_game.id, joining_user.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already on the waitlist for this game.",
        )

    roster_count = count_roster_players(db, db_game.id)
    display_name = get_user_display_name(joining_user)
    guest_count = validate_guest_count(db_game, join_request.guest_count)
    party_size = guest_count + 1
    spots_left = max(db_game.total_spots - roster_count, 0)

    if party_size <= spots_left:
        booking = build_booking(
            db_game,
            joining_user.id,
            party_size,
            now,
            is_confirmed=True,
        )
        participants = build_booking_participants(
            db_game,
            booking,
            joining_user,
            display_name,
            guest_count,
            now,
            participant_status="confirmed",
            first_roster_order=get_next_roster_order(db, db_game.id),
        )

        try:
            db.add(booking)
            if game_requires_app_player_payment(db_game):
                db.add(
                    create_booking_payment(
                        db_game, booking, joining_user.id, now, source="checkout_demo"
                    )
                )
            db.add_all(participants)
            db.add(db_game)
            db.commit()
            db.refresh(participants[0])
            db.refresh(booking)
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=build_game_conflict_detail(exc),
            ) from exc

        return GameJoinRead(
            status="joined",
            message="You joined this game.",
            participant_id=participants[0].id,
            booking_id=booking.id,
        )

    if not db_game.waitlist_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough spots are available for this join.",
        )

    booking = build_booking(
        db_game,
        joining_user.id,
        party_size,
        now,
        is_confirmed=False,
    )
    waitlist_entry = build_waitlist_entry_for_join(
        db,
        db_game,
        booking,
        joining_user,
        join_request,
        now,
    )
    participants = build_booking_participants(
        db_game,
        booking,
        joining_user,
        display_name,
        guest_count,
        now,
        participant_status="waitlisted",
        first_roster_order=None,
    )
    try:
        db.add(booking)
        db.add(waitlist_entry)
        db.add_all(participants)
        db.add(db_game)
        db.commit()
        db.refresh(participants[0])
        db.refresh(booking)
        db.refresh(waitlist_entry)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    return GameJoinRead(
        status="waitlisted",
        message="You joined the waitlist.",
        participant_id=participants[0].id,
        booking_id=booking.id,
        waitlist_entry_id=waitlist_entry.id,
    )


def leave_game_roster_workflow(
    db: Session,
    game_id: uuid.UUID,
    leaving_user: User,
) -> GameLeaveRead:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    if db_game.host_user_id == leaving_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hosts cannot leave their own game from the player flow.",
        )

    participant = get_existing_active_participant(db, db_game.id, leaving_user.id)
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not currently joined to this game.",
        )

    now = datetime.now(timezone.utc)
    require_roster_window_open(db_game, now, "Attendance changes are closed for this game.")
    refundable = is_refund_eligible(db_game.starts_at, now)
    app_payment_required = game_requires_app_player_payment(db_game)
    app_refund_eligible = refundable and app_payment_required
    was_waitlisted = participant.participant_status == "waitlisted"

    waitlist_entry = get_existing_active_waitlist_entry(db, db_game.id, leaving_user.id)
    if waitlist_entry is not None:
        waitlist_entry.waitlist_status = "cancelled"
        waitlist_entry.cancelled_at = now
        waitlist_entry.updated_at = now
        db.add(waitlist_entry)

    booking = db.get(Booking, participant.booking_id) if participant.booking_id else None
    participants_to_cancel = [participant]
    if booking is not None:
        participants_to_cancel = list(
            db.scalars(
                select(GameParticipant).where(
                    GameParticipant.game_id == db_game.id,
                    GameParticipant.booking_id == booking.id,
                    GameParticipant.participant_status.in_(ACTIVE_JOIN_STATUSES),
                )
            ).all()
        )

    for booking_participant in participants_to_cancel:
        booking_participant.cancelled_at = now
        booking_participant.updated_at = now
        booking_participant.cancellation_type = (
            "on_time" if refundable or was_waitlisted else "late"
        )
        booking_participant.participant_status = (
            "cancelled" if refundable or was_waitlisted else "late_cancelled"
        )
        booking_participant.attendance_status = "not_applicable"
        db.add(booking_participant)

    if booking is not None:
        booking.booking_status = "cancelled"
        booking.payment_status = (
            "refunded"
            if app_refund_eligible and not was_waitlisted
            else booking.payment_status
        )
        booking.cancelled_at = now
        booking.cancelled_by_user_id = leaving_user.id
        if was_waitlisted:
            booking.cancel_reason = "waitlist_cancelled"
        else:
            booking.cancel_reason = (
                "player_cancelled_on_time" if refundable else "player_cancelled_late"
            )
        booking.updated_at = now
        db.add(booking)

    db_game.updated_at = now
    if not was_waitlisted:
        db.flush()
        promote_waitlist_entries(db, db_game, now)

    try:
        db.add(db_game)
        db.commit()
        db.refresh(participant)
        if booking is not None:
            db.refresh(booking)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    if was_waitlisted:
        message = "You left the waitlist."
    elif app_refund_eligible:
        message = "You left the game. Your payment is marked for refund."
    elif app_payment_required:
        message = "You left the game. This is within 24 hours, so no refund is due."
    else:
        message = "You left the game."

    return GameLeaveRead(
        status="left_waitlist" if was_waitlisted else "left_game",
        message=message,
        refund_eligible=app_refund_eligible and not was_waitlisted,
        participant_id=participant.id,
        booking_id=booking.id if booking is not None else None,
    )


def add_booking_game_guests_workflow(
    db: Session,
    game_id: uuid.UUID,
    guest_request: GameGuestAddCreate,
    acting_user: User,
) -> GameGuestAddRead:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    if db_game.publish_status != "published" or db_game.game_status not in JOINABLE_GAME_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only published active games can add guests.",
        )
    require_community_game_joining_open(db_game)

    now = datetime.now(timezone.utc)
    require_roster_window_open(db_game, now, "Attendance changes are closed for this game.")

    if guest_request.guest_count <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="guest_count must be greater than 0.",
        )

    participant = get_existing_active_participant(db, db_game.id, acting_user.id)
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not currently joined to this game.",
        )

    if (
        participant.participant_status != "confirmed"
        or participant.participant_type != "registered_user"
        or participant.booking_id is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only confirmed players can add guests.",
        )

    booking = db.get(Booking, participant.booking_id)
    if booking is None or booking.booking_status not in {"confirmed", "partially_cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your booking is not eligible for guest changes.",
        )

    booking_participants = get_booking_participants(
        db, db_game.id, booking.id, ACTIVE_JOIN_STATUSES
    )
    current_guest_count = sum(
        booking_participant.participant_type == "guest"
        for booking_participant in booking_participants
    )
    max_guests = db_game.max_guests_per_booking if db_game.allow_guests else 0
    if current_guest_count + guest_request.guest_count > max_guests:
        detail = (
            "This game does not allow guests."
            if max_guests == 0
            else f"This game allows up to {max_guests} guests."
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    roster_count = count_roster_players(db, db_game.id)
    if guest_request.guest_count > max(db_game.total_spots - roster_count, 0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough spots are available for guests.",
        )

    added_guests = build_added_booking_guest_participants(
        db_game,
        booking,
        acting_user.id,
        get_user_display_name(acting_user),
        guest_request.guest_count,
        current_guest_count,
        now,
        get_next_roster_order(db, db_game.id),
    )
    booking.participant_count += len(added_guests)
    booking.subtotal_cents = db_game.price_per_player_cents * booking.participant_count
    booking.total_cents = booking.subtotal_cents + booking.platform_fee_cents - booking.discount_cents
    booking.booking_status = "confirmed"
    booking.payment_status = (
        "paid" if game_requires_app_player_payment(db_game) else "not_required"
    )
    booking.updated_at = now
    db_game.updated_at = now

    db.add_all(added_guests)
    db.add(booking)
    if game_requires_app_player_payment(db_game):
        db.add(
            create_booking_guest_add_payment(
                db_game,
                booking,
                acting_user.id,
                len(added_guests),
                now,
            )
        )
    db.flush()
    sync_game_capacity_status(db, db_game)

    try:
        db.add(db_game)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    return GameGuestAddRead(
        status="guests_added",
        message="Guests added to your booking.",
        added_count=len(added_guests),
        booking_id=booking.id,
    )


def add_host_game_guests_workflow(
    db: Session,
    game_id: uuid.UUID,
    guest_request: GameGuestAddCreate,
    acting_user: User,
) -> GameGuestAddRead:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    if db_game.host_user_id != acting_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the game host can add host guests.",
        )

    if (
        db_game.publish_status != "published"
        or db_game.game_status not in HOST_EDITABLE_GAME_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only published active games can be updated.",
        )
    require_community_game_joining_open(db_game)

    now = datetime.now(timezone.utc)
    require_roster_window_open(db_game, now, "Attendance changes are closed for this game.")

    if guest_request.guest_count < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="guest_count must be greater than or equal to 0.",
        )

    guest_count = guest_request.guest_count
    if guest_count <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="guest_count must be greater than 0.",
        )

    current_host_guest_count = db.scalar(
        select(func.count())
        .select_from(GameParticipant)
        .where(
            GameParticipant.game_id == db_game.id,
            GameParticipant.guest_of_user_id == acting_user.id,
            GameParticipant.participant_type == "guest",
            GameParticipant.participant_status.in_(ACTIVE_JOIN_STATUSES),
        )
    ) or 0
    max_guests = db_game.host_guest_max if db_game.allow_guests else 0
    if current_host_guest_count + guest_count > max_guests:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This game allows up to {max_guests} host guests.",
        )

    roster_count = count_roster_players(db, db_game.id)
    if guest_count > max(db_game.total_spots - roster_count, 0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough spots are available for host guests.",
        )

    guests = build_host_guest_participants(
        db_game,
        acting_user.id,
        get_user_display_name(acting_user),
        guest_count,
        now,
        get_next_roster_order(db, db_game.id),
    )
    db.add_all(guests)
    db.flush()
    sync_game_capacity_status(db, db_game)
    db_game.updated_at = now

    try:
        db.add(db_game)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    return GameGuestAddRead(
        status="guests_added",
        message="Host guests added.",
        added_count=len(guests),
    )


def remove_game_guests_workflow(
    db: Session,
    game_id: uuid.UUID,
    guest_request: GameGuestRemoveCreate,
    acting_user: User,
) -> GameGuestRemoveRead:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    if guest_request.remove_count <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="remove_count must be greater than 0.",
        )

    if db_game.publish_status != "published" or db_game.game_status not in JOINABLE_GAME_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only published active games can update guests.",
        )
    require_community_game_joining_open(db_game)

    participant = get_existing_active_participant(db, db_game.id, acting_user.id)
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not currently joined to this game.",
        )

    now = datetime.now(timezone.utc)
    require_roster_window_open(db_game, now, "Attendance changes are closed for this game.")
    refundable = is_refund_eligible(db_game.starts_at, now)
    app_payment_required = game_requires_app_player_payment(db_game)
    was_waitlisted = participant.participant_status == "waitlisted"
    booking = db.get(Booking, participant.booking_id) if participant.booking_id else None

    if booking is not None:
        booking_participants = get_booking_participants(
            db, db_game.id, booking.id, ACTIVE_JOIN_STATUSES
        )
        guests = [
            booking_participant
            for booking_participant in booking_participants
            if booking_participant.participant_type == "guest"
        ]
    else:
        guests = list(
            db.scalars(
                select(GameParticipant)
                .where(
                    GameParticipant.game_id == db_game.id,
                    GameParticipant.guest_of_user_id == acting_user.id,
                    GameParticipant.participant_type == "guest",
                    GameParticipant.participant_status.in_(ACTIVE_JOIN_STATUSES),
                )
                .order_by(
                    GameParticipant.roster_order.desc().nulls_last(),
                    GameParticipant.joined_at.desc(),
                )
            ).all()
        )
        booking_participants = [participant, *guests]

    if len(guests) < guest_request.remove_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You do not have that many guests to remove.",
        )

    guests_to_remove = guests[: guest_request.remove_count]
    removed_guest_ids = {guest.id for guest in guests_to_remove}

    for guest in guests_to_remove:
        guest.cancelled_at = now
        guest.updated_at = now
        guest.cancellation_type = "on_time" if refundable or was_waitlisted else "late"
        guest.participant_status = "cancelled" if refundable or was_waitlisted else "late_cancelled"
        guest.attendance_status = "not_applicable"
        db.add(guest)

    if booking is not None:
        remaining_participants = [
            booking_participant
            for booking_participant in booking_participants
            if booking_participant.id not in removed_guest_ids
        ]
        booking.participant_count = len(remaining_participants)
        booking.subtotal_cents = db_game.price_per_player_cents * len(remaining_participants)
        booking.total_cents = booking.subtotal_cents + booking.platform_fee_cents - booking.discount_cents
        if was_waitlisted:
            booking.booking_status = "waitlisted"
            booking.payment_status = (
                "unpaid" if app_payment_required else "not_required"
            )
        else:
            booking.booking_status = "partially_cancelled"
            if refundable and app_payment_required:
                booking.payment_status = "partially_refunded"
        booking.updated_at = now
        db.add(booking)

        waitlist_entry = get_existing_active_waitlist_entry(db, db_game.id, acting_user.id)
        if waitlist_entry is not None:
            waitlist_entry.party_size = booking.participant_count
            waitlist_entry.updated_at = now
            db.add(waitlist_entry)

    db_game.updated_at = now
    db.flush()
    promote_waitlist_entries(db, db_game, now)

    try:
        db.add(db_game)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    return GameGuestRemoveRead(
        status="guests_removed",
        message="Guest attendance updated.",
        removed_count=len(guests_to_remove),
        booking_id=booking.id if booking is not None else None,
    )
