import { fireEvent, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  fakePageApi, game, renderEditGame, requestCount, SAVE_GAME, signIn,
} from './editGameTestKit.jsx'

vi.mock('../../../src/lib/apiClient.js', async (importOriginal) => ({
  ...(await importOriginal()),
  apiRequest: vi.fn(),
}))
vi.mock('../../../src/hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))
vi.mock('../../../src/lib/stripe.js', () => ({
  areStripePaymentsEnabled: () => true,
  hasStripeCheckoutSupport: () => true,
  hasStripePublishableKey: () => true,
  stripePromise: null,
}))

beforeEach(() => signIn())

describe('Edit Game cancel and validation', () => {
  it('F18-5: Cancel without changes returns to Game Details', async () => {
    const user = userEvent.setup()
    fakePageApi(game())
    renderEditGame()

    await user.click(await screen.findByRole('button', { name: 'Cancel' }))

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(requestCount(SAVE_GAME)).toBe(0)
  })

  it('F18-5: Cancel with changes asks to keep editing or discard', async () => {
    const user = userEvent.setup()
    fakePageApi(game())
    renderEditGame()

    await user.selectOptions(await screen.findByRole('combobox', { name: 'Total spots' }), '16')
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    await user.click(screen.getByRole('button', { name: 'Keep editing' }))

    expect(screen.getByRole('combobox', { name: 'Total spots' })).toHaveValue('16')

    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    await user.click(screen.getByRole('button', { name: 'Discard' }))

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(requestCount(SAVE_GAME)).toBe(0)
  })

  it('F18-10: a date past the 21-day limit is reported on the Game step and not saved', async () => {
    const user = userEvent.setup()
    fakePageApi(game())
    renderEditGame()

    const tooFar = new Date()
    tooFar.setDate(tooFar.getDate() + 22)
    const tooFarValue = [
      tooFar.getFullYear(),
      String(tooFar.getMonth() + 1).padStart(2, '0'),
      String(tooFar.getDate()).padStart(2, '0'),
    ].join('-')
    fireEvent.change(await screen.findByLabelText('Date'), { target: { value: tooFarValue } })
    await user.click(screen.getByRole('button', { name: /^Next: Location/ }))

    expect(await screen.findByText('Choose a date no more than 21 days ahead.')).toBeInTheDocument()
    expect(screen.getByLabelText('Date')).toBeInTheDocument()
    expect(requestCount(SAVE_GAME)).toBe(0)
  })
})
