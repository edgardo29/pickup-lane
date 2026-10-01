"""Semantic map of current database invariants and their enforcement.

The map names current roster, waitlist, capacity, and financial invariants
without executing database queries, provider calls, retries, workers, or
runtime orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseInvariantDisposition:
    invariant_id: str
    owner: str
    enforcement: tuple[str, ...]
    serialization_owner: str | None
    contention_result: str
    external_side_effect_boundary: str | None = None


DATABASE_INVARIANT_DISPOSITIONS: tuple[DatabaseInvariantDisposition, ...] = (
    DatabaseInvariantDisposition(
        invariant_id="community_roster_capacity",
        owner="Game plus Booking/GameParticipant/WaitlistEntry capacity rows",
        enforcement=(
            "Game row SELECT FOR UPDATE before community roster capacity decisions",
            "capacity-holding participant count includes confirmed and unexpired pending_payment holds",
            "bounded HTTP/domain rejection when the complete party no longer fits",
        ),
        serialization_owner="backend.services.game_service.get_locked_game_or_404",
        contention_result="one transaction wins the capacity decision; the loser is waitlisted or rejected by current game rules",
    ),
    DatabaseInvariantDisposition(
        invariant_id="community_active_participant_identity",
        owner="GameParticipant active registered-user relationship",
        enforcement=(
            "partial unique index for active registered user per game",
            "service precheck for clearer conflict messages",
        ),
        serialization_owner="Game row lock for roster-capacity workflows",
        contention_result="duplicate active participant attempts fail with bounded conflict",
    ),
    DatabaseInvariantDisposition(
        invariant_id="waitlist_identity_and_position",
        owner="WaitlistEntry active user and position rows",
        enforcement=(
            "partial unique index for active user per game",
            "partial unique index for active waitlist position per game",
            "Game row lock before next-position assignment and promotion decisions",
        ),
        serialization_owner="Game row lock for join and promotion workflows",
        contention_result="duplicate user or position attempts fail with bounded conflict",
    ),
    DatabaseInvariantDisposition(
        invariant_id="waitlist_promotion_capacity_hold",
        owner="WaitlistEntry, Booking, GameParticipant, and Payment promotion rows",
        enforcement=(
            "Game row lock before every promotion capacity decision",
            "pending_payment booking and participant state persists before provider mutation",
            "promotion reacquires Game lock and recomputes capacity after provider/checkpoint commit boundaries",
        ),
        serialization_owner="backend.services.game_waitlist_service.promote_waitlist_entries",
        contention_result="a paid promotion hold counts against capacity while provider work is pending",
        external_side_effect_boundary="waitlist.auto_promotion.payment_intent",
    ),
    DatabaseInvariantDisposition(
        invariant_id="account_deletion_roster_lock_order",
        owner="Account-deletion future roster cleanup",
        enforcement=(
            "candidate affected games are discovered without dependent-row locks",
            "affected Game rows lock in deterministic ID order",
            "Booking and GameParticipant rows are reread and locked under owned Game locks",
        ),
        serialization_owner="backend.services.account_deletion_service.cancel_future_roster_activity",
        contention_result="multi-game cleanup follows game-first ordering and avoids reverse-order deadlock hazards",
        external_side_effect_boundary="account_deletion.firebase_delete",
    ),
    DatabaseInvariantDisposition(
        invariant_id="official_checkout_and_roster_serialization",
        owner="Official checkout, official roster, cancellation, and player-removal workflows",
        enforcement=(
            "accepted official checkout Game row lock",
            "accepted official roster administration Game row lock",
            "accepted official cancellation/removal row locks",
        ),
        serialization_owner="existing official-game service lock helpers",
        contention_result="official capacity and roster mutations remain serialized by current accepted locks",
        external_side_effect_boundary="checkout.payment_intent.create",
    ),
    DatabaseInvariantDisposition(
        invariant_id="payment_identity",
        owner="Payment idempotency and provider identity rows",
        enforcement=(
            "unique payment idempotency key",
            "partial unique provider PaymentIntent identity when present",
            "partial unique provider charge identity when present",
        ),
        serialization_owner="workflow-specific row locks where payment state mutates",
        contention_result="duplicate payment identities fail at the database boundary",
        external_side_effect_boundary="checkout.payment_intent.create",
    ),
    DatabaseInvariantDisposition(
        invariant_id="refund_identity_and_amount_state",
        owner="Refund and refund amount availability rows",
        enforcement=(
            "partial unique provider refund identity when present",
            "refund amount availability validation under current admin/provider workflow locks",
            "refund lifecycle check constraints",
        ),
        serialization_owner="admin refund and financial outcome row locks",
        contention_result="duplicate or over-limit refund mutation is rejected or routed to bounded repair state",
    ),
    DatabaseInvariantDisposition(
        invariant_id="refund_event_identity",
        owner="RefundEvent provider event and idempotency rows",
        enforcement=(
            "partial unique provider event identity when present",
            "partial unique refund-event idempotency key when present",
            "refund-event status and target check constraints",
        ),
        serialization_owner="refund-event ingestion and reconciliation workflow state gates",
        contention_result="duplicate refund events converge on one persisted event identity",
    ),
    DatabaseInvariantDisposition(
        invariant_id="host_publish_fee_financial_outcome",
        owner="HostPublishFee, Payment, Refund, and AdminFinancialOutcome rows",
        enforcement=(
            "current publish/payment state transitions",
            "row locks in admin financial outcome mutation paths",
            "idempotency keys for admin financial outcome actions",
        ),
        serialization_owner="admin financial outcome workflow row locks",
        contention_result="duplicate publish-fee financial outcomes are bounded by current state gates",
        external_side_effect_boundary="community_publish_fee.payment_intent.create",
    ),
    DatabaseInvariantDisposition(
        invariant_id="game_credit_grant_balance",
        owner="GameCredit grants and GameCreditUsage reservation rows",
        enforcement=(
            "ordered available GameCredit grant SELECT FOR UPDATE",
            "available_cents check constraints",
            "game-credit and usage idempotency keys",
        ),
        serialization_owner="backend.services.game_credit_service.reserve_game_credits",
        contention_result="concurrent reservations cannot overdraw a grant",
    ),
    DatabaseInvariantDisposition(
        invariant_id="game_credit_usage_lifecycle",
        owner="GameCreditUsage redeem, release, restore, and reverse ledger rows",
        enforcement=(
            "locked GameCreditUsage rows for release/redeem/restore",
            "locked GameCredit rows for balance restoration/reversal",
            "unique restore idempotency key and one-restore-per-original partial index",
        ),
        serialization_owner="backend.services.game_credit_service and backend.services.game_credit_admin_service",
        contention_result="double release, restore, redeem, or reverse attempts converge or fail without lost ledger state",
    ),
    DatabaseInvariantDisposition(
        invariant_id="money_issue_operation_identity",
        owner="MoneyIssue operation keys and admin-money repair rows",
        enforcement=(
            "unique money-issue operation key",
            "MoneyIssue SELECT FOR UPDATE in repair/resolution paths",
            "admin action idempotency keys for current financial repair actions",
        ),
        serialization_owner="backend.services.admin_money_issue_service",
        contention_result="duplicate repair/reconciliation attempts cannot create incompatible money-issue outcomes",
    ),
    DatabaseInvariantDisposition(
        invariant_id="admin_support_financial_operation_identity",
        owner="AdminAction, SupportFlag, and PlatformNotice operation identities tied to financial flows",
        enforcement=(
            "partial admin-action idempotency indexes for financial/support actions",
            "support flag idempotency indexes when support rows are created by financial failures",
            "platform-notice idempotency hash uniqueness for admin-visible local effects",
        ),
        serialization_owner="owning admin/support workflow state gates",
        contention_result="duplicate operational rows are bounded by idempotency or state gates",
    ),
    DatabaseInvariantDisposition(
        invariant_id="database_failure_classification",
        owner="Current database-invariant mutation paths",
        enforcement=(
            "database constraints for duplicate facts",
            "PostgreSQL row locks for aggregate facts",
            "bounded HTTP/domain conflicts or database errors for loser outcomes",
            "no process-local locks or blind whole-transaction replay",
        ),
        serialization_owner="current service transaction boundaries",
        contention_result="contention, integrity, timeout, deadlock, serialization, and unknown database outcomes remain bounded",
    ),
)


def dispositions_by_invariant_id() -> dict[str, DatabaseInvariantDisposition]:
    return {
        disposition.invariant_id: disposition
        for disposition in DATABASE_INVARIANT_DISPOSITIONS
    }
