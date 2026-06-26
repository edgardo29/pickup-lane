import { useCallback, useEffect, useRef, useState } from 'react'
import { listNeedASubPostCards } from './needASubApi.js'

const NEED_SUB_PAGE_LIMIT = 40

function buildEmptyPage() {
  return {
    hasMore: false,
    isLoading: true,
    isLoadingMore: false,
    nextCursor: '',
    posts: [],
  }
}

export function useNeedASubPostsData({
  currentUser,
  isAuthLoading,
  postView,
  selectedDateKey,
}) {
  const [page, setPage] = useState(() => buildEmptyPage())
  const [error, setError] = useState('')
  const requestVersionRef = useRef(0)
  const requestContextKey = [
    currentUser?.uid || 'guest',
    isAuthLoading ? 'loading' : 'ready',
    postView,
    selectedDateKey || '',
  ].join(':')
  const requestContextKeyRef = useRef(requestContextKey)

  if (requestContextKeyRef.current !== requestContextKey) {
    requestContextKeyRef.current = requestContextKey
    requestVersionRef.current += 1
  }

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
          setPage({
            hasMore: Boolean(response.has_more),
            isLoading: false,
            isLoadingMore: false,
            nextCursor: response.next_cursor || '',
            posts: response.posts || [],
          })
        }
      } catch (loadError) {
        if (!ignore && isCurrentRequest(request)) {
          setError(loadError instanceof Error ? loadError.message : 'Unable to load Need a Sub.')
          setPage({
            ...buildEmptyPage(),
            isLoading: false,
          })
        }
      }
    }

    loadInitialNeedASub()

    return () => {
      ignore = true
    }
  }, [beginRequest, currentUser, isAuthLoading, isCurrentRequest, postView, selectedDateKey])

  const refreshNeedASub = useCallback(async ({ showLoading = false } = {}) => {
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

    if (showLoading) {
      setPage(buildEmptyPage())
    }
    setError('')
    const request = beginRequest()

    try {
      const response = await listNeedASubPostCards(currentUser, {
        limit: NEED_SUB_PAGE_LIMIT,
        startsOn: selectedDateKey,
        view: postView,
      })

      if (!isCurrentRequest(request)) {
        return
      }

      setPage({
        hasMore: Boolean(response.has_more),
        isLoading: false,
        isLoadingMore: false,
        nextCursor: response.next_cursor || '',
        posts: response.posts || [],
      })
    } catch (loadError) {
      if (!isCurrentRequest(request)) {
        return
      }

      setError(loadError instanceof Error ? loadError.message : 'Unable to load Need a Sub.')
      setPage({
        ...buildEmptyPage(),
        isLoading: false,
      })
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

      setError(loadError instanceof Error ? loadError.message : 'Unable to load more Need a Sub posts.')
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

  useEffect(() => {
    function refreshVisibleNeedASub() {
      if (document.visibilityState === 'visible') {
        refreshNeedASub()
      }
    }

    window.addEventListener('focus', refreshNeedASub)
    document.addEventListener('visibilitychange', refreshVisibleNeedASub)

    return () => {
      window.removeEventListener('focus', refreshNeedASub)
      document.removeEventListener('visibilitychange', refreshVisibleNeedASub)
    }
  }, [refreshNeedASub])

  return {
    error,
    hasMorePosts: page.hasMore,
    isLoading: page.isLoading,
    isLoadingMore: page.isLoadingMore,
    loadMoreNeedASub,
    posts: page.posts,
    refreshNeedASub,
    setError,
  }
}
