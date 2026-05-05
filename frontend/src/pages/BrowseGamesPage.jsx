import { useEffect, useMemo, useState } from 'react'
import BrowseAppNav from '../components/BrowseAppNav.jsx'
import BrowseDateStrip from '../components/BrowseDateStrip.jsx'
import { MapPinIcon, SoccerBallIcon } from '../components/BrowseIcons.jsx'
import BrowseTimeSection from '../components/BrowseTimeSection.jsx'
import { apiRequest, buildMediaUrl } from '../lib/apiClient.js'
import '../styles/browse-games.css'

const ACTIVE_PARTICIPANT_STATUSES = new Set(['pending_payment', 'confirmed'])

function BrowseGamesPage() {
  const [games, setGames] = useState([])
  const [gameImages, setGameImages] = useState([])
  const [participants, setParticipants] = useState([])
  const [selectedDateKey, setSelectedDateKey] = useState('')
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')

  useEffect(() => {
    let ignore = false

    async function loadBrowseData() {
      setStatus('loading')
      setError('')

      try {
        const [gamesResponse, imagesResponse, participantsResponse] = await Promise.all([
          apiRequest('/games'),
          apiRequest('/game-images?image_status=active&is_primary=true'),
          apiRequest('/game-participants'),
        ])

        if (!ignore) {
          setGames(gamesResponse)
          setGameImages(imagesResponse)
          setParticipants(participantsResponse)
          setStatus('success')
        }
      } catch (requestError) {
        if (!ignore) {
          setError(requestError instanceof Error ? requestError.message : 'Unable to load games.')
          setStatus('error')
        }
      }
    }

    loadBrowseData()

    return () => {
      ignore = true
    }
  }, [])

  const visibleGames = useMemo(() => getVisibleGames(games), [games])
  const dateOptions = useMemo(() => buildDateOptions(visibleGames), [visibleGames])
  const activeDateKey = dateOptions.some((date) => date.key === selectedDateKey)
    ? selectedDateKey
    : dateOptions[0]?.key || ''

  const gamesForSelectedDate = useMemo(
    () => visibleGames.filter((game) => getDateKey(game.starts_at) === activeDateKey),
    [activeDateKey, visibleGames],
  )

  const imageUrlsByGameId = useMemo(() => {
    const images = new Map()

    gameImages.forEach((image) => {
      if (!images.has(image.game_id)) {
        images.set(image.game_id, buildMediaUrl(image.image_url))
      }
    })

    return images
  }, [gameImages])

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

  const timeGroups = useMemo(() => groupGamesByHour(gamesForSelectedDate), [gamesForSelectedDate])

  return (
    <div className="browse-page">
      <BrowseAppNav />

      <main className="browse-shell">
        <section className="browse-hero" aria-labelledby="browse-title">
          <div className="browse-hero__copy">
            <button className="location-pill" type="button">
              <MapPinIcon />
              Chicago, IL
            </button>

            <h1 id="browse-title">Find your next game</h1>
            <p>Pickup games available near Chicago</p>
          </div>
        </section>

        <section className="browse-panel" aria-label="Available games">
          <div className="browse-panel__summary">
            <span>
              <SoccerBallIcon />
              {visibleGames.length} {visibleGames.length === 1 ? 'game' : 'games'} available
            </span>
          </div>

          <BrowseDateStrip
            dates={dateOptions}
            selectedDateKey={activeDateKey}
            onSelectDate={setSelectedDateKey}
          />

          {status === 'loading' && <BrowseState title="Loading games" />}
          {status === 'error' && <BrowseState title="Could not load games" message={error} />}
          {status === 'success' && timeGroups.length === 0 && (
            <BrowseState title="No games found" message="Try another date or check back soon." />
          )}

          {status === 'success' && timeGroups.length > 0 && (
            <div className="browse-results">
              {timeGroups.map((group) => (
                <BrowseTimeSection
                  group={group}
                  imageUrlsByGameId={imageUrlsByGameId}
                  participantCountsByGameId={participantCountsByGameId}
                  key={group.label}
                />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

function BrowseState({ title, message }) {
  return (
    <div className="browse-state">
      <SoccerBallIcon />
      <h2>{title}</h2>
      {message && <p>{message}</p>}
    </div>
  )
}

function buildDateOptions(games) {
  const startDate = games.length > 0 ? new Date(games[0].starts_at) : new Date()

  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(startDate)
    date.setHours(12, 0, 0, 0)
    date.setDate(startDate.getDate() + index)

    return {
      key: getDateKey(date),
      weekday: new Intl.DateTimeFormat('en-US', { weekday: 'short' }).format(date).toUpperCase(),
      month: new Intl.DateTimeFormat('en-US', { month: 'short' }).format(date),
      day: new Intl.DateTimeFormat('en-US', { day: 'numeric' }).format(date),
    }
  })
}

function getDateKey(value) {
  const date = new Date(value)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')

  return `${year}-${month}-${day}`
}

function getVisibleGames(games) {
  const now = Date.now()
  const upcomingGames = games
    .filter(
      (game) =>
        !game.deleted_at &&
        game.game_status !== 'cancelled' &&
        new Date(game.starts_at).getTime() >= now,
    )
    .sort((first, second) => new Date(first.starts_at) - new Date(second.starts_at))

  const publishedGames = upcomingGames.filter((game) => game.publish_status === 'published')

  return publishedGames.length > 0 ? publishedGames : upcomingGames
}

function groupGamesByHour(games) {
  const groupedGames = games.reduce((groups, game) => {
    const date = new Date(game.starts_at)
    const label = new Intl.DateTimeFormat('en-US', { hour: 'numeric' }).format(date)

    if (!groups.has(label)) {
      groups.set(label, [])
    }

    groups.get(label).push(game)
    return groups
  }, new Map())

  return [...groupedGames.entries()].map(([label, groupGames]) => ({
    label,
    games: groupGames,
  }))
}

export default BrowseGamesPage
