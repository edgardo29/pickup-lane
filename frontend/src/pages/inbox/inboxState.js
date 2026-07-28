import {
  APP_UPDATES_TAB,
  GAME_ACTIVITY_TAB,
} from './inboxData.js'

export const EMPTY_COUNTS = {
  app_updates_new_count: 0,
  game_activity_unread_count: 0,
}

export function createFeedState(status = 'idle') {
  return {
    error: '',
    globalSeenToken: '',
    hasMore: false,
    isLoadingMore: false,
    items: [],
    loadMoreError: '',
    nextCursor: '',
    requestKey: '',
    status,
  }
}

export function createInitialFeeds() {
  return {
    [APP_UPDATES_TAB]: createFeedState(),
    [GAME_ACTIVITY_TAB]: createFeedState(),
  }
}

export function buildInboxUserChangeReset({ activeUserId, loadedUserId }) {
  if (loadedUserId === activeUserId) {
    return null
  }

  return {
    activeNotification: null,
    counts: EMPTY_COUNTS,
    feeds: createInitialFeeds(),
    globalSeenInFlight: '',
    loadedUserId: activeUserId,
  }
}
