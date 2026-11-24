import { act, fireEvent, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { loadBrowseGamesPage } from '../../../src/pages/browse-games/browseGamesApi.js'
import { addDays, card, cards, cardLink, cardTitles, deferred, linkDate, page, renderBrowse, selectedDateButton, TODAY, waitForCards } from './browseTestKit.jsx'

vi.mock('../../../src/pages/browse-games/browseGamesApi.js', () => ({ loadBrowseGamesPage: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))

const ONE_MINUTE = 60_000

function setVisibility(state) {
  Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => state })
  document.dispatchEvent(new Event('visibilitychange'))
}

async function waitOneMinute() {
  await act(async () => { vi.advanceTimersByTime(ONE_MINUTE) })
}

async function returnToPage() {
  await act(async () => { fireEvent.blur(window); fireEvent.focus(window) })
}

beforeEach(() => { vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] }) })
afterEach(() => { delete document.visibilityState })

async function openExpandedList() {
  const first = cards(40, 'Field')
  const last = card({ display_title: 'Field 41', starts_at: '2026-06-15T23:50:00Z', ends_at: '2026-06-16T00:50:00Z' })
  const totals = [{ group_key: '18:00', total_games: 41 }]
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: first, hasMore: true, nextCursor: 'old-cursor', timeGroups: totals }))
    .mockResolvedValueOnce(page({ games: [last], timeGroups: totals }))
  const view = renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  await userEvent.setup().click(screen.getByRole('button', { name: 'Load More' }))
  await screen.findByRole('heading', { name: 'Field 41' })
  return { ...view, first, last, totals }
}

it("F15-7: a card disappears when the refreshed result reaches its cutoff", async () => {
  const game = card({ display_title: 'Closing Field' })
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: [game] })).mockResolvedValueOnce(page())
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  await waitOneMinute()
  expect(await screen.findByRole('heading', { name: 'No games found' })).toBeInTheDocument()
  expect(cardTitles()).toEqual([])
})

