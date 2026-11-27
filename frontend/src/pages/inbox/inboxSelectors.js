import {
  APP_UPDATES_TAB,
  GAME_ACTIVITY_TAB,
  getStatusFilterOptions,
  INBOX_STATUS_FILTER_ALL,
  isInboxItemNew,
} from './inboxData.js'

const EMPTY_STATES = {
  [APP_UPDATES_TAB]: {
    all: {
      title: 'No app updates',
      message: 'Platform notices and account updates will show up here.',
    },
    new: {
      title: 'No new app updates',
      message: 'New platform notices and account updates will show up here.',
    },
  },
  [GAME_ACTIVITY_TAB]: {
    all: {
      title: 'No game activity',
      message: 'Game, chat, roster, and Need a Sub updates will show up here.',
    },
    unread: {
      title: 'No unread game activity',
      message: 'Unread game, chat, roster, and Need a Sub updates will show up here.',
    },
    read: {
      title: 'No read game activity',
      message: 'Game activity you have opened will show up here.',
    },
  },
}

function createInboxSection({
  count,
  description,
  hasMore,
  isLoadingMore,
  key,
  loadMoreError,
  items,
  statusFilters,
  title,
}) {
  const statusFilter = statusFilters?.[key] || INBOX_STATUS_FILTER_ALL
  const fallbackCount = items.filter(isInboxItemNew).length
  const emptyState = EMPTY_STATES[key][statusFilter] || EMPTY_STATES[key].all

  return {
    count: typeof count === 'number' ? count : fallbackCount,
    description,
    emptyMessage: emptyState.message,
    emptyTitle: emptyState.title,
    hasMore: Boolean(hasMore),
    isLoadingMore: Boolean(isLoadingMore),
    items,
    key,
    loadMoreError: loadMoreError || '',
    statusFilterOptions: getStatusFilterOptions(key),
    statusFilterValue: statusFilter,
    title,
  }
}

export function getInboxSections(feeds, statusFilters = {}, counts = {}) {
  const appUpdates = feeds?.[APP_UPDATES_TAB] || {}
  const gameActivity = feeds?.[GAME_ACTIVITY_TAB] || {}

  return [
    createInboxSection({
      count: counts.app_updates_new_count,
      description: 'Platform notices, account alerts, and admin updates.',
      hasMore: appUpdates.hasMore,
      isLoadingMore: appUpdates.isLoadingMore,
      key: APP_UPDATES_TAB,
      loadMoreError: appUpdates.loadMoreError,
      items: appUpdates.items || [],
      statusFilters,
      title: 'App Updates',
    }),
    createInboxSection({
      count: counts.game_activity_unread_count,
      description: 'Game, roster, chat, and Need a Sub updates.',
      hasMore: gameActivity.hasMore,
      isLoadingMore: gameActivity.isLoadingMore,
      key: GAME_ACTIVITY_TAB,
      loadMoreError: gameActivity.loadMoreError,
      items: gameActivity.items || [],
      statusFilters,
      title: 'Game Activity',
    }),
  ]
}

export function getFilteredSections(
  activeFilter,
  feeds,
  statusFilters = {},
  counts = {},
) {
  return getInboxSections(feeds, statusFilters, counts).filter(
    (section) => section.key === activeFilter,
  )
}
