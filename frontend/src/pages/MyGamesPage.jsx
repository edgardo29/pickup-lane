import { Link } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import defaultCommunityVenueImage from '../assets/community-default/default-venue-wide.png'
import BrowseAppNav from '../components/BrowseAppNav.jsx'
import {
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  ShieldCheckIcon,
  SoccerBallIcon,
  UsersIcon,
} from '../components/BrowseIcons.jsx'
import { useAuth } from '../hooks/useAuth.js'
import { apiRequest, buildMediaUrl } from '../lib/apiClient.js'
import '../styles/browse-games/BrowseGamesPage.css'
import '../styles/my-games.css'

const ACTIVE_PARTICIPANT_STATUSES = new Set(['pending_payment', 'confirmed'])
const UPCOMING_MY_GAME_STATUSES = new Set(['pending_payment', 'confirmed', 'waitlisted'])
const HISTORY_MY_GAME_STATUSES = new Set(['confirmed'])
const GAME_CANCELLED_TYPES = new Set(['host_cancelled', 'admin_cancelled'])
const UPCOMING_WINDOW_DAYS = 14

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

  const participantCountsByGameId = useMemo(() => {
    const counts = new Map()

    participants.forEach((participant) => {
      if (!ACTIVE_PARTICIPANT_STATUSES.has(participant.participant_status)) {
        return
      }

      counts.set(participant.game_id, (counts.get(participant.game_id) || 0) + 1)
    })

    return counts
  }, [participants])

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
    <div className="browse-page my-games-page">
      <BrowseAppNav />

      <main className="browse-shell my-games-shell">
        <section className="browse-hero my-games-hero" aria-labelledby="my-games-title">
          <div className="browse-hero__copy my-games-hero__copy">
            <h1 id="my-games-title">
              <span>My Games</span>
            </h1>
            <div className="my-games-tabs" role="tablist" aria-label="My games sections">
              <button
                className={activeTab === 'upcoming' ? 'active' : ''}
                type="button"
                role="tab"
                aria-selected={activeTab === 'upcoming'}
                onClick={() => setActiveTab('upcoming')}
              >
                Upcoming
              </button>
              <button
                className={activeTab === 'history' ? 'active' : ''}
                type="button"
                role="tab"
                aria-selected={activeTab === 'history'}
                onClick={() => setActiveTab('history')}
              >
                History
              </button>
            </div>
          </div>

        </section>

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
                <>
                  {upcomingGroups.map((dateGroup) => (
                    <section className="my-games-agenda-day" key={dateGroup.key}>
                      <div className="time-section__header my-games-agenda-day__header">
                        <h2>
                          <CalendarIcon />
                          {dateGroup.label}
                        </h2>
                      </div>

                      <div className="my-games-agenda-grid">
                        {dateGroup.items.map((item) => (
                          <MyGameCard
                            imageUrl={imageUrlsByGameId.get(item.game.id)}
                            item={item}
                            participantCount={participantCountsByGameId.get(item.game.id) || 0}
                            key={item.participant.id}
                          />
                        ))}
                      </div>
                    </section>
                  ))}

                  {hasMoreUpcomingItems && (
                    <button
                      className="my-games-view-more"
                      type="button"
                      onClick={() => setVisibleUpcomingWindows((windowCount) => windowCount + 1)}
                    >
                      View more games
                    </button>
                  )}
                </>
              ) : (
                historyGroups.map((dateGroup) => (
                  <section className="my-games-agenda-day" key={dateGroup.key}>
                    <div className="time-section__header my-games-agenda-day__header">
                      <h2>
                        <CalendarIcon />
                        {dateGroup.label}
                      </h2>
                    </div>

                    <div className="my-games-agenda-grid">
                      {dateGroup.items.map((item) => (
                        <MyGameCard
                          imageUrl={imageUrlsByGameId.get(item.game.id)}
                          item={item}
                          participantCount={participantCountsByGameId.get(item.game.id) || 0}
                          key={item.participant.id}
                        />
                      ))}
                    </div>
                  </section>
                ))
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

function MyGameCard({ imageUrl, item, participantCount }) {
  const { bucket, game, statusLabel, statusTone } = item
  const tone = game.game_type === 'community' ? 'community' : 'official'
  const title = game.venue_name_snapshot || game.title
  const cardImageUrl = imageUrl || (tone === 'community' ? defaultCommunityVenueImage : '')
  const isFull = participantCount >= game.total_spots
  const isHistory = bucket === 'history'

  return (
    <Link
      className={`game-card game-card--${tone} ${
        isFull ? 'game-card--full' : ''
      } my-game-card my-game-card--${statusTone}`}
      to={`/games/${game.id}`}
    >
      <div className="game-card__media">
        <div className="game-card__fallback">
          <SoccerBallIcon />
        </div>

        {cardImageUrl && <img src={cardImageUrl} alt="" loading="lazy" />}

        <GameTypeBadge gameType={game.game_type} />
        {isFull && !isHistory && <span className="game-card__full-badge">Full</span>}
      </div>

      <div className="game-card__body">
        <div className="my-game-card__heading">
          <h3>{title}</h3>
          <span className={`my-game-card__status my-game-card__status--${statusTone}`}>
            {statusLabel}
          </span>
        </div>

        <p className="game-card__location">
          <MapPinIcon />
          {game.city_snapshot}
        </p>

        <p className="game-card__meta">
          <ClockIcon />
          {formatTimeRange(game.starts_at, game.ends_at)}
        </p>

        <p className="game-card__meta">
          <SoccerBallIcon />
          {formatEnvironment(game.environment_type)}
          <span aria-hidden="true">•</span>
          {game.format_label}
        </p>
      </div>

      <div className="game-card__footer">
        <span>
          <UsersIcon />
          <strong>
            {participantCount}/{game.total_spots}
          </strong>{' '}
          spots
        </span>

        <span>{formatPrice(game.price_per_player_cents, game.currency)}</span>
      </div>
    </Link>
  )
}

function GameTypeBadge({ gameType }) {
  const isCommunity = gameType === 'community'

  return (
    <span className={`game-card__badge game-card__badge--${gameType}`}>
      {isCommunity ? <SoccerBallIcon /> : <ShieldCheckIcon />}
      {isCommunity ? 'Community' : 'Official'}
    </span>
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

function buildMyGameItems(myParticipants, gamesById, currentUser, nowMs) {
  return myParticipants
    .map((participant) => {
      const game = gamesById.get(participant.game_id)

      if (!game || game.deleted_at || game.publish_status !== 'published') {
        return null
      }

      const isPast = new Date(game.ends_at).getTime() < nowMs || game.game_status === 'completed'
      const isCancelled = game.game_status === 'cancelled'
      const isHost = participant.participant_type === 'host' || game.host_user_id === currentUser?.id
      const bucket = getMyGameBucket(game, participant, isPast, isCancelled, isHost)

      if (!bucket) {
        return null
      }

      const status = getMyGameStatus(game, participant, isHost, bucket)

      return {
        bucket,
        game,
        isHost,
        participant,
        ...status,
      }
    })
    .filter(Boolean)
    .sort((first, second) =>
      first.bucket === 'history'
        ? new Date(second.game.starts_at) - new Date(first.game.starts_at)
        : new Date(first.game.starts_at) - new Date(second.game.starts_at),
    )
}

function getMyGameBucket(game, participant, isPast, isCancelled, isHost) {
  if (isCancelled) {
    return isGameCancelledHistoryParticipant(participant, isHost) ? 'history' : null
  }

  if (isPast) {
    return isHistoricalParticipant(participant, isHost) ? 'history' : null
  }

  if (UPCOMING_MY_GAME_STATUSES.has(participant.participant_status) || isHost) {
    return 'upcoming'
  }

  return null
}

function isGameCancelledHistoryParticipant(participant, isHost) {
  if (UPCOMING_MY_GAME_STATUSES.has(participant.participant_status) || isHost) {
    return true
  }

  return (
    participant.participant_status === 'cancelled' &&
    GAME_CANCELLED_TYPES.has(participant.cancellation_type)
  )
}

function isHistoricalParticipant(participant, isHost) {
  return HISTORY_MY_GAME_STATUSES.has(participant.participant_status) || isHost
}

function getVisibleUpcomingItems(items, visibleWindowCount, nowMs) {
  const windowEnd = nowMs + visibleWindowCount * UPCOMING_WINDOW_DAYS * 24 * 60 * 60 * 1000

  return items.filter((item) => new Date(item.game.starts_at).getTime() <= windowEnd)
}

function getMyGameStatus(game, participant, isHost, bucket) {
  if (game.game_status === 'cancelled') {
    return { statusLabel: 'Cancelled', statusTone: 'cancelled' }
  }

  if (bucket === 'history') {
    return {
      statusLabel: isHost ? 'Hosted' : 'Played',
      statusTone: isHost ? 'hosted' : 'played',
    }
  }

  if (participant.participant_status === 'waitlisted') {
    return { statusLabel: 'Waitlisted', statusTone: 'waitlisted' }
  }

  if (isHost) {
    return { statusLabel: 'Hosting', statusTone: 'hosting' }
  }

  return { statusLabel: 'Confirmed', statusTone: 'confirmed' }
}

function groupUpcomingAgendaItems(items) {
  const dateGroups = new Map()

  items.forEach((item) => {
    const dateKey = getDateKey(item.game.starts_at)

    if (!dateGroups.has(dateKey)) {
      dateGroups.set(dateKey, {
        key: dateKey,
        label: formatAgendaDate(item.game.starts_at),
        items: [],
      })
    }

    dateGroups.get(dateKey).items.push(item)
  })

  return [...dateGroups.values()]
}

function groupHistoryAgendaItems(items) {
  const groups = items.reduce((groupMap, item) => {
    const key = getDateKey(item.game.starts_at)
    const label = formatAgendaDate(item.game.starts_at)

    if (!groupMap.has(key)) {
      groupMap.set(key, { key, label, items: [] })
    }

    groupMap.get(key).items.push(item)
    return groupMap
  }, new Map())

  return [...groups.values()]
}

function getDateKey(value) {
  const date = new Date(value)
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`
}

function formatAgendaDate(value) {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
    .format(new Date(value))
    .toUpperCase()
}

function formatStartTime(value) {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

function formatTimeRange(start, end) {
  return `${formatStartTime(start)} - ${formatStartTime(end)}`
}

function formatEnvironment(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1).replaceAll('_', ' ') : 'Pickup'
}

function formatPrice(cents, currency) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'USD',
    maximumFractionDigits: 0,
  }).format((cents || 0) / 100)
}

export default MyGamesPage
