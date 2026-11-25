import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../../../src/hooks/useAuth.js'
import { apiRequest, ApiRequestError } from '../../../src/lib/apiClient.js'
import { MyGamesPage } from '../../../src/pages/my-games/index.js'
import { RequireAppUser } from '../../../src/routes/RouteGuards.jsx'
import {
  fakePageApi, GAMES, gameItem, NEED_A_SUB, OTHER_PLAYER_ID, page, PLAYER_ID, postItem, renderMyGames,
  requestsTo, signIn,
} from './myGamesTestKit.jsx'

vi.mock('../../../src/lib/apiClient.js', async (importOriginal) => ({
  ...(await importOriginal()),
  apiRequest: vi.fn(),
}))
vi.mock('../../../src/hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))

const serverFailure = () => new ApiRequestError('An unexpected error occurred.', { status: 500 })

function deferred() {
  let resolve
  const promise = new Promise((done) => { resolve = done })
  return { promise, resolve }
}

beforeEach(() => signIn())

// The first load fails; every later load returns an empty page.
function fakeFailedFirstLoad() {
  let attempts = 0
  fakePageApi({
    [GAMES]: () => {
      attempts += 1
      return attempts === 1 ? serverFailure() : page()
    },
  })
}

// The first batch loads; the first Load More fails and a retry returns the
// next batch, which repeats nothing from the first.
function fakeFailedLoadMore() {
  let laterAttempts = 0
  fakePageApi({
    [GAMES]: ({ cursor }) => {
      if (!cursor) return page([gameItem({ venue: 'First Field' })], { nextCursor: 'cursor-2' })
      laterAttempts += 1
      return laterAttempts === 1
        ? serverFailure()
        : page([gameItem({ venue: 'Second Field', startsAt: '2030-06-16T12:00:00Z' })])
    },
  })
}

describe('My Games loading and recovery', () => {
  it('F19-9: a late answer for another view does not replace the active view', async () => {
    const user = userEvent.setup()
    const upcomingAnswer = deferred()
    fakePageApi({
      [GAMES]: ({ view }) => (view === 'upcoming'
        ? upcomingAnswer.promise
        : page([gameItem({ venue: 'Past Field', bucket: 'history', startsAt: '2030-05-01T12:00:00Z' })])),
    })
    renderMyGames()

    await user.click(await screen.findByRole('tab', { name: 'History' }))
    expect(await screen.findByRole('heading', { name: 'Past Field' })).toBeInTheDocument()
    await act(async () => upcomingAnswer.resolve(page([gameItem({ venue: 'Late Field' })])))

    expect(screen.getByRole('heading', { name: 'Past Field' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Late Field' })).not.toBeInTheDocument()
  })

  it('F19-9: a view shows its own loading state while it loads', async () => {
    const user = userEvent.setup()
    fakePageApi({
      [GAMES]: ({ view }) => (view === 'upcoming'
        ? deferred().promise
        : page([gameItem({ venue: 'Past Field', bucket: 'history', startsAt: '2030-05-01T12:00:00Z' })])),
    })
    renderMyGames()
    expect(await screen.findByRole('status')).toHaveTextContent('Loading your games')

    await user.click(screen.getByRole('tab', { name: 'History' }))
    expect(await screen.findByRole('heading', { name: 'Past Field' })).toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Upcoming' }))
    expect(screen.getByRole('status')).toHaveTextContent('Loading your games')
    expect(screen.queryByRole('heading', { name: 'Past Field' })).not.toBeInTheDocument()
  })

  it('F19-15: returning to a view shows the cards it already loaded, and Load More continues', async () => {
    const user = userEvent.setup()
    fakePageApi({
      [GAMES]: ({ view, cursor }) => {
        if (view === 'history') return page()
        if (cursor === 'cursor-2') {
          return page([gameItem({ venue: 'Second Field', startsAt: '2030-06-16T12:00:00Z' })], { nextCursor: 'cursor-3' })
        }
        if (cursor === 'cursor-3') return page([gameItem({ venue: 'Third Field', startsAt: '2030-06-17T12:00:00Z' })])
        return page([gameItem({ venue: 'First Field', startsAt: '2030-06-15T12:00:00Z' })], { nextCursor: 'cursor-2' })
      },
    })
    renderMyGames()
    await screen.findByRole('heading', { name: 'First Field' })
    await user.click(screen.getByRole('button', { name: 'Load More' }))
    await screen.findByRole('heading', { name: 'Second Field' })

    await user.click(screen.getByRole('tab', { name: 'History' }))
    await screen.findByText('No game history yet')
    await user.click(screen.getByRole('tab', { name: 'Upcoming' }))

    expect(screen.getAllByRole('heading', { level: 3 }).map((heading) => heading.textContent))
      .toEqual(['First Field', 'Second Field'])
    await user.click(screen.getByRole('button', { name: 'Load More' }))
    expect(await screen.findByRole('heading', { name: 'Third Field' })).toBeInTheDocument()
    expect(requestsTo(GAMES).filter((request) => request.view === 'upcoming').map((request) => request.cursor))
      .toEqual([null, 'cursor-2', 'cursor-3'])
  })

  it('F19-10: a failed first load shows a view-specific error', async () => {
    const user = userEvent.setup()
    fakeFailedFirstLoad()
    renderMyGames()

    expect(await screen.findByText('Could not load My Games')).toBeInTheDocument()
    expect(screen.getByText('An unexpected error occurred.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
    await user.click(screen.getByRole('tab', { name: 'History' }))
    expect(await screen.findByText('No game history yet')).toBeInTheDocument()
    expect(screen.queryByText('Could not load My Games')).not.toBeInTheDocument()
  })

  it('F19-10: Retry shows the view\'s items or empty state', async () => {
    const user = userEvent.setup()
    fakeFailedFirstLoad()
    renderMyGames()
    await screen.findByText('Could not load My Games')

    await user.click(screen.getByRole('button', { name: 'Retry' }))

    expect(await screen.findByText('No upcoming games yet')).toBeInTheDocument()
    expect(screen.queryByText('Could not load My Games')).not.toBeInTheDocument()
  })

  it('F19-11: a failed Load More keeps the existing cards visible', async () => {
    const user = userEvent.setup()
    fakeFailedLoadMore()
    renderMyGames()
    await screen.findByRole('heading', { name: 'First Field' })

    await user.click(screen.getByRole('button', { name: 'Load More' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('An unexpected error occurred.')
    expect(screen.getByRole('heading', { name: 'First Field' })).toBeInTheDocument()
  })

  it('F19-11: Retry adds the next batch without duplicates', async () => {
    const user = userEvent.setup()
    fakeFailedLoadMore()
    renderMyGames()
    await screen.findByRole('heading', { name: 'First Field' })
    await user.click(screen.getByRole('button', { name: 'Load More' }))
    await screen.findByRole('alert')

    await user.click(screen.getByRole('button', { name: 'Retry' }))

    expect(await screen.findByRole('heading', { name: 'Second Field' })).toBeInTheDocument()
    expect(screen.getAllByRole('heading', { level: 3 }).map((heading) => heading.textContent))
      .toEqual(['First Field', 'Second Field'])
    expect(requestsTo(GAMES).map((request) => request.cursor)).toEqual([null, 'cursor-2', 'cursor-2'])
  })

  it('F19-12: a signed-out visitor is sent to sign in', async () => {
    vi.mocked(useAuth).mockReturnValue({ appUser: null, currentUser: null, isLoading: false })
    fakePageApi()
    // The app's own route: My Games sits behind the signed-in guard.
    const router = createMemoryRouter([
      { path: '/my-games', element: <RequireAppUser><MyGamesPage /></RequireAppUser> },
      { path: '/sign-in', element: <h1>Sign In</h1> },
    ], { initialEntries: ['/my-games'] })
    render(<RouterProvider router={router} />)

    expect(await screen.findByRole('heading', { name: 'Sign In' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/sign-in')
    expect(vi.mocked(apiRequest)).not.toHaveBeenCalled()
  })

  it('F19-12: switching accounts clears the previous account\'s cards', async () => {
    fakePageApi({
      [GAMES]: ({ options }) => (options.headers.Authorization === `Bearer token-${PLAYER_ID}`
        ? page([gameItem({ venue: 'First Account Field' })])
        : page([gameItem({ venue: 'Second Account Field' })])),
    })
    renderMyGames()
    await screen.findByRole('heading', { name: 'First Account Field' })

    signIn({ id: OTHER_PLAYER_ID })

    expect(await screen.findByRole('heading', { name: 'Second Account Field' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'First Account Field' })).not.toBeInTheDocument()
  })

  it('F19-12: a late answer for the previous account does not replace the next account\'s view', async () => {
    const firstAccountAnswer = deferred()
    fakePageApi({
      [GAMES]: ({ options }) => (options.headers.Authorization === `Bearer token-${PLAYER_ID}`
        ? firstAccountAnswer.promise
        : page([gameItem({ venue: 'Second Account Field' })])),
    })
    renderMyGames()
    await waitFor(() => expect(requestsTo(GAMES)).toHaveLength(1))

    signIn({ id: OTHER_PLAYER_ID })
    await screen.findByRole('heading', { name: 'Second Account Field' })
    await act(async () => firstAccountAnswer.resolve(page([gameItem({ venue: 'First Account Field' })])))

    expect(screen.getByRole('heading', { name: 'Second Account Field' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'First Account Field' })).not.toBeInTheDocument()
  })

  it('F19-13: a suspended player still sees their existing hosted and confirmed items', async () => {
    const user = userEvent.setup()
    signIn({ account_status: 'suspended' })
    fakePageApi({
      [GAMES]: page([
        gameItem({ venue: 'Hosted Field', isHost: true, game: { game_type: 'community' } }),
        gameItem({ venue: 'Joined Field', startsAt: '2030-06-16T23:00:00Z' }),
      ]),
      [NEED_A_SUB]: page([
        postItem({ location: 'Owned Post Field' }),
        postItem({ location: 'Confirmed Post Field', isOwner: false, startsAt: '2030-06-16T23:00:00Z' }),
      ]),
    })
    renderMyGames()

    const hostedCard = await screen.findByRole('link', { name: /Hosted Field/ })
    expect(within(hostedCard).getByText('Hosting')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Joined Field' })).toBeInTheDocument()
    await user.click(screen.getByRole('tab', { name: 'Need a Sub' }))
    expect(await screen.findByText('Owned Post Field')).toBeInTheDocument()
    expect(screen.getByText('Confirmed Post Field')).toBeInTheDocument()
  })
})
