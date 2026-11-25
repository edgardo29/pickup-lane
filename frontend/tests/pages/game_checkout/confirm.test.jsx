import { act, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../../../src/hooks/useAuth.js'
import { ApiRequestError, apiRequest } from '../../../src/lib/apiClient.js'
import { CARD_ID, checkoutStatus, communityGame, fakePageApi, game, GAME_ID, joinAnswer, OTHER_CARD_ID, paymentIntent, PLAYER_ID, quote, renderCheckout, savedCard, sentBody } from './gameCheckoutTestKit.jsx'

const fakeStripe = vi.hoisted(() => ({
  handleNextAction: vi.fn(), confirmSetup: vi.fn(), supported: true, enabled: true,
}))
vi.mock('../../../src/lib/apiClient.js', async (importOriginal) => ({
  ...(await importOriginal()), apiRequest: vi.fn(),
}))
vi.mock('../../../src/hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../../../src/components/BrowseAppNav.jsx', () => ({ default: () => null }))
vi.mock('../../../src/lib/stripe.js', () => ({
  areStripePaymentsEnabled: () => fakeStripe.enabled,
  hasStripeCheckoutSupport: () => fakeStripe.supported,
  hasStripePublishableKey: () => fakeStripe.supported,
  stripePromise: Promise.resolve(fakeStripe),
}))
vi.mock('@stripe/react-stripe-js', () => ({
  Elements: ({ children }) => children,
  PaymentElement: ({ onChange }) => (
    <button type="button" onClick={() => onChange({ complete: true })}>Enter test card</button>
  ),
  useElements: () => ({ submit: async () => ({}) }),
  useStripe: () => fakeStripe,
}))

function signIn(overrides = {}) {
  vi.mocked(useAuth).mockReturnValue({
    appUser: { id: PLAYER_ID, first_name: 'Test', last_name: 'Player', date_of_birth: '1990-01-01', account_status: 'active', ...overrides },
    currentUser: { getIdToken: vi.fn().mockResolvedValue('test-token') },
    isLoading: false,
  })
}

beforeEach(() => {
  signIn()
  fakeStripe.supported = true
  fakeStripe.enabled = true
  fakeStripe.handleNextAction.mockResolvedValue({})
  fakeStripe.confirmSetup.mockResolvedValue({ setupIntent: { id: 'seti_test_123' } })
})
afterEach(() => vi.useRealTimers())

async function agreeAndConfirm(user, label = 'Confirm Spot') {
  await user.click(await screen.findByRole('checkbox', { name: 'Agree to Pickup Lane terms' }))
  await user.click(screen.getAllByRole('button', { name: label })[0])
}

function paidAnswers(overrides = {}) {
  return {
    'POST /checkout/games/{game_id}/payment-intent': paymentIntent(),
    'GET /checkout/bookings/{booking_id}/status': checkoutStatus(),
    ...overrides,
  }
}

describe('Game Checkout', () => {
  it('F17-4: choosing another saved card pays with that card', async () => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'GET /user-payment-methods': [
        savedCard(),
        savedCard({ id: OTHER_CARD_ID, card_last4: '1881', is_default: false }),
      ],
      'POST /checkout/games/{game_id}/payment-intent': paymentIntent(),
      'GET /checkout/bookings/{booking_id}/status': checkoutStatus(),
    })
    renderCheckout()

    await user.click(await screen.findByRole('button', { name: 'Change' }))
    const selector = screen.getByRole('dialog', { name: 'Choose payment method' })
    await user.click(within(selector).getByRole('button', { name: 'Use this card' }))
    await agreeAndConfirm(user)

    await screen.findByRole('heading', { name: 'Game Details' })
    expect(sentBody('/payment-intent').payment_method_id).toBe(OTHER_CARD_ID)
  })

  it('F17-12: failed card authentication is shown without claiming a spot', async () => {
    const user = userEvent.setup()
    fakeStripe.handleNextAction.mockResolvedValue({ error: { message: 'Your card was declined.' } })
    fakePageApi(game(), {
      'POST /checkout/games/{game_id}/payment-intent': paymentIntent({ stripe_status: 'requires_action', payment_status: 'requires_action', provider_status: 'requires_action', booking_payment_status: 'requires_action' }),
    })
    renderCheckout()

    await agreeAndConfirm(user)

    expect(await screen.findByText('Your card was declined.')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
  })

  it('F17-12: a card that cannot be charged asks for another card', async () => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'POST /checkout/games/{game_id}/payment-intent': paymentIntent({
        stripe_status: 'requires_payment_method', payment_status: 'requires_payment_method',
      }),
    })
    renderCheckout()

    await agreeAndConfirm(user)

    expect(await screen.findByText(
      'This saved card could not be charged. Choose another card.',
    )).toBeInTheDocument()
  })

  it('F17-13: a payment completed after the hold expired reports a refund, not a spot', async () => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'POST /checkout/games/{game_id}/payment-intent': paymentIntent(),
      'GET /checkout/bookings/{booking_id}/status': checkoutStatus({
        booking_status: 'expired', reservation_status: 'released', compensation_status: 'required',
      }),
    })
    renderCheckout()

    await agreeAndConfirm(user)

    expect(await screen.findByText(
      'Your payment completed after the spot expired. A refund is required.',
    )).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
  })

  it('F17-14: a failed load offers a way back to the game', async () => {
    fakePageApi(new Error('Unable to load this game.'))
    renderCheckout()

    expect(await screen.findByRole('heading', { name: 'Checkout unavailable' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to game' })).toHaveAttribute(
      'href', expect.stringMatching(/\/games\/.+$/),
    )
  })

  it('F17-14: a second click while confirming sends only one request', async () => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'POST /checkout/games/{game_id}/payment-intent': () => new Promise(() => {}),
    })
    renderCheckout()

    await agreeAndConfirm(user)
    await user.click(screen.getAllByRole('button', { name: 'Confirming...' })[0])

    const intentCalls = vi.mocked(apiRequest).mock.calls.filter(
      ([path]) => path.endsWith('/payment-intent'),
    )
    expect(intentCalls).toHaveLength(1)
  })

  it('F17-14: a saved-card load error is shown and can be retried', async () => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'GET /user-payment-methods': new Error('Card service unavailable'),
    })
    renderCheckout()

    expect(await screen.findByText('Saved cards could not be loaded. Try again.')).toBeInTheDocument()
    expect(screen.queryByText('No payment method')).not.toBeInTheDocument()
    await user.click(screen.getByRole('checkbox', { name: 'Agree to Pickup Lane terms' }))
    expect(screen.getAllByRole('button', { name: 'Confirm Spot' })[0]).toBeDisabled()

    fakePageApi(game())
    await user.click(screen.getByRole('button', { name: 'Retry' }))

    expect(await screen.findByText('Selected for this booking', { exact: false })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Confirm Spot' })[0]).toBeEnabled()
  })

  it('F17-7: a signed-out visitor is sent to sign in', async () => {
    vi.mocked(useAuth).mockReturnValue({ appUser: null, currentUser: null, isLoading: false })
    fakePageApi(game())
    renderCheckout()

    expect(await screen.findByRole('heading', { name: 'Sign In' })).toBeInTheDocument()
  })

  it('F17-7: an incomplete profile is sent to Finish Profile', async () => {
    signIn({ date_of_birth: null })
    fakePageApi(game())
    renderCheckout()

    expect(await screen.findByRole('heading', { name: 'Finish Profile' })).toBeInTheDocument()
  })

  it('F17-7: an unverified email sees the rejection and stays on checkout', async () => {
    const user = userEvent.setup()
    fakePageApi(communityGame(), {
      'POST /games/{game_id}/join': new ApiRequestError(
        'Verified email required.', { status: 403 },
      ),
    })
    renderCheckout()

    await agreeAndConfirm(user)

    expect(await screen.findByText('Verified email required.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Confirm Spot' })).toBeInTheDocument()
  })

  it('F17-10: a stale confirmation reports the failure without success', async () => {
    const user = userEvent.setup()
    fakePageApi(communityGame(), {
      'POST /games/{game_id}/join': new ApiRequestError(
        'This game is not open for joining.', { status: 400 },
      ),
    })
    renderCheckout()

    await agreeAndConfirm(user)

    expect(await screen.findByText('This game is not open for joining.')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
  })

  it('F17-15: a suspended player cannot confirm a new booking', async () => {
    const user = userEvent.setup()
    signIn({ account_status: 'suspended' })
    fakePageApi(communityGame(), {
      'POST /games/{game_id}/join': new ApiRequestError('Active account required.', { status: 403 }),
    })
    renderCheckout()

    await agreeAndConfirm(user)

    expect(await screen.findByText('Active account required.')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
  })

  it('F17-19: full credit confirms without a card', async () => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'GET /user-payment-methods': [],
      'GET /checkout/games/{game_id}/quote': quote({
        available_credit_cents: 1000, credit_applied_cents: 1000,
        final_amount_due_cents: 0, payment_required: false,
      }),
      'POST /checkout/games/{game_id}/payment-intent': paymentIntent({
        client_secret: null, payment_id: null, amount_cents: 0, stripe_status: null,
        credit_applied_cents: 1000, final_amount_due_cents: 0, stripe_amount_cents: 0,
        payment_required: false, booking_status: 'confirmed', booking_payment_status: 'paid',
        reservation_status: 'confirmed', payment_status: null, provider_status: null,
      }),
    })
    renderCheckout()

    expect(await screen.findByText('Nothing is due, so no card is needed.')).toBeInTheDocument()
    await agreeAndConfirm(user)

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(sentBody('/payment-intent')).toEqual({
      guest_count: 0,
      return_url: expect.stringContaining('/checkout'),
    })
  })

  it('F17-19: card-list failure does not block a fully covered booking', async () => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'GET /user-payment-methods': new Error('Card service unavailable'),
      'GET /checkout/games/{game_id}/quote': quote({
        available_credit_cents: 1000, credit_applied_cents: 1000,
        final_amount_due_cents: 0, payment_required: false,
      }),
      'POST /checkout/games/{game_id}/payment-intent': paymentIntent({
        client_secret: null, payment_id: null, amount_cents: 0, stripe_status: null,
        credit_applied_cents: 1000, final_amount_due_cents: 0, stripe_amount_cents: 0,
        payment_required: false, booking_status: 'confirmed', booking_payment_status: 'paid',
        reservation_status: 'confirmed', payment_status: null, provider_status: null,
      }),
    })
    renderCheckout()

    expect(await screen.findByText('Saved cards could not be loaded. Try again.')).toBeInTheDocument()
    expect(await screen.findByText('Nothing is due, so no card is needed.')).toBeInTheDocument()
    await agreeAndConfirm(user)

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
  })

  it("F17-2: community confirmation submits the whole selected party", async () => {
    const user = userEvent.setup()
    fakePageApi(communityGame(), { 'POST /games/{game_id}/join': joinAnswer() })
    renderCheckout('?guest_count=2')
    await agreeAndConfirm(user)
    await screen.findByRole('heading', { name: 'Game Details' })
    expect(sentBody('/join')).toEqual({ guest_count: 2 })
  })

  it("F17-2: confirmed community checkout returns without app payment", async () => {
    const user = userEvent.setup()
    fakePageApi(communityGame({ price_per_player_cents: 1000 }), { 'POST /games/{game_id}/join': joinAnswer() })
    renderCheckout()
    await agreeAndConfirm(user)
    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(vi.mocked(apiRequest).mock.calls.some(([path]) => path.includes('/payment-intent'))).toBe(false)
  })

  it("F17-3: official checkout waits for payment confirmation before returning", async () => {
    const user = userEvent.setup()
    let finishStatus
    let statusCalls = 0
    const pending = new Promise((resolve) => { finishStatus = resolve })
    fakePageApi(game(), paidAnswers({ 'GET /checkout/bookings/{booking_id}/status': () => ++statusCalls === 1 ? pending : checkoutStatus() }))
    renderCheckout()
    await agreeAndConfirm(user)
    await waitFor(() => expect(apiRequest).toHaveBeenCalledWith(expect.stringContaining('/status'), expect.anything()))
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    await act(async () => { finishStatus(checkoutStatus({ booking_status: 'pending_payment', booking_payment_status: 'processing', reservation_status: 'held', payment_status: 'processing', provider_status: 'processing' })) })
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
    await act(async () => { await vi.advanceTimersByTimeAsync(1200) })
    expect(screen.getByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
  })

  it("F17-12: card authentication runs before any confirmed return", async () => {
    const user = userEvent.setup()
    let finishAuthentication
    fakeStripe.handleNextAction.mockImplementation(() => new Promise((resolve) => { finishAuthentication = resolve }))
    fakePageApi(game(), paidAnswers({ 'POST /checkout/games/{game_id}/payment-intent': paymentIntent({ stripe_status: 'requires_action', payment_status: 'requires_action', booking_payment_status: 'requires_action' }) }))
    renderCheckout()
    await agreeAndConfirm(user)
    await waitFor(() => expect(fakeStripe.handleNextAction).toHaveBeenCalledWith({ clientSecret: 'pi_test_secret' }))
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
    await act(async () => { finishAuthentication({}) })
    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
  })

  it("F17-13: an unresolved payment is shown without a confirmed spot", async () => {
    const user = userEvent.setup()
    let finishStatus
    let calls = 0
    const pending = new Promise((resolve) => { finishStatus = resolve })
    fakePageApi(game(), paidAnswers({
      'GET /checkout/bookings/{booking_id}/status': () => ++calls === 1 ? pending : checkoutStatus(),
    }))
    renderCheckout()
    await agreeAndConfirm(user)
    await waitFor(() => expect(calls).toBe(1))
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    await act(async () => { finishStatus(checkoutStatus({ booking_status: 'pending_payment', booking_payment_status: 'processing', reservation_status: 'held', payment_status: 'requires_capture', provider_status: 'requires_capture' })) })
    expect(screen.getByText('Payment is unresolved and no spot has been confirmed.')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
    await act(async () => { await vi.advanceTimersByTimeAsync(1200) })
    expect(screen.getByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
  })

  it("F17-13: an expired hold is shown without claiming confirmation", async () => {
    const user = userEvent.setup()
    fakePageApi(game(), paidAnswers({ 'GET /checkout/bookings/{booking_id}/status': checkoutStatus({ booking_status: 'expired', booking_payment_status: 'processing', reservation_status: 'released', payment_status: 'unknown', provider_status: 'unknown' }) }))
    renderCheckout()
    await agreeAndConfirm(user)
    expect(await screen.findByText('The spot expired while payment was unresolved. Payment status is still being checked.')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
  })

  it("F17-13: a payment capacity conflict reports a refund rather than a spot", async () => {
    const user = userEvent.setup()
    fakePageApi(game(), paidAnswers({ 'GET /checkout/bookings/{booking_id}/status': checkoutStatus({ booking_status: 'capacity_conflict', reservation_status: 'capacity_conflict', compensation_status: 'required' }) }))
    renderCheckout()
    await agreeAndConfirm(user)
    expect(await screen.findByText('Your payment completed, but the spot could not be confirmed. A refund is required.')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
  })

  it("F17-14: load failure returns to the same game", async () => {
    const user = userEvent.setup()
    fakePageApi(new Error('Unable to load this game.'))
    const router = renderCheckout()
    await user.click(await screen.findByRole('link', { name: 'Back to game' }))
    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe(`/games/${GAME_ID}`)
  })

  it("F17-10: new confirmation closes at the exact five-minute cutoff", async () => {
    const now = new Date('2030-06-15T23:05:00Z').valueOf()
    vi.spyOn(Date, 'now').mockReturnValue(now)
    const user = userEvent.setup()
    fakePageApi(communityGame())
    renderCheckout()
    expect(await screen.findByText('Joining is closed for this game.')).toBeInTheDocument()
    await user.click(screen.getByRole('checkbox', { name: 'Agree to Pickup Lane terms' }))
    expect(screen.getAllByRole('button', { name: 'Confirm Spot' })[0]).toBeDisabled()
    expect(sentBody('/join')).toBeNull()
  })

  it("F17-24: small-balance coverage allows confirmation without a card", async () => {
    const user = userEvent.setup()
    fakePageApi(game({ price_per_player_cents: 1000 }), {
      'GET /user-payment-methods': [],
      'GET /checkout/games/{game_id}/quote': quote({ subtotal_cents: 1000, checkout_total_cents: 1000, available_credit_cents: 970, credit_applied_cents: 970, minimum_charge_adjustment_cents: 30, final_amount_due_cents: 0, payment_required: false }),
      'POST /checkout/games/{game_id}/payment-intent': paymentIntent({ client_secret: null, payment_id: null, amount_cents: 0, stripe_status: null, subtotal_cents: 1000, checkout_total_cents: 1000, available_credit_cents: 970, credit_applied_cents: 970, minimum_charge_adjustment_cents: 30, final_amount_due_cents: 0, stripe_amount_cents: 0, payment_required: false, booking_status: 'confirmed', booking_payment_status: 'paid', reservation_status: 'confirmed', payment_status: null, provider_status: null }),
    })
    renderCheckout()
    expect((await screen.findByText('Amount due')).nextSibling).toHaveTextContent('$0.00')
    await agreeAndConfirm(user)
    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(sentBody('/payment-intent')).not.toHaveProperty('payment_method_id')
  })

  it("F17-26: a covered low price confirms without a card", async () => {
    const user = userEvent.setup()
    fakePageApi(game({ price_per_player_cents: 30 }), {
      'GET /user-payment-methods': [],
      'GET /checkout/games/{game_id}/quote': quote({ subtotal_cents: 30, checkout_total_cents: 30, available_credit_cents: 0, credit_applied_cents: 0, minimum_charge_adjustment_cents: 30, final_amount_due_cents: 0, payment_required: false }),
      'POST /checkout/games/{game_id}/payment-intent': paymentIntent({ client_secret: null, payment_id: null, amount_cents: 0, stripe_status: null, subtotal_cents: 30, checkout_total_cents: 30, available_credit_cents: 0, credit_applied_cents: 0, minimum_charge_adjustment_cents: 30, final_amount_due_cents: 0, stripe_amount_cents: 0, payment_required: false, booking_status: 'confirmed', booking_payment_status: 'paid', reservation_status: 'confirmed', payment_status: null, provider_status: null }),
    })
    renderCheckout()
    expect((await screen.findByText('Amount due')).nextSibling).toHaveTextContent('$0.00')
    await agreeAndConfirm(user)
    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(sentBody('/payment-intent')).not.toHaveProperty('payment_method_id')
  })

  it("F17-25: a balance exactly at the minimum uses normal Stripe payment", async () => {
    const user = userEvent.setup()
    const amounts = { available_credit_cents: 950, credit_applied_cents: 950, final_amount_due_cents: 50, minimum_charge_adjustment_cents: 0 }
    fakePageApi(game(), paidAnswers({
      'GET /checkout/games/{game_id}/quote': quote(amounts),
      'POST /checkout/games/{game_id}/payment-intent': paymentIntent({ ...amounts, amount_cents: 50, stripe_amount_cents: 50 }),
      'GET /checkout/bookings/{booking_id}/status': checkoutStatus({ ...amounts, amount_cents: 50, stripe_amount_cents: 50 }),
    }))
    renderCheckout()
    expect((await screen.findByText('Amount due')).nextSibling).toHaveTextContent('$0.50')
    expect(screen.queryByText('Covered by Pickup Lane')).not.toBeInTheDocument()
    await agreeAndConfirm(user)
    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(sentBody('/payment-intent').payment_method_id).toBe(CARD_ID)
  })
})
