import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError } from '../../../src/lib/apiClient.js'
import {
  card, fakePageApi, GAME_ID, LIST, MAKE_DEFAULT, REMOVE,
  renderPaymentMethods, requestCount, SAVE_CARD, signIn,
} from './paymentMethodsTestKit.jsx'

const { runWithStepUp, fakeStripe } = vi.hoisted(() => ({
  // Account confirmation passes, then the protected request runs.
  runWithStepUp: vi.fn((action) => action()),
  fakeStripe: { confirmSetup: vi.fn() },
}))

vi.mock('../../../src/lib/apiClient.js', async (importOriginal) => ({
  ...(await importOriginal()),
  apiRequest: vi.fn(),
}))
vi.mock('../../../src/hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../../../src/hooks/useStepUp.js', () => ({ useStepUp: () => ({ runWithStepUp }) }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))
vi.mock('../../../src/components/BrowseAppNav.jsx', () => ({ default: () => null }))
vi.mock('../../../src/lib/stripe.js', () => ({
  areStripePaymentsEnabled: () => true,
  hasStripeCheckoutSupport: () => true,
  hasStripePublishableKey: () => true,
  stripePromise: {},
}))
vi.mock('@stripe/react-stripe-js', () => ({
  Elements: ({ children }) => children,
  PaymentElement: ({ onChange }) => (
    <button type="button" onClick={() => onChange({ complete: true })}>Enter test card</button>
  ),
  useElements: () => ({ submit: async () => ({}) }),
  useStripe: () => fakeStripe,
}))

const CHECKOUT_PATH = `/games/${GAME_ID}/checkout`

beforeEach(() => {
  signIn()
  fakeStripe.confirmSetup.mockResolvedValue({ setupIntent: { id: 'seti_test_123' } })
})

async function openCardMenu(user, label) {
  await user.click(await screen.findByRole('button', { name: `Open actions for ${label}` }))
}

