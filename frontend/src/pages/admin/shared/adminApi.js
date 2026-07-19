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

export async function listAdminReviewCases({
  caseCategory = '',
  caseStatus = 'open',
  cursor = '',
  firebaseUser,
  limit = 50,
  offset = 0,
  targetType = 'content_targets',
} = {}) {
  const searchParams = new URLSearchParams()
  if (caseStatus) {
    searchParams.set('case_status', caseStatus)
  }
  if (caseCategory) {
    searchParams.set('case_category', caseCategory)
  }
  if (targetType) {
    searchParams.set('target_type', targetType)
  }
  if (cursor) {
    searchParams.set('cursor', cursor)
  } else {
    searchParams.set('offset', String(offset))
  }
  searchParams.set('limit', String(limit))

  return apiRequest(`/admin/review-cases?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function getAdminReviewCase({ firebaseUser, reviewCaseId }) {
  return apiRequest(`/admin/review-cases/${reviewCaseId}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function addAdminReviewCaseNote({
  body,
  firebaseUser,
  idempotencyKey,
  reviewCaseId,
}) {
  return apiRequest(`/admin/review-cases/${reviewCaseId}/notes`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      body,
      idempotency_key: idempotencyKey,
    }),
  })
}

export async function closeAdminReviewCase({
  firebaseUser,
  idempotencyKey,
  outcome,
  reason,
  reviewCaseId,
}) {
  return apiRequest(`/admin/review-cases/${reviewCaseId}/close`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      outcome,
      reason,
      idempotency_key: idempotencyKey,
    }),
  })
}

export async function listAdminCommunityGames({
  cursor = '',
  firebaseUser,
  limit = 50,
  offset = 0,
  publishStatus = '',
  query = '',
  view = 'active',
} = {}) {
  const searchParams = new URLSearchParams()

  if (query.trim()) {
    searchParams.set('query', query.trim())
  }
  if (view) {
    searchParams.set('view', view)
  }
  if (publishStatus) {
    searchParams.set('publish_status', publishStatus)
  }

  searchParams.set('limit', String(limit))
  if (cursor) {
    searchParams.set('cursor', cursor)
  } else {
    searchParams.set('offset', String(offset))
  }

  return apiRequest(`/admin/community-games?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function getAdminCommunityGame({
  auditLimit = 50,
  auditOffset = 0,
  firebaseUser,
  gameId,
  supportFlagLimit = 50,
  supportFlagOffset = 0,
} = {}) {
  const searchParams = new URLSearchParams()
  searchParams.set('support_flag_offset', String(supportFlagOffset))
  searchParams.set('support_flag_limit', String(supportFlagLimit))
  searchParams.set('audit_offset', String(auditOffset))
  searchParams.set('audit_limit', String(auditLimit))

  return apiRequest(`/admin/community-games/${gameId}?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function hideAdminCommunityGamePaymentText({
  firebaseUser,
  gameId,
  idempotencyKey,
  reason,
} = {}) {
  return apiRequest(`/admin/community-games/${gameId}/hide-payment-text`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      reason,
      idempotency_key: idempotencyKey,
    }),
  })
}

export async function restoreAdminCommunityGamePaymentText({
  firebaseUser,
  gameId,
  idempotencyKey,
  reason,
} = {}) {
  return apiRequest(`/admin/community-games/${gameId}/restore-payment-text`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      reason,
      idempotency_key: idempotencyKey,
    }),
  })
}

async function performAdminCommunityGameAction({
  action,
  firebaseUser,
  gameId,
  idempotencyKey,
  reason,
} = {}) {
  return apiRequest(`/admin/community-games/${gameId}/${action}`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      reason,
      idempotency_key: idempotencyKey,
    }),
  })
}

export async function hideAdminCommunityGame({
  firebaseUser,
  gameId,
  idempotencyKey,
  reason,
} = {}) {
  return performAdminCommunityGameAction({
    action: 'hide',
    firebaseUser,
    gameId,
    idempotencyKey,
    reason,
  })
}

