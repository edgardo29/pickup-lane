import { useEffect, useMemo, useState } from 'react'
import { AppPageHeader, AppPageShell, AppTabs } from '../../components/app/index.js'
import { SoccerBallIcon } from '../../components/BrowseIcons.jsx'
import { useAuth } from '../../hooks/useAuth.js'
import { apiRequest, buildMediaUrl } from '../../lib/apiClient.js'
import '../../styles/browse-games/BrowseGamesPage.css'
import '../../styles/my-games.css'
import HistoryGamesTab from './HistoryGamesTab.jsx'
import UpcomingGamesTab from './UpcomingGamesTab.jsx'
import {
  buildMyGameItems,
  buildParticipantCounts,
  getVisibleUpcomingItems,
  groupHistoryAgendaItems,
  groupUpcomingAgendaItems,
} from './myGamesData.js'

const tabs = [
  { key: 'upcoming', label: 'Upcoming' },
  { key: 'history', label: 'History' },
]

function MyGamesPage() {
  const { appUser, isLoading } = useAuth()
  const [activeTab, setActiveTab] = useState('upcoming')
  const [visibleUpcomingWindows, setVisibleUpcomingWindows] = useState(1)
  const [currentUser, setCurrentUser] = useState(null)
  const [games, setGames] = useState([])
  const [images, setImages] = useState([])
  const [participants, setParticipants] = useState([])
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

    async function loadMyGames() {
      setStatus('loading')
      setError('')

      try {
        if (isLoading) {
          return
        }

        if (!appUser?.id) {
          throw new Error('Sign in to view your games.')
        }

        const [gamesResponse, imagesResponse, participantsResponse, myParticipantsResponse] =
          await Promise.all([
            apiRequest('/games'),
            apiRequest('/game-images?image_status=active&is_primary=true'),
            apiRequest('/game-participants'),
            apiRequest(`/game-participants?user_id=${appUser.id}`),
          ])

        if (!ignore) {
          setCurrentUser(appUser)
          setGames(gamesResponse)
          setImages(imagesResponse)
          setParticipants(participantsResponse)
          setMyParticipants(myParticipantsResponse)
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

    loadMyGames()

    return () => {
      ignore = true
    }
  }, [appUser, isLoading])

  const gamesById = useMemo(() => new Map(games.map((game) => [game.id, game])), [games])
  const imageUrlsByGameId = useMemo(() => {
    const imageMap = new Map()

    images.forEach((image) => {
      if (!imageMap.has(image.game_id)) {
        imageMap.set(image.game_id, buildMediaUrl(image.image_url))
      }
    })

    return imageMap
  }, [images])
  const participantCountsByGameId = useMemo(
    () => buildParticipantCounts(participants),
    [participants],
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

  return (
    <AppPageShell className="browse-page my-games-page">
      <AppPageHeader
        title="My Games"
        tabs={<AppTabs ariaLabel="My games sections" items={tabs} onChange={setActiveTab} value={activeTab} />}
      />

      <section className="browse-panel my-games-panel" aria-label="My games">
        {status === 'loading' && <MyGamesState title="Loading your games" />}
        {status === 'error' && <MyGamesState title="Could not load games" message={error} />}
        {status === 'success' && activeItems.length === 0 && (
          <MyGamesState
            title={
              activeTab === 'history'
                ? 'No game history yet'
                : hasHiddenUpcomingItems
                  ? 'No games in this window'
                  : 'No upcoming games yet'
            }
            message={
              hasHiddenUpcomingItems
                ? 'You have games scheduled further out.'
                : 'Once you join or host a game, it will show up here.'
            }
          />
        )}

        {status === 'success' && (activeItems.length > 0 || hasMoreUpcomingItems) && (
          <div className="browse-results my-games-timeline">
            {activeTab === 'upcoming' ? (
              <UpcomingGamesTab
                groups={upcomingGroups}
                hasMoreItems={hasMoreUpcomingItems}
                imageUrlsByGameId={imageUrlsByGameId}
                participantCountsByGameId={participantCountsByGameId}
                onViewMore={() => setVisibleUpcomingWindows((windowCount) => windowCount + 1)}
              />
            ) : (
              <HistoryGamesTab
                groups={historyGroups}
                imageUrlsByGameId={imageUrlsByGameId}
                participantCountsByGameId={participantCountsByGameId}
              />
            )}
          </div>
        )}
      </section>
    </AppPageShell>
  )
}

function MyGamesState({ title, message }) {
  return (
    <div className="my-games-state">
      <SoccerBallIcon />
      <h2>{title}</h2>
      {message && <p>{message}</p>}
    </div>
  )
}

export default MyGamesPage
