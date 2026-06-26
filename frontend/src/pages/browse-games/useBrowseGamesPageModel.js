import { useEffect, useMemo, useRef, useState } from 'react'
import { DATE_PAGE_SIZE } from './browseGamesData.js'
import { loadBrowseGamesPage } from './browseGamesApi.js'
import {
  buildDateOptions,
  groupGamesByHour,
} from './browseGamesSelectors.js'

const BROWSE_GAME_PAGE_LIMIT = 40

export function useBrowseGamesPageModel() {
  const [games, setGames] = useState([])
  const [selectedDateKey, setSelectedDateKey] = useState('')
  const [datePageIndex, setDatePageIndex] = useState(0)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [nowMs, setNowMs] = useState(null)
  const [nextCursor, setNextCursor] = useState(null)
  const [hasMoreGames, setHasMoreGames] = useState(false)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const activeDateKeyRef = useRef('')
  const requestVersionRef = useRef(0)

  useEffect(() => {
    function updateNow() {
      setNowMs(Date.now())
    }

    updateNow()
    const intervalId = window.setInterval(updateNow, 30000)

    return () => window.clearInterval(intervalId)
  }, [])

  const dateOptions = useMemo(
    () => (nowMs === null ? [] : buildDateOptions(nowMs)),
    [nowMs],
  )
  const activeDateKey = dateOptions.some((date) => date.key === selectedDateKey)
    ? selectedDateKey
    : dateOptions[0]?.key || ''
  const datePageCount = Math.ceil(dateOptions.length / DATE_PAGE_SIZE)
  const activeDateIndex = dateOptions.findIndex((date) => date.key === activeDateKey)
  const displayedDatePageIndex = activeDateIndex === -1
    ? Math.min(datePageIndex, Math.max(datePageCount - 1, 0))
    : Math.floor(activeDateIndex / DATE_PAGE_SIZE)
  const visibleDateOptions = dateOptions.slice(
    displayedDatePageIndex * DATE_PAGE_SIZE,
    displayedDatePageIndex * DATE_PAGE_SIZE + DATE_PAGE_SIZE,
  )
  const timeGroups = useMemo(() => groupGamesByHour(games), [games])

  useEffect(() => {
    activeDateKeyRef.current = activeDateKey
  }, [activeDateKey])

  useEffect(() => {
    let ignore = false
    const requestVersion = requestVersionRef.current + 1
    requestVersionRef.current = requestVersion

    async function loadSelectedDateGames() {
      if (!activeDateKey) {
        return
      }

      setStatus('loading')
      setError('')
      setGames([])
      setNextCursor(null)
      setHasMoreGames(false)
      setIsLoadingMore(false)

      try {
        const pageData = await loadBrowseGamesPage({
          startsOn: activeDateKey,
          limit: BROWSE_GAME_PAGE_LIMIT,
        })

        if (!ignore && requestVersion === requestVersionRef.current) {
          setGames(pageData.games || [])
          setNextCursor(pageData.next_cursor || null)
          setHasMoreGames(Boolean(pageData.has_more))
          setStatus('success')
        }
      } catch (requestError) {
        if (!ignore && requestVersion === requestVersionRef.current) {
          setError(requestError instanceof Error ? requestError.message : 'Unable to load games.')
          setStatus('error')
        }
      }
    }

    loadSelectedDateGames()

    return () => {
      ignore = true
    }
  }, [activeDateKey])

  function selectDatePage(nextPageIndex) {
    const safePageIndex = Math.min(Math.max(nextPageIndex, 0), Math.max(datePageCount - 1, 0))
    const nextDateKey = dateOptions[safePageIndex * DATE_PAGE_SIZE]?.key || activeDateKey

    if (nextDateKey !== activeDateKey) {
      requestVersionRef.current += 1
      activeDateKeyRef.current = nextDateKey
      setIsLoadingMore(false)
    }
    setDatePageIndex(safePageIndex)
    setSelectedDateKey(nextDateKey)
  }

  function selectDate(nextDateKey) {
    if (nextDateKey !== activeDateKey) {
      requestVersionRef.current += 1
      activeDateKeyRef.current = nextDateKey
      setIsLoadingMore(false)
    }
    setSelectedDateKey(nextDateKey)
  }

  async function loadMoreGames() {
    if (!activeDateKey || !nextCursor || isLoadingMore) {
      return
    }

    const requestDateKey = activeDateKey
    const requestVersion = requestVersionRef.current

    setIsLoadingMore(true)
    setError('')

    try {
      const pageData = await loadBrowseGamesPage({
        startsOn: activeDateKey,
        limit: BROWSE_GAME_PAGE_LIMIT,
        cursor: nextCursor,
      })

      if (
        requestVersion !== requestVersionRef.current
        || requestDateKey !== activeDateKeyRef.current
      ) {
        return
      }

      setGames((currentGames) => [...currentGames, ...(pageData.games || [])])
      setNextCursor(pageData.next_cursor || null)
      setHasMoreGames(Boolean(pageData.has_more))
    } catch (requestError) {
      if (
        requestVersion !== requestVersionRef.current
        || requestDateKey !== activeDateKeyRef.current
      ) {
        return
      }

      setError(requestError instanceof Error ? requestError.message : 'Unable to load more games.')
    } finally {
      if (
        requestVersion === requestVersionRef.current
        && requestDateKey === activeDateKeyRef.current
      ) {
        setIsLoadingMore(false)
      }
    }
  }

  return {
    activeDateKey,
    canGoNextDates: displayedDatePageIndex < datePageCount - 1,
    canGoPreviousDates: displayedDatePageIndex > 0,
    datePageIndex: displayedDatePageIndex,
    error,
    hasMoreGames,
    isLoadingMore,
    loadMoreGames,
    selectDatePage,
    setSelectedDateKey: selectDate,
    status,
    timeGroups,
    visibleDateOptions,
  }
}
