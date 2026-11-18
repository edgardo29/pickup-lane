import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../../../src/hooks/useAuth.js'
import { ApiRequestError, apiRequest } from '../../../src/lib/apiClient.js'
import {
  CARD_ID, checkoutStatus, communityGame, fakePageApi, game, joinAnswer, OTHER_CARD_ID,
  paymentIntent, PLAYER_ID, quote, renderCheckout, savedCard, sentBody,
} from './gameCheckoutTestKit.jsx'

const fakeStripe = vi.hoisted(() => ({ handleNextAction: vi.fn() }))

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
  stripePromise: Promise.resolve(fakeStripe),
}))
vi.mock('@stripe/react-stripe-js', () => ({ Elements: ({ children }) => children }))
vi.mock('../../../src/features/payment-methods/PaymentMethodSetupDialog.jsx', () => ({
  PaymentMethodSetupDialog: ({ children, title }) => (
    <div aria-label={title} role="dialog">{children}</div>
  ),
  PaymentMethodSetupForm: () => <p>Secure card form</p>,
}))

function signIn(appUser = {}) {
  vi.mocked(useAuth).mockReturnValue({
    appUser: { id: PLAYER_ID, first_name: 'Test', last_name: 'Player',
      date_of_birth: '1990-01-01', account_status: 'active', ...appUser },
    currentUser: { getIdToken: vi.fn().mockResolvedValue('test-token') },
    isLoading: false,
  })
}

async function agreeAndConfirm(user, label = 'Confirm Spot') {
  await user.click(await screen.findByRole('checkbox', { name: 'Agree to Pickup Lane terms' }))
  await user.click(screen.getAllByRole('button', { name: label })[0])
}

beforeEach(() => {
  signIn()
  fakeStripe.handleNextAction.mockReset()
})

describe('Game Checkout confirmation', () => {
  it('F17-2: a community game confirms the whole party and returns to Game Details', async () => {
    const user = userEvent.setup()
    fakePageApi(communityGame(), { 'POST /games/{game_id}/join': joinAnswer() })
    renderCheckout()

    await agreeAndConfirm(user)

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(sentBody('/join')).toEqual({ guest_count: 0 })
  })

  it('F17-3: an official game returns to Game Details only after the payment confirms', async () => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'POST /checkout/games/{game_id}/payment-intent': paymentIntent(),
      'GET /checkout/bookings/{booking_id}/status': checkoutStatus(),
    })
    renderCheckout()

    await agreeAndConfirm(user)

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(sentBody('/payment-intent')).toMatchObject({ guest_count: 0, payment_method_id: CARD_ID })
    expect(apiRequest).toHaveBeenCalledWith(
      expect.stringMatching(/\/checkout\/bookings\/.+\/status$/), expect.anything(),
    )
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

  it('F17-4: a player without a card can open card setup during checkout', async () => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'GET /user-payment-methods': [],
      'POST /user-payment-methods/setup-intent': { client_secret: 'seti_test_secret' },
    })
    renderCheckout()

    await user.click(await screen.findByRole('button', { name: 'Add card' }))

    expect(await screen.findByRole('dialog', { name: 'Add card' })).toBeInTheDocument()
    expect(screen.getByText('Secure card form')).toBeInTheDocument()
  })

  it('F17-12: failed card authentication is shown without claiming a spot', async () => {
    const user = userEvent.setup()
    fakeStripe.handleNextAction.mockResolvedValue({ error: { message: 'Your card was declined.' } })
    fakePageApi(game(), {
      'POST /checkout/games/{game_id}/payment-intent': paymentIntent({ stripe_status: 'requires_action' }),
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
        stripe_status: 'requires_payment_method',
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
        booking_status: 'expired', reservation_status: 'released',
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
        'Verify your email before booking.', { status: 403 },
      ),
    })
    renderCheckout()

    await agreeAndConfirm(user)

    expect(await screen.findByText('Verify your email before booking.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Confirm Spot' })).toBeInTheDocument()
  })

  it('F17-10: after the cutoff the page cannot confirm and says joining is closed', async () => {
    const user = userEvent.setup()
    fakePageApi(communityGame({ starts_at: '2020-01-01T00:00:00Z', ends_at: '2020-01-01T01:00:00Z' }))
    renderCheckout()

    expect(await screen.findByText('Joining is closed for this game.')).toBeInTheDocument()
    await user.click(screen.getByRole('checkbox', { name: 'Agree to Pickup Lane terms' }))
    expect(screen.getAllByRole('button', { name: 'Confirm Spot' })[0]).toBeDisabled()
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
})
