import { act, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../../../src/hooks/useAuth.js'
import { ApiRequestError, apiRequest } from '../../../src/lib/apiClient.js'
import { CARD_ID, guestCheckoutStatus, communityGame, fakePageApi, game, guestPaymentIntent, joinAnswer, OTHER_CARD_ID, otherPlayers, participant, PLAYER_ID, quote, renderCheckout, sentBody } from './gameCheckoutTestKit.jsx'

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

async function agree(user) {
  await user.click(await screen.findByRole('checkbox', { name: 'Agree to Pickup Lane terms' }))
}
const fullGame = { total_spots: 1 }
const waitlistAnswer = joinAnswer({ status: 'waitlisted', message: 'You joined the waitlist.', waitlist_entry_id: '00000000-0000-4000-8000-000000000030' })

describe('Game Checkout', () => {
  it('F17-5: a paid official waitlist sends the saved card and consent to a later charge', async () => {
    const user = userEvent.setup()
    fakePageApi(game(fullGame), {
      'GET /games/{game_id}/participants': otherPlayers(1),
      'POST /games/{game_id}/join': waitlistAnswer,
    })
    renderCheckout()

    await user.click(await screen.findByRole('checkbox', {
      name: /If a spot opens for your whole party, Pickup Lane may charge this card up to \$10\.00 after applying any available game credit/,
    }))
    await agree(user)
    await user.click(screen.getAllByRole('button', { name: 'Join Waitlist' })[0])

    await screen.findByRole('heading', { name: 'Game Details' })
    expect(sentBody('/join')).toEqual({
      guest_count: 0,
      payment_method_id: CARD_ID,
      auto_charge_consent_accepted: true,
      auto_charge_consent_version: 'waitlist-auto-charge-v1',
    })
  })

  it('F17-11: a paid official waitlist cannot be joined without consent', async () => {
    const user = userEvent.setup()
    fakePageApi(game(fullGame), { 'GET /games/{game_id}/participants': otherPlayers(1) })
    renderCheckout()

    await agree(user)

    expect(screen.getAllByRole('button', { name: 'Join Waitlist' })[0]).toBeDisabled()
    expect(screen.getAllByText(
      'Agree to the possible later charge to join this waitlist.',
    )[0]).toBeInTheDocument()
  })

  it('F17-11: a paid official waitlist cannot be joined without a saved card', async () => {
    const user = userEvent.setup()
    fakePageApi(game(fullGame), {
      'GET /games/{game_id}/participants': otherPlayers(1),
      'GET /user-payment-methods': [],
    })
    renderCheckout()

    await agree(user)

    await user.click(screen.getByRole('checkbox', { name: /If a spot opens for your whole party/ }))
    expect(screen.getAllByRole('button', { name: 'Join Waitlist' })[0]).toBeDisabled()
    expect(screen.getByText('Add a card to join this waitlist.')).toBeInTheDocument()
  })

  it('F17-6: paid guests on a partially cancelled booking return to Game Details', async () => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'GET /games/{game_id}/participants': [participant()],
      'POST /checkout/games/{game_id}/guest-payment-intent': guestPaymentIntent({ booking_status: 'partially_cancelled', booking_payment_status: 'partially_refunded' }),
      'GET /checkout/bookings/{booking_id}/status': guestCheckoutStatus({
        payment_status: 'succeeded', provider_status: 'succeeded',
        booking_status: 'partially_cancelled',
        booking_payment_status: 'partially_refunded', amount_cents: 2000, subtotal_cents: 2000, checkout_total_cents: 2000, final_amount_due_cents: 2000, stripe_amount_cents: 2000,
      }),
    })
    renderCheckout('?mode=add-guests&guest_count=1')

    await agree(user)
    await user.click(screen.getAllByRole('button', { name: 'Confirm Guests' })[0])

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
  })

  it('F17-18: a failed guest charge is shown without confirming the guests', async () => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'GET /games/{game_id}/participants': [participant()],
      'POST /checkout/games/{game_id}/guest-payment-intent': guestPaymentIntent({
        stripe_status: 'requires_payment_method', payment_status: 'requires_payment_method', provider_status: 'requires_payment_method',
      }),
    })
    renderCheckout('?mode=add-guests&guest_count=1')

    await agree(user)
    await user.click(screen.getAllByRole('button', { name: 'Confirm Guests' })[0])

    expect(await screen.findByText(
      'This saved card could not be charged. Choose another card.',
    )).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
  })

  it('F17-13: a guest payment that arrives too late reports a refund, not added guests', async () => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'GET /games/{game_id}/participants': [participant()],
      'POST /checkout/games/{game_id}/guest-payment-intent': guestPaymentIntent(),
      'GET /checkout/bookings/{booking_id}/status': guestCheckoutStatus({ payment_status: 'succeeded', provider_status: 'succeeded', compensation_status: 'required' }),
    })
    renderCheckout('?mode=add-guests&guest_count=1')

    await agree(user)
    await user.click(screen.getAllByRole('button', { name: 'Confirm Guests' })[0])

    expect(await screen.findByText(
      'Your payment completed, but the guests could not be added. A refund is required.',
    )).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
  })

  it('F17-8: the guest count stops at the game limit', async () => {
    const user = userEvent.setup()
    fakePageApi(communityGame())
    renderCheckout()

    const addGuest = await screen.findByRole('button', { name: 'Add a guest' })
    await user.click(addGuest)
    await user.click(addGuest)

    expect(addGuest).toBeDisabled()
    expect(screen.getByText('Guest limit: 2/2')).toBeInTheDocument()
  })

  it('F17-8: a party that cannot fit without a waitlist cannot confirm', async () => {
    const user = userEvent.setup()
    fakePageApi(communityGame({ ...fullGame, waitlist_enabled: false }), {
      'GET /games/{game_id}/participants': otherPlayers(1),
    })
    renderCheckout()

    expect(await screen.findByText(
      'Not enough spots are available for this join.',
    )).toBeInTheDocument()
    await agree(user)
    expect(screen.getAllByRole('button', { name: 'Confirm Spot' })[0]).toBeDisabled()
  })

  it('F17-9: a player who already joined cannot book again', async () => {
    const user = userEvent.setup()
    fakePageApi(communityGame(), { 'GET /games/{game_id}/participants': [participant()] })
    renderCheckout()

    expect(await screen.findByText('You already joined this game.')).toBeInTheDocument()
    await agree(user)
    expect(screen.getAllByRole('button', { name: 'Confirm Spot' })[0]).toBeDisabled()
  })

  it('F17-9: add-guest checkout needs a confirmed booking', async () => {
    const user = userEvent.setup()
    fakePageApi(communityGame(), {
      'GET /games/{game_id}/participants': [participant({
        participant_status: 'waitlisted', confirmed_at: null, roster_order: null,
      })],
    })
    renderCheckout('?mode=add-guests&guest_count=1')

    expect(await screen.findByText(
      'Only confirmed players can add guests to an existing booking.',
    )).toBeInTheDocument()
    await agree(user)
    expect(screen.getAllByRole('button', { name: 'Confirm Guests' })[0]).toBeDisabled()
  })

  it("F17-5: a party that cannot fit is offered whole-party waitlist confirmation", async () => {
    fakePageApi(game({ total_spots: 2 }), { 'GET /games/{game_id}/participants': otherPlayers(1) })
    renderCheckout('?guest_count=1')
    expect(await screen.findByRole('heading', { name: 'Join Waitlist' })).toBeInTheDocument()
    expect(screen.getByText('+1 guest')).toBeInTheDocument()
  })

  it("F17-5: waitlist checkout explains there is no charge now", async () => {
    fakePageApi(game({ total_spots: 1 }), { 'GET /games/{game_id}/participants': otherPlayers(1) })
    renderCheckout()
    expect(await screen.findByText('No charge now')).toBeInTheDocument()
    expect(screen.getByText(/You won’t be charged now/)).toBeInTheDocument()
  })

  it("F17-5: paid waitlist consent explains leaving before an offer is free", async () => {
    fakePageApi(game({ total_spots: 1 }), { 'GET /games/{game_id}/participants': otherPlayers(1) })
    renderCheckout()
    expect(await screen.findByRole('checkbox', { name: /leaving the waitlist before a spot opens costs nothing/ })).toBeInTheDocument()
  })

  it("F17-6: add-guest checkout shows the existing booking", async () => {
    fakePageApi(game(), { 'GET /games/{game_id}/participants': [participant()] })
    renderCheckout('?mode=add-guests&guest_count=1')
    expect(await screen.findByText('Your Booking')).toBeInTheDocument()
    expect(screen.getByText('Test Player')).toBeInTheDocument()
  })

  it("F17-6: add-guest checkout shows proposed and resulting guest counts", async () => {
    fakePageApi(game(), { 'GET /games/{game_id}/participants': [participant(), participant({ id: OTHER_CARD_ID, participant_type: 'guest', user_id: null, guest_of_user_id: PLAYER_ID, display_name_snapshot: 'Existing guest' })] })
    renderCheckout('?mode=add-guests&guest_count=1')
    expect(await screen.findByText('Adding 1 guest')).toBeInTheDocument()
    expect(screen.getByText('Guest limit: 2/2')).toBeInTheDocument()
  })

  it("F17-6: add-guest summary applies credit to only the added guests", async () => {
    fakePageApi(game(), {
      'GET /games/{game_id}/participants': [participant()],
      'GET /checkout/games/{game_id}/quote': quote({ subtotal_cents: 2000, checkout_total_cents: 2000, available_credit_cents: 500, credit_applied_cents: 500, final_amount_due_cents: 1500 }),
    })
    renderCheckout('?mode=add-guests&guest_count=2')
    await screen.findByText('Game credit applied')
    expect(screen.getByText('2 x Guests').nextSibling).toHaveTextContent('$20.00')
    expect(screen.queryByText('1 x Player')).not.toBeInTheDocument()
    expect(screen.getByText('Game credit applied').nextSibling).toHaveTextContent('-$5.00')
    expect(screen.getByText('Amount due').nextSibling).toHaveTextContent('$15.00')
  })

  it.each([['confirmed', 'paid'], ['partially_cancelled', 'partially_refunded']])('F17-6: paid guests return only after their payment succeeds (%s)', async (bookingStatus, bookingPaymentStatus) => {
    const user = userEvent.setup()
    let finishStatus
    let statusCalls = 0
    const pending = new Promise((resolve) => { finishStatus = resolve })
    const parentStatus = { booking_status: bookingStatus, booking_payment_status: bookingPaymentStatus, reservation_status: 'confirmed' }
    fakePageApi(game(), {
      'GET /games/{game_id}/participants': [participant()],
      'POST /checkout/games/{game_id}/guest-payment-intent': guestPaymentIntent(parentStatus),
      'GET /checkout/bookings/{booking_id}/status': () => ++statusCalls === 1 ? pending : guestCheckoutStatus({ ...parentStatus, payment_status: 'succeeded', provider_status: 'succeeded', amount_cents: 2000, subtotal_cents: 2000, checkout_total_cents: 2000, final_amount_due_cents: 2000, stripe_amount_cents: 2000 }),
    })
    renderCheckout('?mode=add-guests&guest_count=1')
    await agreeAndConfirm(user, 'Confirm Guests')
    await waitFor(() => expect(apiRequest).toHaveBeenCalledWith(expect.stringContaining('/status'), expect.anything()))
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    await act(async () => { finishStatus(guestCheckoutStatus({ ...parentStatus, payment_status: 'processing', provider_status: 'processing' })) })
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
    await act(async () => { await vi.advanceTimersByTimeAsync(1200) })
    expect(screen.getByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
  })

  it.each([1000, 970])('F17-6: covered guest additions confirm without a saved card (%i cents credit)', async (credit) => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'GET /games/{game_id}/participants': [participant()],
      'GET /user-payment-methods': [],
      'GET /checkout/games/{game_id}/quote': quote({ available_credit_cents: credit, credit_applied_cents: credit, minimum_charge_adjustment_cents: 1000 - credit, final_amount_due_cents: 0, payment_required: false }),
      'POST /checkout/games/{game_id}/guest-payment-intent': guestPaymentIntent({ client_secret: null, payment_id: null, amount_cents: 0, stripe_status: null, available_credit_cents: credit, credit_applied_cents: credit, minimum_charge_adjustment_cents: 1000 - credit, final_amount_due_cents: 0, stripe_amount_cents: 0, payment_required: false, booking_status: 'confirmed', booking_payment_status: 'paid', reservation_status: 'confirmed', payment_status: null, provider_status: null }),
    })
    renderCheckout('?mode=add-guests&guest_count=1')
    await agreeAndConfirm(user, 'Confirm Guests')
    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(sentBody('/guest-payment-intent')).not.toHaveProperty('payment_method_id')
  })

  it("F17-15: suspended waitlist entry reports rejection without confirmation", async () => {
    const user = userEvent.setup()
    signIn({ account_status: 'suspended' })
    fakePageApi(game({ total_spots: 1 }), { 'GET /games/{game_id}/participants': otherPlayers(1), 'GET /checkout/games/{game_id}/quote': new ApiRequestError('Active account required.', { status: 403 }), 'POST /games/{game_id}/join': new ApiRequestError('Active account required.', { status: 403 }) })
    renderCheckout()
    await user.click(await screen.findByRole('checkbox', { name: /If a spot opens for your whole party/ }))
    await agreeAndConfirm(user, 'Join Waitlist')
    expect((await screen.findAllByText('Active account required.'))[0]).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
  })

  it("F17-15: suspended guest addition reports rejection without confirmation", async () => {
    const user = userEvent.setup()
    signIn({ account_status: 'suspended' })
    fakePageApi(game(), { 'GET /games/{game_id}/participants': [participant()], 'GET /checkout/games/{game_id}/quote': new ApiRequestError('Active account required.', { status: 403 }) })
    renderCheckout("?mode=add-guests&guest_count=1")
    await agree(user)
    expect((await screen.findAllByText('Active account required.'))[0]).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Confirm Guests' })[0]).toBeDisabled()
    expect(sentBody('/guest-payment-intent')).toBeNull()
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
  })

  it.each([1000, 970])('F17-11: covered paid waitlist still offers required card setup (%i cents credit)', async (credit) => {
    const user = userEvent.setup()
    fakePageApi(game(fullGame), {
      'GET /games/{game_id}/participants': otherPlayers(1),
      'GET /user-payment-methods': [],
      'GET /checkout/games/{game_id}/quote': quote({ available_credit_cents: credit, credit_applied_cents: credit, minimum_charge_adjustment_cents: 1000 - credit, final_amount_due_cents: 0, payment_required: false }),
      'POST /user-payment-methods/setup-intent': { client_secret: 'seti_test_secret' },
    })
    renderCheckout()
    await screen.findByText(`Available game credit: $${(credit / 100).toFixed(2)}`)
    expect(screen.queryByText('Nothing is due, so no card is needed.')).not.toBeInTheDocument()
    await user.click(screen.getByRole('checkbox', { name: /If a spot opens for your whole party/ }))
    await agree(user)
    expect(screen.getAllByRole('button', { name: 'Join Waitlist' })[0]).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Add card' }))
    expect(await screen.findByRole('dialog', { name: 'Add card' })).toBeInTheDocument()
    expect(sentBody('/join')).toBeNull()
  })

})
