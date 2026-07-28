const adminRoutes = {
  communityGame: (id) => `/admin/community-games/${id}`,
  moneyPayment: (id) => `/admin/money/payments/${id}`,
  moneyRefund: (id) => `/admin/money/refunds/${id}`,
  needASubPost: (id) => `/admin/need-a-sub/${id}`,
  needASubRequest: (id) => `/admin/need-a-sub/requests/${id}`,
  notification: (id) => `/admin/notifications/${id}`,
  officialGame: (id) => `/admin/official-games/${id}`,
  platformNotice: (id) => `/admin/platform-notices/${id}`,
  user: (id) => `/admin/users/${id}`,
}

const notificationRelatedRouteByType = {
  game: null,
  booking: null,
  game_chat: null,
  game_message: null,
  need_a_sub_chat: null,
  need_a_sub_chat_message: null,
  need_a_sub_position: null,
  need_a_sub_post: adminRoutes.needASubPost,
  need_a_sub_request: adminRoutes.needASubRequest,
  participant: null,
  payment: adminRoutes.moneyPayment,
  refund: adminRoutes.moneyRefund,
}

export function buildAdminUserPath(userId) {
  return userId ? adminRoutes.user(userId) : ''
}

export function buildAdminNotificationPath(notificationId) {
  return notificationId ? adminRoutes.notification(notificationId) : ''
}

export function buildAdminPlatformNoticePath(noticeId) {
  return noticeId ? adminRoutes.platformNotice(noticeId) : ''
}

export function buildAdminNotificationRelatedPath(record, notification = null) {
  if (!record?.type || !record?.id) {
    return ''
  }

  if (record.type === 'game') {
    if (notification?.source_type === 'official_game') {
      return adminRoutes.officialGame(record.id)
    }
    if (notification?.source_type === 'community_game') {
      return adminRoutes.communityGame(record.id)
    }
    return ''
  }

  const routeBuilder = notificationRelatedRouteByType[record.type]
  return routeBuilder ? routeBuilder(record.id) : ''
}
