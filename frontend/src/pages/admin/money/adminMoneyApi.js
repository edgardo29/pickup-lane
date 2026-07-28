import { apiRequest } from '../../../lib/apiClient.js'
import { getAdminHeaders } from '../shared/adminApi.js'

export async function getAdminMoneyPayment({ firebaseUser, paymentId }) {
  return apiRequest(`/admin/money/payments/${paymentId}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function listAdminMoneyPayments({
  cursor = '',
  firebaseUser,
  limit = 50,
  paymentType = '',
  paymentStatus = 'all',
  query = '',
  userId = '',
} = {}) {
  const searchParams = new URLSearchParams()

  if (String(query).trim()) {
    searchParams.set('q', String(query).trim())
  }
  if (String(userId).trim()) {
    searchParams.set('user_id', String(userId).trim())
  }
  if (String(paymentType).trim()) {
    searchParams.set('payment_type', String(paymentType).trim())
  }

  searchParams.set('payment_status', paymentStatus)
  searchParams.set('limit', String(limit))
  if (String(cursor).trim()) {
    searchParams.set('cursor', String(cursor).trim())
  }

  return apiRequest(`/admin/money/payments?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function getAdminMoneyRefund({ firebaseUser, refundId }) {
  return apiRequest(`/admin/money/refunds/${refundId}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function listAdminMoneyRefunds({
  cursor = '',
  firebaseUser,
  limit = 50,
  paymentId = '',
  query = '',
  refundStatus = 'all',
  userId = '',
} = {}) {
  const searchParams = new URLSearchParams()

  if (String(query).trim()) {
    searchParams.set('q', String(query).trim())
  }
  if (String(userId).trim()) {
    searchParams.set('user_id', String(userId).trim())
  }
  if (String(paymentId).trim()) {
    searchParams.set('payment_id', String(paymentId).trim())
  }

  searchParams.set('refund_status', refundStatus)
  searchParams.set('limit', String(limit))
  if (String(cursor).trim()) {
    searchParams.set('cursor', String(cursor).trim())
  }

  return apiRequest(`/admin/money/refunds?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function retryAdminMoneyRefund({
  firebaseUser,
  idempotencyKey,
  reason,
  refundId,
}) {
  return apiRequest(`/admin/money/refunds/${refundId}/retry`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      reason,
      idempotency_key: idempotencyKey,
    }),
  })
}

export async function reconcileAdminMoneyRefund({
  firebaseUser,
  idempotencyKey,
  reason,
  refundId,
}) {
  return apiRequest(`/admin/money/refunds/${refundId}/reconcile`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      reason,
      idempotency_key: idempotencyKey,
    }),
  })
}

export async function listAdminMoneyRefundEvents({
  cursor = '',
  eventSource = '',
  eventType = '',
  firebaseUser,
  limit = 50,
  refundId,
}) {
  const searchParams = new URLSearchParams()
  if (String(eventType).trim()) {
    searchParams.set('event_type', String(eventType).trim())
  }
  if (String(eventSource).trim()) {
    searchParams.set('event_source', String(eventSource).trim())
  }
  searchParams.set('limit', String(limit))
  if (String(cursor).trim()) {
    searchParams.set('cursor', String(cursor).trim())
  }

  return apiRequest(`/admin/money/refunds/${refundId}/events?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function listAdminMoneyCredits({
  creditStatus = 'all',
  cursor = '',
  firebaseUser,
  limit = 50,
  query = '',
  sourceBookingId = '',
  sourceGameId = '',
  sourcePaymentId = '',
  userId = '',
} = {}) {
  const searchParams = new URLSearchParams()

  if (String(query).trim()) {
    searchParams.set('q', String(query).trim())
  }
  if (String(userId).trim()) {
    searchParams.set('user_id', String(userId).trim())
  }
  if (String(sourceGameId).trim()) {
    searchParams.set('source_game_id', String(sourceGameId).trim())
  }
  if (String(sourceBookingId).trim()) {
    searchParams.set('source_booking_id', String(sourceBookingId).trim())
  }
  if (String(sourcePaymentId).trim()) {
    searchParams.set('source_payment_id', String(sourcePaymentId).trim())
  }

  searchParams.set('credit_status', creditStatus)
  searchParams.set('limit', String(limit))
  if (String(cursor).trim()) {
    searchParams.set('cursor', String(cursor).trim())
  }

  return apiRequest(`/admin/money/credits?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function getAdminMoneyCredit({ creditId, firebaseUser }) {
  return apiRequest(`/admin/money/credits/${creditId}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function getAdminMoneyUser({
  firebaseUser,
  includeInactivePaymentMethods = false,
  savedCardsCursor = '',
  userId,
} = {}) {
  const searchParams = new URLSearchParams()
  searchParams.set(
    'include_inactive_payment_methods',
    includeInactivePaymentMethods ? 'true' : 'false',
  )
  if (String(savedCardsCursor).trim()) {
    searchParams.set('saved_cards_cursor', String(savedCardsCursor).trim())
  }

  return apiRequest(`/admin/money/users/${userId}?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function listAdminMoneyIssues({
  cursor = '',
  firebaseUser,
  issueStatus = 'open',
  issueType = '',
  limit = 50,
  query = '',
  userId = '',
} = {}) {
  const searchParams = new URLSearchParams()
  searchParams.set('status', issueStatus)
  if (String(query).trim()) {
    searchParams.set('q', String(query).trim())
  }
  if (String(issueType).trim()) {
    searchParams.set('issue_type', String(issueType).trim())
  }
  if (String(userId).trim()) {
    searchParams.set('user_id', String(userId).trim())
  }
  searchParams.set('limit', String(limit))
  if (String(cursor).trim()) {
    searchParams.set('cursor', String(cursor).trim())
  }

  return apiRequest(`/admin/money/issues?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function getAdminMoneyIssue({ firebaseUser, moneyIssueId }) {
  return apiRequest(`/admin/money/issues/${moneyIssueId}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function resolveAdminMoneyIssue({
  firebaseUser,
  idempotencyKey,
  reason,
  resolutionExternalReference = '',
  resolutionReasonCode,
  moneyIssueId,
}) {
  return apiRequest(`/admin/money/issues/${moneyIssueId}/resolve`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      idempotency_key: idempotencyKey,
      resolution_reason_code: resolutionReasonCode,
      resolution_note: reason,
      resolution_external_reference: resolutionExternalReference || null,
    }),
  })
}

export async function retryAdminMoneyIssueCredit({
  firebaseUser,
  idempotencyKey,
  moneyIssueId,
  reason,
}) {
  return apiRequest(`/admin/money/issues/${moneyIssueId}/retry-credit`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      idempotency_key: idempotencyKey,
      reason,
    }),
  })
}
