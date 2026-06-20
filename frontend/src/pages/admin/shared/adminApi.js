import { apiRequest } from '../../../lib/apiClient.js'

export async function getAdminHeaders(firebaseUser, includeJson = false) {
  if (!firebaseUser) {
    throw new Error('Sign in with an authorized staff account.')
  }

  const token = await firebaseUser.getIdToken()
  return {
    Authorization: `Bearer ${token}`,
    ...(includeJson ? { 'Content-Type': 'application/json' } : {}),
  }
}

export async function fetchAdminMe({ firebaseUser, forceRefresh = false }) {
  if (!firebaseUser) {
    return null
  }

  const token = await firebaseUser.getIdToken(forceRefresh)

  try {
    return await apiRequest('/admin/me', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
  } catch (error) {
    if (!forceRefresh && error?.status === 401) {
      return fetchAdminMe({ firebaseUser, forceRefresh: true })
    }

    throw error
  }
}

export async function fetchAdminActionCenter({ firebaseUser }) {
  return apiRequest('/admin/action-center', {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function listAdminActions({
  actionType = '',
  firebaseUser,
  limit = 100,
  targetGameId = '',
} = {}) {
  const searchParams = new URLSearchParams()

  if (actionType.trim()) {
    searchParams.set('action_type', actionType.trim())
  }

  if (String(targetGameId).trim()) {
    searchParams.set('target_game_id', String(targetGameId).trim())
  }

  searchParams.set('limit', String(limit))

  return apiRequest(`/admin/actions?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function getAdminAction({ adminActionId, firebaseUser }) {
  return apiRequest(`/admin/actions/${adminActionId}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function getAdminMoneyPayment({ firebaseUser, paymentId }) {
  return apiRequest(`/admin/money/payments/${paymentId}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function listAdminMoneyPayments({
  bookingId = '',
  firebaseUser,
  gameId = '',
  limit = 100,
  paymentStatus = 'all',
  userId = '',
} = {}) {
  const searchParams = new URLSearchParams()

  if (String(userId).trim()) {
    searchParams.set('user_id', String(userId).trim())
  }
  if (String(bookingId).trim()) {
    searchParams.set('booking_id', String(bookingId).trim())
  }
  if (String(gameId).trim()) {
    searchParams.set('game_id', String(gameId).trim())
  }

  searchParams.set('payment_status', paymentStatus)
  searchParams.set('limit', String(limit))

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
  bookingId = '',
  firebaseUser,
  gameId = '',
  limit = 100,
  paymentId = '',
  refundStatus = 'all',
  userId = '',
} = {}) {
  const searchParams = new URLSearchParams()

  if (String(userId).trim()) {
    searchParams.set('user_id', String(userId).trim())
  }
  if (String(bookingId).trim()) {
    searchParams.set('booking_id', String(bookingId).trim())
  }
  if (String(gameId).trim()) {
    searchParams.set('game_id', String(gameId).trim())
  }
  if (String(paymentId).trim()) {
    searchParams.set('payment_id', String(paymentId).trim())
  }

  searchParams.set('refund_status', refundStatus)
  searchParams.set('limit', String(limit))

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

export async function listAdminMoneyCredits({
  creditStatus = 'all',
  firebaseUser,
  limit = 100,
  sourceBookingId = '',
  sourceGameId = '',
  sourcePaymentId = '',
  userId = '',
} = {}) {
  const searchParams = new URLSearchParams()

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

  return apiRequest(`/admin/money/credits?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function getAdminMoneyCredit({ creditId, firebaseUser }) {
  return apiRequest(`/admin/money/credits/${creditId}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function listAdminMoneyPaymentMethods({
  firebaseUser,
  includeInactive = false,
  userId,
} = {}) {
  const searchParams = new URLSearchParams()
  searchParams.set('user_id', String(userId || '').trim())
  searchParams.set('include_inactive', includeInactive ? 'true' : 'false')

  return apiRequest(`/admin/money/payment-methods?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function getAdminMoneyUser({
  firebaseUser,
  includeInactivePaymentMethods = false,
  limit = 100,
  userId,
} = {}) {
  const searchParams = new URLSearchParams()
  searchParams.set(
    'include_inactive_payment_methods',
    includeInactivePaymentMethods ? 'true' : 'false',
  )
  searchParams.set('limit', String(limit))

  return apiRequest(`/admin/money/users/${userId}?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function listAdminMoneySupportFlags({
  firebaseUser,
  flagStatus = 'open',
  limit = 100,
} = {}) {
  const searchParams = new URLSearchParams()
  searchParams.set('flag_status', flagStatus)
  searchParams.set('limit', String(limit))

  return apiRequest(`/admin/money/support-flags?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function getAdminMoneySupportFlag({ firebaseUser, supportFlagId }) {
  return apiRequest(`/admin/money/support-flags/${supportFlagId}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function resolveAdminMoneySupportFlag({
  firebaseUser,
  outcome,
  reason,
  supportFlagId,
}) {
  return apiRequest(`/admin/money/support-flags/${supportFlagId}/resolve`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      outcome,
      reason,
    }),
  })
}
