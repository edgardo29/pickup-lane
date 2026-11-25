import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiRequestError } from '../../lib/apiClient.js'
import { listNeedASubPostCards } from './needASubApi.js'

const NEED_SUB_PAGE_LIMIT = 40

function buildEmptyPage() {
  return {
    hasMore: false,
    isLoading: true,
    isLoadingMore: false,
    loadFailed: false,
    nextCursor: '',
    posts: [],
  }
}

// The server's own message when it answered; otherwise (no connection) a
// player message instead of the browser's error text.
function describeLoadError(loadError, fallback) {
  return loadError instanceof ApiRequestError ? loadError.message : fallback
}

function buildFirstPage(response) {
  return {
    hasMore: Boolean(response.has_more),
    isLoading: false,
    isLoadingMore: false,
    loadFailed: false,
    nextCursor: response.next_cursor || '',
    posts: response.posts || [],
  }
}

// currentUser is the signed-in user only when they have a Pickup Lane account;
// otherwise null, and the visitor browses as a guest.
export function useNeedASubPostsData({
  currentUser,
  isAuthLoading,
  onReturn,
  postView,
  selectedDateKey,
}) {
  const [page, setPage] = useState(() => buildEmptyPage())
  const [error, setError] = useState('')
  const [reloadCount, setReloadCount] = useState(0)
  const requestVersionRef = useRef(0)
  const wasAwayRef = useRef(false)
  const requestContextKey = [
    currentUser?.uid || 'guest',
    isAuthLoading ? 'loading' : 'ready',
    postView,
    selectedDateKey || '',
  ].join(':')
  const requestContextKeyRef = useRef(requestContextKey)

  useEffect(() => {
    requestContextKeyRef.current = requestContextKey
    requestVersionRef.current += 1
  }, [requestContextKey])

  const beginRequest = useCallback(() => {
    const requestVersion = requestVersionRef.current + 1
    requestVersionRef.current = requestVersion

    return {
      contextKey: requestContextKeyRef.current,
      version: requestVersion,
    }
  }, [])

  const isCurrentRequest = useCallback((request) => {
    return (
      request.version === requestVersionRef.current
      && request.contextKey === requestContextKeyRef.current
    )
  }, [])

  useEffect(() => {
    let ignore = false
    const request = beginRequest()

    async function loadInitialNeedASub() {
      if (isAuthLoading || !selectedDateKey) {
        return
      }

      if (postView === 'mine' && !currentUser) {
        setPage({
          ...buildEmptyPage(),
          isLoading: false,
        })
        setError('')
        return
      }

      setPage(buildEmptyPage())
      setError('')

      try {
        const response = await listNeedASubPostCards(currentUser, {
          limit: NEED_SUB_PAGE_LIMIT,
          startsOn: selectedDateKey,
          view: postView,
        })

        if (!ignore && isCurrentRequest(request)) {
          setPage(buildFirstPage(response))
        }
      } catch (loadError) {
        if (!ignore && isCurrentRequest(request)) {
          setError(describeLoadError(loadError, 'Could not load Need a Sub posts. Try again.'))
          setPage({
            ...buildEmptyPage(),
            isLoading: false,
            loadFailed: true,
          })
        }
      }
    }

    loadInitialNeedASub()

    return () => {
      ignore = true
    }
  }, [beginRequest, currentUser, isAuthLoading, isCurrentRequest, postView, reloadCount, selectedDateKey])

  // Try the first batch again after it failed.
  const retryNeedASub = useCallback(() => {
    setReloadCount((count) => count + 1)
  }, [])

  // A background refresh replaces the list with a fresh first batch. If it
  // fails, the cards already shown stay and the failure is reported.
  const refreshNeedASub = useCallback(async () => {
    if (isAuthLoading || !selectedDateKey || (postView === 'mine' && !currentUser)) {
      return
    }

    setError('')
    const request = beginRequest()

    try {
      const response = await listNeedASubPostCards(currentUser, {
        limit: NEED_SUB_PAGE_LIMIT,
        startsOn: selectedDateKey,
        view: postView,
      })

      if (isCurrentRequest(request)) {
        setPage(buildFirstPage(response))
      }
    } catch (loadError) {
      if (!isCurrentRequest(request)) {
        return
      }

      setError(describeLoadError(loadError, 'Could not load Need a Sub posts. Try again.'))
      setPage((currentPage) => ({
        ...currentPage,
        isLoading: false,
        isLoadingMore: false,
        loadFailed: currentPage.posts.length === 0,
      }))
    }
  }, [
    beginRequest,
    currentUser,
    isAuthLoading,
    isCurrentRequest,
    postView,
    selectedDateKey,
  ])

  const loadMoreNeedASub = useCallback(async () => {
    if (
      isAuthLoading
      || !selectedDateKey
      || !page.hasMore
      || !page.nextCursor
      || page.isLoading
      || page.isLoadingMore
    ) {
      return
    }

    if (postView === 'mine' && !currentUser) {
      return
    }

    const request = beginRequest()
    setPage((currentPage) => ({
      ...currentPage,
      isLoadingMore: true,
    }))
    setError('')

    try {
      const response = await listNeedASubPostCards(currentUser, {
        cursor: page.nextCursor,
        limit: NEED_SUB_PAGE_LIMIT,
        startsOn: selectedDateKey,
        view: postView,
      })

      if (!isCurrentRequest(request)) {
        return
      }

      setPage((currentPage) => ({
        hasMore: Boolean(response.has_more),
        isLoading: false,
        isLoadingMore: false,
        loadFailed: false,
        nextCursor: response.next_cursor || '',
        posts: [
          ...currentPage.posts,
          ...(response.posts || []),
        ],
      }))
    } catch (loadError) {
      if (!isCurrentRequest(request)) {
        return
      }

      setError(describeLoadError(loadError, 'Could not load more posts. Try again.'))
      setPage((currentPage) => ({
        ...currentPage,
        isLoadingMore: false,
      }))
    }
  }, [
    currentUser,
    beginRequest,
    isAuthLoading,
    isCurrentRequest,
    page.hasMore,
    page.isLoading,
    page.isLoadingMore,
    page.nextCursor,
    postView,
    selectedDateKey,
  ])

  // Leaving the page and coming back (window focus or tab visibility) counts
  // as one return and starts one refresh.
  useEffect(() => {
    function refreshOnReturn() {
      if (!wasAwayRef.current || document.visibilityState === 'hidden') {
        return
      }

      wasAwayRef.current = false
      onReturn?.()
      refreshNeedASub()
    }

    function handleVisibilityChange() {
      if (document.visibilityState === 'hidden') {
        wasAwayRef.current = true
      } else {
        refreshOnReturn()
      }
    }

    function handleBlur() {
      wasAwayRef.current = true
    }

    window.addEventListener('blur', handleBlur)
    window.addEventListener('focus', refreshOnReturn)
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      window.removeEventListener('blur', handleBlur)
      window.removeEventListener('focus', refreshOnReturn)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [onReturn, refreshNeedASub])

  return {
    error,
    hasLoadFailed: page.loadFailed,
    hasMorePosts: page.hasMore,
    isLoading: page.isLoading,
    isLoadingMore: page.isLoadingMore,
    loadMoreNeedASub,
    posts: page.posts,
    retryNeedASub,
    setError,
  }
}
