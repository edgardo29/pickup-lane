import { fireEvent, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  fakePageApi, game, renderEditGame, requestCount, SAVE_DETAILS, SAVE_GAME, signIn,
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

function nothingSaved() {
  return [requestCount(SAVE_GAME), requestCount(SAVE_DETAILS)]
}

// Open the form and change the total spots from 14 to 16.
async function openWithAChange(user) {
  fakePageApi(game())
  renderEditGame()
  await user.selectOptions(await screen.findByRole('combobox', { name: 'Total spots' }), '16')
}

describe('Edit Game cancel', () => {
  it('F18-5: Cancel without changes returns to Game Details', async () => {
    const user = userEvent.setup()
    fakePageApi(game())
    renderEditGame()

    await user.click(await screen.findByRole('button', { name: 'Cancel' }))

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(nothingSaved()).toEqual([0, 0])
  })

  it('F18-5: Cancel with changes asks to keep editing or discard the changes', async () => {
    const user = userEvent.setup()
    await openWithAChange(user)

    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    const prompt = screen.getByRole('dialog', { name: 'Discard changes?' })
    expect(prompt).toHaveTextContent('Your game changes have not been saved.')
    expect(screen.getByRole('button', { name: 'Keep editing' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Discard' })).toBeInTheDocument()
  })

  it('F18-5: Discard returns to Game Details without saving', async () => {
    const user = userEvent.setup()
    await openWithAChange(user)

    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    await user.click(screen.getByRole('button', { name: 'Discard' }))

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(nothingSaved()).toEqual([0, 0])
  })

  it('F18-5: Keep editing stays on the form with the changes', async () => {
    const user = userEvent.setup()
    await openWithAChange(user)

    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    await user.click(screen.getByRole('button', { name: 'Keep editing' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Total spots' })).toHaveValue('16')
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
  })

  it('F18-5: Back from the first step asks about changes, and returns to Game Details once there are none', async () => {
    const user = userEvent.setup()
    await openWithAChange(user)

    await user.click(screen.getByRole('button', { name: 'Go back' }))
    expect(screen.getByRole('dialog', { name: 'Discard changes?' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Keep editing' }))
    await user.selectOptions(screen.getByRole('combobox', { name: 'Total spots' }), '14')
    await user.click(screen.getByRole('button', { name: 'Go back' }))

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(nothingSaved()).toEqual([0, 0])
  })
})

describe('Edit Game validation', () => {
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
    expect(screen.getByRole('heading', { name: "Let's start with the game" })).toBeInTheDocument()
    expect(nothingSaved()).toEqual([0, 0])
  })

  it('F18-10: a missing capacity is reported on the Game step and not saved', async () => {
    const user = userEvent.setup()
    fakePageApi(game())
    renderEditGame()

    // The list offers only counts the format allows, so a blank choice is the
    // capacity the form can be left with.
    await user.selectOptions(await screen.findByRole('combobox', { name: 'Total spots' }), '')
    await user.click(screen.getByRole('button', { name: /^Next: Location/ }))

    expect(screen.getByText('Choose total spots.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: "Let's start with the game" })).toBeInTheDocument()
    expect(nothingSaved()).toEqual([0, 0])
  })

  it('F18-10: an incomplete location is reported on the Location step and not saved', async () => {
    const user = userEvent.setup()
    fakePageApi(game())
    renderEditGame()

    await user.click(await screen.findByRole('button', { name: /^Next: Location/ }))
    await user.clear(screen.getByLabelText('Street address'))
    await user.click(screen.getByRole('button', { name: /^Next: Notes/ }))

    expect(screen.getByText('Add street address.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Where will you play?' })).toBeInTheDocument()
    expect(nothingSaved()).toEqual([0, 0])
  })

  it('F18-10: a paid game without host payment details is reported on the Notes step and not saved', async () => {
    const user = userEvent.setup()
    fakePageApi(game())
    renderEditGame()

    await user.click(await screen.findByRole('button', { name: /^Next: Location/ }))
    await user.click(screen.getByRole('button', { name: /^Next: Notes/ }))
    await user.clear(screen.getByRole('textbox', { name: 'Venmo details' }))
    await user.click(screen.getByRole('button', { name: /^Next: Review/ }))

    expect(screen.getByText('Add payment method details before continuing.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Notes and Payment' })).toBeInTheDocument()
    expect(nothingSaved()).toEqual([0, 0])
  })
})
