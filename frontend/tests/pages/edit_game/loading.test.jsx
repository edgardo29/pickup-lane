import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError } from '../../../src/lib/apiClient.js'
import { fakePageApi, game, renderEditGame, signIn } from './editGameTestKit.jsx'

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

describe('Edit Game loading and access', () => {
  it('F18-1: the existing game, venue, and community details load into the form', async () => {
    const user = userEvent.setup()
    fakePageApi(game())
    renderEditGame()

    expect(await screen.findByRole('combobox', { name: 'Total spots' })).toHaveValue('14')
    expect(screen.getByRole('heading', { name: 'Edit Game' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /^Next: Location/ }))
    expect(screen.getByLabelText('Venue name')).toHaveValue('Central Field')
    expect(screen.getByLabelText('ZIP code')).toHaveValue('60601')
    expect(screen.getByLabelText('Neighborhood (optional)')).toHaveValue('Loop')
    await user.click(screen.getByRole('button', { name: /^Next: Notes/ }))
    expect(screen.getByLabelText(/^Game notes \(optional\)/)).toHaveValue('Bring water.')
    expect(screen.getByLabelText(/^Host rules \(optional\)/)).toHaveValue('No slide tackles.')
    expect(screen.getByRole('combobox', { name: 'Payment method 1' })).toHaveValue('venmo')
    expect(screen.getByRole('textbox', { name: 'Venmo details' })).toHaveValue('@host')
  })

  it('F18-6: a visitor who is not the host sees an error instead of the form', async () => {
    fakePageApi(game({ host_user_id: '00000000-0000-4000-8000-000000000099' }))
    renderEditGame()

    expect(await screen.findByText('Only the host of a community game can edit it.')).toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Total spots' })).not.toBeInTheDocument()
  })

  it('F18-6: an official game cannot be edited here', async () => {
    fakePageApi(game({ game_type: 'official', payment_collection_type: 'in_app', host_user_id: null }))
    renderEditGame()

    expect(await screen.findByText('Only the host of a community game can edit it.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Next: Location/ })).not.toBeInTheDocument()
  })

  it('F18-11: a failed load shows the error without the form', async () => {
    fakePageApi(new ApiRequestError('Game could not be loaded.', { status: 500 }))
    renderEditGame()

    expect(await screen.findByText('Game could not be loaded.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Save Changes/ })).not.toBeInTheDocument()
  })

  it('F18-11: a failed venue load shows the error instead of a form missing its address', async () => {
    fakePageApi(game(), {
      'GET /venues/{venue_id}': new ApiRequestError('Venue not found.', { status: 404 }),
    })
    renderEditGame()

    expect(await screen.findByText('Venue not found.')).toBeInTheDocument()
    expect(screen.queryByRole('textbox', { name: /ZIP/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Save Changes/ })).not.toBeInTheDocument()
  })
})
