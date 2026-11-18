import { act, fireEvent, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { loadBrowseGamesPage } from '../../../src/pages/browse-games/browseGamesApi.js'
import {
  addDays,
  card,
  cardTitles,
  deferred,
  linkDate,
  page,
  renderBrowse,
  selectedDateButton,
  TODAY,
  waitForCards,
} from './browseTestKit.jsx'

vi.mock('../../../src/pages/browse-games/browseGamesApi.js', () => ({
  loadBrowseGamesPage: vi.fn(),
}))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({
  default: () => null,
}))

const ONE_MINUTE = 60_000
const GAME_A_ID = '00000000-0000-4000-8000-00000000000a'

function setVisibility(state) {
  Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => state })
  document.dispatchEvent(new Event('visibilitychange'))
}

async function waitOneMinute() {
  await act(async () => {
    vi.advanceTimersByTime(ONE_MINUTE)
  })
}

async function returnToPage() {
  await act(async () => {
    fireEvent.focus(window)
  })
}

function spotsOn(title) {
  const link = screen.getByRole('heading', { level: 3, name: title }).closest('a')
  return within(link)
}

beforeEach(() => {
  // Only the refresh interval is faked; promises and clicks run normally.
  vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] })
})

afterEach(() => {
  delete document.visibilityState
})

