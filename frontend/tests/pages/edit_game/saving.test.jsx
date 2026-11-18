import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError } from '../../../src/lib/apiClient.js'
import {
  communityDetails, fakePageApi, game, goToReview, renderEditGame, requestCount,
  SAVE_DETAILS, SAVE_GAME, sentBody, signIn,
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

describe('Edit Game saving', () => {
  it('F18-2: a permitted save returns to Game Details', async () => {
    const user = userEvent.setup()
    fakePageApi(game())
    renderEditGame()

    await goToReview(user)
    await user.click(screen.getByRole('button', { name: /Save Changes/ }))

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect([requestCount(SAVE_GAME), requestCount(SAVE_DETAILS)]).toEqual([1, 1])
  })

  it('F18-13: a suspended host can still edit a game they host', async () => {
    const user = userEvent.setup()
    signIn({ account_status: 'suspended' })
    // As the server does, refuse a suspended account its saved cards and fee
    // history, which only publishing a new game needs.
    const activeAccountRequired = new ApiRequestError('Active account required.', { status: 403 })
    fakePageApi(game(), {
      'GET /user-payment-methods': activeAccountRequired,
      'GET /host-publish-fees/me': activeAccountRequired,
    })
    renderEditGame()

    await goToReview(user)
    await user.click(screen.getByRole('button', { name: /Save Changes/ }))

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect([requestCount(SAVE_GAME), requestCount(SAVE_DETAILS)]).toEqual([1, 1])
    expect([
      requestCount('GET /user-payment-methods'),
      requestCount('GET /host-publish-fees/me'),
    ]).toEqual([0, 0])
  })

  it('F18-14: when only the payment details fail, a retry sends only that part', async () => {
    const user = userEvent.setup()
    let detailSaves = 0
    fakePageApi(game(), {
      [SAVE_DETAILS]: () => {
        detailSaves += 1
        if (detailSaves === 1) {
          return Promise.reject(new ApiRequestError('Payment details unavailable.', { status: 503 }))
        }
        // The server answers with the details it saved.
        return communityDetails({ payment_methods_snapshot: [{ type: 'venmo', value: '@new-host' }] })
      },
    })
    renderEditGame()

    await user.click(await screen.findByRole('button', { name: /^Next: Location/ }))
    await user.click(screen.getByRole('button', { name: /^Next: Notes/ }))
    const venmoDetails = screen.getByRole('textbox', { name: 'Venmo details' })
    await user.clear(venmoDetails)
    await user.type(venmoDetails, '@new-host')
    await user.click(screen.getByRole('button', { name: /^Next: Review/ }))
    await user.click(screen.getByRole('button', { name: /Save Changes/ }))

    expect(await screen.findByText(
      /Your game changes were saved, but the payment details were not\. Payment details unavailable\. Save again to retry the payment details\./,
    )).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()

    // The entered payment details are kept for the retry.
    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect(screen.getByRole('textbox', { name: 'Venmo details' })).toHaveValue('@new-host')
    await user.click(screen.getByRole('button', { name: /^Next: Review/ }))
    await user.click(screen.getByRole('button', { name: /Save Changes/ }))

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect([requestCount(SAVE_GAME), requestCount(SAVE_DETAILS)]).toEqual([1, 2])
    expect(sentBody(SAVE_DETAILS).payment_methods_snapshot).toEqual([
      { type: 'venmo', value: '@new-host' },
    ])
  })

  it('F18-15: a failed game update keeps the values and saves nothing else', async () => {
    const user = userEvent.setup()
    // Two players have joined a 16-spot game, so the server refuses fewer spots.
    fakePageApi(game({
      total_spots: 16,
      roster_counts: { occupied_spots: 3, spots_remaining: 13, waitlist_count: 0 },
    }), {
      [SAVE_GAME]: new ApiRequestError('Capacity can only be increased after players have joined.', { status: 400 }),
    })
    renderEditGame()

    await user.selectOptions(await screen.findByRole('combobox', { name: 'Total spots' }), '14')
    await goToReview(user)
    await user.click(screen.getByRole('button', { name: /Save Changes/ }))

    expect(await screen.findByText(
      'Your game changes were not saved. Capacity can only be increased after players have joined.',
    )).toBeInTheDocument()
    expect(requestCount(SAVE_DETAILS)).toBe(0)
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
    for (let step = 0; step < 3; step += 1) {
      await user.click(screen.getByRole('button', { name: 'Back' }))
    }
    expect(screen.getByRole('combobox', { name: 'Total spots' })).toHaveValue('14')
  })
})
