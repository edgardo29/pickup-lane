import { act, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { loadBrowseGamesPage } from '../../../src/pages/browse-games/browseGamesApi.js'
import { addDays, card, cards, cardTitles, deferred, linkDate, page, renderBrowse, selectedDateButton, TODAY, waitForCards } from './browseTestKit.jsx'

vi.mock('../../../src/pages/browse-games/browseGamesApi.js', () => ({ loadBrowseGamesPage: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))

function requestedDates() {
  return loadBrowseGamesPage.mock.calls.map(([options]) => options.startsOn)
}

async function chooseTuesday() {
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Browse games on TUE Jun 16' }))
}

it("F15-2: opening Browse without a date loads today", async () => {
  loadBrowseGamesPage.mockResolvedValue(page({ games: [card({ display_title: 'Today Field' })] }))
  renderBrowse()
  expect(await waitForCards()).toEqual(['Today Field'])
  expect(requestedDates()).toEqual([undefined])
})

it("F15-2: opening Browse without a date replaces the link with today", async () => {
  loadBrowseGamesPage.mockResolvedValue(page({ games: [card()] }))
  const { router } = renderBrowse()
  await waitForCards()
  expect(linkDate(router)).toBe(TODAY)
  expect(router.state.historyAction).toBe('REPLACE')
  await act(async () => router.navigate(-1))
  expect(router.state.location.pathname).toBe('/')
})

it("F15-2: the initial loading state lasts until the first response", async () => {
  const response = deferred()
  loadBrowseGamesPage.mockReturnValueOnce(response.promise)
  renderBrowse()
  expect(await screen.findByRole('status')).toHaveTextContent('Loading games')
  await act(async () => response.resolve(page({ games: [card()] })))
  await waitForCards()
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
})

it("F15-3: a valid linked date selects that date and loads its games", async () => {
  const date = addDays(TODAY, 9)
  loadBrowseGamesPage.mockResolvedValue(page({ date, games: [card({ date, display_title: 'Later Field' })] }))
  renderBrowse(`/games/browse?date=${date}`)
  expect(await waitForCards()).toEqual(['Later Field'])
  expect(requestedDates()).toEqual([date])
  expect(selectedDateButton()).toHaveAccessibleName('Browse games on WED Jun 24')
})

it("F15-3: the visible set contains the linked date", async () => {
  const date = addDays(TODAY, 9)
  loadBrowseGamesPage.mockResolvedValue(page({ date, games: [card({ date })] }))
  renderBrowse(`/games/browse?date=${date}`)
  await waitForCards()
  expect(screen.getAllByRole('button', { name: /^Browse games on/ }).map((button) => button.textContent)).toEqual([
    'MONJun22', 'TUEJun23', 'WEDJun24', 'THUJun25', 'FRIJun26', 'SATJun27', 'SUNJun28',
  ])
})

it("F15-5: choosing a date adds a normal history entry", async () => {
  const next = deferred()
  loadBrowseGamesPage
    .mockResolvedValueOnce(page({ games: [card({ display_title: 'Today Field' })] }))
    .mockReturnValueOnce(next.promise)
  const { router } = renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  await chooseTuesday()

  expect(linkDate(router)).toBe('2026-06-16')
  expect(router.state.historyAction).toBe('PUSH')

  await act(async () => next.resolve(page({ date: '2026-06-16', games: [card({ date: '2026-06-16', display_title: 'Tuesday Field' })] })))
  await waitForCards()
})

it("F15-5: old cards clear while the selected date loads", async () => {
  const next = deferred()
  loadBrowseGamesPage
    .mockResolvedValueOnce(page({ games: [card({ display_title: 'Today Field' })] }))
    .mockReturnValueOnce(next.promise)
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  await chooseTuesday()

  expect(cardTitles()).toEqual([])
  expect(await screen.findByRole('status')).toHaveTextContent('Loading games')

  await act(async () => next.resolve(page({ date: '2026-06-16', games: [card({ date: '2026-06-16', display_title: 'Tuesday Field' })] })))
  await waitForCards()
})

it("F15-5: old pagination clears on changing date", async () => {
  const user = userEvent.setup()
  const next = deferred()
  loadBrowseGamesPage
    .mockResolvedValueOnce(page({ games: cards(40, 'Today'), hasMore: true, nextCursor: 'today-more', timeGroups: [{ group_key: '18:00', total_games: 60 }, { group_key: '19:00', total_games: 21 }] }))
    .mockResolvedValueOnce(page({ games: cards(40, 'Later', { minuteOffset: 40 }), hasMore: true, nextCursor: 'today-after-41', timeGroups: [{ group_key: '18:00', total_games: 60 }, { group_key: '19:00', total_games: 21 }] }))
    .mockReturnValueOnce(next.promise)
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  await user.click(screen.getByRole('button', { name: 'Load More' }))
  await screen.findByRole('heading', { name: 'Later 40' })
  expect(cardTitles()).toHaveLength(80)
  expect(screen.getByRole('button', { name: 'Load More' })).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Browse games on TUE Jun 16' }))
  expect(screen.queryByRole('button', { name: 'Load More' })).not.toBeInTheDocument()
  await act(async () => next.resolve(page({ date: '2026-06-16', games: [card({ date: '2026-06-16' })] })))
  await waitForCards()
  expect(screen.queryByRole('button', { name: 'Load More' })).not.toBeInTheDocument()
})

it.each(['first-load', 'load-more'])("F15-5: an old %s error clears on changing date", async (kind) => {
  const user = userEvent.setup()
  const next = deferred()
  let view
  if (kind === 'first-load') {
    loadBrowseGamesPage.mockRejectedValueOnce(new Error('Old request failed'))
    view = renderBrowse(`/games/browse?date=${TODAY}`)
    await screen.findByRole('heading', { name: 'Could not load games' })
  } else {
    loadBrowseGamesPage.mockResolvedValueOnce(page({ games: cards(40, 'Today'), hasMore: true, nextCursor: 'today-more', timeGroups: [{ group_key: '18:00', total_games: 41 }] }))
      .mockRejectedValueOnce(new Error('Old request failed'))
    view = renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()
    await user.click(screen.getByRole('button', { name: 'Load More' }))
    await screen.findByText('Old request failed')
  }
  loadBrowseGamesPage.mockReturnValueOnce(next.promise)
  await act(async () => view.router.navigate('/games/browse?date=2026-06-16'))
  expect(screen.queryByText('Old request failed')).not.toBeInTheDocument()
  await act(async () => next.resolve(page({ date: '2026-06-16', games: [card({ date: '2026-06-16' })] })))
  await waitForCards()
  expect(screen.queryByText('Old request failed')).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument()
})

it.each(['loading', 'loaded', 'failed'])("F15-5 F15-27: Back restores the prior date when the other request is %s", async (state) => {
  const next = deferred()
  loadBrowseGamesPage
    .mockResolvedValueOnce(page({ games: [card({ display_title: 'Today Field' })] }))
    .mockReturnValueOnce(next.promise)
  const { router } = renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  await chooseTuesday()
  expect(await screen.findByRole('status')).toHaveTextContent('Loading games')

  if (state === 'loaded') {
    await act(async () => next.resolve(page({ date: '2026-06-16', games: [card({ date: '2026-06-16', display_title: 'Tuesday Field' })] })))
    await waitForCards()
  } else if (state === 'failed') {
    await act(async () => next.reject(new Error('Tuesday unavailable')))
    await screen.findByRole('heading', { name: 'Could not load games' })
  }

  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: [card({ display_title: 'Today Again' })] }))
  await act(async () => router.navigate(-1))
  expect(await waitForCards()).toEqual(['Today Again'])
  expect(linkDate(router)).toBe(TODAY)
  expect(selectedDateButton()).toHaveAccessibleName('Browse games on MON Jun 15')

  if (state === 'loading') {
    await act(async () => next.resolve(page({ date: '2026-06-16', games: [card({ date: '2026-06-16', display_title: 'Tuesday Field' })] })))
    expect(cardTitles()).toEqual(['Today Again'])
    expect(linkDate(router)).toBe(TODAY)
  }
})

