import { useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from '../../hooks/useAuth.js'
import { loadMyGamesPage } from './myGamesApi.js'
import {
  groupHistoryAgendaItems,
  groupUpcomingAgendaItems,
} from './myGamesSelectors.js'

const MY_GAMES_PAGE_LIMIT = 40
const initialPageState = {
  error: '',
  hasMore: false,
  isLoadingMore: false,
  items: [],
  nextCursor: null,
  status: 'idle',
}

function createInitialPages() {
  return {
    history: { ...initialPageState },
    upcoming: { ...initialPageState },
  }
}

export function useMyGamesPageModel() {
  const { appUser, currentUser: firebaseUser, isLoading } = useAuth()
  const [activeTab, setActiveTab] = useState('upcoming')
  const [pages, setPages] = useState(createInitialPages)
  const activeUserIdRef = useRef(appUser?.id || '')
  const requestVersionRef = useRef(0)

  activeUserIdRef.current = appUser?.id || ''

  useEffect(() => {
    requestVersionRef.current += 1
    setPages(createInitialPages())
  }, [appUser?.id])

  const activePage = pages[activeTab] || initialPageState

  useEffect(() => {
    if (isLoading || activePage.status !== 'idle') {
      return
    }

    loadPage(activeTab)
  }, [activePage.status, activeTab, isLoading])

  const activeItems = activePage.items
  const upcomingGroups = useMemo(
    () => groupUpcomingAgendaItems(pages.upcoming.items),
    [pages.upcoming.items],
  )
  const historyGroups = useMemo(
    () => groupHistoryAgendaItems(pages.history.items),
    [pages.history.items],
  )

  async function loadPage(view, { append = false } = {}) {
    if (isLoading) {
      return
    }

    if (!appUser?.id) {
      setPages((currentPages) => ({
        ...currentPages,
        [view]: {
          ...currentPages[view],
          error: 'Sign in to view your games.',
          status: 'error',
        },
      }))
      return
    }

    const currentPage = pages[view] || initialPageState
    const cursor = append ? currentPage.nextCursor : ''
    const requestUserId = appUser.id
    const requestVersion = requestVersionRef.current

    setPages((currentPages) => ({
      ...currentPages,
      [view]: {
        ...currentPages[view],
        error: '',
        isLoadingMore: append,
        status: append ? currentPages[view].status : 'loading',
      },
    }))

    try {
      const pageData = await loadMyGamesPage(firebaseUser, {
        cursor,
        limit: MY_GAMES_PAGE_LIMIT,
        view,
      })

      if (
        requestVersion !== requestVersionRef.current
        || requestUserId !== activeUserIdRef.current
      ) {
        return
      }

      setPages((currentPages) => ({
        ...currentPages,
        [view]: {
          error: '',
          hasMore: Boolean(pageData.has_more),
          isLoadingMore: false,
          items: append
            ? [...currentPages[view].items, ...(pageData.items || [])]
            : pageData.items || [],
          nextCursor: pageData.next_cursor || null,
          status: 'success',
        },
      }))
    } catch (requestError) {
      if (
        requestVersion !== requestVersionRef.current
        || requestUserId !== activeUserIdRef.current
      ) {
        return
      }

      setPages((currentPages) => ({
        ...currentPages,
        [view]: {
          ...currentPages[view],
          error: requestError instanceof Error ? requestError.message : 'Unable to load your games.',
          isLoadingMore: false,
          status: append ? currentPages[view].status : 'error',
        },
      }))
    }
  }

  function loadMoreActiveItems() {
    if (!activePage.hasMore || activePage.isLoadingMore) {
      return
    }

    loadPage(activeTab, { append: true })
  }

  return {
    activeItems,
    activeTab,
    error: activePage.error,
    hasHiddenUpcomingItems: false,
    hasMoreItems: activePage.hasMore,
    historyGroups,
    isLoadingMore: activePage.isLoadingMore,
    loadMoreActiveItems,
    setActiveTab,
    status: activePage.status === 'idle' ? 'loading' : activePage.status,
    upcomingGroups,
  }
}