it("F15-29: a visible page refreshes once each minute", async () => {
  loadBrowseGamesPage.mockResolvedValue(page({ games: [card()] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  await act(async () => { vi.advanceTimersByTime(59_999) })
  expect(loadBrowseGamesPage).toHaveBeenCalledTimes(1)
  await act(async () => { vi.advanceTimersByTime(1) })
  expect(loadBrowseGamesPage).toHaveBeenCalledTimes(2)
  await waitOneMinute()
  expect(loadBrowseGamesPage).toHaveBeenCalledTimes(3)
})

it("F15-29: returning to a visible page refreshes once", async () => {
  loadBrowseGamesPage.mockResolvedValue(page({ games: [card()] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  await returnToPage()
  fireEvent.focus(window)
  expect(loadBrowseGamesPage).toHaveBeenCalledTimes(2)
  await returnToPage()
  expect(loadBrowseGamesPage).toHaveBeenCalledTimes(3)
})

it("F15-29: returning from a hidden tab refreshes once when visible", async () => {
  loadBrowseGamesPage.mockResolvedValue(page({ games: [card()] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  setVisibility('hidden')
  await act(async () => setVisibility('visible'))
  fireEvent.focus(window)
  expect(loadBrowseGamesPage).toHaveBeenCalledTimes(2)
})

it("F15-29: focus before visibility starts only one refresh on return", async () => {
  loadBrowseGamesPage.mockResolvedValue(page({ games: [card()] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  setVisibility('hidden')
  fireEvent.focus(window)
  expect(loadBrowseGamesPage).toHaveBeenCalledTimes(1)
  await act(async () => setVisibility('visible'))
  fireEvent.focus(window)
  expect(loadBrowseGamesPage).toHaveBeenCalledTimes(2)
})

it("F15-29: a refresh shows the current spot count", async () => {
  const game = card({ display_title: 'Field A', occupied: 3 })
  const updated = { ...game, participant_count: 7, availability: { status: 'open', occupied_spots: 7, total_spots: 14, spots_remaining: 7 } }
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: [game] })).mockResolvedValueOnce(page({ games: [updated] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  await waitOneMinute()
  expect(within(cardLink('Field A')).getByText('7/14')).toBeInTheDocument()
})

it("F15-29: a refresh removes a game that is no longer available", async () => {
  const kept = card({ display_title: 'Kept Field' })
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: [kept, card({ display_title: 'Hidden Field' })] }))
    .mockResolvedValueOnce(page({ games: [kept] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  await waitOneMinute()
  expect(cardTitles()).toEqual(['Kept Field'])
})

it("F15-29: a hidden tab does not start interval refreshes", async () => {
  loadBrowseGamesPage.mockResolvedValue(page({ games: [card()] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  setVisibility('hidden')
  await waitOneMinute()
  expect(loadBrowseGamesPage).toHaveBeenCalledTimes(1)
})

it("F15-30: an expanded list remains visible while refresh is pending", async () => {
  const { first, last } = await openExpandedList()
  const refresh = deferred()
  loadBrowseGamesPage.mockReturnValueOnce(refresh.promise)
  await returnToPage()
  expect(cardTitles()).toEqual([...first, last].map((game) => game.display_title))
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
  await act(async () => refresh.resolve(page({ games: first })))
})

it("F15-30: a successful refresh replaces the expanded list with the first batch", async () => {
  const { first, totals } = await openExpandedList()
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: first, hasMore: true, nextCursor: 'new-cursor', timeGroups: totals }))
  await returnToPage()
  expect(cardTitles()).toEqual(first.map((game) => game.display_title))
})

it("F15-30: a successful refresh resets the Load More cursor", async () => {
  const { first, last, totals } = await openExpandedList()
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: first, hasMore: true, nextCursor: 'new-cursor', timeGroups: totals }))
    .mockResolvedValueOnce(page({ games: [last], timeGroups: totals }))
  await returnToPage()
  await userEvent.setup().click(screen.getByRole('button', { name: 'Load More' }))
  await screen.findByRole('heading', { name: 'Field 41' })
  expect(loadBrowseGamesPage).toHaveBeenLastCalledWith(expect.objectContaining({ cursor: 'new-cursor', startsOn: TODAY }))
})

it("F15-31: a failed refresh preserves cards and working pagination without a full-page error", async () => {
  const first = cards(40, 'Field')
  const last = card({ display_title: 'Field 41', starts_at: '2026-06-15T23:50:00Z', ends_at: '2026-06-16T00:50:00Z' })
  const totals = [{ group_key: '18:00', total_games: 41 }]
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: first, hasMore: true, nextCursor: 'retained-cursor', timeGroups: totals }))
    .mockRejectedValueOnce(new Error('Server unavailable'))
    .mockResolvedValueOnce(page({ games: [last], timeGroups: totals }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  await waitOneMinute()
  expect(cardTitles()).toEqual(first.map((game) => game.display_title))
  expect(screen.queryByRole('heading', { name: 'Could not load games' })).not.toBeInTheDocument()
  await userEvent.setup().click(screen.getByRole('button', { name: 'Load More' }))
  await screen.findByRole('heading', { name: 'Field 41' })
  expect(loadBrowseGamesPage).toHaveBeenLastCalledWith(expect.objectContaining({ cursor: 'retained-cursor' }))
})

it("F15-31: the next successful refresh recovers after a failed refresh", async () => {
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: [card({ display_title: 'Original Field' })] }))
    .mockRejectedValueOnce(new Error('Server unavailable'))
    .mockResolvedValueOnce(page({ games: [card({ display_title: 'Updated Field' })] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  await waitOneMinute()
  await waitOneMinute()
  expect(cardTitles()).toEqual(['Updated Field'])
})

it("F15-34: expired holds reduce the filled count on refresh", async () => {
  const game = card({ display_title: 'Field A', occupied: 14 })
  const expired = { ...game, participant_count: 13, availability: { status: 'open', occupied_spots: 13, total_spots: 14, spots_remaining: 1 } }
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: [game] })).mockResolvedValueOnce(page({ games: [expired] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  expect(within(cardLink('Field A')).getByText('Full')).toBeInTheDocument()
  await waitOneMinute()
  expect(within(cardLink('Field A')).getByText('13/14')).toBeInTheDocument()
})

it("F15-34: expired holds remove Full when a spot opens", async () => {
  const game = card({ display_title: 'Field A', occupied: 14 })
  const expired = { ...game, participant_count: 13, availability: { status: 'open', occupied_spots: 13, total_spots: 14, spots_remaining: 1 } }
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: [game] })).mockResolvedValueOnce(page({ games: [expired] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  expect(within(cardLink('Field A')).getByText('Full')).toBeInTheDocument()
  await waitOneMinute()
  expect(within(cardLink('Field A')).queryByText('Full')).not.toBeInTheDocument()
})

it("F15-21: market midnight moves the fourteen-date window", async () => {
  const tomorrow = addDays(TODAY, 1)
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: [card()] }))
    .mockResolvedValueOnce(page({ today: tomorrow, date: tomorrow, games: [card({ date: tomorrow, display_title: 'Tomorrow Field' })] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  await waitOneMinute()
  await screen.findByRole('heading', { name: 'Tomorrow Field' })

  expect(screen.getAllByRole('button', { name: /^Browse games on/ }).map((button) => button.textContent)).toEqual(['TUEJun16', 'WEDJun17', 'THUJun18', 'FRIJun19', 'SATJun20', 'SUNJun21', 'MONJun22'])
  await userEvent.setup().click(screen.getByRole('button', { name: 'Next week' }))
  expect(screen.getAllByRole('button', { name: /^Browse games on/ }).map((button) => button.textContent)).toEqual(['TUEJun23', 'WEDJun24', 'THUJun25', 'FRIJun26', 'SATJun27', 'SUNJun28', 'MONJun29'])
})

it("F15-21: market midnight corrects the old selected date by replacing history", async () => {
  const tomorrow = addDays(TODAY, 1)
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: [card()] }))
    .mockResolvedValueOnce(page({ today: tomorrow, date: tomorrow, games: [card({ date: tomorrow, display_title: 'Tomorrow Field' })] }))
  const { router } = renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  await waitOneMinute()
  await screen.findByRole('heading', { name: 'Tomorrow Field' })

  expect(linkDate(router)).toBe(tomorrow)
  expect(router.state.historyAction).toBe('REPLACE')
  expect(selectedDateButton()).toHaveAccessibleName('Browse games on TUE Jun 16')
})

it("F15-27: a late first-page result cannot replace a newer date", async () => {
  const user = userEvent.setup()
  const tuesday = deferred()
  const wednesday = deferred()
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: [card({ display_title: 'Today Field' })] }))
    .mockReturnValueOnce(tuesday.promise).mockReturnValueOnce(wednesday.promise)
  const { router } = renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  await user.click(screen.getByRole('button', { name: 'Browse games on TUE Jun 16' }))
  await act(async () => router.navigate('/games/browse?date=2026-06-17'))
  await act(async () => wednesday.resolve(page({ date: '2026-06-17', games: [card({ date: '2026-06-17', display_title: 'Wednesday Field' })] })))
  await act(async () => tuesday.resolve(page({ date: '2026-06-16', games: [card({ date: '2026-06-16', display_title: 'Tuesday Field' })] })))
  expect(cardTitles()).toEqual(['Wednesday Field'])
  expect(selectedDateButton()).toHaveAccessibleName('Browse games on WED Jun 17')
})

it("F15-27: a late Load More result cannot append after a date change", async () => {
  const user = userEvent.setup()
  const more = deferred()
  const first = cards(40, 'Old Field')
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: first, hasMore: true, nextCursor: 'old-cursor', timeGroups: [{ group_key: '18:00', total_games: 41 }] }))
    .mockReturnValueOnce(more.promise)
  const { router } = renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  await user.click(screen.getByRole('button', { name: 'Load More' }))

  loadBrowseGamesPage.mockResolvedValueOnce(page({ date: '2026-06-16', games: [card({ date: '2026-06-16', display_title: 'Tuesday Field' })] }))
  await act(async () => router.navigate('/games/browse?date=2026-06-16'))
  await screen.findByRole('heading', { name: 'Tuesday Field' })
  await act(async () => more.resolve(page({ games: [card({ display_title: 'Stale Field', starts_at: '2026-06-15T23:50:00Z', ends_at: '2026-06-16T00:50:00Z' })], timeGroups: [{ group_key: '18:00', total_games: 41 }] })))
  expect(cardTitles()).toEqual(['Tuesday Field'])
})

it("F15-28: a late Load More result cannot append after refresh replacement", async () => {
  const user = userEvent.setup()
  const more = deferred()
  const first = cards(40, 'Old Field')
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: first, hasMore: true, nextCursor: 'old-cursor', timeGroups: [{ group_key: '18:00', total_games: 41 }] }))
    .mockReturnValueOnce(more.promise)
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  await user.click(screen.getByRole('button', { name: 'Load More' }))

  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: [card({ display_title: 'Fresh Field' })] }))
  await returnToPage()
  await screen.findByRole('heading', { name: 'Fresh Field' })
  await act(async () => more.resolve(page({ games: [card({ display_title: 'Stale Field', starts_at: '2026-06-15T23:50:00Z', ends_at: '2026-06-16T00:50:00Z' })], timeGroups: [{ group_key: '18:00', total_games: 41 }] })))
  expect(cardTitles()).toEqual(['Fresh Field'])
})
