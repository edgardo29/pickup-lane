import { Link, useNavigate, useParams } from 'react-router-dom'
import { useEffect, useMemo, useRef, useState } from 'react'
import defaultCommunityVenueImage from '../../assets/community-default/default-venue-wide.png'
import BrowseAppNav from '../../components/BrowseAppNav.jsx'
import {
  BuildingIcon,
  CalendarIcon,
  CheckIcon,
  ClockIcon,
  CopyIcon,
  MapPinIcon,
  PencilIcon,
  PlusCircleIcon,
  ShareIcon,
  ShieldCheckIcon,
  StopwatchIcon,
  TrashIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import {
  BookingRulesCard,
  CancelGameModal,
  ChatPanel,
  DetailsScaffold,
  DetailsState,
  GameChatCard,
  GameGallery,
  JoinCard,
  HostPaymentSection,
  HostGuestModal,
  LeaveGameModal,
  PlayersCard,
  PlayersListModal,
  QuickFacts,
  StatusPill,
  WhereToGoCard,
} from './GameDetailsSections.jsx'
import { useAuth } from '../../hooks/useAuth.js'
import { apiRequest, buildMediaUrl } from '../../lib/apiClient.js'
import '../../styles/browse-games/BrowseGamesPage.css'
import '../../styles/browse-games/GameDetailsPage.css'

const ACTIVE_PARTICIPANT_STATUSES = new Set(['pending_payment', 'confirmed'])
const ACTIVE_JOIN_STATUSES = new Set(['pending_payment', 'confirmed', 'waitlisted'])
const GUEST_JOIN_MESSAGE = 'Create an Account or Sign In to join this game.'
const CHAT_MESSAGE_MAX_LENGTH = 300
const JOIN_WINDOW_MINUTES = 5

function GameDetailsPage() {
  const { gameId } = useParams()
  const navigate = useNavigate()
  const { appUser, currentUser: firebaseUser, isLoading: isAuthLoading } = useAuth()

  const [game, setGame] = useState(null)
  const [venue, setVenue] = useState(null)
  const [gameImages, setGameImages] = useState([])
  const [communityGameDetails, setCommunityGameDetails] = useState(null)
  const [participants, setParticipants] = useState([])
  const [currentUser, setCurrentUser] = useState(null)
  const [activeChat, setActiveChat] = useState(null)
  const [chatMessages, setChatMessages] = useState([])
  const [chatDraft, setChatDraft] = useState('')
  const [chatError, setChatError] = useState('')
  const [activeImageIndex, setActiveImageIndex] = useState(0)
  const [joinNotice, setJoinNotice] = useState('')
  const [shareCopied, setShareCopied] = useState(false)
  const [isJoining, setIsJoining] = useState(false)
  const [isLeaving, setIsLeaving] = useState(false)
  const [isAddingHostGuest, setIsAddingHostGuest] = useState(false)
  const [isUpdatingGuests, setIsUpdatingGuests] = useState(false)
  const [isCancellingGame, setIsCancellingGame] = useState(false)
  const [isHostGuestModalOpen, setIsHostGuestModalOpen] = useState(false)
  const [isCancelGameModalOpen, setIsCancelGameModalOpen] = useState(false)
  const [isLeaveModalOpen, setIsLeaveModalOpen] = useState(false)
  const [isPlayerListOpen, setIsPlayerListOpen] = useState(false)
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [isSendingChatMessage, setIsSendingChatMessage] = useState(false)
  const [hasUnreadChat, setHasUnreadChat] = useState(false)
  const [activePlayerTab, setActivePlayerTab] = useState('going')
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
  const chatMessagesRef = useRef([])
  const shareCopiedTimeoutRef = useRef(null)

  useEffect(() => {
    chatMessagesRef.current = chatMessages
  }, [chatMessages])

  useEffect(() => () => {
    if (shareCopiedTimeoutRef.current) {
      window.clearTimeout(shareCopiedTimeoutRef.current)
    }
  }, [])

  useEffect(() => {
    let ignore = false

    async function loadGameDetails() {
      setStatus('loading')
      setError('')
      setJoinNotice('')
      setShareCopied(false)
      setIsJoining(false)
      setIsLeaving(false)
      setIsAddingHostGuest(false)
      setIsCancellingGame(false)
      setIsHostGuestModalOpen(false)
      setIsCancelGameModalOpen(false)
      setIsLeaveModalOpen(false)
      setIsPlayerListOpen(false)
      setIsChatOpen(false)
      setActiveChat(null)
      setChatDraft('')
      setChatError('')
      setIsSendingChatMessage(false)
      setHasUnreadChat(false)
      setActivePlayerTab('going')
      setActiveImageIndex(0)

      try {
        const gameResponse = await apiRequest(`/games/${gameId}`)

        const [imagesResponse, participantsResponse, venueResponse] = await Promise.all([
          apiRequest(`/game-images?game_id=${gameId}&image_status=active`),
          apiRequest(`/game-participants?game_id=${gameId}`),
          apiRequest(`/venues/${gameResponse.venue_id}`).catch(() => null),
        ])
        const communityDetailsResponse = gameResponse.game_type === 'community'
          ? await apiRequest(`/community-game-details?game_id=${gameId}`)
            .then((details) => details[0] || null)
            .catch(() => null)
          : null
        const canLoadChat = canUseGameChat(gameResponse, participantsResponse, appUser)
        let activeChatResponse = null
        let messagesResponse = []

        if (gameResponse.is_chat_enabled && canLoadChat && firebaseUser) {
          const chatHeaders = await getChatAuthHeaders(firebaseUser)
          activeChatResponse = await apiRequest(`/game-chats/for-game/${gameId}`, {
            method: 'POST',
            headers: {
              ...chatHeaders,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({}),
          }).catch(() => null)

          if (activeChatResponse) {
            messagesResponse = await apiRequest(
              buildChatMessagesPath(activeChatResponse.id),
              { headers: chatHeaders },
            ).catch(() => [])
          }
        }

        if (!ignore) {
          setGame(gameResponse)
          setVenue(venueResponse)
          setGameImages(imagesResponse)
          setCommunityGameDetails(communityDetailsResponse)
          setParticipants(participantsResponse)
          setCurrentUser(appUser || null)
          setActiveChat(activeChatResponse)
          setChatMessages(messagesResponse)
          setHasUnreadChat(Boolean(activeChatResponse?.unread_count))
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
  }, [appUser, firebaseUser, gameId])

  useEffect(() => {
    if (!activeChat?.id || !firebaseUser || isChatOpen) {
      return undefined
    }

    let ignore = false

    async function refreshChatPreview() {
      try {
        if (document.hidden) {
          return
        }

        const chatHeaders = await getChatAuthHeaders(firebaseUser)
        const readStateResponse = await apiRequest(
          `/game-chats/${activeChat.id}/read-state`,
          { headers: chatHeaders },
        )

        if (!ignore) {
          setHasUnreadChat(Boolean(readStateResponse.unread_count))
        }

        if (readStateResponse.unread_count > 0) {
          const messagesResponse = await apiRequest(
            buildChatMessagesPath(activeChat.id, getLatestMessageCreatedAt(chatMessagesRef.current)),
            { headers: chatHeaders },
          )

          if (!ignore && messagesResponse.length > 0) {
            setChatMessages((currentMessages) => mergeChatMessages(currentMessages, messagesResponse))
          }
        }
      } catch {
        // Chat preview refresh is best-effort; the page should stay usable.
      }
    }

    const intervalId = window.setInterval(refreshChatPreview, 60000)
    return () => {
      ignore = true
      window.clearInterval(intervalId)
    }
  }, [activeChat?.id, firebaseUser, isChatOpen])

  useEffect(() => {
    if (!activeChat?.id || !firebaseUser || !isChatOpen) {
      return undefined
    }

    let ignore = false

    async function refreshOpenChat() {
      try {
        if (document.hidden) {
          return
        }

        const chatHeaders = await getChatAuthHeaders(firebaseUser)
        const afterCreatedAt = getLatestMessageCreatedAt(chatMessagesRef.current)
        const messagesResponse = await apiRequest(
          buildChatMessagesPath(activeChat.id, afterCreatedAt),
          { headers: chatHeaders },
        )

        if (!ignore && messagesResponse.length > 0) {
          setChatMessages((currentMessages) => mergeChatMessages(currentMessages, messagesResponse))
          setHasUnreadChat(false)
        }

        if (messagesResponse.length > 0 || hasUnreadChat) {
          await apiRequest(`/game-chats/${activeChat.id}/read`, {
            method: 'POST',
            headers: {
              ...chatHeaders,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({}),
          }).catch(() => null)
        }
      } catch {
        // Open chat refresh is best-effort; sending and manual refresh still work.
      }
    }

    refreshOpenChat()
    const intervalId = window.setInterval(refreshOpenChat, 5000)

    return () => {
      ignore = true
      window.clearInterval(intervalId)
    }
  }, [activeChat?.id, firebaseUser, hasUnreadChat, isChatOpen])

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
  const currentParticipant = useMemo(
    () =>
      participants.find(
        (participant) =>
          participant.user_id === currentUser?.id &&
          ACTIVE_JOIN_STATUSES.has(participant.participant_status),
      ) || null,
    [currentUser?.id, participants],
  )
  const currentGuestCount = useMemo(
    () => getCurrentGuestCount(participants, currentParticipant, currentUser?.id),
    [currentParticipant, currentUser?.id, participants],
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
  const city = game.city_snapshot || venue?.city || 'Chicago'
  const state = game.state_snapshot || venue?.state
  const heroLocation = formatHeroLocation(venueName, game.neighborhood_snapshot || venue?.neighborhood, city, state)
  const isCancelledGame = game.game_status === 'cancelled'
  const gameToneLabel = isCancelledGame
    ? 'Cancelled'
    : game.game_type === 'community'
      ? 'Community Game'
      : 'Official Game'
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
  const hostPaymentMethods = getVisibleHostPaymentMethods(game, communityGameDetails)
  const parkingNote = game.parking_notes || ''
  const ruleItems = buildRuleItems(game)
  const scheduledStartMs = new Date(game.starts_at).getTime()
  const isGameStarted = nowMs !== null && nowMs >= scheduledStartMs
  const canShowEditGame =
    game.game_type === 'community' &&
    currentUser?.id === game.host_user_id &&
    game.publish_status === 'published' &&
    ['scheduled', 'full'].includes(game.game_status)
  const canEditGame = canShowEditGame && !isGameStarted
  const isHost = currentUser?.id && currentUser.id === game.host_user_id
  const canShowCancelGame =
    game.publish_status === 'published' &&
    ['scheduled', 'full'].includes(game.game_status) &&
    (
      currentUser?.role === 'admin' ||
      (game.game_type === 'community' && isHost)
    )
  const canCancelGame = canShowCancelGame && !isGameStarted
  const canOpenGameChat = canUseGameChat(game, participants, currentUser)
  const hostGuestMax = game.allow_guests ? game.host_guest_max || 0 : 0
  const hostGuestAddSlots = Math.max(
    Math.min(hostGuestMax - currentGuestCount, participantSummary.spotsLeft),
    0,
  )
  const isJoinWindowClosed =
    nowMs !== null &&
    nowMs >= scheduledStartMs + JOIN_WINDOW_MINUTES * 60 * 1000
  const isGameClosed =
    !['published'].includes(game.publish_status) ||
    !['scheduled', 'full'].includes(game.game_status) ||
    isJoinWindowClosed
  const playerGuestMax = game.allow_guests ? game.max_guests_per_booking || 0 : 0
  const isConfirmedPlayer =
    Boolean(currentParticipant) &&
    !isHost &&
    currentParticipant.participant_status === 'confirmed'
  const canShowBookingGuestAction = isConfirmedPlayer && playerGuestMax > 0
  const bookingGuestAddSlots = canShowBookingGuestAction
    ? Math.max(Math.min(playerGuestMax - currentGuestCount, participantSummary.spotsLeft), 0)
    : 0
  const canAddBookingGuests = canShowBookingGuestAction && !isGameClosed && bookingGuestAddSlots > 0
  const joinLabel = getJoinLabel({
    currentParticipant,
    gameStatus: game.game_status,
    isJoinWindowClosed,
    isCancelledGame,
    isGameClosed,
    isPublished: game.publish_status === 'published',
    isHost,
    isJoining,
    participantSummary,
    waitlistEnabled: game.waitlist_enabled,
  })
  const isJoinDisabled = Boolean(isHost || currentParticipant || isGameClosed || isJoining)
  const isClosedJoinStatus =
    isJoinDisabled && ['Cancelled', 'Completed', 'Join Closed', 'Game Closed'].includes(joinLabel)
  const mobileActionCount = [
    canShowEditGame,
    isHost && hostGuestMax > 0,
    currentParticipant && !isHost && !isJoinWindowClosed,
    canShowCancelGame,
    true,
  ].filter(Boolean).length

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
    const shareUrl = `${window.location.origin}/games/${game.id}`
    const shareData = {
      title,
      text: `${title} at ${venueName}`,
      url: shareUrl,
    }

    try {
      setShareCopied(false)

      if (navigator.share) {
        await navigator.share(shareData)
        showShareCopied()
        return
      }

      await navigator.clipboard?.writeText(shareUrl)
      showShareCopied()
    } catch (shareError) {
      if (shareError?.name === 'AbortError') {
        return
      }
    }
  }

  function showShareCopied() {
    setShareCopied(true)

    if (shareCopiedTimeoutRef.current) {
      window.clearTimeout(shareCopiedTimeoutRef.current)
    }

    shareCopiedTimeoutRef.current = window.setTimeout(() => {
      setShareCopied(false)
      shareCopiedTimeoutRef.current = null
    }, 1800)
  }

  async function handleCancelGame() {
    if (!canCancelGame || !firebaseUser) {
      return
    }

    setIsCancellingGame(true)
    setJoinNotice('')

    try {
      await apiRequest(`/games/${game.id}/cancel`, {
        method: 'POST',
        headers: {
          ...(await getChatAuthHeaders(firebaseUser)),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      })
      await refreshParticipants()
      setActiveChat(null)
      setChatMessages([])
      setHasUnreadChat(false)
      setIsChatOpen(false)
      setIsCancelGameModalOpen(false)
      setJoinNotice('Game cancelled. Players were notified.')
    } catch (requestError) {
      setJoinNotice(
        requestError instanceof Error ? requestError.message : 'Unable to cancel this game.',
      )
    } finally {
      setIsCancellingGame(false)
    }
  }

  async function refreshParticipants() {
    const [participantsResponse, gameResponse] = await Promise.all([
      apiRequest(`/game-participants?game_id=${gameId}`),
      apiRequest(`/games/${gameId}`),
    ])
    setParticipants(participantsResponse)
    setGame(gameResponse)
  }

  async function handleJoinIntent() {
    setShareCopied(false)

    if (isAuthLoading) {
      setJoinNotice('Checking your account...')
      return
    }

    if (!currentUser?.id) {
      navigate('/create-account', { state: { from: `/games/${game.id}` } })
      return
    }

    if (!hasCompleteProfile(currentUser)) {
      navigate('/finish-profile', { state: { from: `/games/${game.id}` } })
      return
    }

    if (isHost) {
      setJoinNotice('You are hosting this game.')
      return
    }

    if (currentParticipant) {
      setJoinNotice(
        currentParticipant.participant_status === 'waitlisted'
          ? 'You are already on the waitlist.'
          : 'You already joined this game.',
      )
      return
    }

    if (isGameClosed) {
      setJoinNotice('This game is not open for joining.')
      return
    }

    navigate(`/games/${game.id}/checkout`)
  }

  async function handleLeaveGame() {
    if (!currentUser?.id || !currentParticipant) {
      setIsLeaveModalOpen(false)
      return
    }

    setIsLeaving(true)
    setJoinNotice('')

    try {
      await apiRequest(`/games/${game.id}/leave`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ acting_user_id: currentUser.id }),
      })
      await refreshParticipants()
      setJoinNotice('')
      setIsLeaveModalOpen(false)
    } catch (requestError) {
      setJoinNotice(
        requestError instanceof Error ? requestError.message : 'Unable to leave this game.',
      )
    } finally {
      setIsLeaving(false)
    }
  }

  async function handleSaveHostGuestCount(nextGuestCount) {
    if (!currentUser?.id || !isHost) {
      return
    }

    const guestDelta = nextGuestCount - currentGuestCount
    if (guestDelta === 0) {
      setIsHostGuestModalOpen(false)
      return
    }

    setJoinNotice('')

    if (guestDelta > 0) {
      setIsAddingHostGuest(true)

      try {
        await apiRequest(`/games/${game.id}/guests/add`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ acting_user_id: currentUser.id, guest_count: guestDelta }),
        })
        await refreshParticipants()
        setIsHostGuestModalOpen(false)
      } catch (requestError) {
        setJoinNotice(
          requestError instanceof Error ? requestError.message : 'Unable to update host guests.',
        )
      } finally {
        setIsAddingHostGuest(false)
      }

      return
    }

    await handleRemoveGuests(Math.abs(guestDelta), { closeHostGuestModal: true })
  }

  function handleAddBookingGuests(guestCount) {
    if (!currentUser?.id || !canAddBookingGuests || guestCount <= 0) {
      return
    }

    setJoinNotice('')
    setShareCopied(false)
    navigate(`/games/${game.id}/checkout?mode=add-guests&guest_count=${guestCount}`)
  }

  async function handleRemoveGuests(removeCount, options = {}) {
    if (!currentUser?.id || !currentParticipant || removeCount <= 0) {
      return
    }

    setIsUpdatingGuests(true)
    setJoinNotice('')

    try {
      await apiRequest(`/games/${game.id}/guests/remove`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ acting_user_id: currentUser.id, remove_count: removeCount }),
      })
      await refreshParticipants()
      setIsLeaveModalOpen(false)
      if (options.closeHostGuestModal) {
        setIsHostGuestModalOpen(false)
      }
    } catch (requestError) {
      setJoinNotice(
        requestError instanceof Error ? requestError.message : 'Unable to update attendance.',
      )
    } finally {
      setIsUpdatingGuests(false)
    }
  }

  async function handleOpenChat() {
    if (!canOpenGameChat || !firebaseUser) {
      return
    }

    setShareCopied(false)
    setChatError('')

    try {
      const chatHeaders = await getChatAuthHeaders(firebaseUser)
      const chat = activeChat?.id
        ? activeChat
        : await apiRequest(`/game-chats/for-game/${game.id}`, {
          method: 'POST',
          headers: {
            ...chatHeaders,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({}),
        })

      setActiveChat(chat)
      setIsChatOpen(true)
      setHasUnreadChat(false)

      const messagesResponse = await apiRequest(
        buildChatMessagesPath(chat.id),
        { headers: chatHeaders },
      ).catch(() => [])
      setChatMessages(messagesResponse)

      await apiRequest(`/game-chats/${chat.id}/read`, {
        method: 'POST',
        headers: {
          ...chatHeaders,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      })
    } catch (requestError) {
      setJoinNotice(
        requestError instanceof Error ? requestError.message : 'Unable to open chat.',
      )
    }
  }

  async function handleSendChatMessage(event) {
    event.preventDefault()

    if (!activeChat?.id || !firebaseUser) {
      return
    }

    const trimmedMessage = chatDraft.trim()
    if (!trimmedMessage) {
      setChatError('Type a message first.')
      return
    }

    if (trimmedMessage.length > CHAT_MESSAGE_MAX_LENGTH) {
      setChatError(`Keep messages under ${CHAT_MESSAGE_MAX_LENGTH} characters.`)
      return
    }

    setIsSendingChatMessage(true)
    setChatError('')

    try {
      const newMessage = await apiRequest('/chat-messages', {
        method: 'POST',
        headers: {
          ...(await getChatAuthHeaders(firebaseUser)),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          chat_id: activeChat.id,
          message_body: trimmedMessage,
        }),
      })

      setChatMessages((currentMessages) => [...currentMessages, newMessage].slice(-50))
      setChatDraft('')
      setHasUnreadChat(false)
    } catch (requestError) {
      setChatError(
        requestError instanceof Error ? requestError.message : 'Unable to send message.',
      )
    } finally {
      setIsSendingChatMessage(false)
    }
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

            </div>

            <div className="details-heading">
              <h1>{title}</h1>
              <p>
                <MapPinIcon />
                {heroLocation}
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
              </div>

              <h1>{title}</h1>

              <p>
                <MapPinIcon />
                {heroLocation}
              </p>

              <QuickFacts facts={facts} price={price} variant="mobile" />
            </section>

            <section
              className={[
                'details-card',
                'details-mobile-host-actions',
                mobileActionCount === 1 ? 'details-mobile-host-actions--single' : '',
              ].filter(Boolean).join(' ')}
            >
              {canShowEditGame && (
                canEditGame ? (
                  <Link className="details-secondary-action details-host-edit-action" to={`/games/${game.id}/edit`}>
                    <span className="details-action-icon">
                      <PencilIcon />
                    </span>
                    <span>Edit Game</span>
                    <span className="details-action-chevron" aria-hidden="true">›</span>
                  </Link>
                ) : (
                  <button
                    className="details-secondary-action details-host-edit-action"
                    type="button"
                    disabled
                  >
                    <span className="details-action-icon">
                      <PencilIcon />
                    </span>
                    <span>Edit Game</span>
                    <span className="details-action-chevron" aria-hidden="true">›</span>
                  </button>
                )
              )}

              {isHost && hostGuestMax > 0 && (
                <button
                  className="details-secondary-action details-host-guest-action"
                  type="button"
                  disabled={isJoinWindowClosed || isAddingHostGuest || isUpdatingGuests}
                  onClick={() => setIsHostGuestModalOpen(true)}
                >
                  <span className="details-action-icon">
                    <UsersIcon />
                  </span>
                  <span>Manage Guests</span>
                  <strong className="details-action-count">{currentGuestCount}/{hostGuestMax}</strong>
                  <span className="details-action-chevron" aria-hidden="true">›</span>
                </button>
              )}

              {currentParticipant && !isHost && !isJoinWindowClosed && (
                <button
                  className="details-secondary-action"
                  type="button"
                  onClick={() => setIsLeaveModalOpen(true)}
                >
                  <span className="details-action-icon">
                    <PencilIcon />
                  </span>
                  <span>
                    {currentParticipant.participant_status === 'waitlisted'
                      ? 'Leave Waitlist'
                      : 'Edit Attendance'}
                  </span>
                  <span className="details-action-chevron" aria-hidden="true">›</span>
                </button>
              )}

              {canShowCancelGame && (
                <button
                  className="details-secondary-action details-cancel-game-action"
                  type="button"
                  disabled={!canCancelGame || isCancellingGame}
                  onClick={() => setIsCancelGameModalOpen(true)}
                >
                  <span className="details-action-icon">
                    <TrashIcon />
                  </span>
                  <span>{isCancellingGame ? 'Cancelling...' : 'Cancel Game'}</span>
                  <span className="details-action-chevron" aria-hidden="true">›</span>
                </button>
              )}

              <button
                className="details-secondary-action details-share-button"
                type="button"
                disabled={isCancelledGame}
                onClick={handleShareGame}
              >
                <span className="details-action-icon">
                  <ShareIcon />
                </span>
                <span>Share Game</span>
                <span
                  className={[
                    'details-action-chevron',
                    'details-share-indicator',
                    shareCopied ? 'details-share-indicator--copied' : '',
                  ].filter(Boolean).join(' ')}
                  aria-hidden="true"
                >
                  {shareCopied ? <CheckIcon /> : <CopyIcon />}
                </span>
              </button>
            </section>

            {!currentUser?.id && !isCancelledGame && (
              <section className="details-member-access-notice">
                <p>
                  <Link state={{ from: `/games/${game.id}` }} to="/create-account">
                    Create an Account
                  </Link>{' '}
                  or{' '}
                  <Link state={{ from: `/games/${game.id}` }} to="/sign-in">
                    Sign In
                  </Link>{' '}
                  to view the player list and use game chat.
                </p>
              </section>
            )}

            <section className="details-card details-mobile-info-section details-mobile-about-section">
              <h2 className="details-section-heading">
                <span className="details-section-icon">
                  <PencilIcon />
                </span>
                About This Game
              </h2>
              <p>{aboutText}</p>

              {hostPaymentMethods.length > 0 && (
                <HostPaymentSection methods={hostPaymentMethods} />
              )}
            </section>

            <section className="details-card-grid">
              <PlayersCard
                cta="View player list"
                ctaDisabled={!currentUser?.id}
                onOpenPlayerList={currentUser?.id ? () => setIsPlayerListOpen(true) : undefined}
                participantSummary={participantSummary}
              />

              <GameChatCard
                canOpenChat={canOpenGameChat}
                hasUnread={hasUnreadChat}
                latestChatMessage={latestChatMessage}
                messageCount={chatMessages.length}
                onOpenChat={handleOpenChat}
                senderNames={chatSenderNames}
              />
            </section>

            <BookingRulesCard policyUrl="/policies/cancellation-refunds" rules={ruleItems} />

            <WhereToGoCard
              address={venueAddress}
              mapIcon={<MapPinIcon />}
              mapsUrl={mapsUrl}
              parkingNote={parkingNote}
              venueName={venueName}
            />

            <section className="details-card details-mobile-info-section">
              <h2>Questions?</h2>
              <p>Check out our Help Center or contact our support team.</p>
              <a className="details-help-button" href="mailto:support@pickuplane.local">
                Visit Help Center
              </a>
            </section>
          </div>

          <aside className="details-sidebar" aria-label="Join game">
            <JoinCard
              aboutText={aboutText}
              facts={facts}
              gameToneLabel={gameToneLabel}
              hostPaymentMethods={hostPaymentMethods}
              joinMessage={GUEST_JOIN_MESSAGE}
              joinNotice={joinNotice}
              joinLabel={joinLabel}
              joinDisabled={isJoinDisabled}
              leaveLabel={
                currentParticipant?.participant_status === 'waitlisted'
                  ? 'Leave Waitlist'
                  : 'Edit Attendance'
              }
              onJoin={handleJoinIntent}
              onLeave={
                currentParticipant && !isHost && !isJoinWindowClosed
                  ? () => setIsLeaveModalOpen(true)
                  : null
              }
              onShare={handleShareGame}
              shareDisabled={isCancelledGame}
              onCancelGame={canShowCancelGame ? () => setIsCancelGameModalOpen(true) : null}
              cancelGameDisabled={!canCancelGame}
              price={price}
              returnPath={`/games/${game.id}`}
              shareCopied={shareCopied}
              editGameUrl={canShowEditGame ? `/games/${game.id}/edit` : ''}
              editGameDisabled={!canEditGame}
              hostGuestCount={isHost ? currentGuestCount : 0}
              hostGuestMax={hostGuestMax}
              isAddingHostGuest={isAddingHostGuest}
              isUpdatingHostGuests={isUpdatingGuests}
              isCancellingGame={isCancellingGame}
              onManageHostGuests={
                isHost ? () => setIsHostGuestModalOpen(true) : null
              }
              manageHostGuestsDisabled={isCancelledGame || isJoinWindowClosed}
            />
          </aside>
        </section>
      </main>

      <div
        className={[
          'details-mobile-join',
          isHost ? 'details-mobile-join--host' : '',
          !isHost && currentParticipant ? 'details-mobile-join--participant' : '',
        ].filter(Boolean).join(' ')}
      >
        {isHost ? (
          <>
            <div>
              <strong>{price}</strong>
              <span>per player</span>
            </div>

            <span
              className={[
                'details-mobile-status-pill',
                isCancelledGame ? 'details-mobile-status-pill--cancelled' : '',
              ].filter(Boolean).join(' ')}
            >
              {isCancelledGame ? <TrashIcon /> : <CalendarIcon />}
              {isCancelledGame ? 'Cancelled' : 'Hosting'}
            </span>
          </>
        ) : currentParticipant ? (
          <>
            <div>
              <strong>{price}</strong>
              <span>per player</span>
            </div>

            <span
              className={[
                'details-mobile-status-pill',
                isCancelledGame ? 'details-mobile-status-pill--cancelled' : '',
              ].filter(Boolean).join(' ')}
            >
              {isCancelledGame ? <TrashIcon /> : <ShieldCheckIcon />}
              {isCancelledGame
                ? 'Cancelled'
                : currentParticipant.participant_status === 'waitlisted'
                  ? 'Waitlisted'
                  : 'Joined'}
            </span>
          </>
        ) : (
          <>
            <div>
              <strong>{price}</strong>
              <span>per player</span>
            </div>

            {isClosedJoinStatus ? (
              <span
                className={[
                  'details-mobile-status-pill',
                  isCancelledGame
                    ? 'details-mobile-status-pill--cancelled'
                    : 'details-mobile-status-pill--closed',
                ].filter(Boolean).join(' ')}
              >
                {isCancelledGame ? (
                  <TrashIcon />
                ) : joinLabel === 'Join Closed' ? (
                  <ClockIcon />
                ) : (
                  <ShieldCheckIcon />
                )}
                {joinLabel}
              </span>
            ) : (
              <button type="button" disabled={isJoinDisabled} onClick={handleJoinIntent}>
                {(joinLabel === 'Join Game' || joinLabel === 'Join Waitlist' || !joinLabel) && (
                  <PlusCircleIcon />
                )}
                {joinLabel}
              </button>
            )}

            {joinNotice && (
              <p>
                {joinNotice === GUEST_JOIN_MESSAGE ? (
                  <AuthJoinNotice gameId={game.id} />
                ) : (
                  joinNotice
                )}
              </p>
            )}
          </>
        )}
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
          currentUserId={currentUser?.id || ''}
          currentUserName={getUserDisplayName(currentUser)}
          draft={chatDraft}
          error={chatError}
          isSending={isSendingChatMessage}
          maxLength={CHAT_MESSAGE_MAX_LENGTH}
          messages={chatMessages}
          onChangeDraft={setChatDraft}
          onClose={() => setIsChatOpen(false)}
          onSend={handleSendChatMessage}
          senderNames={chatSenderNames}
        />
      )}

      {isHostGuestModalOpen && (
        <HostGuestModal
          guestCount={currentGuestCount}
          guestMax={hostGuestMax}
          addableCount={hostGuestAddSlots}
          isAdding={isAddingHostGuest}
          isRemoving={isUpdatingGuests}
          onClose={() => setIsHostGuestModalOpen(false)}
          onSave={handleSaveHostGuestCount}
        />
      )}

      {isCancelGameModalOpen && (
        <CancelGameModal
          gameType={game.game_type}
          isCancelling={isCancellingGame}
          onClose={() => setIsCancelGameModalOpen(false)}
          onConfirm={handleCancelGame}
        />
      )}

      {isLeaveModalOpen && (
        <LeaveGameModal
          addableGuestCount={bookingGuestAddSlots}
          canAddGuests={canAddBookingGuests}
          isLeaving={isLeaving}
          isUpdatingGuests={isUpdatingGuests}
          isWaitlisted={currentParticipant?.participant_status === 'waitlisted'}
          guestCount={currentGuestCount}
          guestMax={playerGuestMax}
          onClose={() => setIsLeaveModalOpen(false)}
          onAddGuests={handleAddBookingGuests}
          onConfirm={handleLeaveGame}
          onRemoveGuests={handleRemoveGuests}
        />
      )}
    </div>
  )
}

