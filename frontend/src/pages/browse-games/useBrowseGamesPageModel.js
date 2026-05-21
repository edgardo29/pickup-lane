import { useEffect, useMemo, useState } from 'react'
import { DATE_PAGE_SIZE } from './browseGamesData.js'
import { loadBrowseGamesData } from './browseGamesApi.js'
import {
  buildDateOptions,
  buildImageUrlsByGameId,
  buildParticipantCountsByGameId,
  getDateKey,
  getVisibleGames,
  groupGamesByHour,
} from './browseGamesSelectors.js'

export function useBrowseGamesPageModel() {
  const [games, setGames] = useState([])
  const [gameImages, setGameImages] = useState([])
  const [participants, setParticipants] = useState([])
  const [selectedDateKey, setSelectedDateKey] = useState('')
  const [datePageIndex, setDatePageIndex] = useState(0)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [nowMs, setNowMs] = useState(null)

  useEffect(() => {
    function updateNow() {
      setNowMs(Date.now())
    }

    updateNow()
    const intervalId = window.setInterval(updateNow, 30000)

    return () => window.clearInterval(intervalId)
  }, [])

  useEffect(() => {
    let ignore = false

    async function loadPageData() {
      setStatus('loading')
      setError('')

      try {
        const pageData = await loadBrowseGamesData()

        if (!ignore) {
          setGames(pageData.games)
          setGameImages(pageData.gameImages)
          setParticipants(pageData.participants)
          setStatus('success')
        }
      } catch (requestError) {
        if (!ignore) {
          setError(requestError instanceof Error ? requestError.message : 'Unable to load games.')
          setStatus('error')
        }
      }
    }

    loadPageData()

    return () => {
      ignore = true
    }
  }, [])

  const visibleGames = useMemo(
    () => (nowMs === null ? [] : getVisibleGames(games, nowMs)),
    [games, nowMs],
  )
  const dateOptions = useMemo(
    () => (nowMs === null ? [] : buildDateOptions(nowMs)),
    [nowMs],
  )
  const activeDateKey = dateOptions.some((date) => date.key === selectedDateKey)
    ? selectedDateKey
    : dateOptions[0]?.key || ''
  const datePageCount = Math.ceil(dateOptions.length / DATE_PAGE_SIZE)
  const visibleDateOptions = dateOptions.slice(
    datePageIndex * DATE_PAGE_SIZE,
    datePageIndex * DATE_PAGE_SIZE + DATE_PAGE_SIZE,
  )
  const gamesForSelectedDate = useMemo(
    () => visibleGames.filter((game) => getDateKey(game.starts_at) === activeDateKey),
    [activeDateKey, visibleGames],
  )
  const imageUrlsByGameId = useMemo(() => buildImageUrlsByGameId(gameImages), [gameImages])
  const participantCountsByGameId = useMemo(
    () => buildParticipantCountsByGameId(participants),
    [participants],
  )
  const timeGroups = useMemo(() => groupGamesByHour(gamesForSelectedDate), [gamesForSelectedDate])

  function selectDatePage(nextPageIndex) {
    const safePageIndex = Math.min(Math.max(nextPageIndex, 0), Math.max(datePageCount - 1, 0))
    const nextDate = dateOptions[safePageIndex * DATE_PAGE_SIZE]

    setDatePageIndex(safePageIndex)
    if (nextDate) {
      setSelectedDateKey(nextDate.key)
    }
  }

  return {
    activeDateKey,
    canGoNextDates: datePageIndex < datePageCount - 1,
    canGoPreviousDates: datePageIndex > 0,
    datePageIndex,
    error,
    imageUrlsByGameId,
    participantCountsByGameId,
    selectDatePage,
    setSelectedDateKey,
    status,
    timeGroups,
    visibleDateOptions,
  }
}
