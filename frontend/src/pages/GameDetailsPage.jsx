import { Link, useNavigate, useParams } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import defaultCommunityVenueImage from '../assets/community-default/default-venue.png'
import BrowseAppNav from '../components/BrowseAppNav.jsx'
import {
  BuildingIcon,
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  StopwatchIcon,
  UsersIcon,
} from '../components/BrowseIcons.jsx'
import {
  BookingRulesCard,
  ChatPanel,
  DetailsScaffold,
  DetailsState,
  GameChatCard,
  GameGallery,
  JoinCard,
  PlayersCard,
  PlayersListModal,
  QuickFacts,
  StatusPill,
  WhereToGoCard,
} from '../components/GameDetailsSections.jsx'
import { useAuth } from '../hooks/useAuth.js'
import { apiRequest, buildMediaUrl } from '../lib/apiClient.js'
import '../styles/game-details.css'

const ACTIVE_PARTICIPANT_STATUSES = new Set(['pending_payment', 'confirmed'])
const GUEST_JOIN_MESSAGE = 'Sign in or create an account to join this game.'

function GameDetailsPage() {
  const { gameId } = useParams()
  const navigate = useNavigate()
  const { appUser } = useAuth()

  const [game, setGame] = useState(null)
  const [venue, setVenue] = useState(null)
  const [gameImages, setGameImages] = useState([])
  const [participants, setParticipants] = useState([])
  const [currentUser, setCurrentUser] = useState(null)
  const [chatMessages, setChatMessages] = useState([])
  const [activeImageIndex, setActiveImageIndex] = useState(0)
  const [joinNotice, setJoinNotice] = useState(false)
  const [isPlayerListOpen, setIsPlayerListOpen] = useState(false)
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [hasUnreadChat, setHasUnreadChat] = useState(false)
  const [activePlayerTab, setActivePlayerTab] = useState('going')
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')

  useEffect(() => {
    let ignore = false

    async function loadGameDetails() {
      setStatus('loading')
      setError('')
      setJoinNotice(false)
      setIsPlayerListOpen(false)
      setIsChatOpen(false)
      setHasUnreadChat(false)
      setActivePlayerTab('going')
      setActiveImageIndex(0)

      try {
        const gameResponse = await apiRequest(`/games/${gameId}`)

        const [imagesResponse, participantsResponse, venueResponse, chatsResponse] =
          await Promise.all([
            apiRequest(`/game-images?game_id=${gameId}&image_status=active`),
            apiRequest(`/game-participants?game_id=${gameId}`),
            apiRequest(`/venues/${gameResponse.venue_id}`).catch(() => null),
            gameResponse.is_chat_enabled
              ? apiRequest(`/game-chats?game_id=${gameId}&chat_status=active`).catch(() => [])
              : Promise.resolve([]),
          ])

        const activeChat = chatsResponse[0]
        const messagesResponse = activeChat
          ? await apiRequest(`/chat-messages?chat_id=${activeChat.id}&moderation_status=visible`).catch(
              () => [],
            )
          : []

        if (!ignore) {
          setGame(gameResponse)
          setVenue(venueResponse)
          setGameImages(imagesResponse)
          setParticipants(participantsResponse)
          setCurrentUser(appUser || null)
          setChatMessages(messagesResponse)
          setHasUnreadChat(messagesResponse.length > 0)
          setStatus('success')
        }
      } catch (requestError) {
        if (!ignore) {
          setError(requestError instanceof Error ? requestError.message : 'Unable to load game.')
          setStatus('error')
        }
      }
    }

    loadGameDetails()

    return () => {
      ignore = true
    }
  }, [appUser, gameId])

  const images = useMemo(
    () => {
      const galleryImages = gameImages
        .slice()
        .sort(
          (first, second) =>
            Number(second.is_primary) - Number(first.is_primary) ||
            first.sort_order - second.sort_order ||
            new Date(first.created_at) - new Date(second.created_at),
        )
        .map((image) => buildMediaUrl(image.image_url))

      if (galleryImages.length === 0 && game?.game_type === 'community') {
        return [defaultCommunityVenueImage]
      }

      return galleryImages
    },
    [game?.game_type, gameImages],
  )

  const participantSummary = useMemo(
    () => getParticipantSummary(participants, game?.total_spots),
    [game?.total_spots, participants],
  )
  const latestChatMessage = chatMessages.at(-1) || null
  const chatSenderNames = useMemo(() => buildChatSenderNames(participants), [participants])

  if (status === 'loading') {
    return <DetailsScaffold state={<DetailsState title="Loading game" />} />
  }

  if (status === 'error') {
    return <DetailsScaffold state={<DetailsState title="Could not load game" message={error} />} />
  }

  if (!game) {
    return (
      <DetailsScaffold
        state={
          <>
            <DetailsState title="Game not found" message="This game may no longer be available." />
            <Link className="details-back-link" to="/games">
              Back to games
            </Link>
          </>
        }
      />
    )
  }

  const title = game.title || `${game.venue_name_snapshot || 'Pickup'} Game`
  const venueName = game.venue_name_snapshot || venue?.name || 'Pickup Lane'
  const neighborhood = game.neighborhood_snapshot || venue?.neighborhood || game.city_snapshot
  const city = game.city_snapshot || venue?.city || 'Chicago'
  const gameToneLabel = game.game_type === 'community' ? 'Community Game' : 'Official Game'
  const dateLabel = formatDate(game.starts_at)
  const timeLabel = formatTimeRange(game.starts_at, game.ends_at)
  const durationLabel = getDurationLabel(game.starts_at, game.ends_at)
  const environmentLabel = formatEnvironment(game.environment_type)
  const price = formatPrice(game.price_per_player_cents, game.currency)
  const facts = [
    { icon: <CalendarIcon />, label: dateLabel },
    { icon: <ClockIcon />, label: timeLabel },
    { icon: <StopwatchIcon />, label: durationLabel },
    { icon: <BuildingIcon />, label: environmentLabel },
    { icon: <UsersIcon />, label: game.format_label || 'Pickup' },
  ]
  const venueAddress = formatVenueAddress(game, venue)
  const mapsUrl = buildMapsUrl(venue, venueAddress)
  const aboutText =
    game.description ||
    'Fast-paced pickup soccer. All skill levels welcome. Show up ready to play and have fun.'
  const arrivalText =
    game.arrival_notes ||
    game.parking_notes ||
    'Check your confirmation before kickoff for final entry details.'
  const ruleItems = buildRuleItems(game)
  const canEditGame =
    game.game_type === 'community' &&
    currentUser?.id === game.host_user_id &&
    game.publish_status === 'published' &&
    ['scheduled', 'full'].includes(game.game_status)

  function handlePreviousImage() {
    setActiveImageIndex((currentIndex) =>
      currentIndex === 0 ? images.length - 1 : currentIndex - 1,
    )
  }

  function handleNextImage() {
    setActiveImageIndex((currentIndex) =>
      currentIndex === images.length - 1 ? 0 : currentIndex + 1,
    )
  }

  async function handleShareGame() {
    const shareData = {
      title,
      text: `${title} at ${venueName}`,
      url: window.location.href,
    }

    if (navigator.share) {
      await navigator.share(shareData).catch(() => {})
      return
    }

    await navigator.clipboard?.writeText(window.location.href).catch(() => {})
  }

  function handleJoinIntent() {
    setJoinNotice(true)
  }

  function handleOpenChat() {
    setIsChatOpen(true)
    setHasUnreadChat(false)
  }

  return (
    <div className="details-page">
      <BrowseAppNav />

      <main className="details-shell">
        <button className="details-mobile-back" type="button" onClick={() => navigate('/games')}>
          ←
        </button>

        <section className="details-layout">
          <div className="details-main">
            <div className="details-titlebar">
              <Link className="details-back-to-browse" to="/games">
                ← Back
              </Link>

              <StatusPill label={gameToneLabel} />

              {canEditGame && (
                <Link className="details-host-edit-link" to={`/games/${game.id}/edit`}>
                  Edit Game
                </Link>
              )}
            </div>

            <div className="details-heading">
              <h1>{title}</h1>
              <p>
                <MapPinIcon />
                {venueName} – {neighborhood}, {city}
              </p>
            </div>

            <GameGallery
              activeImageIndex={activeImageIndex}
              images={images}
              onNext={handleNextImage}
              onPrevious={handlePreviousImage}
              onSelectImage={setActiveImageIndex}
            />

            <QuickFacts facts={facts} price={price} variant="desktop" />

            <section className="details-mobile-summary">
              <div className="details-mobile-summary__meta">
                <StatusPill label={gameToneLabel} />
                {canEditGame && (
                  <Link className="details-host-edit-link" to={`/games/${game.id}/edit`}>
                    Edit Game
                  </Link>
                )}
              </div>

              <h1>{title}</h1>

              <p>
                <MapPinIcon />
                {venueName} – {neighborhood}, {city}
              </p>

              <QuickFacts facts={facts} price={price} variant="mobile" />
            </section>

            <section className="details-card-grid">
              <PlayersCard
                onOpenPlayerList={() => setIsPlayerListOpen(true)}
                participantSummary={participantSummary}
              />

              <GameChatCard
                hasUnread={hasUnreadChat}
                isChatEnabled={game.is_chat_enabled}
                latestChatMessage={latestChatMessage}
                onOpenChat={handleOpenChat}
                senderNames={chatSenderNames}
              />
            </section>

            <BookingRulesCard rules={ruleItems} />

            <WhereToGoCard
              address={venueAddress}
              arrivalText={arrivalText}
              mapIcon={<MapPinIcon />}
              mapsUrl={mapsUrl}
              venueName={venueName}
            />
          </div>

          <aside className="details-sidebar" aria-label="Join game">
            <JoinCard
              aboutText={aboutText}
              facts={facts}
              gameToneLabel={gameToneLabel}
              joinMessage={GUEST_JOIN_MESSAGE}
              joinNotice={joinNotice}
              onJoin={handleJoinIntent}
              onShare={handleShareGame}
              price={price}
            />
          </aside>
        </section>
      </main>

      <div className="details-mobile-join">
        <div>
          <strong>{price}</strong>
          <span>per player</span>
        </div>

        <button type="button" onClick={handleJoinIntent}>
          Join Game
        </button>

        {joinNotice && <p>{GUEST_JOIN_MESSAGE}</p>}
      </div>

      {isPlayerListOpen && (
        <PlayersListModal
          onClose={() => setIsPlayerListOpen(false)}
          activeTab={activePlayerTab}
          onSelectTab={setActivePlayerTab}
          participantSummary={participantSummary}
        />
      )}

      {isChatOpen && (
        <ChatPanel
          messages={chatMessages}
          onClose={() => setIsChatOpen(false)}
          senderNames={chatSenderNames}
        />
      )}
    </div>
  )
}

