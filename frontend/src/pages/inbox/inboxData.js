export const APP_NOTIFICATION_CATEGORY = 'app'
export const GAME_ACTIVITY_CATEGORY = 'game_activity'
export const APP_UPDATES_TAB = 'app'
export const GAME_ACTIVITY_TAB = 'game'

export const SOURCE_TYPE_NOTIFICATION = 'notification'
export const SOURCE_TYPE_PLATFORM_NOTICE_GLOBAL = 'platform_notice_global'
export const SOURCE_TYPE_PLATFORM_NOTICE_SELECTED = 'platform_notice_selected'
export const READ_BEHAVIOR_GLOBAL_SEEN = 'global_seen_marker'
export const READ_BEHAVIOR_ITEM_READ = 'item_read'

export const inboxTabs = [
  { key: APP_UPDATES_TAB, label: 'App Updates' },
  { key: GAME_ACTIVITY_TAB, label: 'Game Activity' },
]

export const INBOX_STATUS_FILTER_ALL = 'all'

export const inboxStatusFilters = {
  [APP_UPDATES_TAB]: [
    { key: INBOX_STATUS_FILTER_ALL, label: 'All updates' },
    { key: 'new', label: 'New only' },
  ],
  [GAME_ACTIVITY_TAB]: [
    { key: INBOX_STATUS_FILTER_ALL, label: 'All activity' },
    { key: 'unread', label: 'Unread only' },
    { key: 'read', label: 'Read only' },
  ],
}

export function isGameActivityNotification(notification) {
  return notification?.notification_category === GAME_ACTIVITY_CATEGORY
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

export function getRenderableNotificationAction(notification) {
  const action = getNotificationAction(notification)
  if (!action) {
    return null
  }

  if (action.disabled || action.path) {
    return action
  }

  return null
}

export function getInboxItemKey(notification) {
  return `${notification?.source_type || 'item'}:${notification?.source_id || notification?.id}`
}

export function getStatusFilterOptions(sectionKey) {
  return inboxStatusFilters[sectionKey] || []
}

export function isInboxItemNew(notification) {
  if (typeof notification?.is_new === 'boolean') {
    return notification.is_new
  }

  return !notification?.is_read
}

export function shouldMarkInboxItemReadOptimistically(notification) {
  return (
    isInboxItemNew(notification) &&
    notification?.read_behavior !== READ_BEHAVIOR_GLOBAL_SEEN
  )
}
