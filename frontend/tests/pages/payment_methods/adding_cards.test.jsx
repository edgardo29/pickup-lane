import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { render } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../../../src/hooks/useAuth.js'
import { ApiRequestError } from '../../../src/lib/apiClient.js'
import { PaymentMethodsPage } from '../../../src/pages/profile/PaymentMethodsPage.jsx'
import { RequireAppUser } from '../../../src/routes/RouteGuards.jsx'
import { areStripePaymentsEnabled, hasStripeCheckoutSupport } from '../../../src/lib/stripe.js'
import {
  card, fakePageApi, LIST, renderPaymentMethods, requestCount, SAVE_CARD, sentBodies, signIn,
  setupAnswer, START_SETUP,
} from './paymentMethodsTestKit.jsx'

vi.mock('../../../src/lib/apiClient.js', async (importOriginal) => ({
  ...(await importOriginal()),
  apiRequest: vi.fn(),
}))
vi.mock('../../../src/hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../../../src/hooks/useStepUp.js', () => ({
  useStepUp: () => ({ runWithStepUp: (action) => action() }),
}))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))
vi.mock('../../../src/lib/stripe.js', () => ({
  areStripePaymentsEnabled: vi.fn(() => true),
  hasStripeCheckoutSupport: vi.fn(() => true),
  hasStripePublishableKey: vi.fn(() => true),
  stripePromise: {},
}))
// Stripe's secure card field cannot run in tests. This stands in for it: the
// player marks the card complete, and Stripe confirms the setup.
const fakeStripe = { confirmSetup: vi.fn() }
vi.mock('@stripe/react-stripe-js', () => ({
  Elements: ({ children }) => children,
  PaymentElement: ({ onChange }) => (
    <button type="button" onClick={() => onChange({ complete: true })}>Enter test card</button>
  ),
  useElements: () => ({ submit: async () => ({}) }),
  useStripe: () => fakeStripe,
}))

beforeEach(() => {
  signIn()
  fakeStripe.confirmSetup.mockResolvedValue({ setupIntent: { id: 'seti_test_123' } })
})

async function addCardThroughSetup(user) {
  await user.click(await screen.findByRole('button', { name: 'Add card' }))
  const dialog = await screen.findByRole('dialog', { name: 'Add card' })
  await user.click(within(dialog).getByRole('button', { name: 'Enter test card' }))
  await user.click(within(dialog).getByRole('button', { name: 'Save card' }))
}