function getParticipantSummary(participants, totalSpots = 0) {
  const roster = participants
    .filter((participant) => ACTIVE_PARTICIPANT_STATUSES.has(participant.participant_status))
    .sort(
      (first, second) =>
        Number(first.roster_order || 999) - Number(second.roster_order || 999) ||
        first.display_name_snapshot.localeCompare(second.display_name_snapshot),
    )
  const waitlist = participants.filter(
    (participant) => participant.participant_status === 'waitlisted',
  )
  const host = roster.find((participant) => participant.participant_type === 'host') || null
  const spotsLeft = Math.max((totalSpots || 0) - roster.length, 0)

  return {
    host,
    roster,
    signedUpCount: roster.length,
    spotsLeft,
    totalSpots: totalSpots || roster.length,
    waitlist,
    waitlistCount: waitlist.length,
  }
}

function buildChatSenderNames(participants) {
  return participants.reduce((names, participant) => {
    if (participant.user_id && participant.display_name_snapshot) {
      names.set(participant.user_id, participant.display_name_snapshot)
    }

    return names
  }, new Map())
}

function buildRuleItems(game) {
  const isCommunityGame = game.game_type === 'community'
  const rules = [
    {
      title: 'Cancellation',
      kind: 'clock',
      text:
        game.custom_cancellation_text ||
        'Cancel 24+ hours before the game starts to receive game credit.',
    },
    {
      title: isCommunityGame ? 'If Host Cancels' : 'If We Cancel',
      kind: 'shield',
      text: isCommunityGame
        ? 'If the host cancels the game, players will receive full game credit.'
        : 'If the game is canceled by Pickup Lane, you will receive full game credit.',
    },
    {
      title: 'Weather',
      kind: 'weather',
      text:
        game.environment_type === 'outdoor'
          ? 'Outdoor games may be canceled for dangerous weather, including thunderstorms, lightning, or unsafe field conditions.'
          : 'Indoor games run rain or shine unless the venue has an unexpected closure.',
    },
    {
      title: 'Payment',
      kind: 'payment',
      text: 'Card payment only.',
    },
    {
      title: 'Age Requirement',
      kind: 'age',
      text: `Players must be ${game.minimum_age || 18} years or older.`,
    },
  ]

  if (game.custom_rules_text) {
    rules.unshift({
      title: 'Game Rules',
      kind: 'rules',
      text: game.custom_rules_text,
    })
  }

  return rules
}

