import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from '../../hooks/useAuth.js'
import { loadMyGamesPage } from './myGamesApi.js'
import {
  groupHistoryAgendaItems,
  groupUpcomingAgendaItems,
} from './myGamesSelectors.js'

const MY_GAMES_PAGE_LIMIT = 40
const MY_GAMES_DEFAULT_DOMAIN = 'games'
const MY_GAMES_DEFAULT_VIEW = 'upcoming'
const initialPageState = {
  error: '',
  hasMore: false,
  isLoadingMore: false,
  items: [],
  nextCursor: null,
  status: 'idle',
}

function createInitialPageState() {
  return {
    ...initialPageState,
    items: [],
  }
}

function createInitialDomainPages() {
  return {
    history: createInitialPageState(),
    upcoming: createInitialPageState(),
  }
}

function createInitialPages() {
  return {
    games: createInitialDomainPages(),
    'need-a-sub': createInitialDomainPages(),
  }
}

export function useMyGamesPageModel() {
  const { appUser, currentUser: firebaseUser, isLoading } = useAuth()
  const [activeDomain, setActiveDomain] = useState(MY_GAMES_DEFAULT_DOMAIN)
  const [activeTab, setActiveTab] = useState(MY_GAMES_DEFAULT_VIEW)
  const [pages, setPages] = useState(createInitialPages)
  const activeUserIdRef = useRef(appUser?.id || '')
  const latestRequestByKeyRef = useRef(new Map())
  const pagesRef = useRef(pages)
  const requestSerialRef = useRef(0)
  const requestVersionRef = useRef(0)

  useEffect(() => {
    pagesRef.current = pages
  }, [pages])

  useEffect(() => {
    activeUserIdRef.current = appUser?.id || ''
    latestRequestByKeyRef.current = new Map()
    requestVersionRef.current += 1
    setPages(createInitialPages())
  }, [appUser?.id])

  const activeDomainPages = pages[activeDomain] || createInitialDomainPages()
  const activePage = activeDomainPages[activeTab] || initialPageState

  const activeItems = activePage.items
  const upcomingGroups = useMemo(
    () => groupUpcomingAgendaItems(activeDomainPages.upcoming.items),
    [activeDomainPages.upcoming.items],
  )
  const historyGroups = useMemo(
    () => groupHistoryAgendaItems(activeDomainPages.history.items),
    [activeDomainPages.history.items],
  )

  const loadPage = useCallback(async (domain, view, { append = false } = {}) => {
    if (isLoading) {
      return
    }

    if (!appUser?.id) {
      setPages((currentPages) => ({
        ...currentPages,
        [domain]: {
          ...currentPages[domain],
          [view]: {
            ...currentPages[domain][view],
            error: 'Sign in to view your games.',
            status: 'error',
          },
        },
      }))
      return
    }

    const currentPage = pagesRef.current[domain]?.[view] || initialPageState
    const cursor = append ? currentPage.nextCursor : ''
    const requestKey = `${domain}:${view}`
    const requestId = requestSerialRef.current + 1
    const requestUserId = appUser.id
    const requestVersion = requestVersionRef.current
    requestSerialRef.current = requestId
    latestRequestByKeyRef.current.set(requestKey, requestId)

    setPages((currentPages) => ({
      ...currentPages,
      [domain]: {
        ...currentPages[domain],
        [view]: {
          ...currentPages[domain][view],
          error: '',
          isLoadingMore: append,
          status: append ? currentPages[domain][view].status : 'loading',
        },
      },
    }))

    try {
      const pageData = await loadMyGamesPage(firebaseUser, {
        cursor,
        domain,
        limit: MY_GAMES_PAGE_LIMIT,
        view,
      })

      if (
        requestVersion !== requestVersionRef.current
        || requestUserId !== activeUserIdRef.current
        || latestRequestByKeyRef.current.get(requestKey) !== requestId
      ) {
        return
      }

      setPages((currentPages) => ({
        ...currentPages,
        [domain]: {
          ...currentPages[domain],
          [view]: {
            error: '',
            hasMore: Boolean(pageData.has_more),
            isLoadingMore: false,
            items: append
              ? mergeUniqueItems(
                  currentPages[domain][view].items,
                  pageData.items || [],
                )
              : pageData.items || [],
            nextCursor: pageData.next_cursor || null,
            status: 'success',
          },
        },
      }))
    } catch (requestError) {
      if (
        requestVersion !== requestVersionRef.current
        || requestUserId !== activeUserIdRef.current
        || latestRequestByKeyRef.current.get(requestKey) !== requestId
      ) {
        return
      }

      setPages((currentPages) => ({
        ...currentPages,
        [domain]: {
          ...currentPages[domain],
          [view]: {
            ...currentPages[domain][view],
            error: requestError instanceof Error
              ? requestError.message
              : 'Unable to load your games.',
            isLoadingMore: false,
            status: append ? currentPages[domain][view].status : 'error',
          },
        },
      }))
    }
  }, [appUser, firebaseUser, isLoading])

  useEffect(() => {
    if (isLoading || activePage.status !== 'idle') {
      return
    }

    loadPage(activeDomain, activeTab)
  }, [activeDomain, activePage.status, activeTab, isLoading, loadPage])

  function loadMoreActiveItems() {
    if (!activePage.hasMore || activePage.isLoadingMore) {
      return
    }

    loadPage(activeDomain, activeTab, { append: true })
  }

  function resetPane(domain, view) {
    requestVersionRef.current += 1
    latestRequestByKeyRef.current = new Map()
    setPages((currentPages) => ({
      ...currentPages,
      [domain]: {
        ...(currentPages[domain] || createInitialDomainPages()),
        [view]: createInitialPageState(),
      },
    }))
  }

  function changeActiveDomain(nextDomain) {
    if (nextDomain === activeDomain) {
      return
    }

    resetPane(nextDomain, activeTab)
    setActiveDomain(nextDomain)
  }

  function changeActiveTab(nextTab) {
    if (nextTab === activeTab) {
      return
    }

    resetPane(activeDomain, nextTab)
    setActiveTab(nextTab)
  }

  function retryActiveItems() {
    loadPage(activeDomain, activeTab)
  }

  return {
    activeDomain,
    activeItems,
    activeTab,
    error: activePage.error,
    hasMoreItems: activePage.hasMore,
    historyGroups,
    isLoadingMore: activePage.isLoadingMore,
    loadMoreActiveItems,
    retryActiveItems,
    setActiveDomain: changeActiveDomain,
    setActiveTab: changeActiveTab,
    status: activePage.status === 'idle' ? 'loading' : activePage.status,
    upcomingGroups,
  }
}

function mergeUniqueItems(existingItems, nextItems) {
  const seenKeys = new Set(existingItems.map(getMyGamesItemKey).filter(Boolean))
  const uniqueItems = [...existingItems]

  nextItems.forEach((item) => {
    const itemKey = getMyGamesItemKey(item)
    if (itemKey && seenKeys.has(itemKey)) {
      return
    }

    if (itemKey) {
      seenKeys.add(itemKey)
    }
    uniqueItems.push(item)
  })

  return uniqueItems
}

function getMyGamesItemKey(item) {
  return item.game?.id || item.post?.id || item.participant_id || item.request_id || ''
}