export async function restoreAdminCommunityGame({
  firebaseUser,
  gameId,
  idempotencyKey,
  reason,
} = {}) {
  return performAdminCommunityGameAction({
    action: 'restore',
    firebaseUser,
    gameId,
    idempotencyKey,
    reason,
  })
}

export async function pauseAdminCommunityGameJoining({
  firebaseUser,
  gameId,
  idempotencyKey,
  reason,
} = {}) {
  return performAdminCommunityGameAction({
    action: 'pause-joining',
    firebaseUser,
    gameId,
    idempotencyKey,
    reason,
  })
}

export async function resumeAdminCommunityGameJoining({
  firebaseUser,
  gameId,
  idempotencyKey,
  reason,
} = {}) {
  return performAdminCommunityGameAction({
    action: 'resume-joining',
    firebaseUser,
    gameId,
    idempotencyKey,
    reason,
  })
}

export async function cancelAdminCommunityGame({
  firebaseUser,
  gameId,
  idempotencyKey,
  reason,
} = {}) {
  return performAdminCommunityGameAction({
    action: 'cancel',
    firebaseUser,
    gameId,
    idempotencyKey,
    reason,
  })
}

export async function flagAdminCommunityGameForReview({
  firebaseUser,
  gameId,
  idempotencyKey,
  reason,
} = {}) {
  return apiRequest(`/admin/community-games/${gameId}/flag-for-review`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      reason,
      idempotency_key: idempotencyKey,
    }),
  })
}

export async function resolveAdminSupportFlag({
  firebaseUser,
  idempotencyKey,
  outcome,
  reason,
  supportFlagId,
} = {}) {
  return apiRequest(`/admin/support-flags/${supportFlagId}/resolve`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      idempotency_key: idempotencyKey,
      outcome,
      reason,
    }),
  })
}

