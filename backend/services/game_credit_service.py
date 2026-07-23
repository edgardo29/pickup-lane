import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import GameCredit, GameCreditUsage, User
from backend.schemas.game_credit_schema import GameCreditBalanceRead
from backend.services.auth_service import require_active_admin_user

REDEEM_USAGE_TYPE = "redeem"
REVERSE_USAGE_TYPE = "reverse"
RESTORE_USAGE_TYPE = "restore"

RESERVED_USAGE_STATUS = "reserved"
REDEEMED_USAGE_STATUS = "redeemed"
RELEASED_USAGE_STATUS = "released"
REVERSED_USAGE_STATUS = "reversed"
RESTORED_USAGE_STATUS = "restored"

CONSUMING_REDEEM_STATUSES = {RESERVED_USAGE_STATUS, REDEEMED_USAGE_STATUS}


class GameCreditLedgerError(ValueError):
    pass


class GameCreditInsufficientBalanceError(GameCreditLedgerError):
    pass


class GameCreditReservationConflictError(GameCreditLedgerError):
    pass


class GameCreditCalculationError(GameCreditLedgerError):
    pass


@dataclass(frozen=True)
class GameCreditApplication:
    available_credit_cents: int
    credit_applied_cents: int
    minimum_charge_adjustment_cents: int
    final_amount_due_cents: int
    stripe_amount_cents: int
    payment_required: bool


def calculate_game_credit_application(
    total_amount_cents: int,
    available_credit_cents: int,
    *,
    minimum_stripe_charge_cents: int,
) -> GameCreditApplication:
    if total_amount_cents < 0:
        raise GameCreditCalculationError("Checkout total cannot be negative.")
    if available_credit_cents < 0:
        raise GameCreditCalculationError("Available game credit cannot be negative.")
    if minimum_stripe_charge_cents <= 0:
        raise GameCreditCalculationError("Minimum Stripe charge must be positive.")

    credit_applied_cents = min(available_credit_cents, total_amount_cents)
    remaining_due_cents = total_amount_cents - credit_applied_cents
    minimum_charge_adjustment_cents = 0
    stripe_amount_cents = remaining_due_cents

    if (
        credit_applied_cents > 0
        and 0 < remaining_due_cents < minimum_stripe_charge_cents
    ):
        minimum_charge_adjustment_cents = remaining_due_cents
        stripe_amount_cents = 0

    final_amount_due_cents = stripe_amount_cents

    return GameCreditApplication(
        available_credit_cents=available_credit_cents,
        credit_applied_cents=credit_applied_cents,
        minimum_charge_adjustment_cents=minimum_charge_adjustment_cents,
        final_amount_due_cents=final_amount_due_cents,
        stripe_amount_cents=stripe_amount_cents,
        payment_required=stripe_amount_cents > 0,
    )


def calculate_user_game_credit_application(
    db: Session,
    user_id: uuid.UUID,
    *,
    total_amount_cents: int,
    now: datetime,
    minimum_stripe_charge_cents: int,
) -> GameCreditApplication:
    available_credit_cents = get_available_game_credit_balance(db, user_id, now=now)
    return calculate_game_credit_application(
        total_amount_cents,
        available_credit_cents,
        minimum_stripe_charge_cents=minimum_stripe_charge_cents,
    )


def get_available_game_credit_balance(
    db: Session,
    user_id: uuid.UUID,
    *,
    now: datetime,
) -> int:
    balance = db.scalar(
        select(func.coalesce(func.sum(GameCredit.available_cents), 0)).where(
            GameCredit.user_id == user_id,
            GameCredit.credit_status == "active",
            GameCredit.available_cents > 0,
        )
    )
    return int(balance or 0)


def get_game_credit_balance_for_user(
    db: Session,
    current_user: User,
    *,
    user_id: uuid.UUID | None = None,
) -> GameCreditBalanceRead:
    effective_user_id = user_id or current_user.id

    if effective_user_id != current_user.id:
        require_active_admin_user(current_user)

    balance = get_available_game_credit_balance(
        db,
        effective_user_id,
        now=datetime.now(timezone.utc),
    )

    return GameCreditBalanceRead(
        user_id=effective_user_id,
        available_credit_cents=balance,
    )


def list_game_credits_for_user(
    db: Session,
    current_user: User,
    *,
    user_id: uuid.UUID | None = None,
) -> list[GameCredit]:
    effective_user_id = user_id or current_user.id

    if effective_user_id != current_user.id:
        require_active_admin_user(current_user)

    statement = (
        select(GameCredit)
        .where(GameCredit.user_id == effective_user_id)
        .order_by(GameCredit.created_at.desc(), GameCredit.id.desc())
    )
    return list(db.scalars(statement).all())