async function getChatAuthHeaders(firebaseUser) {
  const token = await firebaseUser.getIdToken()
  return {
    Authorization: `Bearer ${token}`,
  }
}

function buildChatMessagesPath(chatId, afterCreatedAt = '') {
  const query = new URLSearchParams({
    chat_id: chatId,
    moderation_status: 'visible',
    limit: '50',
  })

  if (afterCreatedAt) {
    query.set('after_created_at', afterCreatedAt)
  }

  return `/chat-messages?${query.toString()}`
}

function getLatestMessageCreatedAt(messages) {
  if (!messages.length) {
    return ''
  }

  return messages.reduce((latest, message) => (
    !latest || new Date(message.created_at) > new Date(latest) ? message.created_at : latest
  ), '')
}

function mergeChatMessages(currentMessages, incomingMessages) {
  const messagesById = new Map()

  for (const message of [...currentMessages, ...incomingMessages]) {
    messagesById.set(message.id, message)
  }

  return [...messagesById.values()]
    .sort((first, second) => new Date(first.created_at) - new Date(second.created_at))
    .slice(-50)
}

function canUseGameChat(game, participants, user) {
  if (!game?.is_chat_enabled || !user?.id) {
    return false
  }

  if (!['scheduled', 'full'].includes(game.game_status)) {
    return false
  }

  if (game.host_user_id === user.id) {
    return true
  }

  return participants.some(
    (participant) =>
      participant.user_id === user.id &&
      participant.participant_status === 'confirmed' &&
      ['registered_user', 'host', 'admin_added'].includes(participant.participant_type),
  )
}

