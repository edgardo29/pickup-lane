import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiRequest, ApiRequestError } from '../../../src/lib/apiClient.js'
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

function saveCounts() {
  return [requestCount(SAVE_GAME), requestCount(SAVE_DETAILS)]
}

// The game update saves; the payment details fail once, then save on the retry.
function fakePaymentDetailsFailingOnce() {
  let detailSaves = 0
  fakePageApi(game(), {
    [SAVE_DETAILS]: () => {
      detailSaves += 1
      if (detailSaves === 1) {
        return Promise.reject(new ApiRequestError('An unexpected error occurred.', { status: 500 }))
      }
      // The server answers with the details it saved.
      return communityDetails({ payment_methods_snapshot: [{ type: 'venmo', value: '@new-host' }] })
    },
  })
  renderEditGame()
}

// Change the Venmo details to @new-host and save.
async function saveNewVenmoDetails(user) {
  await user.click(await screen.findByRole('button', { name: /^Next: Location/ }))
  await user.click(screen.getByRole('button', { name: /^Next: Notes/ }))
  const venmoDetails = screen.getByRole('textbox', { name: 'Venmo details' })
  await user.clear(venmoDetails)
  await user.type(venmoDetails, '@new-host')
  await user.click(screen.getByRole('button', { name: /^Next: Review/ }))
  await user.click(screen.getByRole('button', { name: /Save Changes/ }))
}

const PARTLY_SAVED = 'Your game changes were saved, but the payment details were not. An unexpected error occurred. Save again to retry the payment details.'

// Two players have joined a 16-spot game; the host lowers it to 14 and the
// server refuses the game update.
async function saveRefusedCapacity(user) {
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
}

