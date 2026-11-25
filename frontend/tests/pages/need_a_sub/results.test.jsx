import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError } from '../../../src/lib/apiClient.js'
import {
  CARDS, NOW, TODAY, TOMORROW, card, cardPage, cardRequests, cardVenues, deferred, fakeApi, findCards, position,
  renderNeedASub, signedIn, signedOut,
} from './needASubTestKit.jsx'

vi.mock('../../../src/lib/apiClient.js', async (importOriginal) => ({
  ...(await importOriginal()),
  apiRequest: vi.fn(),
}))
vi.mock('../../../src/hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))
vi.mock('../../../src/context/authProviderHelpers.js', () => ({
  waitForCurrentFirebaseUser: vi.fn(),
}))

// The server's generic answer for an unexpected failure.
const serverError = () => new ApiRequestError('An unexpected error occurred.', { status: 500 })
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(NOW))
})

afterEach(() => {
  vi.useRealTimers()
  delete document.visibilityState
})

function dateButton(day) {
  return screen.getByRole('button', { name: `Need a Sub posts on ${day}` })
}

function requestParams(path) {
  const params = new URL(path, 'http://test.local').searchParams
  return { cursor: params.get('cursor'), startsOn: params.get('starts_on'), view: params.get('view') }
}

function batch(prefix, count) {
  return Array.from({ length: count }, (_, index) => card({ location_name: `${prefix} ${index + 1}` }))
}

function setVisibility(state) {
  Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => state })
  document.dispatchEvent(new Event('visibilitychange'))
}