describe('Payment Methods managing cards', () => {
  function fakeMakeDefault() {
    const first = card({ card_last4: '1111', is_default: true })
    const second = card({ card_last4: '2222' })
    let changed = false
    fakePageApi({
      [LIST]: () => (changed
        ? [{ ...first, is_default: false }, { ...second, is_default: true }]
        : [first, second]),
      [MAKE_DEFAULT]: () => {
        changed = true
        return { ...second, is_default: true }
      },
    })
  }

  it('F13-3: Make default asks for account confirmation', async () => {
    const user = userEvent.setup()
    fakeMakeDefault()
    renderPaymentMethods()

    await openCardMenu(user, 'Visa ending 2222')
    await user.click(screen.getByRole('menuitem', { name: 'Make default' }))

    expect(await screen.findByText('Default payment method updated.')).toBeInTheDocument()
    expect(runWithStepUp).toHaveBeenCalledWith(expect.any(Function), {
      actionLabel: 'change your default card',
    })
  })

  it('F13-3: after Make default, exactly that card shows the Default badge', async () => {
    const user = userEvent.setup()
    fakeMakeDefault()
    renderPaymentMethods()

    await openCardMenu(user, 'Visa ending 2222')
    await user.click(screen.getByRole('menuitem', { name: 'Make default' }))
    await screen.findByText('Default payment method updated.')

    const secondRow = screen.getByRole('heading', { name: 'Visa ending 2222' }).closest('article')
    expect(within(secondRow).getByText('Default')).toBeInTheDocument()
    expect(screen.getAllByText('Default')).toHaveLength(1)
  })

  function fakeRemoval() {
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
  }

  async function removeCard(user, label) {
    await openCardMenu(user, label)
    await user.click(screen.getByRole('menuitem', { name: 'Remove card' }))
    const dialog = screen.getByRole('dialog', { name: 'Remove card?' })
    await user.click(within(dialog).getByRole('button', { name: 'Remove card' }))
  }

  it('F13-4: Remove asks for account confirmation', async () => {
    const user = userEvent.setup()
    fakeRemoval()
    renderPaymentMethods()

    await removeCard(user, 'Visa ending 2222')

    expect(await screen.findByText('Payment method removed.')).toBeInTheDocument()
    expect(runWithStepUp).toHaveBeenCalledWith(expect.any(Function), { actionLabel: 'remove this card' })
  })

  it('F13-4: after removal, the card is no longer listed', async () => {
    const user = userEvent.setup()
    fakeRemoval()
    renderPaymentMethods()

    await removeCard(user, 'Visa ending 2222')
    await screen.findByText('Payment method removed.')

    expect(screen.queryByRole('heading', { name: 'Visa ending 2222' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Visa ending 1111' })).toBeInTheDocument()
  })

  it('F13-7: backing out of removal keeps the card', async () => {
    const user = userEvent.setup()
    fakePageApi({ [LIST]: [card({ card_last4: '1111', is_default: true })] })
    renderPaymentMethods()

    await openCardMenu(user, 'Visa ending 1111')
    await user.click(screen.getByRole('menuitem', { name: 'Remove card' }))
    await user.click(within(screen.getByRole('dialog', { name: 'Remove card?' })).getByRole('button', { name: 'Back' }))

    expect(screen.queryByRole('dialog', { name: 'Remove card?' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Visa ending 1111' })).toBeInTheDocument()
    expect(requestCount(REMOVE)).toBe(0)
  })

  it('F13-8: a failed default change shows the error and keeps the old default', async () => {
    const user = userEvent.setup()
    fakePageApi({
      [LIST]: [card({ card_last4: '1111', is_default: true }), card({ card_last4: '2222' })],
      [MAKE_DEFAULT]: new ApiRequestError('Stripe could not set this default payment method.', { status: 502 }),
    })
    renderPaymentMethods()

    await openCardMenu(user, 'Visa ending 2222')
    await user.click(screen.getByRole('menuitem', { name: 'Make default' }))

    expect(await screen.findByText('Stripe could not set this default payment method.')).toBeInTheDocument()
    expect(screen.queryByText('Default payment method updated.')).not.toBeInTheDocument()
    const firstRow = screen.getByRole('heading', { name: 'Visa ending 1111' }).closest('article')
    expect(within(firstRow).getByText('Default')).toBeInTheDocument()
  })

  it('F13-8: a failed default change can be tried again', async () => {
    const user = userEvent.setup()
    const first = card({ card_last4: '1111', is_default: true })
    const second = card({ card_last4: '2222' })
    let attempts = 0
    fakePageApi({
      [LIST]: () => (attempts > 1
        ? [{ ...first, is_default: false }, { ...second, is_default: true }]
        : [first, second]),
      [MAKE_DEFAULT]: () => {
        attempts += 1
        return attempts === 1
          ? new ApiRequestError('Stripe could not set this default payment method.', { status: 502 })
          : { ...second, is_default: true }
      },
    })
    renderPaymentMethods()
    await openCardMenu(user, 'Visa ending 2222')
    await user.click(screen.getByRole('menuitem', { name: 'Make default' }))
    await screen.findByText('Stripe could not set this default payment method.')

    await user.click(screen.getByRole('menuitem', { name: 'Make default' }))

    expect(await screen.findByText('Default payment method updated.')).toBeInTheDocument()
    expect(requestCount(MAKE_DEFAULT)).toBe(2)
  })

  it('F13-8: a failed removal shows the error and keeps the card', async () => {
    const user = userEvent.setup()
    fakePageApi({
      [LIST]: [card({ card_last4: '1111', is_default: true })],
      [REMOVE]: new ApiRequestError('Stripe could not detach this payment method.', { status: 502 }),
    })
    renderPaymentMethods()

    await removeCard(user, 'Visa ending 1111')

    expect(await screen.findByText('Stripe could not detach this payment method.')).toBeInTheDocument()
    expect(screen.queryByText('Payment method removed.')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Visa ending 1111' })).toBeInTheDocument()
  })

  it('F13-8: a failed removal can be tried again', async () => {
    const user = userEvent.setup()
    const only = card({ card_last4: '1111', is_default: true })
    let attempts = 0
    fakePageApi({
      [LIST]: () => (attempts > 1 ? [] : [only]),
      [REMOVE]: () => {
        attempts += 1
        return attempts === 1
          ? new ApiRequestError('Stripe could not detach this payment method.', { status: 502 })
          : { ...only, method_status: 'detached', detached_at: '2029-06-16T18:00:00Z' }
      },
    })
    renderPaymentMethods()
    await removeCard(user, 'Visa ending 1111')
    await screen.findByText('Stripe could not detach this payment method.')

    const dialog = screen.getByRole('dialog', { name: 'Remove card?' })
    await user.click(within(dialog).getByRole('button', { name: 'Remove card' }))

    expect(await screen.findByText('Payment method removed.')).toBeInTheDocument()
    expect(requestCount(REMOVE)).toBe(2)
  })

  it('F13-5: from checkout, Back returns to checkout', async () => {
    const user = userEvent.setup()
    fakePageApi()
    const router = renderPaymentMethods(
      `/profile/payment-methods?returnTo=${encodeURIComponent(`${CHECKOUT_PATH}?guests=1`)}`,
    )

    await user.click(await screen.findByRole('link', { name: 'Back to checkout' }))

    expect(await screen.findByRole('heading', { name: 'Game Checkout' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe(CHECKOUT_PATH)
    expect(router.state.location.search).toBe('?guests=1')
  })

  it('F13-5: from checkout, the link after saving a card returns to checkout', async () => {
    const user = userEvent.setup()
    let saved = false
    fakePageApi({
      [LIST]: () => (saved ? [card({ card_last4: '1111', is_default: true })] : []),
      [SAVE_CARD]: () => {
        saved = true
        return card({ card_last4: '1111', is_default: true })
      },
    })
    const router = renderPaymentMethods(
      `/profile/payment-methods?returnTo=${encodeURIComponent(`${CHECKOUT_PATH}?guests=1`)}`,
    )
    await user.click(await screen.findByRole('button', { name: 'Add card' }))
    const dialog = await screen.findByRole('dialog', { name: 'Add card' })
    await user.click(within(dialog).getByRole('button', { name: 'Enter test card' }))
    await user.click(within(dialog).getByRole('button', { name: 'Save card' }))

    await user.click(await screen.findByRole('link', { name: 'Return to checkout' }))

    expect(await screen.findByRole('heading', { name: 'Game Checkout' })).toBeInTheDocument()
    expect(router.state.location.search).toBe('?guests=1')
  })

  it('F13-5: opened from Profile, Back returns to Profile', async () => {
    const user = userEvent.setup()
    fakePageApi()
    renderPaymentMethods()

    await user.click(await screen.findByRole('link', { name: 'Back to profile' }))

    expect(await screen.findByRole('heading', { name: 'Profile' })).toBeInTheDocument()
  })

  it.each([
    'https://evil.example/games/1/checkout',
    '//evil.example/games/1/checkout',
    '/\\evil.example/games/1/checkout',
    '/admin/users',
    'games/1/checkout',
  ])('F13-12: the return path %s falls back to Profile', async (returnTo) => {
    fakePageApi()
    renderPaymentMethods(`/profile/payment-methods?returnTo=${encodeURIComponent(returnTo)}`)

    expect(await screen.findByRole('link', { name: 'Back to profile' })).toHaveAttribute('href', '/profile')
    expect(screen.queryByRole('link', { name: 'Back to checkout' })).not.toBeInTheDocument()
  })
})