function getVisibleHostPaymentMethods(game, communityGameDetails) {
  if (
    game?.game_type !== 'community' ||
    game?.payment_collection_type !== 'external_host'
  ) {
    return []
  }

  return (communityGameDetails?.payment_methods_snapshot || [])
    .filter((method) => method?.type && method.type !== 'none' && method?.value)
    .map((method) => ({
      type: String(method.type).trim(),
      value: String(method.value).trim(),
    }))
}

function AuthJoinNotice({ gameId }) {
  const returnPath = `/games/${gameId}`

  return (
    <>
      <Link state={{ from: returnPath }} to="/create-account">
        Create Account
      </Link>{' '}
      or{' '}
      <Link state={{ from: returnPath }} to="/sign-in">
        Sign In
      </Link>{' '}
      to join this game.
    </>
  )
}

function getParticipantSummary(participants, totalSpots = 0) {
  const rosterParticipants = participants
    .filter((participant) => ACTIVE_PARTICIPANT_STATUSES.has(participant.participant_status))
    .sort(
      (first, second) =>
        Number(first.roster_order || 999) - Number(second.roster_order || 999) ||
        first.display_name_snapshot.localeCompare(second.display_name_snapshot),
    )
  const waitlistParticipants = participants.filter(
    (participant) => participant.participant_status === 'waitlisted',
  )
  const roster = groupParticipantParties(rosterParticipants)
  const waitlist = groupParticipantParties(waitlistParticipants)
  const host = roster.find((participant) => participant.participant_type === 'host') || null
  const spotsLeft = Math.max((totalSpots || 0) - rosterParticipants.length, 0)

  return {
    host,
    roster,
    signedUpCount: rosterParticipants.length,
    spotsLeft,
    totalSpots: totalSpots || rosterParticipants.length,
    waitlist,
    waitlistCount: waitlistParticipants.length,
  }
}

