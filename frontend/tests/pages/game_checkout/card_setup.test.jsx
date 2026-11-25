import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../../../src/hooks/useAuth.js'

import { checkoutStatus, fakePageApi, game, OTHER_CARD_ID, paymentIntent, PLAYER_ID, renderCheckout, savedCard, sentBody } from './gameCheckoutTestKit.jsx'

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
  it("F17-4: a card saved through the shared form is used for checkout", async () => {
    const user = userEvent.setup()
    let saved = false
    fakePageApi(game(), paidAnswers({
      'GET /user-payment-methods': () => saved ? [savedCard({ id: OTHER_CARD_ID, card_last4: '1881' })] : [],
      'POST /user-payment-methods/setup-intent': { client_secret: 'seti_test_secret' },
      'POST /user-payment-methods/sync': () => { saved = true; return savedCard({ id: OTHER_CARD_ID, card_last4: '1881' }) },
    }))
    renderCheckout()
    await user.click(await screen.findByRole('button', { name: 'Add card' }))
    const dialog = await screen.findByRole('dialog', { name: 'Add card' })
    await user.click(within(dialog).getByRole('button', { name: 'Enter test card' }))
    await user.click(within(dialog).getByRole('button', { name: 'Save card' }))
    expect(await screen.findByText(/Selected for this booking/)).toBeInTheDocument()
    expect(fakeStripe.confirmSetup).toHaveBeenCalledWith(expect.objectContaining({ clientSecret: 'seti_test_secret', redirect: 'if_required' }))
    expect(sentBody('/sync')).toEqual({ setup_intent_id: 'seti_test_123', set_as_default: true })
    await agreeAndConfirm(user)
    await screen.findByRole('heading', { name: 'Game Details' })
    expect(sentBody('/payment-intent').payment_method_id).toBe(OTHER_CARD_ID)
  })

  it("F17-12: failed card setup shows recoverable feedback without false success", async () => {
    const user = userEvent.setup()
    fakeStripe.confirmSetup.mockResolvedValue({ error: { message: 'Your card was declined.' } })
    fakePageApi(game(), {
      'GET /user-payment-methods': [],
      'POST /user-payment-methods/setup-intent': { client_secret: 'seti_test_secret' },
    })
    renderCheckout()
    await user.click(await screen.findByRole('button', { name: 'Add card' }))
    const dialog = await screen.findByRole('dialog', { name: 'Add card' })
    await user.click(within(dialog).getByRole('button', { name: 'Enter test card' }))
    await user.click(within(dialog).getByRole('button', { name: 'Save card' }))
    expect(await within(dialog).findByText('Your card was declined.')).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: 'Save card' })).toBeEnabled()
    expect(sentBody('/sync')).toBeNull()
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
  })

  it("F17-12: unavailable Stripe setup is explained to the player", async () => {
    fakeStripe.supported = false
    fakePageApi(game(), { 'GET /user-payment-methods': [] })
    renderCheckout()
    expect(await screen.findByText("Adding cards isn't available right now.")).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add card' })).not.toBeInTheDocument()
    expect(sentBody('/setup-intent')).toBeNull()
  })

  it("F17-12: an expired card cannot be selected and a usable card can be chosen", async () => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'GET /user-payment-methods': [savedCard({ exp_year: 2020 }), savedCard({ id: OTHER_CARD_ID, card_last4: '1881', is_default: false })],
    })
    renderCheckout()
    await user.click(await screen.findByRole('button', { name: 'Change' }))
    const dialog = screen.getByRole('dialog', { name: 'Choose payment method' })
    expect(within(dialog).getByRole('button', { name: 'Use this card' })).toBeDisabled()
    expect(within(dialog).getByRole('button', { name: 'Selected' })).toBeDisabled()
    expect(within(dialog).getByText(/1881/)).toBeInTheDocument()
  })
})