it("F15-5: selection shows the set containing the chosen date", async () => {
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: [card()] }))
    .mockResolvedValueOnce(page({ date: '2026-06-23', games: [card({ date: '2026-06-23' })] }))
  const { router } = renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  await act(async () => router.navigate('/games/browse?date=2026-06-23'))
  await waitForCards()
  expect(selectedDateButton()).toHaveAccessibleName('Browse games on TUE Jun 23')
})

it.each(['2026-02-30', 'soon'])("F15-19: an invalid date %s loads today", async (badDate) => {
  loadBrowseGamesPage.mockResolvedValue(page({ games: [card({ display_title: 'Today Field' })] }))
  renderBrowse(`/games/browse?date=${badDate}`)
  await waitForCards()

  expect(cardTitles()).toEqual(['Today Field'])
  expect(selectedDateButton()).toHaveAccessibleName('Browse games on MON Jun 15')
  expect(requestedDates()).toEqual([undefined])
})

it.each(['2026-02-30', 'soon'])("F15-19: an invalid date %s is corrected by replacing history", async (badDate) => {
  loadBrowseGamesPage.mockResolvedValue(page({ games: [card({ display_title: 'Today Field' })] }))
  const { router } = renderBrowse(`/games/browse?date=${badDate}`)
  await waitForCards()

  expect(linkDate(router)).toBe(TODAY)
  expect(router.state.historyAction).toBe('REPLACE')
  await act(async () => router.navigate(-1))
  expect(router.state.location.pathname).toBe('/')
})

