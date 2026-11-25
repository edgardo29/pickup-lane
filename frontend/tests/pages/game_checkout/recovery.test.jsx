import { act, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../../../src/hooks/useAuth.js'
import { ApiRequestError, apiRequest } from '../../../src/lib/apiClient.js'
import { checkoutStatus, communityGame, fakePageApi, game, GAME_ID, guestCheckoutStatus, joinAnswer, otherPlayers, participant, PLAYER_ID, guestPaymentIntent, paymentIntent, quote, renderCheckout, savedCard, sentBody } from './gameCheckoutTestKit.jsx'

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


function pendingGuest() {
  return participant({ id: '00000000-0000-4000-8000-000000000025', participant_type: 'guest', user_id: null, guest_of_user_id: PLAYER_ID, participant_status: 'pending_payment', confirmed_at: null, roster_order: null, display_name_snapshot: 'Pending guest' })
}

function guestStatus(overrides = {}) {
  return guestCheckoutStatus(overrides)
}

describe('Game Checkout recovery', () => {
  it.each([true, false])('F17-13: a new held payment keeps ordinary checkout instead of waitlisting (waitlist %s)', async (waitlistEnabled) => {
    const user = userEvent.setup()
    let finishStatus
    const pending = new Promise((resolve) => { finishStatus = resolve })
    const held = checkoutStatus({ booking_status: 'pending_payment', booking_payment_status: 'processing', reservation_status: 'held', payment_status: 'processing', provider_status: 'processing', roster_counts: { occupied_spots: 1, spots_remaining: 0, waitlist_count: 0 } })
    fakePageApi(game({ total_spots: 1, waitlist_enabled: waitlistEnabled }), {
      'POST /checkout/games/{game_id}/payment-intent': paymentIntent(),
      'GET /checkout/bookings/{booking_id}/status': () => pending,
    })
    renderCheckout()
    await agreeAndConfirm(user)
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    await act(async () => { finishStatus(held) })
    await act(async () => { await vi.advanceTimersByTimeAsync(16000) })
    expect(screen.getByRole('heading', { name: 'Confirm Spot' })).toBeInTheDocument()
    expect(screen.queryByText('No charge now')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add a guest' })).toBeDisabled()
    expect(screen.getAllByRole('button', { name: 'Confirm Spot' })[0]).toBeEnabled()
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
  })

  it('F17-13: a new held guest payment preserves its guests and can be checked without another charge', async () => {
    const user = userEvent.setup()
    let finishStatus
    let calls = 0
    let settled = false
    const pending = new Promise((resolve) => { finishStatus = resolve })
    const held = guestStatus({ guest_reservation_status: 'held', roster_counts: { occupied_spots: 2, spots_remaining: 0, waitlist_count: 0 } })
    fakePageApi(game({ total_spots: 2 }), {
      'GET /games/{game_id}/participants': [participant()],
      'POST /checkout/games/{game_id}/guest-payment-intent': guestPaymentIntent(),
      'GET /checkout/bookings/{booking_id}/status': () => {
        calls += 1
        return settled ? guestCheckoutStatus({ payment_status: 'succeeded', guest_reservation_status: 'confirmed', roster_counts: held.roster_counts, amount_cents: 2000, subtotal_cents: 2000, checkout_total_cents: 2000, final_amount_due_cents: 2000, stripe_amount_cents: 2000 }) : calls === 1 ? pending : held
      },
    })
    renderCheckout('?mode=add-guests&guest_count=1')
    await agreeAndConfirm(user, 'Confirm Guests')
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    await act(async () => { finishStatus(held) })
    await act(async () => { await vi.advanceTimersByTimeAsync(16000) })
    expect(screen.getByText('Adding 1 guest')).toBeInTheDocument()
    expect(screen.getByText('Guest limit: 1/2')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add a guest' })).toBeDisabled()
    expect(screen.queryByRole('link', { name: 'Manage cards' })).not.toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Check Payment' })[0]).toBeEnabled()
    vi.useRealTimers()
    settled = true
    await user.click(screen.getAllByRole('button', { name: 'Check Payment' })[0])
    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(calls).toBe(13)
    expect(vi.mocked(apiRequest).mock.calls.filter(([path]) => path.endsWith('/guest-payment-intent'))).toHaveLength(1)
    expect(sentBody('/guest-payment-intent').guest_count).toBe(1)
  })

  it.each([true, false])('F17-8: expired holds do not block available checkout capacity (waitlist %s)', async (waitlistEnabled) => {
    const user = userEvent.setup()
    fakePageApi(game({ total_spots: 1, waitlist_enabled: waitlistEnabled }), {
      'GET /games/{game_id}/participants': otherPlayers(1).map((place) => ({ ...place, participant_status: 'pending_payment', confirmed_at: null })),
    }, { rosterCounts: { occupied_spots: 0, spots_remaining: 1, waitlist_count: 0 } })
    renderCheckout()
    await user.click(await screen.findByRole('checkbox', { name: 'Agree to Pickup Lane terms' }))
    expect(screen.getByRole('heading', { name: 'Confirm Spot' })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Confirm Spot' })[0]).toBeEnabled()
  })

  it('F17-8: expired holds do not block additional guest capacity', async () => {
    const user = userEvent.setup()
    fakePageApi(game({ total_spots: 2 }), {
      'GET /games/{game_id}/participants': [participant(), ...otherPlayers(1).map((place) => ({ ...place, participant_status: 'pending_payment', confirmed_at: null }))],
    }, { rosterCounts: { occupied_spots: 1, spots_remaining: 1, waitlist_count: 0 } })
    renderCheckout('?mode=add-guests&guest_count=1')
    await user.click(await screen.findByRole('checkbox', { name: 'Agree to Pickup Lane terms' }))
    expect(screen.getByText('Adding 1 guest')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Confirm Guests' })[0]).toBeEnabled()
  })

  it.each(['requires_action', 'processing'])('F17-13: an expired guest hold is shown and releases checkout controls (%s)', async (paymentStatus) => {
    const user = userEvent.setup()
    fakePageApi(game({ total_spots: 3 }), {
      'GET /games/{game_id}/participants': [participant(), pendingGuest()],
      'GET /checkout/bookings/{booking_id}/status': guestStatus({ payment_status: paymentStatus, provider_status: paymentStatus, guest_reservation_status: 'released', roster_counts: { occupied_spots: 1, spots_remaining: 2, waitlist_count: 0 } }),
    })
    renderCheckout('?mode=add-guests&guest_count=1')
    await agreeAndConfirm(user, 'Check Payment')
    expect(await screen.findByText('The guest hold ended without adding the guests. Payment is still unresolved; a late successful charge requires a refund.')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Manage cards' })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Confirm Guests' })[0]).toBeEnabled()
    await user.click(screen.getByRole('button', { name: 'Add a guest' }))
    expect(screen.getByText('Adding 2 guests')).toBeInTheDocument()
    expect(sentBody('/guest-payment-intent')).toBeNull()
  })

  it('F17-5: a full roster beyond the first page offers the waitlist', async () => {
    fakePageApi(game({ total_spots: 60 }), { 'GET /games/{game_id}/participants': otherPlayers(60) })
    renderCheckout()
    expect(await screen.findByRole('heading', { name: 'Join Waitlist' })).toBeInTheDocument()
  })

  it('F17-9: an existing booking beyond the first page can add guests', async () => {
    const user = userEvent.setup()
    fakePageApi(game(), { 'GET /games/{game_id}/participants': [
      ...otherPlayers(50).map((place) => ({ ...place, participant_status: 'cancelled', cancelled_at: '2029-06-15T19:00:00Z' })), participant(),
    ] })
    renderCheckout('?mode=add-guests&guest_count=1')
    await user.click(await screen.findByRole('checkbox', { name: 'Agree to Pickup Lane terms' }))
    expect(screen.getAllByRole('button', { name: 'Confirm Guests' })[0]).toBeEnabled()
    expect(screen.queryByText('Only confirmed players can add guests to an existing booking.')).not.toBeInTheDocument()
  })

  it('F17-30: reopened pending guest checkout keeps Manage cards hidden', async () => {
    fakePageApi(game(), { 'GET /games/{game_id}/participants': [participant(), pendingGuest()] })
    renderCheckout('?mode=add-guests&guest_count=1')
    await screen.findByText('Evening Pickup')
    expect(screen.queryByRole('link', { name: 'Manage cards' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add a guest' })).toBeDisabled()
  })

  it('F17-6: reopened guest checkout checks the existing payment without another charge', async () => {
    const user = userEvent.setup()
    let finishStatus
    let calls = 0
    const pending = new Promise((resolve) => { finishStatus = resolve })
    fakePageApi(game({ total_spots: 2 }), {
      'GET /games/{game_id}/participants': [participant(), pendingGuest()],
      'POST /checkout/games/{game_id}/guest-payment-intent': new ApiRequestError('A guest payment is already in progress for your booking.', { status: 409 }),
      'GET /checkout/bookings/{booking_id}/status': () => ++calls === 1 ? pending : guestCheckoutStatus({ payment_status: 'succeeded', totalSpots: 2, amount_cents: 2000, subtotal_cents: 2000, checkout_total_cents: 2000, final_amount_due_cents: 2000, stripe_amount_cents: 2000 }),
    })
    renderCheckout('?mode=add-guests&guest_count=1')
    await agreeAndConfirm(user, 'Check Payment')
    expect(sentBody('/guest-payment-intent')).toBeNull()
    await waitFor(() => expect(calls).toBe(1))
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    await act(async () => { finishStatus(guestStatus({ totalSpots: 2 })) })
    expect(screen.getByText('Adding 1 guest')).toBeInTheDocument()
    expect(screen.getByText('Guest limit: 1/2')).toBeInTheDocument()
    await act(async () => { await vi.advanceTimersByTimeAsync(1200) })
    expect(screen.getByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(sentBody('/guest-payment-intent')).toBeNull()
  })

  it.each(['requires_payment_method', 'failed', 'canceled'])('F17-12: reopened guest checkout releases failed guest controls (%s)', async (paymentStatus) => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'GET /games/{game_id}/participants': [participant(), pendingGuest()],
      'GET /checkout/bookings/{booking_id}/status': guestStatus({ payment_status: paymentStatus, provider_status: paymentStatus === 'failed' ? 'requires_payment_method' : paymentStatus }),
    })
    renderCheckout('?mode=add-guests&guest_count=1')
    await agreeAndConfirm(user, 'Check Payment')
    expect(await screen.findByText(paymentStatus === 'requires_payment_method' ? 'Choose another saved card to continue.' : 'Payment could not be confirmed. Please try again.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Manage cards' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add a guest' })).toBeEnabled()
    await user.click(screen.getByRole('button', { name: 'Add a guest' }))
    expect(screen.getByText('Adding 2 guests')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Confirm Guests' })[0]).toBeEnabled()
    expect(sentBody('/guest-payment-intent')).toBeNull()
  })
  it('F17-3: a failed payment refreshes the released credit before retry', async () => {
    const user = userEvent.setup()
    let released = false
    fakePageApi(game(), {
      'GET /checkout/games/{game_id}/quote': () => quote({ available_credit_cents: released ? 500 : 300, credit_applied_cents: released ? 500 : 300, final_amount_due_cents: released ? 500 : 700 }),
      'POST /checkout/games/{game_id}/payment-intent': paymentIntent({ available_credit_cents: 300, credit_applied_cents: 300, final_amount_due_cents: 700, amount_cents: 700, stripe_amount_cents: 700 }),
      'GET /checkout/bookings/{booking_id}/status': () => {
        released = true
        return checkoutStatus({ booking_status: 'failed', booking_payment_status: 'failed', reservation_status: 'released', payment_status: 'failed', provider_status: 'requires_payment_method', available_credit_cents: 500, credit_applied_cents: 0, minimum_charge_adjustment_cents: 300, final_amount_due_cents: 700, amount_cents: 700, stripe_amount_cents: 700 })
      },
    })
    renderCheckout()
    await screen.findByText('Available game credit: $3.00')
    await agreeAndConfirm(user)
    await screen.findByText('Payment could not be confirmed. Please try again.')
    await waitFor(() => expect(screen.getByText('Amount due').nextSibling).toHaveTextContent('$5.00'))
    expect(screen.getByText('Game credit applied').nextSibling).toHaveTextContent('-$5.00')
  })

})


describe('Game Checkout correction regressions', () => {
  it.each([[false, 1000], [false, 970], [true, 1000], [true, 970]])(
    'F17-19, F17-24: covered checkout needs no Stripe setup (guests %s, credit %i)',
    async (addGuests, credit) => {
      const user = userEvent.setup()
      fakeStripe.supported = false
      const amounts = {
        available_credit_cents: credit, credit_applied_cents: credit,
        minimum_charge_adjustment_cents: 1000 - credit,
        final_amount_due_cents: 0, payment_required: false,
      }
      const answer = paymentIntent({
        ...amounts, client_secret: null, payment_id: null, amount_cents: 0,
        stripe_status: null, stripe_amount_cents: 0, payment_status: null,
        provider_status: null, booking_status: 'confirmed',
        booking_payment_status: 'paid', reservation_status: 'confirmed',
      })
      fakePageApi(game(), {
        'GET /games/{game_id}/participants': addGuests ? [participant()] : [],
        'GET /user-payment-methods': [],
        'GET /checkout/games/{game_id}/quote': quote(amounts),
        [addGuests ? 'POST /checkout/games/{game_id}/guest-payment-intent' : 'POST /checkout/games/{game_id}/payment-intent']: answer,
      })
      renderCheckout(addGuests ? '?mode=add-guests&guest_count=1' : '')
      await screen.findByText('Amount due')
      await agreeAndConfirm(user, addGuests ? 'Confirm Guests' : 'Confirm Spot')
      expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
      expect(sentBody(addGuests ? '/guest-payment-intent' : '/payment-intent')).not.toHaveProperty('payment_method_id')
      expect(fakeStripe.handleNextAction).not.toHaveBeenCalled()
    },
  )

  it.each([
    ['payment request', 'another page'], ['payment request', 'another game'],
    ['payment status', 'another page'], ['payment status', 'another game'],
    ['community join', 'another page'], ['community join', 'another game'],
  ])('F17-14: obsolete checkout results leave the current page intact (%s, %s)', async (phase, destination) => {
    const user = userEvent.setup()
    let finishRequest
    const pending = new Promise((resolve) => { finishRequest = resolve })
    const covered = { available_credit_cents: 1000, credit_applied_cents: 1000, final_amount_due_cents: 0, payment_required: false }
    const noCharge = paymentIntent({ ...covered, client_secret: null, payment_id: null,
      amount_cents: 0, stripe_status: null, stripe_amount_cents: 0,
      payment_status: null, provider_status: null, booking_status: 'confirmed',
      booking_payment_status: 'paid', reservation_status: 'confirmed' })
    fakePageApi(phase === 'community join' ? communityGame() : game(), {
      'GET /checkout/games/{game_id}/quote': phase === 'payment request' ? quote(covered) : quote(),
      'POST /checkout/games/{game_id}/payment-intent': () => phase === 'payment request' ? pending : paymentIntent(),
      'GET /checkout/bookings/{booking_id}/status': () => pending,
      'POST /games/{game_id}/join': () => pending,
    })
    const router = renderCheckout()
    await agreeAndConfirm(user)
    await waitFor(() => expect(apiRequest).toHaveBeenCalledWith(
      expect.stringContaining(phase === 'payment status' ? '/status' : phase === 'community join' ? '/join' : '/payment-intent'),
      expect.anything(),
    ))
    const otherGame = '00000000-0000-4000-8000-000000000090'
    if (destination === 'another page') {
      await user.click(screen.getByRole('button', { name: 'Back' }))
      await act(async () => { await router.navigate('/sign-in') })
      await screen.findByRole('heading', { name: 'Sign In' })
    } else {
      fakePageApi(game({ id: otherGame, title: 'Other Checkout' }))
      await act(async () => { await router.navigate(`/games/${otherGame}/checkout`) })
      await screen.findByText('Other Checkout')
    }
    await act(async () => {
      finishRequest(phase === 'community join' ? joinAnswer() : phase === 'payment request' ? noCharge : checkoutStatus())
    })
    expect(router.state.location.pathname).toBe(destination === 'another page' ? '/sign-in' : `/games/${otherGame}/checkout`)
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
    expect(router.state.location.pathname).not.toBe(`/games/${GAME_ID}`)
  })
})


describe('Reopened guest payment authentication', () => {
  it('F17-12: reopened guest payment authenticates before checking confirmation', async () => {
    const user = userEvent.setup()
    let finishAuthentication
    fakeStripe.handleNextAction.mockImplementation(() => new Promise((resolve) => { finishAuthentication = resolve }))
    let calls = 0
    fakePageApi(game(), {
      'GET /games/{game_id}/participants': [participant(), pendingGuest()],
      'GET /checkout/bookings/{booking_id}/status': () => ++calls === 1
        ? guestStatus({ payment_status: 'requires_action', client_secret: 'pi_test_resume_secret' })
        : guestStatus({ payment_status: 'succeeded', provider_status: 'succeeded' }),
    })
    renderCheckout('?mode=add-guests&guest_count=1')
    await agreeAndConfirm(user, 'Check Payment')
    await waitFor(() => expect(fakeStripe.handleNextAction).toHaveBeenCalledWith({ clientSecret: 'pi_test_resume_secret' }))
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
    expect(calls).toBe(1)
    await act(async () => { finishAuthentication({}) })
    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(fakeStripe.handleNextAction).toHaveBeenCalledTimes(1)
    expect(sentBody('/guest-payment-intent')).toBeNull()
  })

  it('F17-12: declined authentication on reopened guest checkout is recoverable', async () => {
    const user = userEvent.setup()
    fakeStripe.handleNextAction.mockResolvedValue({ error: { message: 'Authentication was cancelled. Try again.' } })
    fakePageApi(game(), {
      'GET /games/{game_id}/participants': [participant(), pendingGuest()],
      'GET /checkout/bookings/{booking_id}/status': guestStatus({ payment_status: 'requires_action', client_secret: 'pi_test_resume_secret' }),
    })
    renderCheckout('?mode=add-guests&guest_count=1')
    await agreeAndConfirm(user, 'Check Payment')
    expect(await screen.findByText('Authentication was cancelled. Try again.')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Check Payment' })[0]).toBeEnabled()
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
    expect(sentBody('/guest-payment-intent')).toBeNull()
  })

  it('F17-14: leaving during reopened guest authentication ignores its result', async () => {
    const user = userEvent.setup()
    let finishAuthentication
    fakeStripe.handleNextAction.mockImplementation(() => new Promise((resolve) => { finishAuthentication = resolve }))
    fakePageApi(game(), {
      'GET /games/{game_id}/participants': [participant(), pendingGuest()],
      'GET /checkout/bookings/{booking_id}/status': guestStatus({ payment_status: 'requires_action', client_secret: 'pi_test_resume_secret' }),
    })
    const router = renderCheckout('?mode=add-guests&guest_count=1')
    await agreeAndConfirm(user, 'Check Payment')
    await waitFor(() => expect(fakeStripe.handleNextAction).toHaveBeenCalled())
    await act(async () => { await router.navigate('/sign-in') })
    await act(async () => { finishAuthentication({}) })
    expect(screen.getByRole('heading', { name: 'Sign In' })).toBeInTheDocument()
    expect(vi.mocked(apiRequest).mock.calls.filter(([path]) => path.endsWith('/status'))).toHaveLength(1)
    expect(sentBody('/guest-payment-intent')).toBeNull()
  })
})


describe('Existing guest payment status access', () => {
  it.each([
    'card list failed', 'no saved card', 'expired card', 'quote failed',
    'joining closed', 'payments disabled', 'card setup unavailable',
  ])('F17-13: existing guest payment remains checkable when %s', async (condition) => {
    const user = userEvent.setup()
    if (condition === 'joining closed') {
      vi.spyOn(Date, 'now').mockReturnValue(new Date('2030-06-15T23:05:00Z').valueOf())
    }
    if (condition === 'payments disabled') fakeStripe.enabled = false
    if (condition === 'card setup unavailable') fakeStripe.supported = false
    const answers = {
      'GET /games/{game_id}/participants': [participant(), pendingGuest()],
      'GET /checkout/bookings/{booking_id}/status': guestStatus({ payment_status: 'succeeded' }),
    }
    if (condition === 'card list failed') answers['GET /user-payment-methods'] = new Error('Cards unavailable')
    if (condition === 'no saved card') answers['GET /user-payment-methods'] = []
    if (condition === 'expired card') answers['GET /user-payment-methods'] = [savedCard({ exp_year: 2020 })]
    if (condition === 'quote failed') answers['GET /checkout/games/{game_id}/quote'] = new Error('Price unavailable')
    fakePageApi(game(), answers)
    renderCheckout('?mode=add-guests&guest_count=1')

    await user.click(await screen.findByRole('checkbox', { name: 'Agree to Pickup Lane terms' }))
    const checkPayment = screen.getAllByRole('button', { name: 'Check Payment' })[0]
    expect(checkPayment).toBeEnabled()
    await user.click(checkPayment)

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(vi.mocked(apiRequest).mock.calls.filter(([path]) => path.endsWith('/status'))).toHaveLength(1)
    expect(vi.mocked(apiRequest).mock.calls.some(([, options]) => options?.method === 'POST')).toBe(false)
  })
})
