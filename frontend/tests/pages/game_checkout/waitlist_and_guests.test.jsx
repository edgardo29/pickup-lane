import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../../../src/hooks/useAuth.js'
import {
  CARD_ID, checkoutStatus, communityGame, fakePageApi, game, joinAnswer, otherPlayers,
  participant, paymentIntent, PLAYER_ID, renderCheckout, sentBody,
} from './gameCheckoutTestKit.jsx'

vi.mock('../../../src/lib/apiClient.js', async (importOriginal) => ({
  ...(await importOriginal()),
  apiRequest: vi.fn(),
}))
vi.mock('../../../src/hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../../../src/components/BrowseAppNav.jsx', () => ({ default: () => null }))
vi.mock('../../../src/lib/stripe.js', () => ({
  areStripePaymentsEnabled: () => true,
  hasStripeCheckoutSupport: () => true,
  hasStripePublishableKey: () => true,
  stripePromise: Promise.resolve({ handleNextAction: vi.fn() }),
}))

beforeEach(() => {
  vi.mocked(useAuth).mockReturnValue({
    appUser: { id: PLAYER_ID, first_name: 'Test', last_name: 'Player',
      date_of_birth: '1990-01-01', account_status: 'active' },
    currentUser: { getIdToken: vi.fn().mockResolvedValue('test-token') },
    isLoading: false,
  })
})

const fullGame = { total_spots: 1 }
const waitlistAnswer = joinAnswer({
  status: 'waitlisted', message: 'You joined the waitlist.',
  waitlist_entry_id: '00000000-0000-4000-8000-000000000030',
})

async function agree(user) {
  await user.click(await screen.findByRole('checkbox', { name: 'Agree to Pickup Lane terms' }))
}

describe('Game Checkout waitlist and guests', () => {
  it('F17-5: a party that does not fit joins the waitlist with no charge now', async () => {
    const user = userEvent.setup()
    fakePageApi(communityGame(fullGame), {
      'GET /games/{game_id}/participants': otherPlayers(1),
      'POST /games/{game_id}/join': waitlistAnswer,
    })
    renderCheckout()

    expect(await screen.findByRole('heading', { name: 'Join Waitlist' })).toBeInTheDocument()
    expect(screen.getByText('No charge now')).toBeInTheDocument()
    await agree(user)
    await user.click(screen.getAllByRole('button', { name: 'Join Waitlist' })[0])

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
  })

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

    expect(screen.getAllByRole('button', { name: 'Join Waitlist' })[0]).toBeDisabled()
    expect(screen.getByText('Add a card to join this waitlist.')).toBeInTheDocument()
  })

  it('F17-6: add-guest checkout shows the booking and pays for only the new guests', async () => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'GET /games/{game_id}/participants': [participant()],
      'POST /checkout/games/{game_id}/guest-payment-intent': paymentIntent(),
      'GET /checkout/bookings/{booking_id}/status': checkoutStatus(),
    })
    renderCheckout('?mode=add-guests&guest_count=1')

    expect(await screen.findByRole('heading', { name: 'Add Guests' })).toBeInTheDocument()
    expect(screen.getByText('Your Booking')).toBeInTheDocument()
    expect(screen.getByText('Guest limit: 1/2')).toBeInTheDocument()
    await agree(user)
    await user.click(screen.getAllByRole('button', { name: 'Confirm Guests' })[0])

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(sentBody('/guest-payment-intent')).toMatchObject({
      guest_count: 1, payment_method_id: CARD_ID,
    })
  })

  it('F17-6: paid guests on a partially cancelled booking return to Game Details', async () => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'GET /games/{game_id}/participants': [participant()],
      'POST /checkout/games/{game_id}/guest-payment-intent': paymentIntent(),
      'GET /checkout/bookings/{booking_id}/status': checkoutStatus({
        booking_status: 'partially_cancelled',
        booking_payment_status: 'partially_refunded',
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
      'POST /checkout/games/{game_id}/guest-payment-intent': paymentIntent({
        stripe_status: 'requires_payment_method',
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
      'POST /checkout/games/{game_id}/guest-payment-intent': paymentIntent(),
      'GET /checkout/bookings/{booking_id}/status': checkoutStatus({ compensation_status: 'required' }),
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
})