it.each([['2026-06-12', TODAY], ['2026-07-15', '2026-06-28']])("F15-20: date %s opens the nearest available date", async (linkedDate, shownDate) => {
  loadBrowseGamesPage.mockResolvedValue(page({ date: shownDate, games: [card({ date: shownDate })] }))
  const { router } = renderBrowse(`/games/browse?date=${linkedDate}`)
  await waitForCards()
  expect(linkDate(router)).toBe(shownDate)
})

it.each([['2026-06-12', TODAY], ['2026-07-15', '2026-06-28']])("F15-20: correcting date %s replaces its history entry", async (linkedDate, shownDate) => {
  loadBrowseGamesPage.mockResolvedValue(page({ date: shownDate, games: [card({ date: shownDate })] }))
  const { router } = renderBrowse(`/games/browse?date=${linkedDate}`)
  await waitForCards()

  expect(router.state.historyAction).toBe('REPLACE')
  await act(async () => router.navigate(-1))
  expect(router.state.location.pathname).toBe('/')
})

it.each(['loaded', 'loading', 'failed'])("F15-36: an invalid link restores today when the other request is %s", async (state) => {
  const next = deferred()
  loadBrowseGamesPage.mockImplementation(({ startsOn = TODAY }) => Promise.resolve(page({
    date: startsOn,
    games: [card({ date: startsOn, display_title: startsOn === TODAY ? 'Today Field' : 'Other Date Field' })],
  })))
  const { router } = renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()

  if (state !== 'loaded') {
    loadBrowseGamesPage.mockReturnValueOnce(next.promise)
    await chooseTuesday()
    expect(await screen.findByRole('status')).toHaveTextContent('Loading games')
    if (state === 'failed') {
      await act(async () => next.reject(new Error('Tuesday unavailable')))
      await screen.findByRole('heading', { name: 'Could not load games' })
    }
  }

  await act(async () => router.navigate('/games/browse?date=not-a-date'))
  expect(await waitForCards()).toEqual(['Today Field'])
  expect(selectedDateButton()).toHaveAccessibleName('Browse games on MON Jun 15')
  expect(linkDate(router)).toBe(TODAY)

  if (state === 'loading') {
    await act(async () => next.resolve(page({ date: '2026-06-16', games: [card({ date: '2026-06-16', display_title: 'Tuesday Field' })] })))
    expect(cardTitles()).toEqual(['Today Field'])
    expect(linkDate(router)).toBe(TODAY)
  }
})

it("F15-36: an invalid link on another date switches results and selection to today", async () => {
  loadBrowseGamesPage.mockResolvedValueOnce(page({ date: '2026-06-17', games: [card({ date: '2026-06-17', display_title: 'Wednesday Field' })] }))
    .mockImplementation(({ startsOn = TODAY }) => Promise.resolve(page({
      date: startsOn,
      games: [card({ date: startsOn, display_title: startsOn === TODAY ? 'Today Field' : 'Other Date Field' })],
    })))
  const { router } = renderBrowse('/games/browse?date=2026-06-17')
  await waitForCards()
  await act(async () => router.navigate('/games/browse?date=not-a-date'))
  expect(await waitForCards()).toEqual(['Today Field'])
  expect(selectedDateButton()).toHaveAccessibleName('Browse games on MON Jun 15')
})

it("F15-36: an invalid link introduced while Browse is open is replaced", async () => {
  loadBrowseGamesPage.mockResolvedValue(page({ games: [card()] }))
  const { router } = renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  await act(async () => router.navigate('/games/browse?date=not-a-date'))
  expect(linkDate(router)).toBe(TODAY)
  expect(router.state.historyAction).toBe('REPLACE')
  await act(async () => router.navigate(-1))
  expect(linkDate(router)).toBe(TODAY)
})
