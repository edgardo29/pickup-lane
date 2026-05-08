import { Link } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import defaultCommunityVenueImage from '../assets/community-default/default-venue.png'
import BrowseAppNav from '../components/BrowseAppNav.jsx'
import {
  CalendarIcon,
  MapPinIcon,
  ShieldCheckIcon,
  SoccerBallIcon,
  UsersIcon,
} from '../components/BrowseIcons.jsx'
import { useAuth } from '../hooks/useAuth.js'
import { apiRequest, buildMediaUrl } from '../lib/apiClient.js'
import '../styles/browse-games.css'
import '../styles/my-games.css'

const ACTIVE_PARTICIPANT_STATUSES = new Set(['pending_payment', 'confirmed'])

function MyGamesPage() {
  const { appUser, isLoading } = useAuth()
  const [activeTab, setActiveTab] = useState('upcoming')
  const [currentUser, setCurrentUser] = useState(null)
  const [games, setGames] = useState([])
  const [images, setImages] = useState([])
  const [participants, setParticipants] = useState([])
  const [myParticipants, setMyParticipants] = useState([])
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')

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
    () => buildMyGameItems(myParticipants, gamesById, currentUser),
    [currentUser, gamesById, myParticipants],
  )
  const upcomingItems = myGameItems.filter((item) => item.bucket === 'upcoming')
  const historyItems = myGameItems.filter((item) => item.bucket === 'history')
  const activeItems = activeTab === 'history' ? historyItems : upcomingItems
  const historyGroups = useMemo(() => groupMyGameItems(historyItems), [historyItems])

  return (
    <div className="my-games-page">
      <BrowseAppNav />

      <main className="my-games-shell">
        <section className="my-games-hero">
          <div>
            <h1>My Games</h1>
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

          <Link className="my-games-hero__calendar" to="/games" aria-label="Browse games">
            <CalendarIcon />
          </Link>
        </section>

        {status === 'loading' && <MyGamesState title="Loading your games" />}
        {status === 'error' && <MyGamesState title="Could not load games" message={error} />}
        {status === 'success' && activeItems.length === 0 && (
          <MyGamesState
            title={activeTab === 'history' ? 'No game history yet' : 'No upcoming games yet'}
            message="Once you join or host a game, it will show up here."
          />
        )}

        {status === 'success' && activeItems.length > 0 && (
          <div className="my-games-timeline">
            {activeTab === 'upcoming' ? (
              <section className="my-games-group">
                <div className="my-games-group__items">
                  {upcomingItems.map((item) => (
                    <MyGameCard
                      imageUrl={imageUrlsByGameId.get(item.game.id)}
                      item={item}
                      participantCount={participantCountsByGameId.get(item.game.id) || 0}
                      key={item.participant.id}
                    />
                  ))}
                </div>
              </section>
            ) : (
              historyGroups.map((group) => (
                <section className="my-games-group" key={group.key}>
                  <h2>{group.label}</h2>

                  <div className="my-games-group__items">
                    {group.items.map((item) => (
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
      </main>
    </div>
  )
}

function MyGameCard({ imageUrl, item, participantCount }) {
  const { game, isHost, statusLabel, statusTone } = item
  const tone = statusTone === 'cancelled' ? 'cancelled' : game.game_type
  const cardImageUrl = imageUrl || (game.game_type === 'community' ? defaultCommunityVenueImage : '')

  return (
    <Link
      className={`game-card my-game-card my-game-card--${tone} my-game-card--${statusTone}`}
      to={`/games/${game.id}`}
    >
      <div className="game-card__media">
        <div className="game-card__fallback">
          <SoccerBallIcon />
        </div>

        {cardImageUrl && <img src={cardImageUrl} alt="" loading="lazy" />}

        <span className="game-card__time">{formatStartTime(game.starts_at)}</span>
        <GameTypeBadge gameType={game.game_type} isCancelled={statusTone === 'cancelled'} />
      </div>

      <div className="game-card__body">
        <div className="my-game-card__title-row">
          <h3>{game.title}</h3>
          {isHost && <span className="my-game-card__host-badge">Your Game</span>}
        </div>

        <p className="game-card__location my-game-card__date">
          <CalendarIcon />
          {formatShortDate(game.starts_at)}
        </p>

        <p className="game-card__location">
          <MapPinIcon />
          {game.neighborhood_snapshot || game.city_snapshot}, {game.state_snapshot}
        </p>

        <p className="game-card__meta">
          {formatEnvironment(game.environment_type)}
          <span aria-hidden="true">•</span>
          {game.format_label}
        </p>

        <div className="game-card__footer my-game-card__footer">
          <span>
            <UsersIcon />
            <strong>{participantCount}/{game.total_spots}</strong> players
          </span>

          <span className={`my-game-card__status my-game-card__status--${statusTone}`}>
            {statusLabel}
          </span>
        </div>
      </div>
    </Link>
  )
}

function GameTypeBadge({ gameType, isCancelled }) {
  const isCommunity = gameType === 'community'

  return (
    <span
      className={`game-card__badge game-card__badge--${gameType} ${
        isCancelled ? 'game-card__badge--cancelled' : ''
      }`}
    >
      {isCommunity ? <SoccerBallIcon /> : <ShieldCheckIcon />}
      {isCancelled ? 'Cancelled' : isCommunity ? 'Community' : 'Official'}
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

function buildMyGameItems(myParticipants, gamesById, currentUser) {
  const now = Date.now()

  return myParticipants
    .map((participant) => {
      const game = gamesById.get(participant.game_id)

      if (!game || game.deleted_at || game.publish_status !== 'published') {
        return null
      }

      const isPast = new Date(game.ends_at).getTime() < now || game.game_status === 'completed'
      const isCancelled = game.game_status === 'cancelled'
      const isHost = participant.participant_type === 'host' || game.host_user_id === currentUser?.id
      const bucket = isPast || isCancelled ? 'history' : 'upcoming'
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

function getMyGameStatus(game, participant, isHost, bucket) {
  if (game.game_status === 'cancelled') {
    return { statusLabel: 'Cancelled', statusTone: 'cancelled' }
  }

  if (bucket === 'history') {
    return {
      statusLabel: participant.attendance_status === 'attended' ? 'Played' : 'Completed',
      statusTone: 'history',
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

function groupMyGameItems(items) {
  const groups = items.reduce((groupMap, item) => {
    const key = getMonthKey(item.game.starts_at)
    const label = formatMonth(item.game.starts_at)

    if (!groupMap.has(key)) {
      groupMap.set(key, { key, label, items: [] })
    }

    groupMap.get(key).items.push(item)
    return groupMap
  }, new Map())

  return [...groups.values()]
}

function getMonthKey(value) {
  const date = new Date(value)
  return `${date.getFullYear()}-${date.getMonth()}`
}

function formatMonth(value) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'long',
    year: 'numeric',
  }).format(new Date(value))
}

function formatShortDate(value) {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value))
}

function formatStartTime(value) {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

function formatEnvironment(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1).replaceAll('_', ' ') : 'Pickup'
}

export default MyGamesPage
