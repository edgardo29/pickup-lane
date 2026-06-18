"""Booking query helpers shared by booking routes and future support flows."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Booking, User


def list_current_user_bookings(db: Session, current_user: User) -> list[Booking]:
    return list(
        db.scalars(
            select(Booking)
            .where(Booking.buyer_user_id == current_user.id)
            .order_by(Booking.created_at.desc())
        ).all()
    )
