import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../../../src/hooks/useAuth.js'
import GameCheckoutPage from '../../../src/pages/browse-games/GameCheckoutPage.jsx'
import { PaymentMethodsPage } from '../../../src/pages/profile/PaymentMethodsPage.jsx'
import {
  checkoutStatus, fakePageApi, game, GAME_ID, otherPlayers, participant, paymentIntent, PLAYER_ID, quote, savedCard, OTHER_CARD_ID, sentBody,
} from './gameCheckoutTestKit.jsx'

const stripeConfig = vi.hoisted(() => ({ enabled: true, supported: true }))

vi.mock('../../../src/lib/apiClient.js', async (importOriginal) => ({
  ...(await importOriginal()),
  apiRequest: vi.fn(),
}))
vi.mock('../../../src/hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../../../src/hooks/useStepUp.js', () => ({
  useStepUp: () => ({ runWithStepUp: (action) => action() }),
}))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))
vi.mock('../../../src/components/BrowseAppNav.jsx', () => ({ default: () => null }))
vi.mock('../../../src/lib/stripe.js', () => ({
  areStripePaymentsEnabled: () => stripeConfig.enabled,
  hasStripeCheckoutSupport: () => stripeConfig.supported,
  hasStripePublishableKey: () => stripeConfig.supported,
  stripePromise: {},
}))

afterEach(() => vi.useRealTimers())

const CHECKOUT_PATH = `/games/${GAME_ID}/checkout`

beforeEach(() => {
  stripeConfig.enabled = true
  stripeConfig.supported = true
  vi.mocked(useAuth).mockReturnValue({
    appUser: {
      id: PLAYER_ID,
      first_name: 'Test',
      last_name: 'Player',
      date_of_birth: '1990-01-01',
      account_status: 'active',
    },
    currentUser: { getIdToken: vi.fn().mockResolvedValue('test-token') },
    isLoading: false,
  })
})

function fakeCheckoutPage(participants = [], extraAnswers = {}) {
  const occupiedSpots = participants.filter(
    (place) => ['confirmed', 'pending_payment'].includes(place.participant_status),
  ).length
  fakePageApi(game({
    roster_counts: {
      occupied_spots: occupiedSpots,
      spots_remaining: 14 - occupiedSpots,
      waitlist_count: 0,
    },
  }), {
    'GET /games/{game_id}/participants': participants,
    'GET /user-payment-methods': [savedCard({ card_last4: '1111' })],
    'GET /checkout/games/{game_id}/quote': (path) => {
      const params = new URL(path, 'http://test.local').searchParams
      const guests = Number(params.get('guest_count') || 0)
      const total = 1000 * (params.get('add_guests') === 'true' ? guests : guests + 1)
      return quote({
        subtotal_cents: total,
        checkout_total_cents: total,
        final_amount_due_cents: total,
      })
    },
    ...extraAnswers,
  })
}

function renderFromCheckout(search = '') {
  const router = createMemoryRouter([
    { path: '/games/:gameId/checkout', element: <GameCheckoutPage /> },
    { path: '/games/:gameId', element: <h1>Game Details</h1> },
    { path: '/profile/payment-methods', element: <PaymentMethodsPage /> },
    { path: '/profile', element: <h1>Profile</h1> },
  ], { initialEntries: [`${CHECKOUT_PATH}${search}`] })
  render(<RouterProvider router={router} />)
  return router
}