export async function listAdminNeedASubPosts({
  cursor = '',
  firebaseUser,
  limit = 50,
  offset = 0,
  query = '',
  view = 'active',
} = {}) {
  const searchParams = new URLSearchParams()
  if (query.trim()) {
    searchParams.set('query', query.trim())
  }
  if (view) {
    searchParams.set('view', view)
  }
  if (cursor) {
    searchParams.set('cursor', cursor)
  } else {
    searchParams.set('offset', String(offset))
  }
  searchParams.set('limit', String(limit))

  return apiRequest(`/admin/need-a-sub?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function getAdminNeedASubPost({
  auditLimit = 50,
  auditOffset = 0,
  firebaseUser,
  postId,
  requestLimit = 50,
  requestOffset = 0,
} = {}) {
  const searchParams = new URLSearchParams()
  searchParams.set('request_offset', String(requestOffset))
  searchParams.set('request_limit', String(requestLimit))
  searchParams.set('audit_offset', String(auditOffset))
  searchParams.set('audit_limit', String(auditLimit))

  return apiRequest(`/admin/need-a-sub/${postId}?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function getAdminNeedASubRequest({
  firebaseUser,
  requestId,
} = {}) {
  return apiRequest(`/admin/need-a-sub/requests/${requestId}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function removeAdminNeedASubPost({
  firebaseUser,
  idempotencyKey,
  postId,
  reason,
} = {}) {
  return apiRequest(`/admin/need-a-sub/${postId}/remove`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      reason,
      idempotency_key: idempotencyKey,
    }),
  })
}

async function performAdminNeedASubPostAction({
  action,
  firebaseUser,
  idempotencyKey,
  postId,
  reason,
} = {}) {
  return apiRequest(`/admin/need-a-sub/${postId}/${action}`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      reason,
      idempotency_key: idempotencyKey,
    }),
  })
}

export async function hideAdminNeedASubPost({
  firebaseUser,
  idempotencyKey,
  postId,
  reason,
} = {}) {
  return performAdminNeedASubPostAction({
    action: 'hide',
    firebaseUser,
    idempotencyKey,
    postId,
    reason,
  })
}

export async function restoreAdminNeedASubPost({
  firebaseUser,
  idempotencyKey,
  postId,
  reason,
} = {}) {
  return performAdminNeedASubPostAction({
    action: 'restore',
    firebaseUser,
    idempotencyKey,
    postId,
    reason,
  })
}

export async function getAdminOfficialGameChatSummary({
  firebaseUser,
  gameId,
} = {}) {
  return apiRequest(`/admin/official-games/${gameId}/chat/summary`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function getAdminCommunityGameChatSummary({
  firebaseUser,
  gameId,
} = {}) {
  return apiRequest(`/admin/community-games/${gameId}/chat/summary`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function getAdminNeedASubChatSummary({
  firebaseUser,
  postId,
} = {}) {
  return apiRequest(`/admin/need-a-sub/${postId}/chat/summary`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

async function listAdminScopedChatMessages({
  endpointBase,
  firebaseUser,
  limit = 20,
  offset = 0,
  view = 'needs_review',
} = {}) {
  const searchParams = new URLSearchParams()
  searchParams.set('view', view)
  searchParams.set('offset', String(offset))
  searchParams.set('limit', String(limit))

  return apiRequest(`${endpointBase}/messages?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function listAdminOfficialGameChatModerationMessages({
  firebaseUser,
  gameId,
  limit,
  offset,
  view,
} = {}) {
  return listAdminScopedChatMessages({
    endpointBase: `/admin/official-games/${gameId}/chat`,
    firebaseUser,
    limit,
    offset,
    view,
  })
}

export async function listAdminCommunityGameChatModerationMessages({
  firebaseUser,
  gameId,
  limit,
  offset,
  view,
} = {}) {
  return listAdminScopedChatMessages({
    endpointBase: `/admin/community-games/${gameId}/chat`,
    firebaseUser,
    limit,
    offset,
    view,
  })
}

export async function listAdminNeedASubChatModerationMessages({
  firebaseUser,
  limit,
  offset,
  postId,
  view,
} = {}) {
  return listAdminScopedChatMessages({
    endpointBase: `/admin/need-a-sub/${postId}/chat`,
    firebaseUser,
    limit,
    offset,
    view,
  })
}

async function moderateAdminScopedChatMessage({
  action,
  endpointBase,
  firebaseUser,
  idempotencyKey,
  messageId,
  reason,
} = {}) {
  return apiRequest(`${endpointBase}/messages/${messageId}/${action}`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      ...(reason ? { reason } : {}),
      idempotency_key: idempotencyKey,
    }),
  })
}

export async function moderateAdminOfficialGameChatMessage({
  action,
  firebaseUser,
  gameId,
  idempotencyKey,
  messageId,
  reason,
} = {}) {
  return moderateAdminScopedChatMessage({
    action,
    endpointBase: `/admin/official-games/${gameId}/chat`,
    firebaseUser,
    idempotencyKey,
    messageId,
    reason,
  })
}

export async function moderateAdminCommunityGameChatMessage({
  action,
  firebaseUser,
  gameId,
  idempotencyKey,
  messageId,
  reason,
} = {}) {
  return moderateAdminScopedChatMessage({
    action,
    endpointBase: `/admin/community-games/${gameId}/chat`,
    firebaseUser,
    idempotencyKey,
    messageId,
    reason,
  })
}

export async function moderateAdminNeedASubChatMessage({
  action,
  firebaseUser,
  idempotencyKey,
  messageId,
  postId,
  reason,
} = {}) {
  return moderateAdminScopedChatMessage({
    action,
    endpointBase: `/admin/need-a-sub/${postId}/chat`,
    firebaseUser,
    idempotencyKey,
    messageId,
    reason,
  })
}

const adminNotificationFilterParams = [
  'user_id',
  'notification_type',
  'notification_category',
  'notification_domain',
  'source_type',
  'is_read',
  'action_key',
  'aggregation_key',
  'related_game_id',
  'related_chat_id',
  'related_booking_id',
  'related_payment_id',
  'related_refund_id',
  'related_participant_id',
  'related_message_id',
  'related_sub_post_id',
  'related_sub_post_chat_id',
  'related_sub_post_chat_message_id',
  'related_sub_post_request_id',
  'related_sub_post_position_id',
]

export async function listAdminNotifications({
  firebaseUser,
  filters = {},
  limit = 50,
  offset = 0,
} = {}) {
  const searchParams = new URLSearchParams()

  adminNotificationFilterParams.forEach((param) => {
    const value = filters[param]
    const normalizedValue = String(value ?? '').trim()
    if (normalizedValue) {
      searchParams.set(param, normalizedValue)
    }
  })

  searchParams.set('offset', String(offset))
  searchParams.set('limit', String(limit))

  return apiRequest(`/admin/notifications?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function getAdminNotification({ firebaseUser, notificationId }) {
  return apiRequest(`/admin/notifications/${notificationId}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function listPlatformNoticeCampaigns({
  audienceType = '',
  campaignStatus = '',
  deliveryClass = '',
  firebaseUser,
  limit = 50,
  offset = 0,
  search = '',
} = {}) {
  const searchParams = new URLSearchParams()

  if (campaignStatus) {
    searchParams.set('campaign_status', campaignStatus)
  }
  if (audienceType) {
    searchParams.set('audience_type', audienceType)
  }
  if (deliveryClass) {
    searchParams.set('delivery_class', deliveryClass)
  }
  if (search.trim()) {
    searchParams.set('search', search.trim())
  }
  searchParams.set('offset', String(offset))
  searchParams.set('limit', String(limit))

  return apiRequest(`/admin/platform-notice-campaigns?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function getPlatformNoticeCampaign({ campaignId, firebaseUser }) {
  return apiRequest(`/admin/platform-notice-campaigns/${campaignId}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function createPlatformNoticeCampaign({
  firebaseUser,
  payload,
}) {
  return apiRequest('/admin/platform-notice-campaigns', {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify(payload),
  })
}

export async function updatePlatformNoticeCampaign({
  campaignId,
  firebaseUser,
  payload,
}) {
  return apiRequest(`/admin/platform-notice-campaigns/${campaignId}`, {
    method: 'PATCH',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify(payload),
  })
}

export async function sendPlatformNoticeCampaign({
  campaignId,
  firebaseUser,
  idempotencyKey,
}) {
  return apiRequest(`/admin/platform-notice-campaigns/${campaignId}/send`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({ idempotency_key: idempotencyKey }),
  })
}

export async function retryFailedPlatformNoticeCampaign({
  campaignId,
  firebaseUser,
  idempotencyKey,
}) {
  return apiRequest(`/admin/platform-notice-campaigns/${campaignId}/retry-failed`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({ idempotency_key: idempotencyKey }),
  })
}

export async function listPlatformNoticeCampaignDeliveries({
  campaignId,
  deliveryStatus = '',
  firebaseUser,
  limit = 50,
  offset = 0,
}) {
  const searchParams = new URLSearchParams()
  if (deliveryStatus) {
    searchParams.set('delivery_status', deliveryStatus)
  }
  searchParams.set('offset', String(offset))
  searchParams.set('limit', String(limit))

  return apiRequest(
    `/admin/platform-notice-campaigns/${campaignId}/deliveries?${searchParams.toString()}`,
    { headers: await getAdminHeaders(firebaseUser) },
  )
}

export async function listPlatformNoticeCampaignAttempts({
  attemptStatus = '',
  attemptType = '',
  campaignId,
  firebaseUser,
  limit = 50,
  offset = 0,
}) {
  const searchParams = new URLSearchParams()
  if (attemptType) {
    searchParams.set('attempt_type', attemptType)
  }
  if (attemptStatus) {
    searchParams.set('attempt_status', attemptStatus)
  }
  searchParams.set('offset', String(offset))
  searchParams.set('limit', String(limit))

  return apiRequest(
    `/admin/platform-notice-campaigns/${campaignId}/attempts?${searchParams.toString()}`,
    { headers: await getAdminHeaders(firebaseUser) },
  )
}

export async function listAdminUsers({
  accountStatus = '',
  firebaseUser,
  hostingStatus = '',
  includeDeleted = false,
  limit = 100,
  query = '',
  role = '',
} = {}) {
  const searchParams = new URLSearchParams()

  if (query.trim()) {
    searchParams.set('query', query.trim())
  }
  if (accountStatus) {
    searchParams.set('account_status', accountStatus)
  }
  if (hostingStatus) {
    searchParams.set('hosting_status', hostingStatus)
  }
  if (role) {
    searchParams.set('role', role)
  }

  searchParams.set('include_deleted', includeDeleted ? 'true' : 'false')
  searchParams.set('limit', String(limit))

  return apiRequest(`/admin/users?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function listAdminStaff({
  firebaseUser,
  includeDeleted = false,
  limit = 100,
} = {}) {
  const searchParams = new URLSearchParams()
  searchParams.set('include_deleted', includeDeleted ? 'true' : 'false')
  searchParams.set('limit', String(limit))

  return apiRequest(`/admin/users/staff?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function changeAdminUserStaffRole({
  firebaseUser,
  idempotencyKey,
  reason,
  role,
  userId,
} = {}) {
  return apiRequest(`/admin/users/${userId}/staff-role`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      role,
      reason,
      idempotency_key: idempotencyKey,
    }),
  })
}

export async function getAdminUser({
  firebaseUser,
  limit = 50,
  userId,
} = {}) {
  const searchParams = new URLSearchParams()
  searchParams.set('limit', String(limit))

  return apiRequest(`/admin/users/${userId}?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function previewAdminUserSuspension({
  firebaseUser,
  userId,
} = {}) {
  return apiRequest(`/admin/users/${userId}/suspension-preview`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function previewAdminUserHostingRestriction({
  firebaseUser,
  userId,
} = {}) {
  return apiRequest(`/admin/users/${userId}/hosting-restriction-preview`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function previewAdminUserDeleteImpact({
  firebaseUser,
  userId,
} = {}) {
  return apiRequest(`/admin/users/${userId}/delete-preview`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function deleteAdminUser({
  firebaseUser,
  idempotencyKey,
  previewToken,
  reason,
  userId,
} = {}) {
  return apiRequest(`/admin/users/${userId}/delete`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      preview_token: previewToken,
      reason,
      idempotency_key: idempotencyKey,
    }),
  })
}

export async function restrictAdminUserHosting({
  firebaseUser,
  idempotencyKey,
  previewToken,
  reason,
  userId,
} = {}) {
  return apiRequest(`/admin/users/${userId}/restrict-hosting`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      preview_token: previewToken,
      reason,
      idempotency_key: idempotencyKey,
    }),
  })
}

export async function restoreAdminUserHosting({
  firebaseUser,
  idempotencyKey,
  reason,
  userId,
} = {}) {
  return apiRequest(`/admin/users/${userId}/restore-hosting`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      reason,
      idempotency_key: idempotencyKey,
    }),
  })
}

export async function suspendAdminUser({
  firebaseUser,
  idempotencyKey,
  previewToken,
  reason,
  userId,
} = {}) {
  return apiRequest(`/admin/users/${userId}/suspend`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      preview_token: previewToken,
      reason,
      idempotency_key: idempotencyKey,
    }),
  })
}

export async function unsuspendAdminUser({
  firebaseUser,
  idempotencyKey,
  reason,
  userId,
} = {}) {
  return apiRequest(`/admin/users/${userId}/unsuspend`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      reason,
      idempotency_key: idempotencyKey,
    }),
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

export async function getAdminMoneyFinancialOutcome({
  financialOutcomeId,
  firebaseUser,
}) {
  return apiRequest(`/admin/money/financial-outcomes/${financialOutcomeId}`, {
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

export async function createAdminMoneyFinancialOutcome({
  firebaseUser,
  payload,
}) {
  return apiRequest('/admin/money/financial-outcomes', {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify(payload),
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