function formatVenueAddress(game, venue) {
  const street = game.address_snapshot || venue?.address_line_1
  const city = game.city_snapshot || venue?.city
  const state = game.state_snapshot || venue?.state
  const postalCode = venue?.postal_code

  return [street, [city, state, postalCode].filter(Boolean).join(' ')].filter(Boolean).join(', ')
}

function buildMapsUrl(venue, address) {
  const latitude = Number(venue?.latitude)
  const longitude = Number(venue?.longitude)

  if (Number.isFinite(latitude) && Number.isFinite(longitude)) {
    return `https://www.google.com/maps/search/?api=1&query=${latitude},${longitude}`
  }

  if (address) {
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`
  }

  return ''
}

function formatDate(value) {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value))
}

function formatTime(value) {
  if (!value) {
    return ''
  }

  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

function formatTimeRange(start, end) {
  if (!start || !end) {
    return ''
  }

  return `${formatTime(start)}-${formatTime(end)}`
}

function getDurationLabel(start, end) {
  if (!start || !end) {
    return '60 min'
  }

  const minutes = Math.round((new Date(end) - new Date(start)) / 60000)
  return `${minutes || 60} min`
}

function formatEnvironment(value) {
  if (!value) {
    return 'Pickup'
  }

  return value.charAt(0).toUpperCase() + value.slice(1).replaceAll('_', ' ')
}

function formatPrice(cents, currency) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'USD',
    maximumFractionDigits: 0,
  }).format((cents || 0) / 100)
}

export default GameDetailsPage
