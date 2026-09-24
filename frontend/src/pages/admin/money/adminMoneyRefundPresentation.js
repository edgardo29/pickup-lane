import { createElement } from 'react'

import { formatStatus } from './adminMoneyFormatters.js'

export function formatRefundDurableDiagnostic(diagnostic) {
  if (!diagnostic) {
    return ''
  }

  return `${formatStatus(diagnostic.status)} · attempt ${diagnostic.refund_attempt_number} · ${formatStatus(diagnostic.error_code)}`
}

export function RefundDurableDiagnostic({ diagnostic }) {
  const value = formatRefundDurableDiagnostic(diagnostic)
  return value ? createElement('span', null, value) : null
}

export function RefundDurableListIndicator({ refund }) {
  const diagnostic = refund?.durable_job_diagnostic
  const value = formatRefundDurableDiagnostic(diagnostic)
  return value
    ? createElement('span', null, `Fulfillment: ${value}`)
    : null
}