describe('Payment Methods adding cards', () => {
  it.each(['/profile/payment-methods', '/settings/payment-methods'])(
    'F13-1: %s shows the cards with one Default badge',
    async (route) => {
      fakePageApi({
        [LIST]: [
          card({ card_last4: '1111', exp_month: 3, exp_year: 2031, is_default: true }),
          card({ card_brand: 'mastercard', card_last4: '2222' }),
        ],
      })
      renderPaymentMethods(route)

      expect(await screen.findByRole('heading', { name: 'Visa ending 1111' })).toBeInTheDocument()
      expect(screen.getByText('Expires 03/2031')).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: 'Mastercard ending 2222' })).toBeInTheDocument()
      expect(screen.getAllByText('Default')).toHaveLength(1)
    },
  )

  it('F13-2: after a card is saved, the list refreshes and shows it', async () => {
    const user = userEvent.setup()
    let saved = false
    fakePageApi({
      [LIST]: () => (saved ? [card({ card_last4: '1111', is_default: true })] : []),
      [SAVE_CARD]: () => {
        saved = true
        return card({ card_last4: '1111', is_default: true })
      },
    })
    renderPaymentMethods()

    await addCardThroughSetup(user)

    expect(await screen.findByRole('heading', { name: 'Visa ending 1111' })).toBeInTheDocument()
    expect(screen.getByText('Card saved.')).toBeInTheDocument()
  })

  it('F13-2: the first card is saved as default', async () => {
    const user = userEvent.setup()
    fakePageApi({ [SAVE_CARD]: card({ card_last4: '1111', is_default: true }) })
    renderPaymentMethods()

    await addCardThroughSetup(user)

    expect(await screen.findByText('Card saved.')).toBeInTheDocument()
    expect(sentBodies(START_SETUP)).toEqual([{ set_as_default: true }])
    expect(sentBodies(SAVE_CARD)).toEqual([{ setup_intent_id: 'seti_test_123', set_as_default: true }])
  })

  it('F13-2: adding another card does not ask for it to replace the default', async () => {
    const user = userEvent.setup()
    fakePageApi({
      [LIST]: [card({ card_last4: '1111', is_default: true })],
      [SAVE_CARD]: card({ card_last4: '2222' }),
    })
    renderPaymentMethods()

    await addCardThroughSetup(user)

    expect(await screen.findByText('Card saved.')).toBeInTheDocument()
    expect(sentBodies(START_SETUP)).toEqual([{ set_as_default: false }])
    expect(sentBodies(SAVE_CARD)[0].set_as_default).toBe(false)
  })

  it('F13-6: Add card is unavailable at five cards', async () => {
    fakePageApi({
      [LIST]: [card({ is_default: true }), card(), card(), card(), card()],
    })
    renderPaymentMethods()

    expect(await screen.findAllByRole('heading', { name: /Visa ending/ })).toHaveLength(5)
    expect(screen.getByRole('button', { name: 'Add card' })).toBeDisabled()
  })

  it('F13-7: cancelling card setup adds nothing and keeps the list', async () => {
    const user = userEvent.setup()
    fakePageApi({ [LIST]: [card({ card_last4: '1111', is_default: true })] })
    renderPaymentMethods()

    await user.click(await screen.findByRole('button', { name: 'Add card' }))
    const dialog = await screen.findByRole('dialog', { name: 'Add card' })
    await user.click(within(dialog).getByRole('button', { name: 'Back' }))

    expect(screen.queryByRole('dialog', { name: 'Add card' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Visa ending 1111' })).toBeInTheDocument()
    expect(requestCount(SAVE_CARD)).toBe(0)
  })

  it('F13-8: a failed card setup start shows the error without claiming success', async () => {
    const user = userEvent.setup()
    fakePageApi({
      [START_SETUP]: new ApiRequestError('Stripe could not create this setup intent.', { status: 502 }),
    })
    renderPaymentMethods()

    await user.click(await screen.findByRole('button', { name: 'Add card' }))

    expect(await screen.findByText('Stripe could not create this setup intent.')).toBeInTheDocument()
    expect(screen.queryByText('Card saved.')).not.toBeInTheDocument()
    expect(screen.queryByRole('dialog', { name: 'Add card' })).not.toBeInTheDocument()
    expect(requestCount(SAVE_CARD)).toBe(0)
  })

  it('F13-8: a failed card setup start can be tried again', async () => {
    const user = userEvent.setup()
    let attempts = 0
    fakePageApi({
      [START_SETUP]: () => {
        attempts += 1
        return attempts === 1
          ? new ApiRequestError('Stripe could not create this setup intent.', { status: 502 })
          : setupAnswer()
      },
    })
    renderPaymentMethods()
    await user.click(await screen.findByRole('button', { name: 'Add card' }))
    await screen.findByText('Stripe could not create this setup intent.')

    await user.click(screen.getByRole('button', { name: 'Add card' }))

    expect(await screen.findByRole('dialog', { name: 'Add card' })).toBeInTheDocument()
    expect(requestCount(START_SETUP)).toBe(2)
  })

  it('F13-8: a rejected card save shows the error without claiming the card was saved', async () => {
    const user = userEvent.setup()
    fakePageApi({
      [SAVE_CARD]: new ApiRequestError('This card is already saved.', { status: 409 }),
    })
    renderPaymentMethods()

    await addCardThroughSetup(user)

    expect(await screen.findByText('This card is already saved. Enter a different card.')).toBeInTheDocument()
    expect(screen.queryByText('Card saved.')).not.toBeInTheDocument()
    expect(screen.getByText('No saved cards yet')).toBeInTheDocument()
  })

  it('F13-8: after a rejected card save, another card can be entered', async () => {
    const user = userEvent.setup()
    fakePageApi({
      [SAVE_CARD]: new ApiRequestError('This card is already saved.', { status: 409 }),
    })
    renderPaymentMethods()
    await addCardThroughSetup(user)
    await screen.findByText('This card is already saved. Enter a different card.')

    const dialog = screen.getByRole('dialog', { name: 'Add card' })
    await user.click(await within(dialog).findByRole('button', { name: 'Enter test card' }))

    // A fresh card setup replaces the rejected one, ready for another card.
    expect(requestCount(START_SETUP)).toBe(2)
    expect(within(dialog).getByRole('button', { name: 'Save card' })).toBeEnabled()
  })

  it('F13-10: when card setup is unavailable the page explains it to the player', async () => {
    vi.mocked(hasStripeCheckoutSupport).mockReturnValue(false)
    fakePageApi()
    renderPaymentMethods()

    expect(await screen.findByText("Adding cards isn't available right now.")).toBeInTheDocument()
    expect(screen.queryByText('Stripe publishable key is not configured.')).not.toBeInTheDocument()
  })

  it('F13-10: when card setup is unavailable, card setup cannot start', async () => {
    vi.mocked(hasStripeCheckoutSupport).mockReturnValue(false)
    fakePageApi()
    renderPaymentMethods()

    await screen.findByText('No saved cards yet')
    expect(screen.getByRole('button', { name: 'Add card' })).toBeDisabled()
    expect(requestCount(START_SETUP)).toBe(0)
  })

  it('F13-10: when card setup is unavailable, the empty state does not invite adding a card', async () => {
    vi.mocked(hasStripeCheckoutSupport).mockReturnValue(false)
    fakePageApi()
    renderPaymentMethods()

    expect(await screen.findByText('No saved cards yet')).toBeInTheDocument()
    expect(screen.queryByText('Add a card to speed up official game checkout.')).not.toBeInTheDocument()
  })

  it('F13-10: when card payments are off the page says so', async () => {
    // With payments off, card setup is never ready either.
    vi.mocked(areStripePaymentsEnabled).mockReturnValue(false)
    vi.mocked(hasStripeCheckoutSupport).mockReturnValue(false)
    fakePageApi()
    renderPaymentMethods()

    expect(await screen.findByText('Card payments are disabled for this demo.')).toBeInTheDocument()
  })

  it('F13-10: when card payments are off, card setup cannot start', async () => {
    vi.mocked(areStripePaymentsEnabled).mockReturnValue(false)
    vi.mocked(hasStripeCheckoutSupport).mockReturnValue(false)
    fakePageApi()
    renderPaymentMethods()

    await screen.findByText('No saved cards yet')
    expect(screen.getByRole('button', { name: 'Add card' })).toBeDisabled()
    expect(requestCount(START_SETUP)).toBe(0)
  })

  it('F13-11: an account with no cards sees the empty state inviting a card', async () => {
    fakePageApi()
    renderPaymentMethods()

    expect(await screen.findByText('No saved cards yet')).toBeInTheDocument()
    expect(screen.getByText('Add a card to speed up official game checkout.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add card' })).toBeEnabled()
  })

  it('F13-11: a signed-out visitor is sent to sign in', async () => {
    vi.mocked(useAuth).mockReturnValue({ appUser: null, currentUser: null, isLoading: false })
    fakePageApi()
    const router = createMemoryRouter([
      {
        path: '/profile/payment-methods',
        element: <RequireAppUser><PaymentMethodsPage /></RequireAppUser>,
      },
      { path: '/sign-in', element: <h1>Sign In</h1> },
    ], { initialEntries: ['/profile/payment-methods'] })
    render(<RouterProvider router={router} />)

    expect(await screen.findByRole('heading', { name: 'Sign In' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/sign-in')
    expect(requestCount(LIST)).toBe(0)
  })
})