function getCurrentGuestCount(participants, currentParticipant, currentUserId) {
  if (!currentParticipant) {
    return 0
  }

  return participants.filter((participant) => {
    if (participant.participant_type !== 'guest' || !ACTIVE_JOIN_STATUSES.has(participant.participant_status)) {
      return false
    }

    if (currentParticipant.booking_id && participant.booking_id === currentParticipant.booking_id) {
      return true
    }

    return participant.guest_of_user_id === currentUserId
  }).length
}

function groupParticipantParties(participants) {
  const guestsByBookingId = new Map()
  const guestsByUserId = new Map()
  const visibleParticipants = []

  participants.forEach((participant) => {
    if (participant.participant_type === 'guest') {
      if (participant.booking_id) {
        const guests = guestsByBookingId.get(participant.booking_id) || []
        guests.push(participant)
        guestsByBookingId.set(participant.booking_id, guests)
      } else if (participant.guest_of_user_id) {
        const guests = guestsByUserId.get(participant.guest_of_user_id) || []
        guests.push(participant)
        guestsByUserId.set(participant.guest_of_user_id, guests)
      }

      return
    }

    visibleParticipants.push(participant)
  })

  return visibleParticipants.map((participant) => ({
    ...participant,
    guest_count: (
      (participant.booking_id ? guestsByBookingId.get(participant.booking_id)?.length || 0 : 0) +
      (participant.user_id ? guestsByUserId.get(participant.user_id)?.length || 0 : 0)
    ),
  }))
}

