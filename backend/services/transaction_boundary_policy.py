"""Source-owned transaction boundary policy for side-effecting workflows.

This module is declarative. It names current database units of work, external
effects, checkpoint expectations, outcome recording, and later owners without
executing providers, retries, workers, or generic transaction decorators.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExternalOperationClass(str, Enum):
    PROVIDER_READ = "PROVIDER_READ"
    IDEMPOTENT_PROVIDER_MUTATION = "IDEMPOTENT_PROVIDER_MUTATION"
    RECONCILE_BEFORE_RETRY_MUTATION = "RECONCILE_BEFORE_RETRY_MUTATION"
    NO_AUTOMATIC_RETRY_MUTATION = "NO_AUTOMATIC_RETRY_MUTATION"
    MANUAL_REPAIR_MUTATION = "MANUAL_REPAIR_MUTATION"
    PROVIDER_REDELIVERY = "PROVIDER_REDELIVERY"
    USER_VISIBLE_LOCAL_EFFECT = "USER_VISIBLE_LOCAL_EFFECT"
    ADMIN_VISIBLE_LOCAL_EFFECT = "ADMIN_VISIBLE_LOCAL_EFFECT"
    STORAGE_OBJECT_DEPENDENCY = "STORAGE_OBJECT_DEPENDENCY"


@dataclass(frozen=True)
class TransactionBoundaryPolicy:
    workflow: str
    service_function: str
    database_unit_of_work: tuple[str, ...]
    external_effect: str
    operation_class: ExternalOperationClass
    provider_retry_contexts: tuple[str, ...]
    required_pre_effect_checkpoint: str
    required_post_effect_recording: tuple[str, ...]
    timeout_or_unknown_outcome: str
    recovery_path: str
    downstream_owner: str | None = None

    @property
    def provider_backed(self) -> bool:
        return bool(self.provider_retry_contexts)


TRANSACTION_BOUNDARY_POLICIES: tuple[TransactionBoundaryPolicy, ...] = (
    TransactionBoundaryPolicy(
        workflow="checkout.payment_intent.create",
        service_function="backend.services.checkout_service.create_game_checkout_payment_intent_workflow",
        database_unit_of_work=(
            "Booking pending_payment row",
            "pending GameParticipant capacity hold rows",
            "Payment booking row",
            "reserved GameCreditUsage rows when credits apply",
        ),
        external_effect="Stripe PaymentIntent creation for official-game checkout.",
        operation_class=ExternalOperationClass.NO_AUTOMATIC_RETRY_MUTATION,
        provider_retry_contexts=("checkout_initial_create_before_provider_result",),
        required_pre_effect_checkpoint=(
            "Committed pending booking, participants, payment idempotency key, "
            "and credit reservation before Stripe create."
        ),
        required_post_effect_recording=(
            "Payment.provider_payment_intent_id",
            "Payment.provider_charge_id when available",
            "Payment.payment_status mapped through keep_payment_pending_until_webhook",
        ),
        timeout_or_unknown_outcome=(
            "Propagate unknown outcome without confirmation or automatic app replay; "
            "the committed local checkout identity remains recoverable."
        ),
        recovery_path="Checkout re-entry or later WS05 provider reconciliation.",
        downstream_owner="WS05",
    ),
    TransactionBoundaryPolicy(
        workflow="checkout.payment_intent.confirm",
        service_function="backend.services.checkout_service.resume_serialized_pending_checkout",
        database_unit_of_work=(
            "existing pending Booking",
            "existing pending Payment with provider PaymentIntent ID",
            "locked Game checkout serialization",
        ),
        external_effect="Stripe PaymentIntent retrieve and confirm for checkout re-entry.",
        operation_class=ExternalOperationClass.RECONCILE_BEFORE_RETRY_MUTATION,
        provider_retry_contexts=(
            "checkout_active_hold_reentry",
            "checkout_initial_confirm_after_checkpoint",
            "checkout_existing_pending_confirm_after_provider_read",
        ),
        required_pre_effect_checkpoint=(
            "Existing committed checkout checkpoint with provider PaymentIntent ID."
        ),
        required_post_effect_recording=(
            "Payment.payment_status",
            "Payment.provider_charge_id",
        ),
        timeout_or_unknown_outcome=(
            "Do not confirm again blindly; keep the checkout pending/processing "
            "until provider state can be reconciled."
        ),
        recovery_path="Serialized checkout re-entry and WS05 post-expiry reconciliation.",
        downstream_owner="WS05",
    ),
    TransactionBoundaryPolicy(
        workflow="checkout.credit_covered_confirm",
        service_function="backend.services.checkout_service.create_game_checkout_payment_intent_workflow",
        database_unit_of_work=(
            "Booking",
            "GameParticipant rows",
            "GameCreditUsage reservations and redemptions",
            "Game capacity status",
        ),
        external_effect="User-visible checkout success without provider mutation.",
        operation_class=ExternalOperationClass.USER_VISIBLE_LOCAL_EFFECT,
        provider_retry_contexts=(),
        required_pre_effect_checkpoint="Not applicable - no external provider mutation.",
        required_post_effect_recording=(
            "confirmed Booking",
            "confirmed GameParticipant rows",
            "redeemed GameCreditUsage rows",
        ),
        timeout_or_unknown_outcome="Not applicable - no provider outcome.",
        recovery_path="Committed local checkout state is the visible source of truth.",
    ),
    TransactionBoundaryPolicy(
        workflow="checkout.stale_pending_expire",
        service_function="backend.services.checkout_service.expire_stale_pending_checkouts",
        database_unit_of_work=(
            "expired Booking rows",
            "cancelled or removed GameParticipant rows",
            "released GameCreditUsage rows",
            "provider-truth-preserving Payment rows",
            "payment_failed WaitlistEntry rows",
        ),
        external_effect="User-visible release of checkout hold and local capacity.",
        operation_class=ExternalOperationClass.USER_VISIBLE_LOCAL_EFFECT,
        provider_retry_contexts=(),
        required_pre_effect_checkpoint="Committed local checkout rows already exist.",
        required_post_effect_recording=(
            "expired booking/payment state",
            "released credit reservations",
            "updated participant/waitlist capacity state",
        ),
        timeout_or_unknown_outcome="Not applicable - no provider mutation.",
        recovery_path="Local committed state drives checkout status and later reconciliation.",
        downstream_owner="WS05 for provider reconciliation when a late provider success appears.",
    ),
    TransactionBoundaryPolicy(
        workflow="waitlist.auto_promotion.payment_intent",
        service_function="backend.services.game_waitlist_service.attempt_paid_waitlist_auto_promotion",
        database_unit_of_work=(
            "locked WaitlistEntry",
            "promoted Booking",
            "promoted GameParticipant rows",
            "Payment row with waitlist idempotency key",
            "notification rows for success or failure",
        ),
        external_effect="Stripe PaymentIntent create and confirm for paid waitlist auto-promotion.",
        operation_class=ExternalOperationClass.RECONCILE_BEFORE_RETRY_MUTATION,
        provider_retry_contexts=(
            "waitlist_auto_promotion_create",
            "waitlist_auto_promotion_confirm",
        ),
        required_pre_effect_checkpoint=(
            "Current locked promotion workflow owns the local payment identity; "
            "later durable execution remains WS05."
        ),
        required_post_effect_recording=(
            "Payment provider identity and status",
            "WaitlistEntry accepted, failed, or processing state",
            "booking/participant promotion state",
            "local notification rows",
        ),
        timeout_or_unknown_outcome=(
            "Leave payment and promotion state processing; no blind request replay."
        ),
        recovery_path="Payment reconciliation and durable promotion recovery in WS05.",
        downstream_owner="WS05",
    ),
    TransactionBoundaryPolicy(
        workflow="community_publish_fee.payment_intent.create",
        service_function="backend.services.community_game_publish_service.create_paid_publish_attempt",
        database_unit_of_work=(
            "CommunityPublishAttempt",
            "Payment community_publish_fee row",
        ),
        external_effect="Stripe PaymentIntent creation for paid community-game publishing.",
        operation_class=ExternalOperationClass.RECONCILE_BEFORE_RETRY_MUTATION,
        provider_retry_contexts=("community_publish_fee_initial_create",),
        required_pre_effect_checkpoint=(
            "Committed publish attempt and payment idempotency key before Stripe create."
        ),
        required_post_effect_recording=(
            "Payment.provider_payment_intent_id",
            "Payment.provider_charge_id when available",
        ),
        timeout_or_unknown_outcome=(
            "Propagate unknown outcome with committed attempt/payment identity; "
            "ordinary app retry is not approved."
        ),
        recovery_path="Publish-attempt status endpoint and WS05 financial reconciliation.",
        downstream_owner="WS05",
    ),
    TransactionBoundaryPolicy(
        workflow="community_publish_fee.payment_intent.confirm",
        service_function="backend.services.community_game_publish_service.create_paid_publish_attempt",
        database_unit_of_work=(
            "CommunityPublishAttempt",
            "Payment community_publish_fee row",
        ),
        external_effect="Stripe PaymentIntent confirmation for paid community-game publishing.",
        operation_class=ExternalOperationClass.RECONCILE_BEFORE_RETRY_MUTATION,
        provider_retry_contexts=("community_publish_fee_confirm_after_checkpoint",),
        required_pre_effect_checkpoint="Committed Payment row with provider PaymentIntent ID.",
        required_post_effect_recording=(
            "CommunityPublishAttempt status",
            "Payment status and provider_charge_id",
        ),
        timeout_or_unknown_outcome="Preserve committed payment identity for reconciliation.",
        recovery_path="Attempt status endpoint, admin repair, and WS05 reconciliation.",
        downstream_owner="WS05",
    ),
    TransactionBoundaryPolicy(
        workflow="community_publish.finalize_success",
        service_function="backend.services.community_game_publish_service.finalize_community_publish_attempt_success",
        database_unit_of_work=(
            "Payment",
            "CommunityPublishAttempt",
            "Game",
            "GameParticipant host row",
            "CommunityGameDetail",
            "HostPublishFee",
        ),
        external_effect="User-visible published community game.",
        operation_class=ExternalOperationClass.USER_VISIBLE_LOCAL_EFFECT,
        provider_retry_contexts=(),
        required_pre_effect_checkpoint="Committed provider payment success identity.",
        required_post_effect_recording=(
            "published Game",
            "succeeded CommunityPublishAttempt",
            "paid HostPublishFee",
        ),
        timeout_or_unknown_outcome="Not applicable - provider success was already observed.",
        recovery_path="Committed game and attempt state are the visible source of truth.",
    ),
    TransactionBoundaryPolicy(
        workflow="stripe.webhook.payment_event_ingest",
        service_function="backend.services.stripe_webhook_service.record_and_process_stripe_webhook_event",
        database_unit_of_work=(
            "PaymentEvent provider-event ledger",
            "Payment/Booking/Refund rows updated by event handlers",
        ),
        external_effect="Stripe provider redelivery and local payment lifecycle processing.",
        operation_class=ExternalOperationClass.PROVIDER_REDELIVERY,
        provider_retry_contexts=("stripe_webhook_provider_redelivery",),
        required_pre_effect_checkpoint="Provider event ID and local uniqueness before processing.",
        required_post_effect_recording=(
            "PaymentEvent processing status",
            "owned local payment, booking, refund, or issue state",
        ),
        timeout_or_unknown_outcome="Provider redelivery, not application replay, owns retry.",
        recovery_path="Webhook idempotency and later WS05 payment lifecycle evidence.",
        downstream_owner="WS05",
    ),
    TransactionBoundaryPolicy(
        workflow="late_checkout_payment.compensation",
        service_function="backend.services.stripe_webhook_service.ensure_payment_compensation",
        database_unit_of_work=(
            "expired Booking",
            "succeeded late Payment",
            "PaymentCompensation refund requirement",
        ),
        external_effect="Operator-visible local compensation requirement for a late successful checkout payment.",
        operation_class=ExternalOperationClass.ADMIN_VISIBLE_LOCAL_EFFECT,
        provider_retry_contexts=(),
        required_pre_effect_checkpoint=(
            "Existing durable booking/payment identity under the game-first lock order."
        ),
        required_post_effect_recording=(
            "One active PaymentCompensation requirement per payment and booking",
        ),
        timeout_or_unknown_outcome="Not applicable - this path performs no provider mutation.",
        recovery_path="Later operator financial repair processes the durable compensation requirement.",
        downstream_owner="WS05",
    ),
    TransactionBoundaryPolicy(
        workflow="admin_money.refund.retry",
        service_function="backend.services.admin_money_refund_service.retry_admin_money_refund",
        database_unit_of_work=(
            "Refund",
            "Payment",
            "AdminAction update_refund retry intent",
            "RefundEvent",
            "MoneyIssue",
            "Booking or HostPublishFee when affected",
        ),
        external_effect="Stripe Refund creation from admin retry.",
        operation_class=ExternalOperationClass.MANUAL_REPAIR_MUTATION,
        provider_retry_contexts=("admin_refund_retry", "admin_refund_retry_state_gate"),
        required_pre_effect_checkpoint=(
            "Committed AdminAction retry intent and idempotency key before Stripe refund create."
        ),
        required_post_effect_recording=(
            "Refund provider_refund_id/status",
            "RefundEvent",
            "AdminAction metadata",
            "MoneyIssue/booking/payment/fee updates when applicable",
        ),
        timeout_or_unknown_outcome=(
            "Committed retry intent blocks duplicate automatic retry until reconciliation."
        ),
        recovery_path="Admin reconciliation and WS05 durable financial reconciliation.",
        downstream_owner="WS05",
    ),
    TransactionBoundaryPolicy(
        workflow="admin_money.refund.reconcile",
        service_function="backend.services.admin_money_refund_service.reconcile_admin_money_refund",
        database_unit_of_work=(
            "Refund",
            "Payment",
            "AdminAction reconcile intent",
            "RefundEvent",
            "MoneyIssue",
        ),
        external_effect="Stripe Refund read for admin reconciliation.",
        operation_class=ExternalOperationClass.PROVIDER_READ,
        provider_retry_contexts=("admin_refund_reconciliation", "admin_refund_reconcile_state_gate"),
        required_pre_effect_checkpoint="Committed refund provider identity or missing-reference issue.",
        required_post_effect_recording=(
            "RefundEvent reconciliation result",
            "MoneyIssue recommendation",
        ),
        timeout_or_unknown_outcome="Safe read timeout returns bounded failure without mutation replay.",
        recovery_path="Admin can reconcile again from durable local state.",
    ),
    TransactionBoundaryPolicy(
        workflow="admin_money.credit.retry",
        service_function="backend.services.admin_money_issue_service.retry_admin_money_issue_credit",
        database_unit_of_work=(
            "MoneyIssue",
            "GameCredit ledger rows",
            "AdminAction repair intent",
        ),
        external_effect="Admin-visible credit repair state-gated by local application rows.",
        operation_class=ExternalOperationClass.MANUAL_REPAIR_MUTATION,
        provider_retry_contexts=("admin_credit_repair_state_gate",),
        required_pre_effect_checkpoint="Existing money issue and admin repair intent.",
        required_post_effect_recording=("GameCredit ledger repair result", "AdminAction row"),
        timeout_or_unknown_outcome="Manual repair remains state gated; no automatic replay.",
        recovery_path="Admin money review and WS05 financial reconciliation.",
        downstream_owner="WS05",
    ),
    TransactionBoundaryPolicy(
        workflow="official_game_cancellation.refunds",
        service_function="backend.services.game_cancellation_service.create_official_cancellation_refunds",
        database_unit_of_work=("cancelled Game", "Booking/Payment/Refund/MoneyIssue rows"),
        external_effect="Stripe refund creation during official-game cancellation.",
        operation_class=ExternalOperationClass.RECONCILE_BEFORE_RETRY_MUTATION,
        provider_retry_contexts=("official_game_cancellation_refund",),
        required_pre_effect_checkpoint="Deterministic game/payment refund key plus refund record.",
        required_post_effect_recording=("Refund status", "MoneyIssue and notification rows"),
        timeout_or_unknown_outcome="Leave refund processing/issue state for reconciliation.",
        recovery_path="WS05 durable financial reconciliation.",
        downstream_owner="WS05",
    ),
    TransactionBoundaryPolicy(
        workflow="official_player_removal.refunds",
        service_function="backend.services.official_game_player_removal_service.execute_admin_removal_refunds",
        database_unit_of_work=("removed participant/booking state", "Payment/Refund/MoneyIssue rows"),
        external_effect="Stripe refund creation during official player removal.",
        operation_class=ExternalOperationClass.RECONCILE_BEFORE_RETRY_MUTATION,
        provider_retry_contexts=("official_player_removal_refund",),
        required_pre_effect_checkpoint="Deterministic booking/payment refund key plus refund record.",
        required_post_effect_recording=("Refund status", "MoneyIssue and notification rows"),
        timeout_or_unknown_outcome="Leave refund processing/issue state for reconciliation.",
        recovery_path="WS05 durable financial reconciliation.",
        downstream_owner="WS05",
    ),
    TransactionBoundaryPolicy(
        workflow="community_publish_financial_outcome.refund",
        service_function="backend.services.admin_financial_outcome_service.apply_refund_outcome",
        database_unit_of_work=("AdminFinancialOutcome", "Payment", "Refund", "MoneyIssue"),
        external_effect="Stripe refund creation from admin financial outcome.",
        operation_class=ExternalOperationClass.MANUAL_REPAIR_MUTATION,
        provider_retry_contexts=("community_publish_financial_outcome_refund",),
        required_pre_effect_checkpoint="Admin financial-outcome action key plus refund suffix.",
        required_post_effect_recording=("Refund status", "MoneyIssue state", "AdminAction metadata"),
        timeout_or_unknown_outcome="Manual repair remains state gated; no automatic replay.",
        recovery_path="Admin money review and WS05 financial reconciliation.",
        downstream_owner="WS05",
    ),
    TransactionBoundaryPolicy(
        workflow="saved_card.customer_create",
        service_function="backend.services.payment_method_service.ensure_stripe_customer_id",
        database_unit_of_work=("durable User row", "User.stripe_customer_id"),
        external_effect="Stripe Customer creation.",
        operation_class=ExternalOperationClass.IDEMPOTENT_PROVIDER_MUTATION,
        provider_retry_contexts=("saved_card_customer_creation",),
        required_pre_effect_checkpoint="Existing durable User identity derives the idempotency key.",
        required_post_effect_recording=("User.stripe_customer_id",),
        timeout_or_unknown_outcome="Stable user-scoped idempotency permits deliberate replay.",
        recovery_path="Saved-card setup can retry through the same durable user identity.",
    ),
    TransactionBoundaryPolicy(
        workflow="saved_card.setup_intent",
        service_function="backend.services.payment_method_service.create_saved_payment_method_setup_intent",
        database_unit_of_work=("durable User row",),
        external_effect="Stripe SetupIntent creation.",
        operation_class=ExternalOperationClass.RECONCILE_BEFORE_RETRY_MUTATION,
        provider_retry_contexts=("saved_card_setup_intent_creation",),
        required_pre_effect_checkpoint=(
            "Committed PaymentMethodOperation row with setup_create kind and "
            "provider idempotency identity before Stripe SetupIntent create."
        ),
        required_post_effect_recording=("returned client_secret only; no saved-card row yet",),
        timeout_or_unknown_outcome=(
            "PaymentMethodOperation identity is committed before provider create; "
            "unknown outcome is durable and blocks blind user replay."
        ),
        recovery_path="WS05 payment-method operation reconciliation reuses the durable setup identity.",
        downstream_owner="WS05",
    ),
    TransactionBoundaryPolicy(
        workflow="saved_card.setup_sync",
        service_function="backend.services.payment_method_service.sync_saved_payment_method",
        database_unit_of_work=("UserPaymentMethod row", "User default-card state"),
        external_effect="Stripe SetupIntent and PaymentMethod reads plus optional default-card mutation.",
        operation_class=ExternalOperationClass.RECONCILE_BEFORE_RETRY_MUTATION,
        provider_retry_contexts=(
            "saved_card_setup_sync",
            "saved_card_default_set",
        ),
        required_pre_effect_checkpoint="Provider setup result and durable user identity.",
        required_post_effect_recording=("UserPaymentMethod row", "default-card state when changed"),
        timeout_or_unknown_outcome="Safe reads can be retried; default mutation requires reconciliation.",
        recovery_path="Saved-card sync/default-card repair from durable local state.",
    ),
    TransactionBoundaryPolicy(
        workflow="saved_card.default_update",
        service_function="backend.services.payment_method_service.set_default_saved_payment_method",
        database_unit_of_work=("UserPaymentMethod default-card rows",),
        external_effect="Stripe Customer default payment method mutation.",
        operation_class=ExternalOperationClass.RECONCILE_BEFORE_RETRY_MUTATION,
        provider_retry_contexts=("saved_card_default_set",),
        required_pre_effect_checkpoint=(
            "Provider-verified active saved-card row, user customer identity, "
            "and PaymentMethodOperation idempotency identity."
        ),
        required_post_effect_recording=("local default-card state",),
        timeout_or_unknown_outcome=(
            "Provider-unknown operation blocks conflicting card mutations until "
            "durable reconciliation or support repair resolves it."
        ),
        recovery_path="Payment-method operation reconciliation and support repair.",
    ),
    TransactionBoundaryPolicy(
        workflow="saved_card.detach",
        service_function="backend.services.payment_method_service.detach_saved_payment_method",
        database_unit_of_work=("UserPaymentMethod row", "User default-card state"),
        external_effect=(
            "Stripe PaymentMethod detach plus a separate default set/clear mutation "
            "when the detached card was default."
        ),
        operation_class=ExternalOperationClass.RECONCILE_BEFORE_RETRY_MUTATION,
        provider_retry_contexts=(
            "user_visible_saved_card_detach",
            "saved_card_default_clear",
        ),
        required_pre_effect_checkpoint=(
            "Provider-verified saved-card row and PaymentMethodOperation "
            "idempotency identity; default repair uses its own operation identity."
        ),
        required_post_effect_recording=("UserPaymentMethod inactive state", "default-card state"),
        timeout_or_unknown_outcome=(
            "Provider-unknown detach or default-repair operation blocks conflicting "
            "card mutations until reconciliation/support resolves it."
        ),
        recovery_path="Saved-card operation repair and WS05 account cleanup recovery when applicable.",
        downstream_owner="WS05 when account cleanup owns the detach.",
    ),
    TransactionBoundaryPolicy(
        workflow="saved_card.unpersisted_cleanup",
        service_function="backend.services.payment_method_service.detach_unpersisted_payment_method",
        database_unit_of_work=("none; payment method was intentionally not persisted",),
        external_effect="Best-effort Stripe PaymentMethod detach after local duplicate/limit rejection.",
        operation_class=ExternalOperationClass.NO_AUTOMATIC_RETRY_MUTATION,
        provider_retry_contexts=("unpersisted_best_effort_payment_method_cleanup",),
        required_pre_effect_checkpoint="Provider PaymentMethod intentionally has no local saved-card row.",
        required_post_effect_recording=("No local saved-card state is created.",),
        timeout_or_unknown_outcome="Cleanup remains best effort; do not create local saved-card state.",
        recovery_path="No automatic replay; later provider cleanup remains support/provider owned.",
    ),
    TransactionBoundaryPolicy(
        workflow="auth.firebase_token_verify",
        service_function="backend.firebase_admin_client.verify_firebase_token",
        database_unit_of_work=("request authentication context",),
        external_effect="Firebase token verification read.",
        operation_class=ExternalOperationClass.PROVIDER_READ,
        provider_retry_contexts=("authenticated_request_identity",),
        required_pre_effect_checkpoint="Incoming request token only; no provider mutation.",
        required_post_effect_recording=("authenticated request identity or safe request rejection",),
        timeout_or_unknown_outcome="Safe read timeout returns dependency-read retry-later.",
        recovery_path="Client can retry authentication after provider-read recovery.",
    ),
    TransactionBoundaryPolicy(
        workflow="auth.firebase_app_check_verify",
        service_function="backend.firebase_admin_client.verify_firebase_app_check_token",
        database_unit_of_work=("request App Check context",),
        external_effect="Firebase App Check token verification read.",
        operation_class=ExternalOperationClass.PROVIDER_READ,
        provider_retry_contexts=("app_check_request_verification",),
        required_pre_effect_checkpoint="Incoming App Check token only; no provider mutation.",
        required_post_effect_recording=("verified App Check context or safe request rejection",),
        timeout_or_unknown_outcome="Safe read timeout returns provider-unavailable request failure.",
        recovery_path="Client can retry after provider-read recovery.",
    ),
    TransactionBoundaryPolicy(
        workflow="auth.firebase_user_lookup",
        service_function="backend.firebase_admin_client.verify_firebase_token",
        database_unit_of_work=("authenticated request identity lookup",),
        external_effect="Firebase user lookup during token verification.",
        operation_class=ExternalOperationClass.PROVIDER_READ,
        provider_retry_contexts=("authenticated_token_user_lookup",),
        required_pre_effect_checkpoint="Incoming request token only; no provider mutation.",
        required_post_effect_recording=("verified Firebase user identity or safe request rejection",),
        timeout_or_unknown_outcome="Safe read timeout returns dependency-read retry-later.",
        recovery_path="Client can retry authentication after provider-read recovery.",
    ),
    TransactionBoundaryPolicy(
        workflow="auth.email_availability_lookup",
        service_function="backend.services.auth_account_service.check_email_availability_workflow",
        database_unit_of_work=("local User email availability query",),
        external_effect="Firebase email existence lookup.",
        operation_class=ExternalOperationClass.PROVIDER_READ,
        provider_retry_contexts=("email_availability_lookup",),
        required_pre_effect_checkpoint="Normalized email and local availability check; no provider mutation.",
        required_post_effect_recording=("availability response only; no local state mutation",),
        timeout_or_unknown_outcome="Safe read timeout returns dependency-read retry-later.",
        recovery_path="Client can retry availability check after provider-read recovery.",
    ),
    TransactionBoundaryPolicy(
        workflow="account_deletion.saved_card_cleanup",
        service_function="backend.services.account_deletion_service.detach_account_saved_payment_methods",
        database_unit_of_work=("pending account deletion", "saved payment methods", "support flags"),
        external_effect="Stripe PaymentMethod detach during account deletion.",
        operation_class=ExternalOperationClass.RECONCILE_BEFORE_RETRY_MUTATION,
        provider_retry_contexts=("account_deletion_saved_card_cleanup",),
        required_pre_effect_checkpoint="Pending account-deletion cleanup state.",
        required_post_effect_recording=("saved-card cleanup state", "support flag on partial failure"),
        timeout_or_unknown_outcome="Pending deletion/support flags remain authoritative.",
        recovery_path="WS05 durable account cleanup recovery.",
        downstream_owner="WS05",
    ),
    TransactionBoundaryPolicy(
        workflow="account_deletion.firebase_delete",
        service_function="backend.services.account_deletion_service.delete_account_workflow",
        database_unit_of_work=("pending User deletion state", "support flags"),
        external_effect="Firebase user deletion.",
        operation_class=ExternalOperationClass.RECONCILE_BEFORE_RETRY_MUTATION,
        provider_retry_contexts=("account_deletion_auth_cleanup",),
        required_pre_effect_checkpoint="Pending deletion and support/recovery state.",
        required_post_effect_recording=("deleted local user state or support partial-failure flag",),
        timeout_or_unknown_outcome="Pending deletion/support flags remain authoritative.",
        recovery_path="WS05 durable account cleanup recovery.",
        downstream_owner="WS05",
    ),
    TransactionBoundaryPolicy(
        workflow="unfinished_account.firebase_cleanup",
        service_function="backend.services.auth_account_service.cleanup_unfinished_account_workflow",
        database_unit_of_work=("incomplete User row", "support partial-failure flag"),
        external_effect="Firebase user deletion for DELETE /auth/unfinished-account.",
        operation_class=ExternalOperationClass.RECONCILE_BEFORE_RETRY_MUTATION,
        provider_retry_contexts=("account_deletion_auth_cleanup",),
        required_pre_effect_checkpoint=(
            "Existing Firebase auth identity and incomplete local User row when present; "
            "current source records support follow-up if Firebase succeeds and the "
            "local delete commit fails."
        ),
        required_post_effect_recording=("hard-deleted incomplete user or support partial-failure flag",),
        timeout_or_unknown_outcome="Rollback local delete and propagate unknown Firebase outcome.",
        recovery_path="Duplicate cleanup reuses Firebase identity; support follows partial failures.",
        downstream_owner="WS05",
    ),
    TransactionBoundaryPolicy(
        workflow="r2.venue_image_metadata",
        service_function="backend.services.r2_storage_service.get_object_properties",
        database_unit_of_work=("VenueImage state that depends on uploaded object existence",),
        external_effect="R2 object metadata read.",
        operation_class=ExternalOperationClass.STORAGE_OBJECT_DEPENDENCY,
        provider_retry_contexts=("venue_image_metadata_verification",),
        required_pre_effect_checkpoint="Existing upload intent and object key.",
        required_post_effect_recording=("venue-image state remains local source of truth",),
        timeout_or_unknown_outcome="Metadata read failure stays bounded; no provider mutation replay.",
        recovery_path="Venue image repair/retry under later storage passes.",
        downstream_owner="WS06",
    ),
    TransactionBoundaryPolicy(
        workflow="notifications.local_rows",
        service_function="backend.services.notification_service.create_notification_workflow",
        database_unit_of_work=("Notification rows", "Inbox-visible state"),
        external_effect="User-visible in-app notification state.",
        operation_class=ExternalOperationClass.USER_VISIBLE_LOCAL_EFFECT,
        provider_retry_contexts=(),
        required_pre_effect_checkpoint="The committed Notification row is the visible effect.",
        required_post_effect_recording=("Notification row committed before visible success is claimed",),
        timeout_or_unknown_outcome="Not applicable - external delivery is not current source behavior.",
        recovery_path="Future external delivery belongs to WS05.",
        downstream_owner="WS05",
    ),
    TransactionBoundaryPolicy(
        workflow="platform_notice.publish",
        service_function="backend.services.platform_notice_service.create_platform_notice",
        database_unit_of_work=("PlatformNotice", "selected recipient notification rows"),
        external_effect="Admin-visible publish and user-visible in-app notice rows.",
        operation_class=ExternalOperationClass.ADMIN_VISIBLE_LOCAL_EFFECT,
        provider_retry_contexts=(),
        required_pre_effect_checkpoint="Committed notice/recipient rows are the visible effect.",
        required_post_effect_recording=("published PlatformNotice", "recipient notification rows"),
        timeout_or_unknown_outcome="Not applicable - no external provider delivery today.",
        recovery_path="Future external platform notice delivery belongs to WS05.",
        downstream_owner="WS05",
    ),
    TransactionBoundaryPolicy(
        workflow="support.local_flags",
        service_function="backend.services.support_flag_service.stage_support_flag",
        database_unit_of_work=("SupportFlag rows",),
        external_effect="Support/admin-visible operational state.",
        operation_class=ExternalOperationClass.ADMIN_VISIBLE_LOCAL_EFFECT,
        provider_retry_contexts=(),
        required_pre_effect_checkpoint="Committed local support row is the visible effect.",
        required_post_effect_recording=("SupportFlag row committed",),
        timeout_or_unknown_outcome="Not applicable for pure local operational effects.",
        recovery_path="Committed local operational state is the source of truth.",
    ),
    TransactionBoundaryPolicy(
        workflow="admin.local_actions",
        service_function="backend.services.admin_action_service.record_admin_action",
        database_unit_of_work=("AdminAction rows",),
        external_effect="Admin-visible operational state.",
        operation_class=ExternalOperationClass.ADMIN_VISIBLE_LOCAL_EFFECT,
        provider_retry_contexts=(),
        required_pre_effect_checkpoint="Committed local admin row is the visible effect.",
        required_post_effect_recording=("AdminAction row committed",),
        timeout_or_unknown_outcome="Not applicable for pure local operational effects.",
        recovery_path="Committed local operational state is the source of truth.",
    ),
)


def policies_by_workflow(workflow: str) -> tuple[TransactionBoundaryPolicy, ...]:
    return tuple(
        policy for policy in TRANSACTION_BOUNDARY_POLICIES if policy.workflow == workflow
    )


def policy_by_workflow(workflow: str) -> TransactionBoundaryPolicy:
    matches = policies_by_workflow(workflow)
    if not matches:
        raise KeyError(workflow)
    if len(matches) > 1:
        raise ValueError(f"workflow {workflow!r} has multiple boundary policies")
    return matches[0]


def provider_retry_contexts() -> frozenset[str]:
    return frozenset(
        context
        for policy in TRANSACTION_BOUNDARY_POLICIES
        for context in policy.provider_retry_contexts
    )
