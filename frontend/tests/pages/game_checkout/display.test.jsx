import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../../../src/hooks/useAuth.js'
import {
  communityGame, fakePageApi, game, otherPlayers, PLAYER_ID, quote, renderCheckout,
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

describe('Game Checkout display', () => {
  it('F17-1: shows the game, player, price, policy, and terms, and waits for agreement', async () => {
    const user = userEvent.setup()
    fakePageApi(game())
    renderCheckout()

    expect(await screen.findByText('Evening Pickup')).toBeInTheDocument()
    expect(screen.getByText('You')).toBeInTheDocument()
    expect(screen.getByText('1 x Player')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Cancellation' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Terms of Service' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancellation Policy' })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Confirm Spot' })[0]).toBeDisabled()

    await user.click(screen.getByRole('checkbox', { name: 'Agree to Pickup Lane terms' }))

    expect(screen.getAllByRole('button', { name: 'Confirm Spot' })[0]).toBeEnabled()
  })

  it('F17-3: the summary shows the price, available and applied credit, and the amount due', async () => {
    fakePageApi(game(), {
      'GET /checkout/games/{game_id}/quote': quote({
        available_credit_cents: 300, credit_applied_cents: 300, final_amount_due_cents: 700,
      }),
    })
    renderCheckout()

    expect(await screen.findByText('Game credit applied')).toBeInTheDocument()
    expect(screen.getByText('-$3.00')).toBeInTheDocument()
    expect(screen.getByText('Amount due').nextSibling).toHaveTextContent('$7.00')
    expect(screen.getByText('Available game credit: $3.00')).toBeInTheDocument()
  })

  it('F17-5: a paid waitlist shows current credit as an estimate of the later charge', async () => {
    fakePageApi(game({ total_spots: 1 }), {
      'GET /games/{game_id}/participants': otherPlayers(1),
      'GET /checkout/games/{game_id}/quote': quote({
        available_credit_cents: 300, credit_applied_cents: 300,
        final_amount_due_cents: 700,
      }),
    })
    renderCheckout()

    expect(await screen.findByText('Available game credit: $3.00')).toBeInTheDocument()
    expect(screen.getByText('Estimated later charge').nextSibling).toHaveTextContent('$7.00')
    expect(screen.getByText(/Credit is applied when a spot opens/)).toBeInTheDocument()
  })

  it('F17-24: a small remainder after credit is covered and nothing is due', async () => {
    fakePageApi(game(), {
      'GET /checkout/games/{game_id}/quote': quote({
        available_credit_cents: 970, credit_applied_cents: 970,
        minimum_charge_adjustment_cents: 30, final_amount_due_cents: 0, payment_required: false,
      }),
    })
    renderCheckout()

    expect(await screen.findByText('Covered by Pickup Lane')).toBeInTheDocument()
    expect(screen.getByText('-$9.70')).toBeInTheDocument()
    expect(screen.getByText('-$0.30')).toBeInTheDocument()
    expect(screen.getByText('Amount due').nextSibling).toHaveTextContent('$0.00')
  })

  it('F17-26: a low price with no credit is covered without recording credit', async () => {
    fakePageApi(game({ price_per_player_cents: 30 }), {
      'GET /checkout/games/{game_id}/quote': quote({
        subtotal_cents: 30, checkout_total_cents: 30,
        minimum_charge_adjustment_cents: 30, final_amount_due_cents: 0, payment_required: false,
      }),
    })
    renderCheckout()

    expect(await screen.findByText('Covered by Pickup Lane')).toBeInTheDocument()
    expect(screen.queryByText('Game credit applied')).not.toBeInTheDocument()
    expect(screen.getByText('Amount due').nextSibling).toHaveTextContent('$0.00')
  })

  it('F17-22: an official game explains the change-related removal request', async () => {
    fakePageApi(game())
    renderCheckout()

    expect(await screen.findByText(/you can ask to leave and choose a refund/)).toBeInTheDocument()
  })

  it('F17-22: a community game shows the organizer terms instead of the official promise', async () => {
    fakePageApi(communityGame({ custom_cancellation_text: 'No refunds within 48 hours.' }))
    renderCheckout()

    expect(await screen.findByText('No refunds within 48 hours.')).toBeInTheDocument()
    expect(screen.queryByText(/stay eligible for a refund or game credit/)).not.toBeInTheDocument()
  })

  it('F17-23: without organizer terms, no refund is promised', async () => {
    fakePageApi(communityGame({ custom_cancellation_text: null }))
    renderCheckout()

    expect(await screen.findByText(
      /confirm payment and refund arrangements with the organizer/,
    )).toBeInTheDocument()
    expect(screen.getByText(/Pickup Lane does not refund off-app payments/)).toBeInTheDocument()
    expect(screen.queryByText(/stay eligible for a refund or game credit/)).not.toBeInTheDocument()
  })

  it('F17-27: community checkout states payment responsibility before confirming', async () => {
    fakePageApi(communityGame())
    renderCheckout()

    expect(await screen.findByText(
      /Payment disputes and refunds remain between you and the original organizer/,
    )).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Confirm Spot' })[0]).toBeDisabled()
  })
})
