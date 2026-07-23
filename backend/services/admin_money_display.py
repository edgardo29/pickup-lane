import uuid

from backend.models import Game, User
from backend.schemas.admin_money_schema import AdminMoneyDisplayRead


def compact_id(value: uuid.UUID | None) -> str | None:
    if value is None:
        return None
    return str(value)[:8]


def user_name(user: User | None) -> str | None:
    if user is None:
        return None
    full_name = " ".join(
        part for part in (user.first_name, user.last_name) if part
    ).strip()
    return full_name or user.email


def game_label(game: Game | None) -> str | None:
    if game is None:
        return None
    return game.title or game.venue_name_snapshot or f"Game {compact_id(game.id)}"


def admin_money_display(
    *,
    user: User | None = None,
    game: Game | None = None,
    context_label: str | None = None,
    payment_id: uuid.UUID | None = None,
    refund_id: uuid.UUID | None = None,
    credit_id: uuid.UUID | None = None,
) -> AdminMoneyDisplayRead:
    return AdminMoneyDisplayRead(
        user_name=user_name(user),
        user_email=user.email if user is not None else None,
        game_label=game_label(game),
        context_label=context_label,
        payment_short_label=f"Payment {compact_id(payment_id)}" if payment_id else None,
        refund_short_label=f"Refund {compact_id(refund_id)}" if refund_id else None,
        credit_short_label=f"Credit {compact_id(credit_id)}" if credit_id else None,
    )