def get_ordered_available_credit_grants_for_update(
    db: Session,
    user_id: uuid.UUID,
    *,
    now: datetime,
) -> list[GameCredit]:
    statement = (
        select(GameCredit)
        .where(
            GameCredit.user_id == user_id,
            GameCredit.credit_status == "active",
            GameCredit.available_cents > 0,
        )
        .order_by(
            GameCredit.created_at.asc(),
            GameCredit.id.asc(),
        )
        .with_for_update()
    )
    return list(db.scalars(statement).all())


def get_checkout_redeem_usages_for_update(
    db: Session,
    booking_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> list[GameCreditUsage]:
    statement = (
        select(GameCreditUsage)
        .join(GameCredit, GameCreditUsage.game_credit_id == GameCredit.id)
        .where(
            GameCreditUsage.booking_id == booking_id,
            GameCreditUsage.usage_type == REDEEM_USAGE_TYPE,
        )
        .order_by(
            GameCredit.created_at.asc(),
            GameCredit.id.asc(),
            GameCreditUsage.created_at.asc(),
            GameCreditUsage.id.asc(),
        )
        .with_for_update()
    )
    if user_id is not None:
        statement = statement.where(GameCredit.user_id == user_id)

    return list(db.scalars(statement).all())


def get_booking_credit_usage_total(
    db: Session,
    booking_id: uuid.UUID,
    *,
    statuses: set[str] | None = None,
) -> int:
    statement = select(func.coalesce(func.sum(GameCreditUsage.amount_cents), 0)).where(
        GameCreditUsage.booking_id == booking_id,
        GameCreditUsage.usage_type == REDEEM_USAGE_TYPE,
    )
    if statuses is not None:
        statement = statement.where(GameCreditUsage.usage_status.in_(statuses))

    total = db.scalar(statement)
    return int(total or 0)


def lock_game_credit(db: Session, game_credit_id: uuid.UUID) -> GameCredit | None:
    return db.scalars(
        select(GameCredit)
        .where(GameCredit.id == game_credit_id)
        .with_for_update()
    ).first()


def has_reserved_usage_for_credit(db: Session, game_credit_id: uuid.UUID) -> bool:
    reserved_count = db.scalar(
        select(func.count())
        .select_from(GameCreditUsage)
        .where(
            GameCreditUsage.game_credit_id == game_credit_id,
            GameCreditUsage.usage_type == REDEEM_USAGE_TYPE,
            GameCreditUsage.usage_status == RESERVED_USAGE_STATUS,
        )
    )
    return int(reserved_count or 0) > 0


def mark_credit_used_if_fully_redeemed(
    db: Session,
    game_credit: GameCredit,
    *,
    now: datetime,
) -> None:
    if game_credit.credit_status == "reversed":
        return

    # SessionLocal disables autoflush, so pending usage status transitions must
    # be flushed before checking whether any reserved usage remains.
    db.flush()

    if game_credit.available_cents != 0:
        game_credit.credit_status = "active"
        game_credit.updated_at = now
        db.add(game_credit)
        return

    if has_reserved_usage_for_credit(db, game_credit.id):
        game_credit.credit_status = "active"
    else:
        game_credit.credit_status = "used"
    game_credit.updated_at = now
    db.add(game_credit)


def build_credit_usage_idempotency_key(
    idempotency_scope: str,
    game_credit_id: uuid.UUID,
) -> str:
    return f"{idempotency_scope}:credit:{game_credit_id}:redeem"[:255]


def build_credit_restore_idempotency_key(
    booking_id: uuid.UUID,
    redeemed_usage_id: uuid.UUID,
    restore_reason: str,
) -> str:
    return f"restore:{booking_id}:usage:{redeemed_usage_id}:{restore_reason}"[:255]


def reserve_game_credits(
    db: Session,
    user_id: uuid.UUID,
    *,
    amount_cents: int,
    booking_id: uuid.UUID,
    game_id: uuid.UUID | None,
    payment_id: uuid.UUID | None = None,
    now: datetime,
    idempotency_scope: str,
) -> list[GameCreditUsage]:
    if amount_cents <= 0:
        return []

    existing_usages = [
        usage
        for usage in get_checkout_redeem_usages_for_update(db, booking_id, user_id)
        if usage.usage_status in CONSUMING_REDEEM_STATUSES
    ]
    if existing_usages:
        existing_total = sum(usage.amount_cents for usage in existing_usages)
        if existing_total != amount_cents:
            raise GameCreditReservationConflictError(
                "Existing credit reservation does not match the requested amount."
            )
        return existing_usages

    grants = get_ordered_available_credit_grants_for_update(db, user_id, now=now)
    available_cents = sum(grant.available_cents for grant in grants)
    if available_cents < amount_cents:
        raise GameCreditInsufficientBalanceError(
            "Not enough available game credit to reserve this amount."
        )

    usages: list[GameCreditUsage] = []
    remaining_to_reserve = amount_cents
    for grant in grants:
        if remaining_to_reserve <= 0:
            break

        reserve_cents = min(grant.available_cents, remaining_to_reserve)
        grant.available_cents -= reserve_cents
        grant.credit_status = "active"
        grant.updated_at = now
        db.add(grant)

        usage = GameCreditUsage(
            id=uuid.uuid4(),
            game_credit_id=grant.id,
            booking_id=booking_id,
            game_id=game_id,
            payment_id=payment_id,
            amount_cents=reserve_cents,
            currency="USD",
            usage_type=REDEEM_USAGE_TYPE,
            usage_status=RESERVED_USAGE_STATUS,
            idempotency_key=build_credit_usage_idempotency_key(
                idempotency_scope,
                grant.id,
            ),
            reserved_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(usage)
        usages.append(usage)
        remaining_to_reserve -= reserve_cents

    db.flush()
    return usages


def redeem_reserved_game_credits(
    db: Session,
    booking_id: uuid.UUID,
    *,
    now: datetime,
    user_id: uuid.UUID | None = None,
) -> list[GameCreditUsage]:
    usages = get_checkout_redeem_usages_for_update(db, booking_id, user_id)
    for usage in usages:
        if usage.usage_status == REDEEMED_USAGE_STATUS:
            continue
        if usage.usage_status != RESERVED_USAGE_STATUS:
            raise GameCreditLedgerError(
                "Only reserved game credit usage can be redeemed."
            )

        game_credit = lock_game_credit(db, usage.game_credit_id)
        if game_credit is None:
            raise GameCreditLedgerError("Game credit grant was not found.")
        if game_credit.credit_status == "reversed":
            raise GameCreditLedgerError("Reversed game credit cannot be redeemed.")

        usage.usage_status = REDEEMED_USAGE_STATUS
        usage.redeemed_at = usage.redeemed_at or now
        usage.updated_at = now
        db.add(usage)
        mark_credit_used_if_fully_redeemed(db, game_credit, now=now)

    db.flush()
    return usages


def release_reserved_game_credits(
    db: Session,
    booking_id: uuid.UUID,
    *,
    now: datetime,
    reason_code: str,
    user_id: uuid.UUID | None = None,
) -> list[GameCreditUsage]:
    usages = get_checkout_redeem_usages_for_update(db, booking_id, user_id)
    released_usages: list[GameCreditUsage] = []

    for usage in usages:
        if usage.usage_status not in {RESERVED_USAGE_STATUS, RELEASED_USAGE_STATUS}:
            continue
        released_usages.append(
            release_reserved_game_credit_usage_record(
                db,
                usage,
                now=now,
                reason_code=reason_code,
            )
        )

    return released_usages


def release_reserved_game_credit_usage_record(
    db: Session,
    usage: GameCreditUsage,
    *,
    now: datetime,
    reason_code: str,
) -> GameCreditUsage:
    if usage.usage_type != REDEEM_USAGE_TYPE:
        raise GameCreditLedgerError("Only redeem credit usage can be released.")
    if usage.usage_status == RELEASED_USAGE_STATUS:
        return usage
    if usage.usage_status != RESERVED_USAGE_STATUS:
        raise GameCreditLedgerError("Only reserved game credit usage can be released.")

    game_credit = lock_game_credit(db, usage.game_credit_id)
    if game_credit is None:
        raise GameCreditLedgerError("Game credit grant was not found.")
    if game_credit.credit_status == "reversed":
        raise GameCreditLedgerError("Reversed game credit cannot be released.")

    game_credit.available_cents += usage.amount_cents
    if game_credit.available_cents > game_credit.amount_cents:
        raise GameCreditLedgerError(
            "Releasing game credit would exceed the original grant amount."
        )
    game_credit.credit_status = "active"
    game_credit.updated_at = now
    db.add(game_credit)

    usage.usage_status = RELEASED_USAGE_STATUS
    usage.reason_code = reason_code
    usage.released_at = usage.released_at or now
    usage.updated_at = now
    db.add(usage)
    db.flush()
    return usage


def release_reserved_game_credit_usage(
    db: Session,
    usage_id: uuid.UUID,
    *,
    now: datetime,
    reason_code: str,
) -> GameCreditUsage:
    usage = db.scalars(
        select(GameCreditUsage)
        .where(GameCreditUsage.id == usage_id)
        .with_for_update()
    ).first()
    if usage is None:
        raise GameCreditLedgerError("Game credit usage was not found.")
    return release_reserved_game_credit_usage_record(
        db,
        usage,
        now=now,
        reason_code=reason_code,
    )


def restore_redeemed_game_credit_usage_record(
    db: Session,
    usage: GameCreditUsage,
    *,
    now: datetime,
    restore_reason: str,
) -> GameCreditUsage:
    if usage.usage_type != REDEEM_USAGE_TYPE:
        raise GameCreditLedgerError("Only redeemed credit usage can be restored.")
    if usage.booking_id is None:
        raise GameCreditLedgerError("Redeemed credit usage is missing booking context.")

    restore_idempotency_key = build_credit_restore_idempotency_key(
        usage.booking_id,
        usage.id,
        restore_reason,
    )
    existing_by_idempotency_key = db.scalars(
        select(GameCreditUsage)
        .where(GameCreditUsage.idempotency_key == restore_idempotency_key)
        .with_for_update()
    ).first()
    if existing_by_idempotency_key is not None:
        return existing_by_idempotency_key

    if usage.usage_status != REDEEMED_USAGE_STATUS:
        raise GameCreditLedgerError("Only redeemed game credit usage can be restored.")

    game_credit = lock_game_credit(db, usage.game_credit_id)
    if game_credit is None:
        raise GameCreditLedgerError("Game credit grant was not found.")
    if game_credit.credit_status == "reversed":
        raise GameCreditLedgerError("Reversed game credit cannot be restored.")

    existing_restore_for_usage = db.scalars(
        select(GameCreditUsage)
        .where(
            GameCreditUsage.original_usage_id == usage.id,
            GameCreditUsage.usage_type == RESTORE_USAGE_TYPE,
            GameCreditUsage.usage_status == RESTORED_USAGE_STATUS,
        )
        .with_for_update()
    ).first()
    if existing_restore_for_usage is not None:
        return existing_restore_for_usage

    game_credit.available_cents += usage.amount_cents
    if game_credit.available_cents > game_credit.amount_cents:
        raise GameCreditLedgerError(
            "Restoring game credit would exceed the original grant amount."
        )
    game_credit.credit_status = "active"
    game_credit.updated_at = now
    db.add(game_credit)

    restored_usage = GameCreditUsage(
        id=uuid.uuid4(),
        game_credit_id=usage.game_credit_id,
        booking_id=usage.booking_id,
        game_id=usage.game_id,
        payment_id=usage.payment_id,
        original_usage_id=usage.id,
        amount_cents=usage.amount_cents,
        currency=usage.currency,
        usage_type=RESTORE_USAGE_TYPE,
        usage_status=RESTORED_USAGE_STATUS,
        idempotency_key=restore_idempotency_key,
        reason_code=restore_reason,
        created_at=now,
        updated_at=now,
    )
    db.add(restored_usage)
    db.flush()
    return restored_usage


def restore_redeemed_game_credit_usage(
    db: Session,
    usage_id: uuid.UUID,
    *,
    now: datetime,
    restore_reason: str,
) -> GameCreditUsage:
    usage = db.scalars(
        select(GameCreditUsage)
        .where(GameCreditUsage.id == usage_id)
        .with_for_update()
    ).first()
    if usage is None:
        raise GameCreditLedgerError("Game credit usage was not found.")
    return restore_redeemed_game_credit_usage_record(
        db,
        usage,
        now=now,
        restore_reason=restore_reason,
    )


def restore_redeemed_game_credits(
    db: Session,
    booking_id: uuid.UUID,
    *,
    now: datetime,
    restore_reason: str,
    user_id: uuid.UUID | None = None,
) -> list[GameCreditUsage]:
    usages = [
        usage
        for usage in get_checkout_redeem_usages_for_update(db, booking_id, user_id)
        if usage.usage_status == REDEEMED_USAGE_STATUS
    ]
    restored_usages: list[GameCreditUsage] = []

    for usage in usages:
        restored_usages.append(
            restore_redeemed_game_credit_usage_record(
                db,
                usage,
                now=now,
                restore_reason=restore_reason,
            )
        )

    db.flush()
    return restored_usages
