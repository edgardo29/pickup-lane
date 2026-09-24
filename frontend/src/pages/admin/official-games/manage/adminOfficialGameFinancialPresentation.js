const cancellationCategoryLabels = {
  cancel_only: 'Cancel only',
  credit_restore: 'Restore credit',
  credit_restored: 'Credit restored',
  follow_up_required: 'Follow-up required',
  pending_hold_release: 'Release pending hold',
  pending_hold_released: 'Pending hold released',
  stripe_refund: 'Refund cash',
  stripe_refund_and_credit_restore: 'Refund cash + restore credit',
  stripe_refunded: 'Cash refunded',
  stripe_refunded_and_credit_restored: 'Cash refunded + credit restored',
}

const cancellationFollowUpLabels = {
  active_refund: 'Active refund',
  existing_or_disputed_refund_state: 'Existing refund state',
  missing_stripe_charge_id: 'Missing Stripe charge',
  payment_state_follow_up: 'Payment state follow-up',
  processing_payment: 'Processing payment',
  stripe_refund_failed: 'Stripe refund failed',
  stripe_refund_processing: 'Stripe refund processing',
  stripe_refund_queued: 'Stripe refund queued',
}

export function getCancellationCategoryLabel(category) {
  return cancellationCategoryLabels[category] || category || 'Review'
}

export function getCancellationFollowUpLabel(reason) {
  return cancellationFollowUpLabels[reason] || reason || ''
}

export function getRemovalRefundLabel(refundStatus) {
  return refundStatus === 'approved' ? 'Stripe refund queued' : 'Stripe refund'
}

export function getRemovalRefundCountLabel() {
  return 'Refunds queued'
}

export function CancellationFollowUpLabel({ reason }) {
  return createElement('span', null, getCancellationFollowUpLabel(reason))
}

export function RemovalRefundLabel({ refundStatus }) {
  return createElement('small', null, getRemovalRefundLabel(refundStatus))
}
import { createElement } from 'react'
