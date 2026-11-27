import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth.js'
import {
  APP_UPDATES_TAB,
  GAME_ACTIVITY_CATEGORY,
  GAME_ACTIVITY_TAB,
  SOURCE_TYPE_NOTIFICATION,
  SOURCE_TYPE_PLATFORM_NOTICE_GLOBAL,
  SOURCE_TYPE_PLATFORM_NOTICE_SELECTED,
  getInboxItemKey,
  shouldMarkInboxItemReadOptimistically,
} from './inboxData.js'
import {
  loadInboxCounts,
  loadInboxFeed,
  saveGlobalAppUpdatesSeen,
  saveNotificationRead,
  saveSelectedPlatformNoticeRead,
} from './inboxApi.js'
import { getFilteredSections, getInboxSections } from './inboxSelectors.js'
import {
  EMPTY_COUNTS,
  buildInboxUserChangeReset,
  createFeedState,
  createInitialFeeds,
} from './inboxState.js'

const INBOX_PAGE_LIMIT = 30

function normalizeCounts(counts) {
  return {
    app_updates_new_count: counts?.app_updates_new_count || 0,
    game_activity_unread_count: counts?.game_activity_unread_count || 0,
  }
}

function normalizeFeed(response) {
  return {
    globalSeenToken: response?.global_seen_token || '',
    hasMore: Boolean(response?.has_more),
    items: response?.items || [],
    nextCursor: response?.next_cursor || '',
  }
}

function getInboxSectionKey(notification) {
  return notification.notification_category === GAME_ACTIVITY_CATEGORY
    ? GAME_ACTIVITY_TAB
    : APP_UPDATES_TAB
}

function getFirebaseUserKey(firebaseUser) {
  return firebaseUser?.uid || firebaseUser?.email || ''
}

function buildFeedRequestKey({
  activeFilter,
  activeStatusFilter,
  activeUserId,
  firebaseUser,
}) {
  return [
    activeFilter,
    activeStatusFilter,
    activeUserId || '',
    getFirebaseUserKey(firebaseUser),
  ].join(':')
}

function canApplyInboxBatch(currentFeed, requestKey, requestCursor) {
  return (
    currentFeed?.requestKey === requestKey &&
    currentFeed?.nextCursor === requestCursor
  )
}

