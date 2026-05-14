import { Link, useNavigate, useParams } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import defaultCommunityVenueImage from '../../assets/community-default/default-venue-wide.png'
import BrowseAppNav from '../../components/BrowseAppNav.jsx'
import {
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  ShieldCheckIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import { useAuth } from '../../hooks/useAuth.js'
import { apiRequest, buildMediaUrl } from '../../lib/apiClient.js'
import '../../styles/browse-games/BrowseGamesPage.css'
import '../../styles/browse-games/GameCheckoutPage.css'

const ACTIVE_ROSTER_STATUSES = new Set(['pending_payment', 'confirmed'])
const ACTIVE_JOIN_STATUSES = new Set(['pending_payment', 'confirmed', 'waitlisted'])

function GameCheckoutPage() {
  const { gameId } = useParams()
  const navigate = useNavigate()
  const { appUser, isLoading: isAuthLoading } = useAuth()

  const [game, setGame] = useState(null)
  const [venue, setVenue] = useState(null)
  const [images, setImages] = useState([])
  const [participants, setParticipants] = useState([])
  const [paymentMethods, setPaymentMethods] = useState([])
  const [guestCount, setGuestCount] = useState(0)
  const [agreed, setAgreed] = useState(false)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [submitError, setSubmitError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    let ignore = false

    async function loadCheckout() {
      if (isAuthLoading) {
        return
      }

      if (!appUser?.id) {
        navigate('/sign-in', { replace: true })
        return
      }

      if (!hasCompleteProfile(appUser)) {
        navigate('/finish-profile', { replace: true })
        return
      }

      setStatus('loading')
      setError('')
      setSubmitError('')

      try {
        const gameResponse = await apiRequest(`/games/${gameId}`)
        const [venueResponse, imageResponse, participantResponse, methodResponse] =
          await Promise.all([
            apiRequest(`/venues/${gameResponse.venue_id}`).catch(() => null),
            apiRequest(`/game-images?game_id=${gameId}&image_status=active`).catch(() => []),
            apiRequest(`/game-participants?game_id=${gameId}`),
            apiRequest(`/user-payment-methods?user_id=${appUser.id}`).catch(() => []),
          ])

        if (!ignore) {
          setGame(gameResponse)
          setVenue(venueResponse)
          setImages(imageResponse)
          setParticipants(participantResponse)
          setPaymentMethods(methodResponse)
          setStatus('success')
        }
      } catch (requestError) {
        if (!ignore) {
          setError(requestError instanceof Error ? requestError.message : 'Unable to load checkout.')
          setStatus('error')
        }
      }
    }

    loadCheckout()

    return () => {
      ignore = true
    }
  }, [appUser, gameId, isAuthLoading, navigate])

  const summary = useMemo(() => getParticipantSummary(participants, game?.total_spots), [game, participants])
  const existingParticipant = useMemo(
    () =>
      participants.find(
        (participant) =>
          participant.user_id === appUser?.id &&
          ACTIVE_JOIN_STATUSES.has(participant.participant_status),
      ) || null,
    [appUser?.id, participants],
  )
  const primaryImage = useMemo(() => getPrimaryImage(images, game), [game, images])
  const maxGuests = game?.allow_guests ? game.max_guests_per_booking || 0 : 0
  const effectiveGuestCount = Math.min(guestCount, maxGuests)
  const partySize = effectiveGuestCount + 1
  const price = game?.price_per_player_cents || 0
  const platformFee = 0
  const subtotal = price * partySize
  const total = subtotal + platformFee

  async function confirmBooking() {
    if (!agreed || !game || !appUser?.id || existingParticipant) {
      return
    }

    setIsSubmitting(true)
    setSubmitError('')

    try {
      await apiRequest(`/games/${game.id}/join`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ acting_user_id: appUser.id, guest_count: effectiveGuestCount }),
      })
      navigate(`/games/${game.id}`, { replace: true })
    } catch (requestError) {
      setSubmitError(requestError instanceof Error ? requestError.message : 'Unable to confirm booking.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (status === 'loading') {
    return (
      <div className="checkout-page">
        <BrowseAppNav />
        <main className="checkout-shell checkout-state">Loading checkout...</main>
      </div>
    )
  }

  if (status === 'error' || !game) {
    return (
      <div className="checkout-page">
        <BrowseAppNav />
        <main className="checkout-shell checkout-state">
          <h1>Checkout unavailable</h1>
          <p>{error || 'This game could not be loaded.'}</p>
          <Link to={`/games/${gameId}`}>Back to game</Link>
        </main>
      </div>
    )
  }

  const hasEnoughSpots = partySize <= summary.spotsLeft
  const isWaitlistCheckout = !hasEnoughSpots && game.waitlist_enabled
  const isBlockedByCapacity = !hasEnoughSpots && !game.waitlist_enabled
  const title = game.title || `${game.venue_name_snapshot} ${game.format_label}`
  const address = formatVenueAddress(game, venue)
  const paymentMethod = paymentMethods.find((method) => method.is_default) || paymentMethods[0]
  const chargeTiming = isWaitlistCheckout ? 'later' : ''

  return (
    <div className="checkout-page">
      <BrowseAppNav />

      <main className="checkout-shell">
        <header className="checkout-header">
          <button className="checkout-back" type="button" onClick={() => navigate(`/games/${game.id}`)}>
            ←
          </button>
          <div>
            <span>{isWaitlistCheckout ? 'Waitlist checkout' : 'Game checkout'}</span>
            <h1>{isWaitlistCheckout ? 'Join Waitlist' : 'Confirm Spot'}</h1>
          </div>
        </header>

        <section className="checkout-card checkout-game-card">
          <img src={primaryImage} alt="" />
          <div>
            <h2>{title}</h2>
            <p className="checkout-location">
              <MapPinIcon />
              <span>
                {game.venue_name_snapshot}
                <small>{address}</small>
              </span>
            </p>
            <div className="checkout-chips">
              <span>
                <CalendarIcon /> {formatDate(game.starts_at)}
              </span>
              <span>
                <ClockIcon /> {formatTimeRange(game.starts_at, game.ends_at)}
              </span>
              <span>
                <UsersIcon /> {game.format_label}
              </span>
            </div>
          </div>
        </section>

        <div className="checkout-layout">
          <div className="checkout-stack">
            <section className="checkout-card">
              <div className="checkout-section-heading">
                <h2>{isWaitlistCheckout ? 'Waitlist' : 'Players'}</h2>
                {maxGuests > 0 && <span>{maxGuests} guests max</span>}
              </div>
              <div className="checkout-player-row">
                <span className="checkout-avatar">{getInitials(appUser)}</span>
                <div>
                  <strong>You</strong>
                  <p>{getDisplayName(appUser)}</p>
                </div>
                <strong>{isWaitlistCheckout ? 'No charge now' : formatMoney(price)}</strong>
              </div>
              {maxGuests > 0 && (
                <div className="checkout-guest-row">
                  <div>
                    <strong>Guests</strong>
                  </div>
                  <div className="checkout-guest-stepper" aria-label="Guest count">
                    <button
                      type="button"
                      disabled={effectiveGuestCount <= 0}
                      onClick={() => setGuestCount((count) => Math.max(count - 1, 0))}
                    >
                      -
                    </button>
                    <span>{effectiveGuestCount}</span>
                    <button
                      type="button"
                      disabled={effectiveGuestCount >= maxGuests}
                      onClick={() => setGuestCount((count) => Math.min(count + 1, maxGuests))}
                    >
                      +
                    </button>
                  </div>
                </div>
              )}
              {isWaitlistCheckout && (
                <p className="checkout-waitlist-note">
                  You won’t be charged now. If enough spots open, your saved payment method will be
                  charged automatically and you’ll move to the player list.
                </p>
              )}
              {isBlockedByCapacity && (
                <p className="checkout-error">Not enough spots are available for this join.</p>
              )}
            </section>

            <section className="checkout-card">
              <h2>Payment method</h2>
              <div className="checkout-payment-row">
                <strong>{paymentMethod ? formatPaymentMethod(paymentMethod) : 'Demo card .... 4242'}</strong>
                <span>Change payment coming soon</span>
              </div>
            </section>

            <section className="checkout-card checkout-policy">
              <ShieldCheckIcon />
              <div>
                <h2>Cancellation</h2>
                <p>
                  Free cancellation up to 24 hours before game time. After that, refunds are not issued.
                </p>
                <Link to="/terms" state={{ from: `/games/${game.id}/checkout`, fromLabel: 'Back to checkout' }}>
                  View policy
                </Link>
              </div>
            </section>

            <label className="checkout-card checkout-agree">
              <input checked={agreed} type="checkbox" onChange={(event) => setAgreed(event.target.checked)} />
              <span>
                I agree to the Pickup Lane <Link to="/terms">Terms of Service</Link> and refund policy.
              </span>
            </label>

            {existingParticipant && (
              <p className="checkout-error">
                {existingParticipant.participant_status === 'waitlisted'
                  ? 'You are already on the waitlist for this game.'
                  : 'You already joined this game.'}
              </p>
            )}
            {submitError && <p className="checkout-error">{submitError}</p>}
          </div>

          <aside className="checkout-card checkout-summary-card">
            <h2>Order summary</h2>
            <CheckoutLine
              label="1 x Player"
              value={formatMoneyWithTiming(price, chargeTiming)}
            />
            {effectiveGuestCount > 0 && (
              <CheckoutLine
                label={`${effectiveGuestCount} x ${effectiveGuestCount === 1 ? 'Guest' : 'Guests'}`}
                value={formatMoneyWithTiming(price * effectiveGuestCount, chargeTiming)}
              />
            )}
            {!isWaitlistCheckout && <CheckoutLine label="Pickup Lane fee" value={formatMoney(platformFee)} />}
            {isWaitlistCheckout && <p className="checkout-summary-note">No charge now</p>}
            <div className="checkout-total">
              <span>Total</span>
              <strong>{formatMoneyWithTiming(total, chargeTiming)}</strong>
            </div>

            <button
              className="checkout-confirm-button"
              type="button"
              disabled={!agreed || isSubmitting || Boolean(existingParticipant) || isBlockedByCapacity}
              onClick={confirmBooking}
            >
              {isSubmitting
                ? 'Confirming...'
                : isBlockedByCapacity
                  ? 'Not Enough Spots'
                  : isWaitlistCheckout
                    ? 'Join Waitlist'
                    : 'Confirm & Pay'}
            </button>

            <p className="checkout-secure-note">
              <ShieldCheckIcon />
              Secure checkout
            </p>
          </aside>
        </div>
      </main>
    </div>
  )
}