function buildChatSenderNames(participants) {
  return participants.reduce((names, participant) => {
    if (participant.user_id && participant.display_name_snapshot) {
      names.set(participant.user_id, participant.display_name_snapshot)
    }

    return names
  }, new Map())
}

function hasCompleteProfile(user) {
  return Boolean(user?.first_name && user?.last_name && user?.date_of_birth)
}

function getUserDisplayName(user) {
  return `${user?.first_name || ''} ${user?.last_name || ''}`.trim() || user?.email || ''
}

function getJoinLabel({
  currentParticipant,
  gameStatus,
  isJoinWindowClosed,
  isCancelledGame,
  isGameClosed,
  isPublished,
  isHost,
  isJoining,
  participantSummary,
  waitlistEnabled,
}) {
  if (isJoining) {
    return 'Joining...'
  }

  if (isCancelledGame) {
    return 'Cancelled'
  }

  if (isHost) {
    return 'Hosting'
  }

  if (currentParticipant?.participant_status === 'waitlisted') {
    return 'Waitlisted'
  }

  if (currentParticipant) {
    return 'Joined'
  }

  if (isGameClosed) {
    if (!isPublished) {
      return 'Game Closed'
    }

    if (gameStatus === 'completed') {
      return 'Completed'
    }

    if (isJoinWindowClosed) {
      return 'Join Closed'
    }

    return 'Game Closed'
  }

  if (participantSummary.spotsLeft <= 0 && waitlistEnabled) {
    return 'Join Waitlist'
  }

  return 'Join Game'
}