describe('Browse keeps the list current', () => {
  it('F15-29: refreshes about once a minute and shows the current spot counts', async () => {
    loadBrowseGamesPage
      .mockResolvedValueOnce(page({ games: [card({ id: GAME_A_ID, display_title: 'Field A', occupied: 3 })] }))
      .mockResolvedValueOnce(page({ games: [card({ id: GAME_A_ID, display_title: 'Field A', occupied: 7 })] }))
    renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    await waitOneMinute()

    expect(await spotsOn('Field A').findByText('7/14')).toBeInTheDocument()
    expect(loadBrowseGamesPage).toHaveBeenCalledTimes(2)
    expect(loadBrowseGamesPage).toHaveBeenLastCalledWith(expect.objectContaining({ startsOn: TODAY }))
  })

  it('F15-29: a hidden tab does not refresh on the interval', async () => {
    loadBrowseGamesPage.mockResolvedValue(page({ games: [card()] }))
    renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    setVisibility('hidden')
    await waitOneMinute()

    expect(loadBrowseGamesPage).toHaveBeenCalledTimes(1)
  })

  it('F15-29: returning to the page refreshes it', async () => {
    loadBrowseGamesPage.mockResolvedValue(page({ games: [card()] }))
    renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    await act(async () => setVisibility('visible'))
    await returnToPage()

    expect(loadBrowseGamesPage).toHaveBeenCalledTimes(3)
  })

  it('F15-30: an expanded list stays visible while refreshing, then returns to the first batch', async () => {
    const user = userEvent.setup()
    const refresh = deferred()
    loadBrowseGamesPage
      .mockResolvedValueOnce(page({
        games: [card({ display_title: 'Field 1' }), card({ display_title: 'Field 2' })],
        hasMore: true,
        nextCursor: 'cursor-1',
      }))
      .mockResolvedValueOnce(page({ games: [card({ display_title: 'Field 3' })] }))
      .mockReturnValueOnce(refresh.promise)
    renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()
    await user.click(screen.getByRole('button', { name: 'Load More' }))
    await screen.findByRole('heading', { name: 'Field 3' })

    await returnToPage()

    expect(cardTitles()).toEqual(['Field 1', 'Field 2', 'Field 3'])
    expect(screen.queryByRole('status')).not.toBeInTheDocument()

    await act(async () => refresh.resolve(page({
      games: [card({ display_title: 'Field 1' }), card({ display_title: 'Field 2' })],
      hasMore: true,
      nextCursor: 'cursor-2',
    })))

    expect(cardTitles()).toEqual(['Field 1', 'Field 2'])
    expect(screen.getByRole('button', { name: 'Load More' })).toBeEnabled()
  })

  it('F15-31: a failed background refresh leaves the list and Load More in place', async () => {
    loadBrowseGamesPage
      .mockResolvedValueOnce(page({
        games: [card({ display_title: 'Field 1' })],
        hasMore: true,
        nextCursor: 'cursor-1',
      }))
      .mockRejectedValueOnce(new Error('Server unavailable'))
      .mockResolvedValueOnce(page({ games: [card({ display_title: 'Field 1 Updated' })] }))
    renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    await waitOneMinute()

    expect(cardTitles()).toEqual(['Field 1'])
    expect(screen.getByRole('button', { name: 'Load More' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Could not load games' })).not.toBeInTheDocument()

    await waitOneMinute()

    expect(await screen.findByRole('heading', { name: 'Field 1 Updated' })).toBeInTheDocument()
  })

  it('F15-34: when a hold expires on a full game, the next refresh drops the count and the Full badge', async () => {
    loadBrowseGamesPage
      .mockResolvedValueOnce(page({ games: [card({ id: GAME_A_ID, display_title: 'Field A', occupied: 14 })] }))
      .mockResolvedValueOnce(page({ games: [card({ id: GAME_A_ID, display_title: 'Field A', occupied: 13 })] }))
    renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()
    expect(spotsOn('Field A').getByText('Full')).toBeInTheDocument()

    await waitOneMinute()

    expect(await spotsOn('Field A').findByText('13/14')).toBeInTheDocument()
    expect(spotsOn('Field A').queryByText('Full')).not.toBeInTheDocument()
  })

  it('F15-21: after midnight in the market timezone, the next refresh moves the window and corrects the link', async () => {
    const tomorrow = addDays(TODAY, 1)
    loadBrowseGamesPage
      .mockResolvedValueOnce(page({ games: [card()] }))
      .mockResolvedValueOnce(page({ today: tomorrow, date: tomorrow, games: [card({ display_title: 'Tomorrow Field' })] }))
    const router = renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    await waitOneMinute()

    expect(await screen.findByRole('heading', { name: 'Tomorrow Field' })).toBeInTheDocument()
    expect(linkDate(router)).toBe(tomorrow)
    expect(router.state.historyAction).toBe('REPLACE')
    expect(selectedDateButton()).toHaveAccessibleName('Browse games on TUE Jun 16')
    expect(screen.getAllByRole('button', { name: /^Browse games on/ })[0])
      .toHaveAccessibleName('Browse games on TUE Jun 16')
  })

  it('F15-27: a late response for an earlier date choice cannot replace the newer date', async () => {
    const user = userEvent.setup()
    const tuesday = deferred()
    const wednesday = deferred()
    loadBrowseGamesPage
      .mockResolvedValueOnce(page({ games: [card({ display_title: 'Today Field' })] }))
      .mockReturnValueOnce(tuesday.promise)
      .mockReturnValueOnce(wednesday.promise)
    const router = renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    // The date strip is replaced by the loading view during a load, so the
    // second change arrives through the link, as with Back or a shared link.
    await user.click(screen.getByRole('button', { name: 'Browse games on TUE Jun 16' }))
    await act(async () => router.navigate('/games/browse?date=2026-06-17'))
    await act(async () => wednesday.resolve(
      page({ date: '2026-06-17', games: [card({ display_title: 'Wednesday Field' })] }),
    ))
    await act(async () => tuesday.resolve(
      page({ date: '2026-06-16', games: [card({ display_title: 'Tuesday Field' })] }),
    ))

    expect(cardTitles()).toEqual(['Wednesday Field'])
    expect(selectedDateButton()).toHaveAccessibleName('Browse games on WED Jun 17')
  })

  it('F15-28: a late Load More response cannot add cards after a refresh replaced the list', async () => {
    const user = userEvent.setup()
    const loadMore = deferred()
    loadBrowseGamesPage
      .mockResolvedValueOnce(page({
        games: [card({ display_title: 'Field 1' }), card({ display_title: 'Field 2' })],
        hasMore: true,
        nextCursor: 'cursor-1',
      }))
      .mockReturnValueOnce(loadMore.promise)
      .mockResolvedValueOnce(page({
        games: [card({ display_title: 'Fresh Field 1' }), card({ display_title: 'Fresh Field 2' })],
        hasMore: true,
        nextCursor: 'cursor-2',
      }))
    renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    await user.click(screen.getByRole('button', { name: 'Load More' }))
    await returnToPage()
    await screen.findByRole('heading', { name: 'Fresh Field 1' })
    await act(async () => loadMore.resolve(page({ games: [card({ display_title: 'Stale Field 3' })] })))

    expect(cardTitles()).toEqual(['Fresh Field 1', 'Fresh Field 2'])
  })
})
