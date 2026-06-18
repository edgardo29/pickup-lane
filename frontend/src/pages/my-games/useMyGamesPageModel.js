import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../../hooks/useAuth.js'
import { buildImageUrlsByGameId } from '../browse-games/browseGamesSelectors.js'
import { loadMyGamesData } from './myGamesApi.js'
import {
  buildMyGameItems,
  buildParticipantCounts,
  getVisibleUpcomingItems,
  groupHistoryAgendaItems,
  groupUpcomingAgendaItems,
} from './myGamesSelectors.js'

export function useMyGamesPageModel() {
  const { appUser, currentUser: firebaseUser, isLoading } = useAuth()
  const [activeTab, setActiveTab] = useState('upcoming')
  const [visibleUpcomingWindows, setVisibleUpcomingWindows] = useState(1)
  const [currentUser, setCurrentUser] = useState(null)
  const [games, setGames] = useState([])
  const [images, setImages] = useState([])
  const [venueImages, setVenueImages] = useState([])
  const [participantCounts, setParticipantCounts] = useState([])
  const [myParticipants, setMyParticipants] = useState([])
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
        if (isLoading) {
          return
        }

        if (!appUser?.id) {
          throw new Error('Sign in to view your games.')
        }

        const pageData = await loadMyGamesData(firebaseUser)

        if (!ignore) {
          setCurrentUser(appUser)
          setGames(pageData.games)
          setImages(pageData.images)
          setVenueImages(pageData.venueImages || [])
          setParticipantCounts(pageData.participantCounts)
          setMyParticipants(pageData.myParticipants)
          setStatus('success')
        }
      } catch (requestError) {
        if (!ignore) {
          setError(
            requestError instanceof Error ? requestError.message : 'Unable to load your games.',
          )
          setStatus('error')
        }
      }
    }

    loadPageData()

    return () => {
      ignore = true
    }
  }, [appUser, firebaseUser, isLoading])

  const gamesById = useMemo(() => new Map(games.map((game) => [game.id, game])), [games])
  const imageUrlsByGameId = useMemo(
    () => buildImageUrlsByGameId(games, images, venueImages),
    [games, images, venueImages],
  )
  const participantCountsByGameId = useMemo(
    () => buildParticipantCounts(participantCounts),
    [participantCounts],
  )
  const myGameItems = useMemo(
    () => (nowMs === null ? [] : buildMyGameItems(myParticipants, gamesById, currentUser, nowMs)),
    [currentUser, gamesById, myParticipants, nowMs],
  )
  const upcomingItems = myGameItems.filter((item) => item.bucket === 'upcoming')
  const historyItems = myGameItems.filter((item) => item.bucket === 'history')
  const visibleUpcomingItems = useMemo(
    () => (nowMs === null ? [] : getVisibleUpcomingItems(upcomingItems, visibleUpcomingWindows, nowMs)),
    [nowMs, upcomingItems, visibleUpcomingWindows],
  )
  const hasMoreUpcomingItems = visibleUpcomingItems.length < upcomingItems.length
  const activeItems = activeTab === 'history' ? historyItems : visibleUpcomingItems
  const hasHiddenUpcomingItems =
    activeTab === 'upcoming' && upcomingItems.length > 0 && visibleUpcomingItems.length === 0
  const upcomingGroups = useMemo(
    () => groupUpcomingAgendaItems(visibleUpcomingItems),
    [visibleUpcomingItems],
  )
  const historyGroups = useMemo(() => groupHistoryAgendaItems(historyItems), [historyItems])

  function showMoreUpcomingItems() {
    setVisibleUpcomingWindows((windowCount) => windowCount + 1)
  }

  return {
    activeItems,
    activeTab,
    error,
    hasHiddenUpcomingItems,
    hasMoreUpcomingItems,
    historyGroups,
    imageUrlsByGameId,
    participantCountsByGameId,
    setActiveTab,
    showMoreUpcomingItems,
    status,
    upcomingGroups,
  }
}
