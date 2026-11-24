import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  card, fakePageApi, LIST, REMOVE, renderPaymentMethods, requestCount, signIn, START_SETUP,
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
  areStripePaymentsEnabled: () => true,
  hasStripeCheckoutSupport: () => true,
  hasStripePublishableKey: () => true,
  stripePromise: {},
}))
vi.mock('@stripe/react-stripe-js', () => ({ Elements: ({ children }) => children }))

const SUSPENDED_NOTE =
  "Your account is suspended. You can view and remove saved cards, but you can't add a card or change your default."

beforeEach(() => {
  signIn({ account_status: 'suspended' })
})

describe('Payment Methods for a suspended player', () => {
  it('F13-15: a suspended player sees their saved cards', async () => {
    fakePageApi({
      [LIST]: [card({ card_last4: '1111', is_default: true }), card({ card_last4: '2222' })],
    })
    renderPaymentMethods()

    expect(await screen.findByRole('heading', { name: 'Visa ending 1111' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Visa ending 2222' })).toBeInTheDocument()
  })

  it('F13-15: a suspended player sees why adding a card and changing the default are not offered', async () => {
    fakePageApi({ [LIST]: [card({ card_last4: '1111', is_default: true })] })
    renderPaymentMethods()

    expect(await screen.findByText(SUSPENDED_NOTE)).toBeInTheDocument()
  })

  it('F13-15: a suspended player is not offered Add card', async () => {
    fakePageApi({ [LIST]: [card({ card_last4: '1111', is_default: true })] })
    renderPaymentMethods()

    await screen.findByRole('heading', { name: 'Visa ending 1111' })
    expect(screen.queryByRole('button', { name: 'Add card' })).not.toBeInTheDocument()
    expect(requestCount(START_SETUP)).toBe(0)
  })

  it('F13-15: a suspended player is not offered Make default', async () => {
    const user = userEvent.setup()
    fakePageApi({
      [LIST]: [card({ card_last4: '1111', is_default: true }), card({ card_last4: '2222' })],
    })
    renderPaymentMethods()

    await user.click(await screen.findByRole('button', { name: 'Open actions for Visa ending 2222' }))

    expect(screen.getByRole('menuitem', { name: 'Remove card' })).toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: 'Make default' })).not.toBeInTheDocument()
  })

  it('F13-15: a suspended player can remove a card', async () => {
    const user = userEvent.setup()
    const kept = card({ card_last4: '1111', is_default: true })
    const removed = card({ card_last4: '2222' })
    let gone = false
    fakePageApi({
      [LIST]: () => (gone ? [kept] : [kept, removed]),
      [REMOVE]: () => {
        gone = true
        return { ...removed, method_status: 'detached', detached_at: '2029-06-16T18:00:00Z' }
      },
    })
    renderPaymentMethods()

    await user.click(await screen.findByRole('button', { name: 'Open actions for Visa ending 2222' }))
    await user.click(screen.getByRole('menuitem', { name: 'Remove card' }))
    await user.click(within(screen.getByRole('dialog', { name: 'Remove card?' })).getByRole('button', { name: 'Remove card' }))

    expect(await screen.findByText('Payment method removed.')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Visa ending 2222' })).not.toBeInTheDocument()
    expect(requestCount(REMOVE)).toBe(1)
  })

  it('F13-15: a suspended player with no cards is not invited to add one', async () => {
    fakePageApi()
    renderPaymentMethods()

    expect(await screen.findByText('No saved cards yet')).toBeInTheDocument()
    expect(screen.queryByText('Add a card to speed up official game checkout.')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add card' })).not.toBeInTheDocument()
  })
})