describe('Game Checkout Manage cards', () => {
  it('F17-28: Manage cards opens Payment Methods', async () => {
    const user = userEvent.setup()
    fakeCheckoutPage()
    renderFromCheckout()

    await user.click(await screen.findByRole('button', { name: 'Add a guest' }))
    await user.click(screen.getByRole('button', { name: 'Add a guest' }))
    await user.click(screen.getByRole('link', { name: 'Manage cards' }))
    expect(await screen.findByRole('heading', { name: 'Payment Methods' })).toBeInTheDocument()
  })

  it('F17-28: Back restores checkout for the same game and guests', async () => {
    const user = userEvent.setup()
    fakeCheckoutPage()
    const router = renderFromCheckout()

    await user.click(await screen.findByRole('button', { name: 'Add a guest' }))
    await user.click(screen.getByRole('button', { name: 'Add a guest' }))
    await user.click(screen.getByRole('link', { name: 'Manage cards' }))
    expect(await screen.findByRole('heading', { name: 'Payment Methods' })).toBeInTheDocument()
    await user.click(await screen.findByRole('link', { name: 'Back to checkout' }))

    expect(await screen.findByRole('heading', { name: 'Confirm Spot' })).toBeInTheDocument()
    expect(await screen.findByText('+2 guests')).toBeInTheDocument()
    expect(router.state.location.pathname).toBe(CHECKOUT_PATH)
    expect(router.state.location.search).toBe('?guest_count=2')
  })

  it('F17-29: from adding guests, Back returns to adding the same number of guests', async () => {
    const user = userEvent.setup()
    fakeCheckoutPage([participant()])
    const router = renderFromCheckout('?mode=add-guests&guest_count=1')

    await user.click(await screen.findByRole('button', { name: 'Add a guest' }))
    await user.click(screen.getByRole('link', { name: 'Manage cards' }))
    await user.click(await screen.findByRole('link', { name: 'Back to checkout' }))

    expect(await screen.findByRole('heading', { name: 'Add Guests' })).toBeInTheDocument()
    expect(await screen.findByText('Adding 2 guests')).toBeInTheDocument()
    expect(router.state.location.search).toBe('?mode=add-guests&guest_count=2')
  })

  it('F17-30: checkout does not offer Manage cards while a payment is under way', async () => {
    fakeCheckoutPage([participant({ participant_status: 'pending_payment', confirmed_at: null })])
    renderFromCheckout()

    expect(await screen.findByText(/Selected for this booking/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Change' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Manage cards' })).not.toBeInTheDocument()
  })


  it.each(['processing', 'unavailable'])('F17-30: Manage cards stays hidden while a new payment is submitted and checked (%s)', async (result) => {
    const user = userEvent.setup()
    let finishPayment
    let finishStatus
    const paymentPending = new Promise((resolve) => { finishPayment = resolve })
    const statusPending = new Promise((resolve) => { finishStatus = resolve })
    fakeCheckoutPage([], {
      'POST /checkout/games/{game_id}/payment-intent': () => paymentPending,
      'GET /checkout/bookings/{booking_id}/status': async () => {
        const status = await statusPending
        if (result === 'unavailable') throw new Error('Payment status unavailable.')
        return status
      },
      'GET /user-payment-methods': [savedCard(), savedCard({ id: OTHER_CARD_ID, card_last4: '2222', is_default: false })],
    })
    renderFromCheckout()
    await user.click(await screen.findByRole('checkbox', { name: 'Agree to Pickup Lane terms' }))
    await user.click(screen.getAllByRole('button', { name: 'Confirm Spot' })[0])
    await screen.findAllByRole('button', { name: 'Confirming...' })
    expect(screen.queryByRole('link', { name: 'Manage cards' })).not.toBeInTheDocument()
    await act(async () => { finishPayment(paymentIntent()) })
    await waitFor(() => expect(screen.getByText('Confirming your spot...')).toBeInTheDocument())
    expect(screen.queryByRole('link', { name: 'Manage cards' })).not.toBeInTheDocument()
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    await act(async () => { finishStatus(checkoutStatus({ booking_status: 'pending_payment', booking_payment_status: 'processing', reservation_status: 'held', payment_status: 'processing', provider_status: 'processing' })) })
    await act(async () => { await vi.advanceTimersByTimeAsync(16000) })
    expect(screen.getByText(result === 'processing' ? 'Payment is still unresolved. Your spot will not remain held past expiry.' : 'Payment status unavailable.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Manage cards' })).not.toBeInTheDocument()
    vi.useRealTimers()
    await user.click(screen.getByRole('button', { name: 'Change' }))
    await user.click(screen.getByRole('button', { name: 'Use this card' }))
    expect(screen.queryByRole('link', { name: 'Manage cards' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add a guest' })).toBeDisabled()
    expect(screen.getByText(result === 'processing' ? 'Payment is still unresolved. Your spot will not remain held past expiry.' : 'Payment status unavailable.')).toBeInTheDocument()
  })

  it.each(['ordinary checkout', 'paid waitlist'])('F17-31: Manage cards is hidden when card payments are disabled (%s)', async (mode) => {
    stripeConfig.enabled = false
    fakeCheckoutPage(mode === 'paid waitlist' ? otherPlayers(14) : [])
    renderFromCheckout()
    await screen.findByText('Evening Pickup')
    expect(screen.queryByRole('link', { name: 'Manage cards' })).not.toBeInTheDocument()
  })

  it.each(['ordinary checkout', 'paid waitlist'])('F17-31: Manage cards is hidden when Stripe card setup is unavailable (%s)', async (mode) => {
    stripeConfig.supported = false
    fakeCheckoutPage(mode === 'paid waitlist' ? otherPlayers(14) : [])
    renderFromCheckout()
    await screen.findByText('Evening Pickup')
    expect(screen.queryByRole('link', { name: 'Manage cards' })).not.toBeInTheDocument()
  })


  it.each([['new', 'failed'], ['new', 'requires_payment_method'], ['reopened', 'failed'], ['reopened', 'requires_payment_method']])('F17-12: Manage cards returns after a known payment failure (%s, %s)', async (mode, status) => {
    const user = userEvent.setup()
    fakeCheckoutPage(mode === 'reopened' ? [participant({ participant_status: 'pending_payment', confirmed_at: null })] : [], {
      'POST /checkout/games/{game_id}/payment-intent': paymentIntent(),
      'GET /checkout/bookings/{booking_id}/status': checkoutStatus({
        booking_status: status === 'failed' ? 'failed' : 'pending_payment',
        booking_payment_status: status === 'failed' ? 'failed' : 'processing',
        reservation_status: status === 'failed' ? 'released' : 'held',
        payment_status: status,
        provider_status: 'requires_payment_method',
      }),
    })
    renderFromCheckout()
    await user.click(await screen.findByRole('checkbox', { name: 'Agree to Pickup Lane terms' }))
    await user.click(screen.getAllByRole('button', { name: 'Confirm Spot' })[0])
    expect(await screen.findByText(status === 'failed' ? 'Payment could not be confirmed. Please try again.' : 'Choose another saved card to continue.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Manage cards' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
  })

  it.each(['new', 'reopened'])('F17-12: a card retry keeps the held party fixed (%s)', async (mode) => {
    const user = userEvent.setup()
    fakeCheckoutPage(mode === 'reopened' ? [participant({ participant_status: 'pending_payment', confirmed_at: null })] : [], {
      'POST /checkout/games/{game_id}/payment-intent': paymentIntent({ stripe_status: 'requires_payment_method', payment_status: 'requires_payment_method', provider_status: 'requires_payment_method' }),
    })
    renderFromCheckout()
    await user.click(await screen.findByRole('checkbox', { name: 'Agree to Pickup Lane terms' }))
    await user.click(screen.getAllByRole('button', { name: 'Confirm Spot' })[0])
    expect(await screen.findByText('This saved card could not be charged. Choose another card.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add a guest' })).toBeDisabled()
  })

  it('F17-12: a released reopened checkout allows a different party on retry', async () => {
    const user = userEvent.setup()
    let attempts = 0
    let statusCalls = 0
    fakeCheckoutPage([participant({ participant_status: 'pending_payment', confirmed_at: null })], {
      'POST /checkout/games/{game_id}/payment-intent': () => paymentIntent(++attempts === 1 ? {} : {
        booking_id: '00000000-0000-4000-8000-000000000026', amount_cents: 2000, subtotal_cents: 2000, checkout_total_cents: 2000, final_amount_due_cents: 2000, stripe_amount_cents: 2000,
      }),
      'GET /checkout/bookings/{booking_id}/status': () => ++statusCalls === 1 ? checkoutStatus({
        booking_status: 'failed', booking_payment_status: 'failed', reservation_status: 'released', payment_status: 'failed', provider_status: 'requires_payment_method',
      }) : checkoutStatus({ partySize: 2, booking_id: '00000000-0000-4000-8000-000000000026', amount_cents: 2000, subtotal_cents: 2000, checkout_total_cents: 2000, final_amount_due_cents: 2000, stripe_amount_cents: 2000 }),
    })
    renderFromCheckout()
    await user.click(await screen.findByRole('checkbox', { name: 'Agree to Pickup Lane terms' }))
    await user.click(screen.getAllByRole('button', { name: 'Confirm Spot' })[0])
    await screen.findByText('Payment could not be confirmed. Please try again.')
    expect(screen.getByRole('button', { name: 'Add a guest' })).toBeEnabled()
    await user.click(screen.getByRole('button', { name: 'Add a guest' }))
    expect(await screen.findByText('+1 guest')).toBeInTheDocument()
    await waitFor(() => expect(screen.getAllByRole('button', { name: 'Confirm Spot' })[0]).toBeEnabled())
    await user.click(screen.getAllByRole('button', { name: 'Confirm Spot' })[0])
    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(sentBody('/payment-intent')).toMatchObject({ guest_count: 1 })
  })

})