describe('Need a Sub results', () => {
  // Forty posts with a further batch of one, named so no name contains another.
  const FIRST_BATCH = Array.from({ length: 40 }, (_, index) => `Field ${String(index + 1).padStart(2, '0')}`)
  const LAST_POST = 'Field 41'

  function fortyPostsAndOneMore() {
    signedOut()
    fakeApi({
      [CARDS]: (path) => (requestParams(path).cursor === 'cursor-2'
        ? cardPage({ posts: [card({ location_name: LAST_POST })] })
        : cardPage({
          posts: FIRST_BATCH.map((name) => card({ location_name: name })),
          hasMore: true,
          nextCursor: 'cursor-2',
        })),
    })
    renderNeedASub()
  }

  it('F20-8: Load More appends later posts in order', async () => {
    const user = userEvent.setup()
    fortyPostsAndOneMore()
    expect(await findCards()).toHaveLength(40)

    await user.click(screen.getByRole('button', { name: 'Load More' }))

    expect(await screen.findByText(LAST_POST)).toBeInTheDocument()
    expect(cardVenues([...FIRST_BATCH, LAST_POST])).toEqual([...FIRST_BATCH, LAST_POST])
    expect(cardRequests().at(-1)).toEqual({ cursor: 'cursor-2', signedIn: false, startsOn: TODAY, view: 'all' })
  })

  it('F20-8: Load More disappears when no further batch remains', async () => {
    const user = userEvent.setup()
    fortyPostsAndOneMore()
    await findCards()

    await user.click(screen.getByRole('button', { name: 'Load More' }))

    await screen.findByText(LAST_POST)
    expect(screen.queryByRole('button', { name: 'Load More' })).not.toBeInTheDocument()
  })

  it('F20-9: a date with no eligible posts shows the empty message instead of cards or Load More', async () => {
    signedOut()
    fakeApi({ [CARDS]: cardPage() })
    renderNeedASub()

    expect(await screen.findByText('No Need a Sub posts yet')).toBeInTheDocument()
    expect(screen.queryAllByRole('button', { name: /^Need \d+ Subs?/ })).toHaveLength(0)
    expect(screen.queryByRole('button', { name: 'Load More' })).not.toBeInTheDocument()
  })

  it('F20-9: My Posts with no posts on that date shows its own empty message', async () => {
    const user = userEvent.setup()
    signedIn()
    fakeApi({
      [CARDS]: (path) => (requestParams(path).view === 'mine'
        ? cardPage()
        : cardPage({ posts: [card({ location_name: 'Everyone Field' })] })),
    })
    renderNeedASub()
    await screen.findByText('Everyone Field')

    await user.click(screen.getByRole('tab', { name: 'My Posts' }))

    expect(await screen.findByText('No posts created yet')).toBeInTheDocument()
    expect(screen.queryByText('Everyone Field')).not.toBeInTheDocument()
  })

  it('F20-10: a loading skeleton shows while the first batch loads', async () => {
    signedOut()
    const firstBatch = deferred()
    fakeApi({ [CARDS]: () => firstBatch.promise })
    renderNeedASub()

    expect(await screen.findByRole('status')).toHaveTextContent('Loading Need a Sub posts')
    await act(async () => firstBatch.resolve(cardPage({ posts: [card({ location_name: 'North Park' })] })))
    expect(await screen.findByText('North Park')).toBeInTheDocument()
    expect(screen.queryByText('Loading Need a Sub posts')).not.toBeInTheDocument()
  })

  it('F20-10: a failed first request shows an error alert', async () => {
    signedOut()
    fakeApi({ [CARDS]: serverError() })
    renderNeedASub()

    expect(await screen.findByRole('alert')).toHaveTextContent('An unexpected error occurred.')
    expect(screen.getByText('Could not load posts')).toBeInTheDocument()
    expect(screen.queryByText('No Need a Sub posts yet')).not.toBeInTheDocument()
  })

  it('F20-10: no stale cards from the previous date remain after a failed request', async () => {
    const user = userEvent.setup()
    signedOut()
    fakeApi({
      [CARDS]: (path) => (requestParams(path).startsOn === TOMORROW
        ? serverError()
        : cardPage({ posts: [card({ location_name: 'Today Field' })] })),
    })
    renderNeedASub()
    await screen.findByText('Today Field')

    await user.click(dateButton('Tue Jun 16'))

    expect(await screen.findByRole('alert')).toHaveTextContent('An unexpected error occurred.')
    expect(screen.queryByText('Today Field')).not.toBeInTheDocument()
  })

  // Two posts with a further batch; the first Load More fails and the next succeeds.
  function loadMoreFailsOnce() {
    signedOut()
    let loadMoreAttempts = 0
    fakeApi({
      [CARDS]: (path) => {
        if (requestParams(path).cursor !== 'cursor-2') {
          return cardPage({ posts: batch('First', 2), hasMore: true, nextCursor: 'cursor-2' })
        }
        loadMoreAttempts += 1
        return loadMoreAttempts === 1 ? serverError() : cardPage({ posts: batch('Second', 1) })
      },
    })
    renderNeedASub()
  }

  it('F20-11: a failed Load More keeps the existing cards', async () => {
    const user = userEvent.setup()
    loadMoreFailsOnce()
    await screen.findByText('First 2')

    await user.click(screen.getByRole('button', { name: 'Load More' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('An unexpected error occurred.')
    expect(await findCards()).toHaveLength(2)
    expect(screen.getByRole('button', { name: 'Load More' })).toBeEnabled()
  })

  it('F20-11: a later successful Load More appends the next batch', async () => {
    const user = userEvent.setup()
    loadMoreFailsOnce()
    await screen.findByText('First 2')
    await user.click(screen.getByRole('button', { name: 'Load More' }))
    await screen.findByRole('alert')

    await user.click(screen.getByRole('button', { name: 'Load More' }))

    expect(await screen.findByText('Second 1')).toBeInTheDocument()
    expect(await findCards()).toHaveLength(3)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('F20-12: a late response for the previous date cannot replace the current results', async () => {
    const user = userEvent.setup()
    signedOut()
    const lateToday = deferred()
    fakeApi({
      [CARDS]: (path) => (requestParams(path).startsOn === TODAY
        ? lateToday.promise
        : cardPage({ posts: [card({ location_name: 'Tomorrow Field' })] })),
    })
    renderNeedASub()
    await waitFor(() => expect(cardRequests()).toHaveLength(1))

    await user.click(dateButton('Tue Jun 16'))
    await screen.findByText('Tomorrow Field')
    await act(async () => lateToday.resolve(cardPage({ posts: [card({ location_name: 'Late Today Field' })] })))

    expect(screen.getByText('Tomorrow Field')).toBeInTheDocument()
    expect(screen.queryByText('Late Today Field')).not.toBeInTheDocument()
  })

  it('F20-12: a late response for the previous tab cannot replace the current results', async () => {
    const user = userEvent.setup()
    signedIn()
    const lateAll = deferred()
    fakeApi({
      [CARDS]: (path) => (requestParams(path).view === 'all'
        ? lateAll.promise
        : cardPage({ posts: [card({ location_name: 'My Field' })] })),
    })
    renderNeedASub()
    await waitFor(() => expect(cardRequests()).toHaveLength(1))

    await user.click(screen.getByRole('tab', { name: 'My Posts' }))
    await screen.findByText('My Field')
    await act(async () => lateAll.resolve(cardPage({ posts: [card({ location_name: 'Everyone Field' })] })))

    expect(screen.getByText('My Field')).toBeInTheDocument()
    expect(screen.queryByText('Everyone Field')).not.toBeInTheDocument()
  })

  it('F20-12: a late Load More response cannot append to another date\'s results', async () => {
    const user = userEvent.setup()
    signedOut()
    const lateMore = deferred()
    fakeApi({
      [CARDS]: (path) => {
        const { cursor, startsOn } = requestParams(path)
        if (cursor) return lateMore.promise
        return startsOn === TODAY
          ? cardPage({ posts: [card({ location_name: 'Today Field' })], hasMore: true, nextCursor: 'cursor-2' })
          : cardPage({ posts: [card({ location_name: 'Tomorrow Field' })] })
      },
    })
    renderNeedASub()
    await screen.findByText('Today Field')

    await user.click(screen.getByRole('button', { name: 'Load More' }))
    await user.click(dateButton('Tue Jun 16'))
    await screen.findByText('Tomorrow Field')
    await act(async () => lateMore.resolve(cardPage({ posts: [card({ location_name: 'Late Today Field' })] })))

    expect(await findCards()).toHaveLength(1)
    expect(screen.queryByText('Late Today Field')).not.toBeInTheDocument()
  })

  // The list first shows two posts; later the first is cancelled and the
  // second gains a confirmed sub.
  function postsThatChangeWhileAway() {
    signedOut()
    let answer = cardPage({
      posts: [
        card({ location_name: 'Cancelled Field' }),
        card({ location_name: 'Filling Field', positions: [position({ spots_needed: 2 })] }),
      ],
    })
    fakeApi({ [CARDS]: () => answer })
    renderNeedASub()
    return () => {
      answer = cardPage({
        posts: [card({ location_name: 'Filling Field', positions: [position({ spots_needed: 2, confirmed_count: 1 })] })],
      })
    }
  }

  async function expectCurrentPostsAndCounts() {
    await waitFor(() => expect(screen.queryByText('Cancelled Field')).not.toBeInTheDocument())
    expect(screen.getByText('Filling Field')).toBeInTheDocument()
    expect(screen.getByText('1/2 spots')).toBeInTheDocument()
    expect(cardRequests()).toHaveLength(2)
  }

  it('F20-13: regaining window focus refreshes the first batch with current posts and counts', async () => {
    const changeWhileAway = postsThatChangeWhileAway()
    await screen.findByText('Cancelled Field')
    changeWhileAway()

    await act(async () => {
      fireEvent.blur(window)
      fireEvent.focus(window)
    })

    await expectCurrentPostsAndCounts()
  })

  it('F20-13: becoming visible again refreshes the first batch with current posts and counts', async () => {
    const changeWhileAway = postsThatChangeWhileAway()
    await screen.findByText('Cancelled Field')
    changeWhileAway()

    await act(async () => {
      setVisibility('hidden')
      setVisibility('visible')
    })

    await expectCurrentPostsAndCounts()
  })
})
