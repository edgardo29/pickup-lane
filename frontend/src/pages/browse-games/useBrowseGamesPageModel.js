import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { DATE_PAGE_SIZE } from './browseGamesData.js'
import { loadBrowseGamesPage } from './browseGamesApi.js'
import {
  buildBrowseMetaFromPageData,
  buildDateOptions,
  getDatePageIndexForDate,
  getNextBrowseListGeneration,
  groupLoadedGamesByTimeGroups,
  resolveRequestedDateKey,
  shouldApplyBrowseRequest,
} from './browseGamesSelectors.js'

const BROWSE_GAME_PAGE_LIMIT = 40
const BROWSE_REFRESH_INTERVAL_MS = 60000

export function useBrowseGamesPageModel() {
  const [searchParams, setSearchParams] = useSearchParams()
  const rawDateKey = searchParams.get('date') || ''
  const requestedDateKey = resolveRequestedDateKey(rawDateKey)
  const [browseMeta, setBrowseMeta] = useState(null)
  const [games, setGames] = useState([])
  const [datePageIndex, setDatePageIndex] = useState(0)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [loadMoreError, setLoadMoreError] = useState('')
  const [nextCursor, setNextCursor] = useState(null)
  const [hasMoreGames, setHasMoreGames] = useState(false)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const activeDateKeyRef = useRef('')
  const listGenerationRef = useRef(0)
  const rawDateKeyRef = useRef(rawDateKey)
  const requestVersionRef = useRef(0)

  const activeDateKey = requestedDateKey || browseMeta?.browse_date || ''

  useEffect(() => {
    rawDateKeyRef.current = rawDateKey
  }, [rawDateKey])

  const dateOptions = useMemo(
    () => buildDateOptions({
      maximumDate: browseMeta?.maximum_browse_date,
      minimumDate: browseMeta?.minimum_browse_date,
      timeZone: browseMeta?.browse_timezone,
    }),
    [
      browseMeta?.browse_timezone,
      browseMeta?.maximum_browse_date,
      browseMeta?.minimum_browse_date,
    ],
  )
  const datePageCount = Math.ceil(dateOptions.length / DATE_PAGE_SIZE)
  const visibleDateOptions = dateOptions.slice(
    datePageIndex * DATE_PAGE_SIZE,
    datePageIndex * DATE_PAGE_SIZE + DATE_PAGE_SIZE,
  )
  const timeGroups = useMemo(
    () => groupLoadedGamesByTimeGroups(games, browseMeta?.time_groups || []),
    [browseMeta?.time_groups, games],
  )

  const replaceUrlDate = useCallback(
    (dateKey, { replace = false } = {}) => {
      setSearchParams({ date: dateKey }, { replace })
    },
    [setSearchParams],
  )

  const applyPageData = useCallback((pageData, { append = false } = {}) => {
    listGenerationRef.current = getNextBrowseListGeneration(
      listGenerationRef.current,
      { append },
    )
    setBrowseMeta(buildBrowseMetaFromPageData(pageData))
    setNextCursor(pageData.next_cursor || null)
    setHasMoreGames(Boolean(pageData.has_more))
    setGames((currentGames) => (
      append
        ? dedupeGames([...currentGames, ...(pageData.games || [])])
        : dedupeGames(pageData.games || [])
    ))
    activeDateKeyRef.current = pageData.browse_date || ''
  }, [])

  const loadFirstPage = useCallback(
    async ({ dateKey, signal, silent = false } = {}) => {
      const requestVersion = requestVersionRef.current + 1
      requestVersionRef.current = requestVersion

      if (!silent) {
        listGenerationRef.current = getNextBrowseListGeneration(listGenerationRef.current)
        setStatus('loading')
        setError('')
        setLoadMoreError('')
        setGames([])
        setNextCursor(null)
        setHasMoreGames(false)
        setIsLoadingMore(false)
      } else {
        setIsRefreshing(true)
      }

      try {
        const pageData = await loadBrowseGamesPage({
          startsOn: dateKey || undefined,
          limit: BROWSE_GAME_PAGE_LIMIT,
          signal,
        })

        if (requestVersion !== requestVersionRef.current) {
          return
        }

        applyPageData(pageData)
        setLoadMoreError('')
        setIsLoadingMore(false)
        setStatus('success')
        setError('')
        if (pageData.browse_date && rawDateKeyRef.current !== pageData.browse_date) {
          replaceUrlDate(pageData.browse_date, { replace: true })
        }
      } catch (requestError) {
        if (requestError?.name === 'AbortError') {
          return
        }

        if (requestVersion !== requestVersionRef.current) {
          return
        }

        if (!silent) {
          setError(requestError instanceof Error ? requestError.message : 'Unable to load games.')
          setStatus('error')
        }
      } finally {
        if (requestVersion === requestVersionRef.current) {
          setIsRefreshing(false)
        }
      }
    },
    [applyPageData, replaceUrlDate],
  )

  useEffect(() => {
    if (requestedDateKey && browseMeta?.browse_date === requestedDateKey) {
      activeDateKeyRef.current = requestedDateKey
      return undefined
    }

    if (
      !requestedDateKey
      && browseMeta?.browse_date
      && browseMeta.browse_date === browseMeta.browse_today
    ) {
      activeDateKeyRef.current = browseMeta.browse_date
      return undefined
    }

    const controller = new AbortController()
    activeDateKeyRef.current = requestedDateKey

    queueMicrotask(() => {
      if (controller.signal.aborted) {
        return
      }

      loadFirstPage({
        dateKey: requestedDateKey || undefined,
        signal: controller.signal,
      })
    })

    return () => {
      controller.abort()
    }
  }, [browseMeta?.browse_date, browseMeta?.browse_today, loadFirstPage, requestedDateKey])

  useEffect(() => {
    let ignore = false
    const nextPageIndex = getDatePageIndexForDate(
      dateOptions,
      activeDateKey,
      DATE_PAGE_SIZE,
    )
    if (nextPageIndex !== null) {
      queueMicrotask(() => {
        if (!ignore) {
          setDatePageIndex(nextPageIndex)
        }
      })
    }

    return () => {
      ignore = true
    }
  }, [activeDateKey, dateOptions])

  useEffect(() => {
    if (!activeDateKey || status !== 'success') {
      return undefined
    }

    function refreshCurrentDate() {
      if (document.visibilityState === 'hidden') {
        return
      }

      loadFirstPage({ dateKey: activeDateKey, silent: true })
    }

    function handleVisibilityChange() {
      if (document.visibilityState === 'visible') {
        refreshCurrentDate()
      }
    }

    window.addEventListener('focus', refreshCurrentDate)
    document.addEventListener('visibilitychange', handleVisibilityChange)
    const intervalId = window.setInterval(refreshCurrentDate, BROWSE_REFRESH_INTERVAL_MS)

    return () => {
      window.removeEventListener('focus', refreshCurrentDate)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.clearInterval(intervalId)
    }
  }, [activeDateKey, loadFirstPage, status])

  function selectDatePage(nextPageIndex) {
    setDatePageIndex(Math.min(Math.max(nextPageIndex, 0), Math.max(datePageCount - 1, 0)))
  }

  function selectDate(nextDateKey) {
    if (nextDateKey === activeDateKey) {
      return
    }

    requestVersionRef.current += 1
    activeDateKeyRef.current = nextDateKey
    setStatus('loading')
    setError('')
    setLoadMoreError('')
    setGames([])
    setNextCursor(null)
    setHasMoreGames(false)
    setIsLoadingMore(false)
    setIsRefreshing(false)
    replaceUrlDate(nextDateKey)
  }

  function retryFirstPage() {
    loadFirstPage({ dateKey: activeDateKey || undefined })
  }

  async function loadMoreGames() {
    if (!activeDateKey || !nextCursor || isLoadingMore) {
      return
    }

    const requestDateKey = activeDateKey
    const requestGeneration = listGenerationRef.current

    setIsLoadingMore(true)
    setLoadMoreError('')

    try {
      const pageData = await loadBrowseGamesPage({
        startsOn: activeDateKey,
        limit: BROWSE_GAME_PAGE_LIMIT,
        cursor: nextCursor,
      })

      if (!shouldApplyBrowseRequest({
        currentDateKey: activeDateKeyRef.current,
        currentGeneration: listGenerationRef.current,
        requestDateKey,
        requestGeneration,
      })) {
        return
      }

      applyPageData(pageData, { append: true })
    } catch (requestError) {
      if (!shouldApplyBrowseRequest({
        currentDateKey: activeDateKeyRef.current,
        currentGeneration: listGenerationRef.current,
        requestDateKey,
        requestGeneration,
      })) {
        return
      }

      setLoadMoreError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to load more games.',
      )
    } finally {
      if (shouldApplyBrowseRequest({
        currentDateKey: activeDateKeyRef.current,
        currentGeneration: listGenerationRef.current,
        requestDateKey,
        requestGeneration,
      })) {
        setIsLoadingMore(false)
      }
    }
  }

  return {
    activeDateKey,
    browseTimezone: browseMeta?.browse_timezone || '',
    canGoNextDates: datePageIndex < datePageCount - 1,
    canGoPreviousDates: datePageIndex > 0,
    datePageIndex,
    error,
    hasMoreGames,
    isLoadingMore,
    isRefreshing,
    loadMoreError,
    loadMoreGames,
    retryFirstPage,
    retryLoadMore: loadMoreGames,
    selectDatePage,
    setSelectedDateKey: selectDate,
    status,
    timeGroups,
    visibleDateOptions,
  }
}

function dedupeGames(games) {
  const seenIds = new Set()
  return games.filter((game) => {
    if (seenIds.has(game.id)) {
      return false
    }

    seenIds.add(game.id)
    return true
  })
}