function CheckoutLine({ label, value }) {
  return (
    <div className="checkout-line">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function getParticipantSummary(participants, totalSpots = 0) {
  const signedUpCount = participants.filter((participant) =>
    ACTIVE_ROSTER_STATUSES.has(participant.participant_status),
  ).length

  return {
    signedUpCount,
    spotsLeft: Math.max((totalSpots || 0) - signedUpCount, 0),
  }
}

function getPrimaryImage(images, game) {
  const image = images
    .slice()
    .sort(
      (first, second) =>
        Number(second.is_primary) - Number(first.is_primary) ||
        first.sort_order - second.sort_order,
    )[0]

  if (image?.image_url) {
    return buildMediaUrl(image.image_url)
  }

  return game?.game_type === 'community' ? defaultCommunityVenueImage : defaultCommunityVenueImage
}

function hasCompleteProfile(user) {
  return Boolean(user?.first_name && user?.last_name && user?.date_of_birth)
}

function getDisplayName(user) {
  return `${user?.first_name || ''} ${user?.last_name || ''}`.trim() || user?.email || 'You'
}

function getInitials(user) {
  const first = user?.first_name?.[0] || ''
  const last = user?.last_name?.[0] || ''
  return `${first}${last}`.toUpperCase() || 'PL'
}

function formatVenueAddress(game, venue) {
  const street = game.address_snapshot || venue?.address_line_1
  const city = game.city_snapshot || venue?.city
  const state = game.state_snapshot || venue?.state
  const postalCode = venue?.postal_code
  return [street, [city, state, postalCode].filter(Boolean).join(' ')].filter(Boolean).join(', ')
}

function formatDate(value) {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value))
}

function formatTime(value) {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

function formatTimeRange(start, end) {
  return `${formatTime(start)} - ${formatTime(end)}`
}

function formatMoney(cents) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format((cents || 0) / 100)
}

function formatMoneyWithTiming(cents, timing) {
  const amount = formatMoney(cents)
  return timing ? `${amount} ${timing}` : amount
}

function formatPaymentMethod(paymentMethod) {
  if (!paymentMethod) {
    return 'Demo card .... 4242'
  }

  return `${capitalize(paymentMethod.card_brand || 'card')} .... ${paymentMethod.card_last4}`
}

function capitalize(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : ''
}

export default GameCheckoutPage