export function useInboxPageModel() {
  const navigate = useNavigate()
  const { appUser, currentUser: firebaseUser, isLoading } = useAuth()
  const [activeFilter, setActiveFilter] = useState(APP_UPDATES_TAB)
  const [feeds, setFeeds] = useState(createInitialFeeds)
  const [counts, setCounts] = useState(EMPTY_COUNTS)
  const [activeNotification, setActiveNotification] = useState(null)
  const [statusFilters, setStatusFilters] = useState({
    [APP_UPDATES_TAB]: 'all',
    [GAME_ACTIVITY_TAB]: 'all',
  })
  const globalSeenInFlightRef = useRef('')
  const activeUserId = appUser?.id || ''
  const loadedUserIdRef = useRef(activeUserId)
  const isMountedRef = useRef(false)
  const activeStatusFilter = statusFilters[activeFilter] || 'all'
  const activeFeed = feeds[activeFilter] || createFeedState()
  const activeFeedRequestKey = buildFeedRequestKey({
    activeFilter,
    activeStatusFilter,
    activeUserId,
    firebaseUser,
  })

  useEffect(() => {
    isMountedRef.current = true

    return () => {
      isMountedRef.current = false
    }
  }, [])

  useEffect(() => {
    const resetState = buildInboxUserChangeReset({
      activeUserId,
      loadedUserId: loadedUserIdRef.current,
    })

    if (!resetState) {
      return
    }

    loadedUserIdRef.current = resetState.loadedUserId
    globalSeenInFlightRef.current = resetState.globalSeenInFlight
    setCounts(resetState.counts)
    setActiveNotification(resetState.activeNotification)
    setFeeds(resetState.feeds)
  }, [activeUserId])

  useEffect(() => {
    let ignore = false

    async function loadCounts() {
      if (isLoading) {
        return
      }

      if (!appUser?.id || !firebaseUser) {
        if (!ignore) {
          setCounts(EMPTY_COUNTS)
        }
        return
      }

      try {
        const nextCounts = await loadInboxCounts(firebaseUser)
        if (!ignore) {
          setCounts(normalizeCounts(nextCounts))
        }
      } catch {
        if (!ignore) {
          setCounts(EMPTY_COUNTS)
        }
      }
    }

    loadCounts()

    return () => {
      ignore = true
    }
  }, [appUser?.id, firebaseUser, isLoading])

  useEffect(() => {
    if (isLoading) {
      return undefined
    }

    if (
      activeFeed.requestKey === activeFeedRequestKey &&
      ['error', 'loading', 'success'].includes(activeFeed.status)
    ) {
      return undefined
    }

    if (!appUser?.id || !firebaseUser) {
      setFeeds((currentFeeds) => ({
        ...currentFeeds,
        [activeFilter]: {
          ...createFeedState('error'),
          error: 'Sign in to view your inbox.',
          requestKey: activeFeedRequestKey,
        },
      }))
      return undefined
    }

    async function loadActiveFeed() {
      setFeeds((currentFeeds) => ({
        ...currentFeeds,
        [activeFilter]: {
          ...createFeedState('loading'),
          requestKey: activeFeedRequestKey,
          statusFilter: activeStatusFilter,
        },
      }))

      try {
        const response = await loadInboxFeed(firebaseUser, {
          feedKey: activeFilter,
          filter: activeStatusFilter,
          limit: INBOX_PAGE_LIMIT,
        })
        const nextFeed = normalizeFeed(response)
        if (isMountedRef.current) {
          setFeeds((currentFeeds) => {
            if (currentFeeds[activeFilter]?.requestKey !== activeFeedRequestKey) {
              return currentFeeds
            }

            return {
              ...currentFeeds,
              [activeFilter]: {
                ...nextFeed,
                error: '',
                isLoadingMore: false,
                loadMoreError: '',
                requestKey: activeFeedRequestKey,
                status: 'success',
                statusFilter: activeStatusFilter,
              },
            }
          })
        }
      } catch (requestError) {
        if (isMountedRef.current) {
          setFeeds((currentFeeds) => {
            if (currentFeeds[activeFilter]?.requestKey !== activeFeedRequestKey) {
              return currentFeeds
            }

            return {
              ...currentFeeds,
              [activeFilter]: {
                ...createFeedState('error'),
                error: requestError instanceof Error
                  ? requestError.message
                  : 'Unable to load inbox.',
                requestKey: activeFeedRequestKey,
              },
            }
          })
        }
      }
    }

    loadActiveFeed()
    return undefined
  }, [
    activeFeed.requestKey,
    activeFeed.status,
    activeFeedRequestKey,
    activeFilter,
    activeStatusFilter,
    appUser?.id,
    firebaseUser,
    isLoading,
  ])

  useEffect(() => {
    const appFeed = feeds[APP_UPDATES_TAB]
    const seenToken = appFeed?.globalSeenToken

    if (
      appFeed?.status !== 'success' ||
      activeFilter !== APP_UPDATES_TAB ||
      !seenToken ||
      !firebaseUser ||
      globalSeenInFlightRef.current === `${activeUserId}:${seenToken}`
    ) {
      return undefined
    }

    const requestUserId = activeUserId
    const inFlightKey = `${requestUserId}:${seenToken}`
    globalSeenInFlightRef.current = inFlightKey

    saveGlobalAppUpdatesSeen(firebaseUser, seenToken)
      .then((updatedCounts) => {
        if (loadedUserIdRef.current !== requestUserId) {
          return
        }
        setCounts(normalizeCounts(updatedCounts))
        setFeeds((currentFeeds) => {
          const currentAppFeed = currentFeeds[APP_UPDATES_TAB]
          if (currentAppFeed.globalSeenToken !== seenToken) {
            return currentFeeds
          }

          return {
            ...currentFeeds,
            [APP_UPDATES_TAB]: {
              ...currentAppFeed,
              globalSeenToken: '',
              items: currentAppFeed.items.map((item) => (
                item.source_type === SOURCE_TYPE_PLATFORM_NOTICE_GLOBAL
                  ? { ...item, is_new: false }
                  : item
              )),
            },
          }
        })
      })
      .catch(() => {
        if (
          loadedUserIdRef.current === requestUserId &&
          globalSeenInFlightRef.current === inFlightKey
        ) {
          globalSeenInFlightRef.current = ''
        }
      })

    return undefined
  }, [
    activeFilter,
    activeUserId,
    feeds,
    firebaseUser,
  ])

  const inboxSections = getInboxSections(feeds, statusFilters, counts)
  const filteredSections = getFilteredSections(
    activeFilter,
    feeds,
    statusFilters,
    counts,
  )

  function handleSourceFilterChange(sectionKey, sourceFilter) {
    setStatusFilters((currentFilters) => ({
      ...currentFilters,
      [sectionKey]: sourceFilter,
    }))
    setFeeds((currentFeeds) => ({
      ...currentFeeds,
      [sectionKey]: createFeedState(),
    }))
  }

  async function handleOpenNotification(notification) {
    const itemKey = getInboxItemKey(notification)
    setActiveNotification(notification)
    const markedNotification = await markInboxItemRead(notification)
    setActiveNotification((currentNotification) => (
      getInboxItemKey(currentNotification) === itemKey
        ? markedNotification
        : currentNotification
    ))
  }

  function handleNotificationAction(action) {
    if (action?.disabled || !action?.path) {
      return
    }

    setActiveNotification(null)
    navigate(action.path, action.state ? { state: action.state } : undefined)
  }

  function replaceInboxItem(notification, replacement) {
    const itemKey = getInboxItemKey(notification)
    const replaceItem = (item) => (
      getInboxItemKey(item) === itemKey ? replacement : item
    )
    setFeeds((currentFeeds) => ({
      [APP_UPDATES_TAB]: {
        ...currentFeeds[APP_UPDATES_TAB],
        items: currentFeeds[APP_UPDATES_TAB].items.map(replaceItem),
      },
      [GAME_ACTIVITY_TAB]: {
        ...currentFeeds[GAME_ACTIVITY_TAB],
        items: currentFeeds[GAME_ACTIVITY_TAB].items.map(replaceItem),
      },
    }))
  }

  function removeReadItemFromFilteredFeed(notification) {
    const itemKey = getInboxItemKey(notification)
    const sectionKey = getInboxSectionKey(notification)

    setFeeds((currentFeeds) => {
      // Use the filter of the list showing now, which may have loaded while
      // the save was pending: a read item leaves a New or Unread list only.
      const statusFilter = currentFeeds[sectionKey]?.statusFilter
      if (statusFilter !== 'new' && statusFilter !== 'unread') {
        return currentFeeds
      }

      return {
        ...currentFeeds,
        [sectionKey]: {
          ...currentFeeds[sectionKey],
          items: currentFeeds[sectionKey].items.filter(
            (item) => getInboxItemKey(item) !== itemKey,
          ),
        },
      }
    })
  }

  function updateCountsForRead(notification, direction) {
    setCounts((currentCounts) => {
      if (notification.notification_category === GAME_ACTIVITY_CATEGORY) {
        return {
          ...currentCounts,
          game_activity_unread_count: Math.max(
            0,
            currentCounts.game_activity_unread_count + direction,
          ),
        }
      }

      return {
        ...currentCounts,
        app_updates_new_count: Math.max(
          0,
          currentCounts.app_updates_new_count + direction,
        ),
      }
    })
  }

  async function markInboxItemRead(notification) {
    if (!shouldMarkInboxItemReadOptimistically(notification)) {
      return notification
    }

    const optimisticNotification = {
      ...notification,
      is_new: false,
      is_read: true,
      read_at: new Date().toISOString(),
    }

    const requestUserId = loadedUserIdRef.current
    // After an account switch the feeds and counts belong to another account.
    const isSameAccount = () => loadedUserIdRef.current === requestUserId

    replaceInboxItem(notification, optimisticNotification)
    updateCountsForRead(notification, -1)

    try {
      if (notification.source_type === SOURCE_TYPE_PLATFORM_NOTICE_SELECTED) {
        const savedNotification = await saveSelectedPlatformNoticeRead(
          firebaseUser,
          notification.source_id,
        )
        if (isSameAccount()) {
          replaceInboxItem(notification, savedNotification)
          removeReadItemFromFilteredFeed(notification)
        }
        return savedNotification
      }

      if (notification.source_type === SOURCE_TYPE_NOTIFICATION) {
        await saveNotificationRead(
          firebaseUser,
          notification.original_notification_id || notification.source_id,
        )
        if (isSameAccount()) {
          replaceInboxItem(notification, optimisticNotification)
          removeReadItemFromFilteredFeed(notification)
        }
        return optimisticNotification
      }

      return optimisticNotification
    } catch {
      if (isSameAccount()) {
        replaceInboxItem(notification, notification)
        updateCountsForRead(notification, 1)
      }
      return notification
    }
  }

  async function handleLoadMore(sectionKey) {
    const feed = feeds[sectionKey]
    if (
      !firebaseUser ||
      !feed?.hasMore ||
      !feed.nextCursor ||
      feed.isLoadingMore
    ) {
      return
    }

    const requestKey = feed.requestKey
    const requestCursor = feed.nextCursor

    setFeeds((currentFeeds) => ({
      ...currentFeeds,
      [sectionKey]: {
        ...currentFeeds[sectionKey],
        isLoadingMore: true,
        loadMoreError: '',
      },
    }))

    try {
      const response = await loadInboxFeed(firebaseUser, {
        cursor: requestCursor,
        feedKey: sectionKey,
        filter: statusFilters[sectionKey] || 'all',
        limit: INBOX_PAGE_LIMIT,
      })
      const nextFeed = normalizeFeed(response)

      setFeeds((currentFeeds) => {
        const currentFeed = currentFeeds[sectionKey]
        if (!canApplyInboxBatch(currentFeed, requestKey, requestCursor)) {
          return currentFeeds
        }
        const existingKeys = new Set(currentFeed.items.map(getInboxItemKey))
        const nextItems = nextFeed.items.filter(
          (item) => !existingKeys.has(getInboxItemKey(item)),
        )

        return {
          ...currentFeeds,
          [sectionKey]: {
            ...currentFeed,
            globalSeenToken: nextFeed.globalSeenToken,
            hasMore: nextFeed.hasMore,
            isLoadingMore: false,
            items: [...currentFeed.items, ...nextItems],
            loadMoreError: '',
            nextCursor: nextFeed.nextCursor,
          },
        }
      })
    } catch (requestError) {
      setFeeds((currentFeeds) => {
        const currentFeed = currentFeeds[sectionKey]
        if (!canApplyInboxBatch(currentFeed, requestKey, requestCursor)) {
          return currentFeeds
        }

        return {
          ...currentFeeds,
          [sectionKey]: {
            ...currentFeed,
            isLoadingMore: false,
            loadMoreError: requestError instanceof Error
              ? requestError.message
              : 'More items could not be loaded.',
          },
        }
      })
    }
  }

  const pageStatus = isLoading || activeFeed.status === 'idle'
    ? 'loading'
    : activeFeed.status
  const pageError = activeFeed.error || ''

  return {
    activeFilter,
    activeNotification,
    error: pageError,
    filteredSections,
    handleLoadMore,
    handleNotificationAction,
    handleOpenNotification,
    handleSourceFilterChange,
    inboxSections,
    setActiveFilter,
    setActiveNotification,
    status: pageStatus,
  }
}
