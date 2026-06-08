export const APP_NOTIFICATION_CATEGORY = 'app'
export const GAME_ACTIVITY_CATEGORY = 'game_activity'

export const LEGACY_GAME_ACTIVITY_TYPES = new Set(['chat_message'])

export const inboxTabs = [
  { key: 'app', label: 'App Notifications' },
  { key: 'game', label: 'Game Activity' },
]

export const INBOX_SOURCE_FILTER_ALL = 'all'

export const inboxSourceFilters = {
  app: [
    { key: INBOX_SOURCE_FILTER_ALL, label: 'All filters' },
    { key: 'pickup_lane', label: 'Pickup Lane' },
    { key: 'account', label: 'Account' },
    { key: 'support', label: 'Support' },
    { key: 'policy', label: 'Policy' },
    { key: 'payment', label: 'Payment' },
  ],
  game: [
    { key: INBOX_SOURCE_FILTER_ALL, label: 'All filters' },
    { key: 'need_a_sub', label: 'Need a Sub' },
    { key: 'community_game', label: 'Community games' },
    { key: 'official_game', label: 'Official games' },
    { key: 'game', label: 'Games' },
  ],
}

export function isGameActivityNotification(notification) {
  return (
    notification?.notification_category === GAME_ACTIVITY_CATEGORY ||
    LEGACY_GAME_ACTIVITY_TYPES.has(notification?.notification_type)
  )
}

export function isAppNotification(notification) {
  return (
    notification?.notification_category === APP_NOTIFICATION_CATEGORY ||
    !isGameActivityNotification(notification)
  )
}

export function getNotificationAction(notification) {
  return notification?.action || null
}

export function getSourceFilterOptions(sectionKey) {
  return inboxSourceFilters[sectionKey] || []
}

export function filterNotificationsBySource(notifications, sourceFilter) {
  if (!sourceFilter || sourceFilter === INBOX_SOURCE_FILTER_ALL) {
    return notifications
  }

  return notifications.filter((notification) => notification?.source_type === sourceFilter)
}