function buildRuleItems(game) {
  const isCommunityGame = game.game_type === 'community'
  const isOutdoorGame = game.environment_type === 'outdoor'
  const rules = [
    {
      title: 'Canceling Your Spot',
      kind: 'clock',
      text: isCommunityGame
        ? game.custom_cancellation_text ||
          'Check the host payment note before canceling. Pickup Lane does not process player refunds for community games.'
        : 'Cancel 24+ hours before game time for refund or game credit eligibility.',
    },
    {
      title: isCommunityGame ? 'If The Host Cancels' : 'If Pickup Lane Cancels',
      kind: 'shield',
      text: isCommunityGame
        ? 'The host should contact players with next steps for any off-app payments.'
        : 'Players receive a refund or game credit when Pickup Lane cancels an official game.',
    },
    {
      title: 'Signup Window',
      kind: 'clock',
      text: 'New signups close 5 minutes after the scheduled start time.',
    },
    {
      title: 'Waitlist',
      kind: 'players',
      text: 'Waitlisted players only pay if moved to the confirmed player list.',
    },
    {
      title: 'Weather',
      kind: 'weather',
      text: isOutdoorGame
        ? 'Outdoor games may be canceled for dangerous weather, including thunderstorms, lightning, or unsafe field conditions.'
        : 'Indoor games run unless the venue has an unexpected closure or unsafe condition.',
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

function formatHeroLocation(venueName, neighborhood, city, state) {
  const placeParts = []

  if (neighborhood && neighborhood !== city) {
    placeParts.push(neighborhood)
  }

  if (city) {
    placeParts.push(state ? `${city}, ${state}` : city)
  }

  return [venueName, placeParts.join(', ')].filter(Boolean).join(' – ')
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
