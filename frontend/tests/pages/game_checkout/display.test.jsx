import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../../../src/hooks/useAuth.js'

import { communityGame, fakePageApi, game, GAME_ID, otherPlayers, PLAYER_ID, quote, renderCheckout } from './gameCheckoutTestKit.jsx'

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

describe('Game Checkout', () => {
  it("F17-1: the game summary appears", async () => {
    fakePageApi(game())
    renderCheckout('?guest_count=1')
    expect(await screen.findByText('Evening Pickup')).toBeInTheDocument()
    expect(screen.getByText('Central Field')).toBeInTheDocument()
  })

  it("F17-1: the signed-in player appears", async () => {
    fakePageApi(game())
    renderCheckout('?guest_count=1')
    expect(await screen.findByText('Test Player')).toBeInTheDocument()
  })

  it("F17-1: the party guest count and limit appear", async () => {
    fakePageApi(game())
    renderCheckout('?guest_count=1')
    expect(await screen.findByText('+1 guest')).toBeInTheDocument()
    expect(screen.getByText('Guest limit: 1/2')).toBeInTheDocument()
  })

  it("F17-1: the booking price appears", async () => {
    fakePageApi(game())
    renderCheckout('?guest_count=1')
    expect((await screen.findByText('1 x Player')).nextSibling).toHaveTextContent('$10.00')
  })

  it("F17-1: cancellation information appears", async () => {
    fakePageApi(game())
    renderCheckout('?guest_count=1')
    expect(await screen.findByRole('heading', { name: 'Cancellation' })).toBeInTheDocument()
    expect(screen.getByText(/Cancel 24/)).toBeInTheDocument()
  })

  it("F17-1: Terms of Service opens its policy", async () => {
    const user = userEvent.setup()
    fakePageApi(game())
    renderCheckout()
    await user.click(await screen.findByRole('button', { name: 'Terms of Service' }))
    expect(await screen.findByRole('dialog', { name: 'Terms of Service' })).toBeInTheDocument()
    const content = screen.getByRole('region', { name: 'Terms of Service text' })
    expect(content).toHaveAttribute('tabindex', '0')
    await user.tab(); expect(content).toHaveFocus()
    await user.tab(); expect(screen.getByRole('button', { name: 'Close Terms of Service' })).toHaveFocus()
  })

  it("F17-1: Cancellation Policy opens its policy", async () => {
    const user = userEvent.setup()
    fakePageApi(game())
    renderCheckout()
    await user.click(await screen.findByRole('button', { name: 'Cancellation Policy' }))
    expect(await screen.findByRole('dialog', { name: 'Cancellation and Refund Policy' })).toBeInTheDocument()
    const content = screen.getByRole('region', { name: 'Cancellation and Refund Policy text' })
    expect(content).toHaveAttribute('tabindex', '0')
    await user.tab(); expect(content).toHaveFocus()
    await user.tab(); expect(screen.getByRole('button', { name: 'Close Cancellation and Refund Policy' })).toHaveFocus()
  })

  it("F17-1: confirmation waits for agreement", async () => {
    const user = userEvent.setup()
    fakePageApi(game())
    renderCheckout()
    await screen.findByText('Amount due')
    const button = (await screen.findAllByRole('button', { name: 'Confirm Spot' }))[0]
    expect(button).toBeDisabled()
    await user.click(screen.getByRole('checkbox', { name: 'Agree to Pickup Lane terms' }))
    expect(button).toBeEnabled()
  })

  it("F17-1: Back returns to Game Details", async () => {
    const user = userEvent.setup()
    fakePageApi(game())
    const router = renderCheckout()
    await user.click(await screen.findByRole('button', { name: /Back/ }))
    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe(`/games/${GAME_ID}`)
  })

  it("F17-3: the official summary shows party price", async () => {
    fakePageApi(game(), { 'GET /checkout/games/{game_id}/quote': quote({ available_credit_cents: 300, credit_applied_cents: 300, final_amount_due_cents: 700 }) })
    renderCheckout()
    expect((await screen.findByText('1 x Player')).nextSibling).toHaveTextContent('$10.00')
  })

  it("F17-3: the official summary shows available credit", async () => {
    fakePageApi(game(), { 'GET /checkout/games/{game_id}/quote': quote({ available_credit_cents: 300, credit_applied_cents: 300, final_amount_due_cents: 700 }) })
    renderCheckout()
    expect(await screen.findByText('Available game credit: $3.00')).toBeInTheDocument()
  })

  it("F17-3: the official summary shows applied credit", async () => {
    fakePageApi(game(), { 'GET /checkout/games/{game_id}/quote': quote({ available_credit_cents: 300, credit_applied_cents: 300, final_amount_due_cents: 700 }) })
    renderCheckout()
    expect((await screen.findByText('Game credit applied')).nextSibling).toHaveTextContent('-$3.00')
  })

  it("F17-3: the official summary shows the balance after credit", async () => {
    fakePageApi(game(), { 'GET /checkout/games/{game_id}/quote': quote({ available_credit_cents: 300, credit_applied_cents: 300, final_amount_due_cents: 700 }) })
    renderCheckout()
    expect((await screen.findByText('Amount due')).nextSibling).toHaveTextContent('$7.00')
  })

  it("F17-27: paid community checkout explains outside payment", async () => {
    fakePageApi(communityGame({ price_per_player_cents: 1000 }))
    renderCheckout()
    expect(await screen.findByText('Handled outside Pickup Lane')).toBeInTheDocument()
  })

  it("F17-5: the later-charge estimate explains when credit is applied", async () => {
    fakePageApi(game({ total_spots: 1 }), {
      'GET /games/{game_id}/participants': otherPlayers(1),
      'GET /checkout/games/{game_id}/quote': quote({ available_credit_cents: 300, credit_applied_cents: 300, final_amount_due_cents: 700 }),
    })
    renderCheckout()
    await screen.findByText('Available game credit: $3.00')
    expect(screen.getByText('Estimated later charge').nextSibling).toHaveTextContent('$7.00')
    expect(screen.getByText(/Credit is applied when a spot opens/)).toBeInTheDocument()
  })

  it("F17-22: official cancellation explains the change-related removal request", async () => {
    fakePageApi(game())
    renderCheckout()
    expect(await screen.findByText(/you can ask to leave and choose a refund/)).toBeInTheDocument()
  })

  it("F17-22: community checkout shows organizer terms instead of the official promise", async () => {
    fakePageApi(communityGame({ custom_cancellation_text: 'No refunds within 48 hours.' }))
    renderCheckout()
    expect(await screen.findByText('No refunds within 48 hours.')).toBeInTheDocument()
    expect(screen.queryByText(/stay eligible for a refund or game credit/)).not.toBeInTheDocument()
  })

  it("F17-23: community checkout without terms promises no refund", async () => {
    fakePageApi(communityGame({ custom_cancellation_text: null }))
    renderCheckout()
    expect(await screen.findByText(/confirm payment and refund arrangements with the organizer/)).toBeInTheDocument()
    expect(screen.getByText(/Pickup Lane does not refund off-app payments/)).toBeInTheDocument()
    expect(screen.queryByText(/stay eligible for a refund or game credit/)).not.toBeInTheDocument()
  })

  it("F17-24: small-balance checkout applies all available credit", async () => {
    fakePageApi(game(), { 'GET /checkout/games/{game_id}/quote': quote({ available_credit_cents: 970, credit_applied_cents: 970, minimum_charge_adjustment_cents: 30, final_amount_due_cents: 0, payment_required: false }) })
    renderCheckout()
    expect((await screen.findByText('Game credit applied')).nextSibling).toHaveTextContent('-$9.70')
  })

  it("F17-24: small-balance coverage is shown separately", async () => {
    fakePageApi(game(), { 'GET /checkout/games/{game_id}/quote': quote({ available_credit_cents: 970, credit_applied_cents: 970, minimum_charge_adjustment_cents: 30, final_amount_due_cents: 0, payment_required: false }) })
    renderCheckout()
    expect((await screen.findByText('Covered by Pickup Lane')).nextSibling).toHaveTextContent('-$0.30')
  })

  it("F17-19: full credit shows zero amount due", async () => {
    fakePageApi(game(), { 'GET /checkout/games/{game_id}/quote': quote({ available_credit_cents: 1000, credit_applied_cents: 1000, final_amount_due_cents: 0, payment_required: false }) })
    renderCheckout()
    expect((await screen.findByText('Amount due')).nextSibling).toHaveTextContent('$0.00')
  })

  it("F17-26: a covered low price does not display invented game credit", async () => {
    fakePageApi(game({ price_per_player_cents: 30 }), { 'GET /checkout/games/{game_id}/quote': quote({ subtotal_cents: 30, checkout_total_cents: 30, minimum_charge_adjustment_cents: 30, final_amount_due_cents: 0, payment_required: false }) })
    renderCheckout()
    expect((await screen.findByText('Covered by Pickup Lane')).nextSibling).toHaveTextContent('-$0.30')
    expect(screen.queryByText('Game credit applied')).not.toBeInTheDocument()
  })

  it("F17-27: with organizer terms community refunds stay with the original organizer", async () => {
    fakePageApi(communityGame({ custom_cancellation_text: 'Organizer terms apply.' }))
    renderCheckout()
    expect(await screen.findByText(/Payment disputes and refunds remain between you and the original organizer/)).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Confirm Spot' })[0]).toBeDisabled()
  })

  it("F17-27: without organizer terms community refunds stay with the original organizer", async () => {
    fakePageApi(communityGame({ custom_cancellation_text: null }))
    renderCheckout()
    expect(await screen.findByText(/Payment disputes and refunds remain between you and the original organizer/)).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Confirm Spot' })[0]).toBeDisabled()
  })
})
