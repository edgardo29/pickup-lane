import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    Game,
    GameCredit,
    GameCreditUsage,
    GameParticipant,
    Payment,
    Refund,
    WaitlistEntry,
)
from backend.schemas.admin_official_game_schema import AdminOfficialGameMoneyRead
from backend.services.official_game_service import get_official_game_or_404


def list_official_games(
    db: Session,
    *,
    game_status: str | None = None,
    limit: int = 50,
) -> list[Game]:
    statement = select(Game).where(
        Game.game_type == "official",
        Game.deleted_at.is_(None),
    )

    if game_status is not None:
        statement = statement.where(Game.game_status == game_status)

    statement = statement.order_by(
        Game.starts_at.asc(),
        Game.created_at.asc(),
    ).limit(limit)

    return list(db.scalars(statement).all())


def list_official_game_participants(
    db: Session,
    game_id: uuid.UUID,
) -> list[GameParticipant]:
    get_official_game_or_404(db, game_id)
    return list(
        db.scalars(
            select(GameParticipant)
            .where(GameParticipant.game_id == game_id)
            .order_by(
                GameParticipant.roster_order.asc().nulls_last(),
                GameParticipant.created_at.asc(),
            )
        ).all()
    )


def list_official_game_bookings(
    db: Session,
    game_id: uuid.UUID,
) -> list[Booking]:
    get_official_game_or_404(db, game_id)
    return list(
        db.scalars(
            select(Booking)
            .where(Booking.game_id == game_id)
            .order_by(Booking.created_at.desc())
        ).all()
    )


def list_official_game_waitlist_entries(
    db: Session,
    game_id: uuid.UUID,
) -> list[WaitlistEntry]:
    get_official_game_or_404(db, game_id)
    return list(
        db.scalars(
            select(WaitlistEntry)
            .where(WaitlistEntry.game_id == game_id)
            .order_by(
                WaitlistEntry.position.asc(),
                WaitlistEntry.joined_at.asc(),
                WaitlistEntry.created_at.asc(),
            )
        ).all()
    )


def get_official_game_money(
    db: Session,
    game_id: uuid.UUID,
) -> AdminOfficialGameMoneyRead:
    get_official_game_or_404(db, game_id)

    booking_ids = select(Booking.id).where(Booking.game_id == game_id)
    participant_ids = select(GameParticipant.id).where(
        GameParticipant.game_id == game_id
    )
    payment_ids = select(Payment.id).where(
        or_(
            Payment.game_id == game_id,
            Payment.booking_id.in_(booking_ids),
        )
    )
    scoped_credit_usage_ids = select(GameCreditUsage.game_credit_id).where(
        or_(
            GameCreditUsage.game_id == game_id,
            GameCreditUsage.booking_id.in_(booking_ids),
            GameCreditUsage.payment_id.in_(payment_ids),
        )
    )

    payments = list(
        db.scalars(
            select(Payment)
            .where(
                or_(
                    Payment.game_id == game_id,
                    Payment.booking_id.in_(booking_ids),
                )
            )
            .order_by(Payment.created_at.desc(), Payment.id.desc())
        ).all()
    )
    refunds = list(
        db.scalars(
            select(Refund)
            .where(
                or_(
                    Refund.payment_id.in_(payment_ids),
                    Refund.booking_id.in_(booking_ids),
                    Refund.participant_id.in_(participant_ids),
                )
            )
            .order_by(Refund.created_at.desc(), Refund.id.desc())
        ).all()
    )
    credits = list(
        db.scalars(
            select(GameCredit)
            .where(
                or_(
                    GameCredit.source_game_id == game_id,
                    GameCredit.source_booking_id.in_(booking_ids),
                    GameCredit.source_payment_id.in_(payment_ids),
                    GameCredit.id.in_(scoped_credit_usage_ids),
                )
            )
            .order_by(GameCredit.created_at.desc(), GameCredit.id.desc())
        ).all()
    )
    credit_usages = list(
        db.scalars(
            select(GameCreditUsage)
            .where(
                or_(
                    GameCreditUsage.game_id == game_id,
                    GameCreditUsage.booking_id.in_(booking_ids),
                    GameCreditUsage.payment_id.in_(payment_ids),
                )
            )
            .order_by(
                GameCreditUsage.created_at.desc(),
                GameCreditUsage.id.desc(),
            )
        ).all()
    )

    return AdminOfficialGameMoneyRead(
        payments=payments,
        refunds=refunds,
        credits=credits,
        credit_usages=credit_usages,
    )
