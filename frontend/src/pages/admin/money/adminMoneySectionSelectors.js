import { shortId } from './adminMoneyFormatters.js'

export function getDisplayContext(record) {
  const display = record?.display
  return record?.context_label
    || display?.context_label
    || display?.game_label
    || display?.user_email
    || display?.user_name
    || 'No context label'
}

export function getUserName(user) {
  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(' ')
  return fullName || user?.email || 'User'
}

export function getPaymentRefundLabel(payment) {
  if (payment?.is_fully_refunded) {
    return 'Fully refunded'
  }

  return 'Not fully refunded'
}

export function getPaymentRefundSummary(payment) {
  return getPaymentRefundLabel(payment)
}

export function getRefundRowTarget(refund, showIssueContext) {
  if (showIssueContext) {
    return getDisplayContext(refund)
  }

  return refund?.payment_id
    ? `Payment ${shortId(refund.payment_id)}`
    : getDisplayContext(refund)
}

export function getIssueTargetLabel(issue) {
  const target = [
    ['Payment', issue?.target_payment_id],
    ['Refund', issue?.target_refund_id],
    ['Credit', issue?.target_game_credit_id],
    ['Usage', issue?.target_credit_usage_id],
  ].find(([, value]) => Boolean(value))

  if (!target) {
    return 'No target'
  }

  return `${target[0]} ${shortId(target[1])}`
}
