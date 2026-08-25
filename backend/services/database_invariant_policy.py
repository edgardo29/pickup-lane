"""Current database invariant policy for WS04-02B.

This module is declarative. It names current roster, waitlist, capacity, and
financial database invariant dispositions without executing database queries,
provider calls, retries, workers, or runtime orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseInvariantDisposition:
    invariant_id: str
    owner: str
    requirements: tuple[str, ...]
    enforcement: tuple[str, ...]
    serialization_owner: str | None
    contention_result: str
    ws04_02a_boundary: str | None = None
    later_owner: str | None = None


DATABASE_INVARIANT_DISPOSITIONS: tuple[DatabaseInvariantDisposition, ...] = (
    DatabaseInvariantDisposition(
        invariant_id="community_roster_capacity",
        owner="Game plus Booking/GameParticipant/WaitlistEntry capacity rows",
        requirements=("WS04-02B-R1", "WS04-02B-R2", "WS04-02B-R4"),
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
        requirements=("WS04-02B-R1", "WS04-02B-R5"),
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
        requirements=("WS04-02B-R1", "WS04-02B-R3", "WS04-02B-R5"),
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
        requirements=("WS04-02B-R1", "WS04-02B-R3", "WS04-02B-R8"),
        enforcement=(
            "Game row lock before every promotion capacity decision",
            "pending_payment booking and participant state persists before provider mutation",
            "promotion reacquires Game lock and recomputes capacity after provider/checkpoint commit boundaries",
        ),
        serialization_owner="backend.services.game_waitlist_service.promote_waitlist_entries",
        contention_result="a paid promotion hold counts against capacity while provider work is pending",
        ws04_02a_boundary="waitlist.auto_promotion.payment_intent",
        later_owner="WS05 for durable provider reconciliation and worker-backed recovery",
    ),
    DatabaseInvariantDisposition(
        invariant_id="account_deletion_roster_lock_order",
        owner="Account-deletion future roster cleanup",
        requirements=("WS04-02B-R1", "WS04-02B-R4"),
        enforcement=(
            "candidate affected games are discovered without dependent-row locks",
            "affected Game rows lock in deterministic ID order",
            "Booking and GameParticipant rows are reread and locked under owned Game locks",
        ),
        serialization_owner="backend.services.account_deletion_service.cancel_future_roster_activity",
        contention_result="multi-game cleanup follows game-first ordering and avoids reverse-order deadlock hazards",
        ws04_02a_boundary="account_deletion.firebase_delete",
    ),
    DatabaseInvariantDisposition(
        invariant_id="official_checkout_and_roster_serialization",
        owner="Official checkout, official roster, cancellation, and player-removal workflows",
        requirements=("WS04-02B-R1", "WS04-02B-R2", "WS04-02B-R9"),
        enforcement=(
            "accepted official checkout Game row lock",
            "accepted official roster administration Game row lock",
            "accepted official cancellation/removal row locks",
        ),
        serialization_owner="existing official-game service lock helpers",
        contention_result="official capacity and roster mutations remain serialized by current accepted locks",
        ws04_02a_boundary="checkout.payment_intent.create",
        later_owner="WS05 for full payment and provider reconciliation lifecycle",
    ),
    DatabaseInvariantDisposition(
        invariant_id="payment_identity",
        owner="Payment idempotency and provider identity rows",
        requirements=("WS04-02B-R1", "WS04-02B-R5", "WS04-02B-R6"),
        enforcement=(
            "unique payment idempotency key",
            "partial unique provider PaymentIntent identity when present",
            "partial unique provider charge identity when present",
        ),
        serialization_owner="workflow-specific row locks where payment state mutates",
        contention_result="duplicate payment identities fail at the database boundary",
        ws04_02a_boundary="checkout.payment_intent.create",
        later_owner="WS05 for provider truth and reconciliation",
    ),
    DatabaseInvariantDisposition(
        invariant_id="refund_identity_and_amount_state",
        owner="Refund and refund amount availability rows",
        requirements=("WS04-02B-R1", "WS04-02B-R5", "WS04-02B-R6"),
        enforcement=(
            "partial unique provider refund identity when present",
            "refund amount availability validation under current admin/provider workflow locks",
            "refund lifecycle check constraints",
        ),
        serialization_owner="admin refund and financial outcome row locks",
        contention_result="duplicate or over-limit refund mutation is rejected or routed to bounded repair state",
        later_owner="WS05 for full provider reconciliation",
    ),
    DatabaseInvariantDisposition(
        invariant_id="refund_event_identity",
        owner="RefundEvent provider event and idempotency rows",
        requirements=("WS04-02B-R1", "WS04-02B-R5", "WS04-02B-R6"),
        enforcement=(
            "partial unique provider event identity when present",
            "partial unique refund-event idempotency key when present",
            "refund-event status and target check constraints",
        ),
        serialization_owner="refund-event ingestion and reconciliation workflow state gates",
        contention_result="duplicate refund events converge on one persisted event identity",
        later_owner="WS05 for provider event lifecycle proof",
    ),
    DatabaseInvariantDisposition(
        invariant_id="host_publish_fee_financial_outcome",
        owner="HostPublishFee, Payment, Refund, and AdminFinancialOutcome rows",
        requirements=("WS04-02B-R1", "WS04-02B-R6"),
        enforcement=(
            "current publish/payment state transitions",
            "row locks in admin financial outcome mutation paths",
            "idempotency keys for admin financial outcome actions",
        ),
        serialization_owner="admin financial outcome workflow row locks",
        contention_result="duplicate publish-fee financial outcomes are bounded by current state gates",
        ws04_02a_boundary="community_publish_fee.payment_intent.create",
        later_owner="WS05 for full payment lifecycle and provider reconciliation",
    ),
    DatabaseInvariantDisposition(
        invariant_id="game_credit_grant_balance",
        owner="GameCredit grants and GameCreditUsage reservation rows",
        requirements=("WS04-02B-R1", "WS04-02B-R6", "WS04-02B-R7"),
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
        requirements=("WS04-02B-R1", "WS04-02B-R6", "WS04-02B-R7"),
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
        requirements=("WS04-02B-R1", "WS04-02B-R5", "WS04-02B-R6"),
        enforcement=(
            "unique money-issue operation key",
            "MoneyIssue SELECT FOR UPDATE in repair/resolution paths",
            "admin action idempotency keys for current financial repair actions",
        ),
        serialization_owner="backend.services.admin_money_issue_service",
        contention_result="duplicate repair/reconciliation attempts cannot create incompatible money-issue outcomes",
        later_owner="WS05 for broader reconciliation lifecycle",
    ),
    DatabaseInvariantDisposition(
        invariant_id="admin_support_financial_operation_identity",
        owner="AdminAction, SupportFlag, and PlatformNotice operation identities tied to financial flows",
        requirements=("WS04-02B-R1", "WS04-02B-R5", "WS04-02B-R6"),
        enforcement=(
            "partial admin-action idempotency indexes for financial/support actions",
            "support flag idempotency indexes when support rows are created by financial failures",
            "platform-notice idempotency hash uniqueness for admin-visible local effects",
        ),
        serialization_owner="owning admin/support workflow state gates",
        contention_result="duplicate operational rows are bounded by idempotency or state gates",
        later_owner="WS09 and WS10 for full operational audit and incident evidence",
    ),
    DatabaseInvariantDisposition(
        invariant_id="database_failure_classification",
        owner="Current database-invariant mutation paths",
        requirements=("WS04-02B-R1", "WS04-02B-R8", "WS04-02B-R9"),
        enforcement=(
            "database constraints for duplicate facts",
            "PostgreSQL row locks for aggregate facts",
            "bounded HTTP/domain conflicts or database errors for loser outcomes",
            "no process-local locks or blind whole-transaction replay",
        ),
        serialization_owner="current service transaction boundaries",
        contention_result="contention, integrity, timeout, deadlock, serialization, and unknown database outcomes remain bounded",
        later_owner="WS04-03 for migration rehearsal and WS09/WS10 for deployed operational evidence",
    ),
)


def dispositions_by_invariant_id() -> dict[str, DatabaseInvariantDisposition]:
    return {
        disposition.invariant_id: disposition
        for disposition in DATABASE_INVARIANT_DISPOSITIONS
    }


def dispositions_for_requirement(
    requirement_id: str,
) -> tuple[DatabaseInvariantDisposition, ...]:
    return tuple(
        disposition
        for disposition in DATABASE_INVARIANT_DISPOSITIONS
        if requirement_id in disposition.requirements
    )
