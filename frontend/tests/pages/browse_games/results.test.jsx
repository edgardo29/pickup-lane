import { act, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { loadBrowseGamesPage } from '../../../src/pages/browse-games/browseGamesApi.js'
import { card, cards, cardTitles, deferred, hourSection, page, renderBrowse, TODAY, waitForCards } from './browseTestKit.jsx'

vi.mock('../../../src/pages/browse-games/browseGamesApi.js', () => ({ loadBrowseGamesPage: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))

async function openPagedList() {
  const first = cards(40, 'Field')
  const last = card({ display_title: 'Field 41', starts_at: '2026-06-15T23:50:00Z', ends_at: '2026-06-16T00:50:00Z' })
  const totals = [{ group_key: '18:00', total_games: 41 }]
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: first, hasMore: true, nextCursor: 'cursor-1', timeGroups: totals }))
  const view = renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  return { ...view, first, last, totals }
}

async function failLoadMore() {
  const data = await openPagedList()
  loadBrowseGamesPage.mockRejectedValueOnce(new Error('Network trouble'))
  await userEvent.setup().click(screen.getByRole('button', { name: 'Load More' }))
  await act(async () => {})
  return data
}

it("F15-15: hour sections run from earliest to latest", async () => {
  loadBrowseGamesPage.mockResolvedValue(page({ games: [
    card({ display_title: 'Earlier', starts_at: '2026-06-15T21:00:00Z', ends_at: '2026-06-15T22:00:00Z', time_group_key: '16:00' }),
    card({ display_title: 'Later' }),
  ] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  expect(screen.getAllByRole('heading', { level: 2 }).map((heading) => heading.textContent)).toEqual(['4 PM', '6 PM'])
})

it("F15-15: games keep their chronological order within an hour", async () => {
  const games = [
    card({ display_title: 'Six Ten', starts_at: '2026-06-15T23:10:00Z', ends_at: '2026-06-16T00:10:00Z' }),
    card({ display_title: 'Six Forty', starts_at: '2026-06-15T23:40:00Z', ends_at: '2026-06-16T00:40:00Z' }),
  ]
  loadBrowseGamesPage.mockResolvedValue(page({ games }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  expect(await waitForCards()).toEqual(['Six Ten', 'Six Forty'])
})

it("F15-15: equal start times keep the API creation order", async () => {
  loadBrowseGamesPage.mockResolvedValue(page({ games: [
    card({ id: 'ffffffff-ffff-4fff-8fff-ffffffffffff', display_title: 'Created First' }),
    card({ id: '00000000-0000-4000-8000-000000000001', display_title: 'Created Second' }),
  ] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  expect(await waitForCards()).toEqual(['Created First', 'Created Second'])
})

it("F15-16: an hour displays the total including unloaded games", async () => {
  loadBrowseGamesPage.mockResolvedValue(page({ games: cards(40, 'Six PM Field'), timeGroups: [
    { group_key: '18:00', total_games: 45 }, { group_key: '20:00', total_games: 2 },
  ], hasMore: true, nextCursor: 'cursor-1' }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  expect(within(hourSection('6 PM')).getByText('45 games')).toBeInTheDocument()
})

it("F15-16: hours without loaded cards have no section", async () => {
  loadBrowseGamesPage.mockResolvedValue(page({ games: cards(40, 'Six PM Field'), timeGroups: [
    { group_key: '18:00', total_games: 45 }, { group_key: '20:00', total_games: 2 },
  ], hasMore: true, nextCursor: 'cursor-1' }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  expect(screen.queryByRole('heading', { level: 2, name: '8 PM' })).not.toBeInTheDocument()
})

it("F15-17: an empty day suggests another date or checking back", async () => {
  loadBrowseGamesPage.mockResolvedValue(page())
  renderBrowse(`/games/browse?date=${TODAY}`)
  await screen.findByRole('heading', { name: 'No games found' })
  expect(screen.getByText('Try another date or check back soon.')).toBeInTheDocument()
})

it("F15-17: an empty day has no game cards", async () => {
  loadBrowseGamesPage.mockResolvedValue(page())
  renderBrowse(`/games/browse?date=${TODAY}`)
  await screen.findByRole('heading', { name: 'No games found' })
  expect(cardTitles()).toEqual([])
})

it("F15-17: an empty day has no Load More", async () => {
  loadBrowseGamesPage.mockResolvedValue(page())
  renderBrowse(`/games/browse?date=${TODAY}`)
  await screen.findByRole('heading', { name: 'No games found' })
  expect(screen.queryByRole('button', { name: 'Load More' })).not.toBeInTheDocument()
})

it("F15-18: the first batch displays forty cards", async () => {
  const { first } = await openPagedList()
  expect(cardTitles()).toEqual(first.map((game) => game.display_title))
  expect(loadBrowseGamesPage).toHaveBeenCalledWith(expect.objectContaining({ limit: 40 }))
})

it("F15-18: Load More appends later games in order without duplicates", async () => {
  const user = userEvent.setup()
  const { first, last, totals } = await openPagedList()
  // An already displayed game moved later while this page was open, so the
  // next keyset page can include its ID again. Its updated start is later than
  // the old cursor. The UI must not display a second copy.
  const moved = { ...first[39], starts_at: '2026-06-15T23:45:00Z', ends_at: '2026-06-16T00:45:00Z', registration_closes_at: '2026-06-15T23:50:00Z' }
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: [moved, last], timeGroups: totals }))
  await user.click(screen.getByRole('button', { name: 'Load More' }))
  await screen.findByRole('heading', { name: 'Field 41' })
  expect(cardTitles()).toEqual([...first, last].map((game) => game.display_title))
  expect(loadBrowseGamesPage).toHaveBeenLastCalledWith(expect.objectContaining({ cursor: 'cursor-1', startsOn: TODAY }))
})

it("F15-18: Load More disappears after the final batch", async () => {
  const { last, totals } = await openPagedList()
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: [last], timeGroups: totals }))
  await userEvent.setup().click(screen.getByRole('button', { name: 'Load More' }))
  await screen.findByRole('heading', { name: 'Field 41' })
  expect(screen.queryByRole('button', { name: 'Load More' })).not.toBeInTheDocument()
})

it("F15-23: exactly forty games all appear", async () => {
  loadBrowseGamesPage.mockResolvedValue(page({ games: cards(40, 'Field') }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  expect(cardTitles()).toEqual(Array.from({ length: 40 }, (_, index) => `Field ${index + 1}`))
})

it("F15-23: exactly forty games need no Load More", async () => {
  loadBrowseGamesPage.mockResolvedValue(page({ games: cards(40, 'Field') }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  expect(screen.queryByRole('button', { name: 'Load More' })).not.toBeInTheDocument()
})

it("F15-24: a first-load failure displays an error with Retry", async () => {
  loadBrowseGamesPage.mockRejectedValueOnce(new Error('Server unavailable'))
  renderBrowse(`/games/browse?date=${TODAY}`)
  expect(await screen.findByRole('heading', { name: 'Could not load games' })).toBeInTheDocument()
  expect(screen.getByText('Server unavailable')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Retry' })).toBeEnabled()
})

it.each([['games', false], ['an empty day', true]])("F15-24: first-load Retry recovers to %s", async (_label, empty) => {
  const user = userEvent.setup()
  loadBrowseGamesPage.mockRejectedValueOnce(new Error('Server unavailable'))
    .mockResolvedValueOnce(page({ games: empty ? [] : [card({ display_title: 'Recovered Field' })] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await screen.findByRole('heading', { name: 'Could not load games' })
  await user.click(screen.getByRole('button', { name: 'Retry' }))
  expect(await screen.findByRole('heading', { name: empty ? 'No games found' : 'Recovered Field' })).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Could not load games' })).not.toBeInTheDocument()
})

it("F15-25: a failed Load More preserves the loaded cards", async () => {
  const { first } = await failLoadMore()
  expect(cardTitles()).toEqual(first.map((game) => game.display_title))
  expect(screen.queryByRole('heading', { name: 'Could not load games' })).not.toBeInTheDocument()
})

it("F15-25: a failed Load More offers an inline Retry", async () => {
  await failLoadMore()
  expect(screen.getByRole('button', { name: 'Retry' })).toBeEnabled()
  expect(screen.getByText('Network trouble')).toBeInTheDocument()
})

it("F15-25: Load More Retry uses the same cursor and appends the remainder", async () => {
  const { first, last, totals } = await failLoadMore()
  const moved = { ...first[39], starts_at: '2026-06-15T23:45:00Z', ends_at: '2026-06-16T00:45:00Z', registration_closes_at: '2026-06-15T23:50:00Z' }
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: [moved, last], timeGroups: totals }))
  await userEvent.setup().click(screen.getByRole('button', { name: 'Retry' }))
  await screen.findByRole('heading', { name: 'Field 41' })
  expect(cardTitles()).toEqual([...first, last].map((game) => game.display_title))
  expect(loadBrowseGamesPage).toHaveBeenLastCalledWith(expect.objectContaining({ cursor: 'cursor-1' }))
  expect(screen.queryByText('Network trouble')).not.toBeInTheDocument()
})

it("F15-32: Load More works with the keyboard", async () => {
  const { last, totals } = await openPagedList()
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: [last], timeGroups: totals }))
  screen.getByRole('button', { name: 'Load More' }).focus()
  await userEvent.setup().keyboard('{Enter}')
  expect(await screen.findByRole('heading', { name: 'Field 41' })).toBeInTheDocument()
})

it("F15-32: Load More is disabled while its response is pending", async () => {
  const next = deferred()
  const { last, totals } = await openPagedList()
  loadBrowseGamesPage.mockReturnValueOnce(next.promise)
  await userEvent.setup().click(screen.getByRole('button', { name: 'Load More' }))
  expect(screen.getByRole('button', { name: 'Loading...' })).toBeDisabled()
  await act(async () => next.resolve(page({ games: [last], timeGroups: totals })))
  await screen.findByRole('heading', { name: 'Field 41' })
})

it("F15-32: Retry works with the keyboard", async () => {
  loadBrowseGamesPage.mockRejectedValueOnce(new Error('Server unavailable'))
    .mockResolvedValueOnce(page({ games: [card({ display_title: 'Recovered Field' })] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  const retry = await screen.findByRole('button', { name: 'Retry' })
  retry.focus()
  await userEvent.setup().keyboard('{Enter}')
  expect(await screen.findByRole('heading', { name: 'Recovered Field' })).toBeInTheDocument()
})
