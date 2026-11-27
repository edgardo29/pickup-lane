import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../../../src/hooks/useAuth.js'
import { apiRequest, ApiRequestError } from '../../../src/lib/apiClient.js'
import {
  communityDetails, fakePageApi, GAME_ID, game, renderEditGame, requestCount, SAVE_DETAILS, SAVE_GAME,
  sentBody, signIn,
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

  it('F18-1, F18-2: a free game opens with no player payment needed, so it saves without payment details', async () => {
    const user = userEvent.setup()
    // A published free game collects nothing and lists no payment method.
    const freeGame = game({ price_per_player_cents: 0, payment_collection_type: 'none' })
    fakePageApi(freeGame, {
      'GET /community-game-details/games/{game_id}/host-edit': communityDetails({ payment_methods_snapshot: [] }),
      [SAVE_DETAILS]: communityDetails({ payment_methods_snapshot: [] }),
    })
    renderEditGame()

    await user.click(await screen.findByRole('button', { name: /^Next: Location/ }))
    await user.click(screen.getByRole('button', { name: /^Next: Notes/ }))
    expect(screen.getByRole('combobox', { name: 'Payment method 1' })).toHaveValue('none')
    await user.click(screen.getByRole('button', { name: /^Next: Review/ }))
    await user.click(screen.getByRole('button', { name: /Save Changes/ }))

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect([requestCount(SAVE_GAME), requestCount(SAVE_DETAILS)]).toEqual([1, 1])
    expect(sentBody(SAVE_DETAILS).payment_methods_snapshot).toEqual([])
  })

  it('F18-1: the owner of a game staff have hidden can open it in the form', async () => {
    // Game Details hides a hidden game from anyone not signed in as someone
    // allowed to see it, such as its host.
    fakePageApi((_path, options) => (options?.headers?.Authorization === 'Bearer test-token'
      ? game({ public_visibility_status: 'hidden' })
      : Promise.reject(new ApiRequestError('Game not found.', { status: 404 }))))
    renderEditGame()

    expect(await screen.findByRole('combobox', { name: 'Total spots' })).toHaveValue('14')
    expect(screen.queryByText('Game not found.')).not.toBeInTheDocument()
  })

  it('F18-16: an owner whose email is not verified sees the email-verification requirement instead of the form', async () => {
    signIn({ email_verified_at: null })
    fakePageApi(game())
    renderEditGame()

    const requirement = await screen.findByRole('region', { name: 'Email verification' })
    expect(requirement).toHaveTextContent('Verify your account email before saving changes to this game.')
    expect(screen.getByRole('button', { name: 'Send verification email' })).toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Total spots' })).not.toBeInTheDocument()
  })

  it('F18-6: a signed-out visitor is sent to sign in', async () => {
    vi.mocked(useAuth).mockReturnValue({ appUser: null, currentUser: null, isLoading: false })
    fakePageApi(game())
    const router = renderEditGame()

    expect(await screen.findByRole('heading', { name: 'Sign In' })).toBeInTheDocument()
    // Sign In returns the visitor to this game's edit page.
    expect(router.state.location.state.from).toBe(`/games/${GAME_ID}/edit`)
    expect(vi.mocked(apiRequest)).not.toHaveBeenCalled()
  })

  it('F18-6: a visitor who is not the host sees an error instead of the form', async () => {
    // The server shows the host and the host's guest limit only to the host and staff.
    fakePageApi(game({ host_user_id: null, host_guest_max: 0 }))
    renderEditGame()

    expect(await screen.findByText('Only the host of a community game can edit it.')).toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Total spots' })).not.toBeInTheDocument()
  })

  it('F18-6: an official game cannot be edited here', async () => {
    fakePageApi(game({
      game_type: 'official',
      payment_collection_type: 'in_app',
      host_user_id: null,
      host_guest_max: 0,
      custom_rules_text: null,
    }))
    renderEditGame()

    expect(await screen.findByText('Only the host of a community game can edit it.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Next: Location/ })).not.toBeInTheDocument()
  })

  it('F18-11: a failed load shows the error without the form', async () => {
    fakePageApi(new ApiRequestError('An unexpected error occurred.', { status: 500 }))
    renderEditGame()

    expect(await screen.findByText('An unexpected error occurred.')).toBeInTheDocument()
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
