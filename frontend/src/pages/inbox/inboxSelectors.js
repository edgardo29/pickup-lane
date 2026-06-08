import {
  filterNotificationsBySource,
  getSourceFilterOptions,
  INBOX_SOURCE_FILTER_ALL,
} from './inboxData.js'

function createInboxSection({
  description,
  emptyMessage,
  emptyTitle,
  key,
  notifications,
  sourceFilters,
  title,
}) {
  const sourceFilter = sourceFilters?.[key] || INBOX_SOURCE_FILTER_ALL

  return {
    description,
    emptyMessage,
    emptyTitle,
    items: filterNotificationsBySource(notifications, sourceFilter),
    key,
    sourceFilterOptions: getSourceFilterOptions(key),
    sourceFilterValue: sourceFilter,
    title,
    totalItems: notifications.length,
  }
}

export function getInboxSections(appNotifications, gameNotifications, sourceFilters = {}) {
  return [
    createInboxSection({
      description: 'Important updates and support messages.',
      emptyMessage: 'App-wide updates and support messages will show up here.',
      emptyTitle: 'No app notifications',
      key: 'app',
      notifications: appNotifications,
      sourceFilters,
      title: 'App Notifications',
    }),
    createInboxSection({
      description: 'Game, roster, chat, and Need a Sub updates.',
      emptyMessage: 'Game, chat, roster, and Need a Sub updates will show up here.',
      emptyTitle: 'No game activity',
      key: 'game',
      notifications: gameNotifications,
      sourceFilters,
      title: 'Game Activity',
    }),
  ]
}

export function getFilteredSections(
  activeFilter,
  appNotifications,
  gameNotifications,
  sourceFilters = {},
) {
  return getInboxSections(appNotifications, gameNotifications, sourceFilters).filter(
    (section) => section.key === activeFilter,
  )
}