describe('Edit Game review and save', () => {
  it('F18-2: the host can move between the steps and review the proposed changes', async () => {
    const user = userEvent.setup()
    fakePageApi(game())
    renderEditGame()

    await user.selectOptions(await screen.findByRole('combobox', { name: 'Total spots' }), '16')
    await goToReview(user)

    expect(screen.getByRole('heading', { name: 'Review your changes' })).toBeInTheDocument()
    expect(screen.getByText('Total spots').nextSibling).toHaveTextContent('16 players')

    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect(screen.getByRole('heading', { name: 'Notes and Payment' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect(screen.getByRole('heading', { name: 'Where will you play?' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect(screen.getByRole('heading', { name: "Let's start with the game" })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Total spots' })).toHaveValue('16')
    expect(saveCounts()).toEqual([0, 0])
  })

  it('F18-2: a permitted save returns to Game Details', async () => {
    const user = userEvent.setup()
    fakePageApi(game())
    renderEditGame()

    await goToReview(user)
    await user.click(screen.getByRole('button', { name: /Save Changes/ }))

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(saveCounts()).toEqual([1, 1])
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
    expect(saveCounts()).toEqual([1, 1])
    expect([
      requestCount('GET /user-payment-methods'),
      requestCount('GET /host-publish-fees/me'),
    ]).toEqual([0, 0])
  })
})

describe('Edit Game when only the payment details fail', () => {
  it('F18-14: the page names what saved and what did not', async () => {
    const user = userEvent.setup()
    fakePaymentDetailsFailingOnce()

    await saveNewVenmoDetails(user)

    expect(await screen.findByText(PARTLY_SAVED)).toBeInTheDocument()
  })

  it('F18-14: the entered payment details are kept', async () => {
    const user = userEvent.setup()
    fakePaymentDetailsFailingOnce()
    await saveNewVenmoDetails(user)
    await screen.findByText(PARTLY_SAVED)

    await user.click(screen.getByRole('button', { name: 'Back' }))

    expect(screen.getByRole('textbox', { name: 'Venmo details' })).toHaveValue('@new-host')
  })

  it('F18-14: a retry sends only the payment details', async () => {
    const user = userEvent.setup()
    fakePaymentDetailsFailingOnce()
    await saveNewVenmoDetails(user)
    await screen.findByText(PARTLY_SAVED)

    await user.click(screen.getByRole('button', { name: /Save Changes/ }))
    await screen.findByRole('heading', { name: 'Game Details' })

    expect(saveCounts()).toEqual([1, 2])
    expect(sentBody(SAVE_DETAILS).payment_methods_snapshot).toEqual([
      { type: 'venmo', value: '@new-host' },
    ])
  })

  it('F18-14: the edit is reported complete only after both parts save', async () => {
    const user = userEvent.setup()
    fakePaymentDetailsFailingOnce()
    await saveNewVenmoDetails(user)

    // The first save stops at the partly-saved notice, not Game Details.
    expect(await screen.findByText(PARTLY_SAVED)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Save Changes/ }))

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
  })
})

describe('Edit Game when the game update fails', () => {
  it('F18-15: the entered values are kept and the unsaved part is named', async () => {
    const user = userEvent.setup()
    await saveRefusedCapacity(user)

    expect(await screen.findByText(
      'Your game changes were not saved. Capacity can only be increased after players have joined.',
    )).toBeInTheDocument()
    for (let step = 0; step < 3; step += 1) {
      await user.click(screen.getByRole('button', { name: 'Back' }))
    }
    expect(screen.getByRole('combobox', { name: 'Total spots' })).toHaveValue('14')
  })

  it('F18-15: no complete success is shown and the payment details are not sent', async () => {
    const user = userEvent.setup()
    await saveRefusedCapacity(user)
    await screen.findByText(/Your game changes were not saved\./)

    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
    expect(saveCounts()).toEqual([1, 0])
  })
})

// A published free game: it collects nothing and lists no payment method.
const FREE_GAME = { price_per_player_cents: 0, payment_collection_type: 'none' }
// What the server answers once the game is $5 and pays the host directly.
const PAID_GAME = { price_per_player_cents: 500, payment_collection_type: 'external_host', roster_counts: null }

function fakeFreeGame(saveGame) {
  fakePageApi(game(FREE_GAME), {
    'GET /community-game-details/games/{game_id}/host-edit': communityDetails({ payment_methods_snapshot: [] }),
    [SAVE_DETAILS]: communityDetails({ payment_methods_snapshot: [{ type: 'venmo', value: '@host' }] }),
    [SAVE_GAME]: saveGame,
  })
  renderEditGame()
}

// Set a $5 price, add Venmo details, and save.
async function makeFreeGamePaid(user) {
  const price = await screen.findByRole('textbox', { name: 'Price per player' })
  await user.clear(price)
  await user.type(price, '5')
  await user.click(screen.getByRole('button', { name: /^Next: Location/ }))
  await user.click(screen.getByRole('button', { name: /^Next: Notes/ }))
  const venmoDetails = screen.getByRole('textbox', { name: 'Venmo details' })
  await user.clear(venmoDetails)
  await user.type(venmoDetails, '@host')
  await user.click(screen.getByRole('button', { name: /^Next: Review/ }))
  await user.click(screen.getByRole('button', { name: /Save Changes/ }))
}

// The game update fails once with a server error, then saves on the retry.
function gameUpdateFailingOnce() {
  let gameSaves = 0
  return () => {
    gameSaves += 1
    if (gameSaves === 1) {
      return Promise.reject(new ApiRequestError('An unexpected error occurred.', { status: 500 }))
    }
    return game(PAID_GAME)
  }
}

const GAME_PART_UNSAVED = 'Your payment details were saved, but the game changes were not. An unexpected error occurred. Save again to retry the game changes.'

describe('Edit Game when a free game becomes paid', () => {
  it('F18-18: the payment methods save before the game update', async () => {
    const user = userEvent.setup()
    fakeFreeGame(game(PAID_GAME))

    await makeFreeGamePaid(user)
    await screen.findByRole('heading', { name: 'Game Details' })

    const saves = vi.mocked(apiRequest).mock.calls
      .filter(([, options]) => ['PATCH', 'PUT'].includes(options?.method))
      .map(([, options]) => options.method)
    expect(saves).toEqual(['PUT', 'PATCH'])
    expect(sentBody(SAVE_DETAILS).payment_methods_snapshot).toEqual([{ type: 'venmo', value: '@host' }])
  })

  it('F18-18: when the game update then fails, the page names the saved and unsaved parts', async () => {
    const user = userEvent.setup()
    fakeFreeGame(gameUpdateFailingOnce())

    await makeFreeGamePaid(user)

    expect(await screen.findByText(GAME_PART_UNSAVED)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Game Details' })).not.toBeInTheDocument()
  })

  it('F18-18: a retry then sends only the game update', async () => {
    const user = userEvent.setup()
    fakeFreeGame(gameUpdateFailingOnce())
    await makeFreeGamePaid(user)
    await screen.findByText(GAME_PART_UNSAVED)

    await user.click(screen.getByRole('button', { name: /Save Changes/ }))
    await screen.findByRole('heading', { name: 'Game Details' })

    expect(saveCounts()).toEqual([2, 1])
  })
})
