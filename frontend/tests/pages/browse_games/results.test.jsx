import { act, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { loadBrowseGamesPage } from '../../../src/pages/browse-games/browseGamesApi.js'
import {
  card,
  cardTitles,
  deferred,
  page,
  renderBrowse,
  TODAY,
  waitForCards,
} from './browseTestKit.jsx'

vi.mock('../../../src/pages/browse-games/browseGamesApi.js', () => ({
  loadBrowseGamesPage: vi.fn(),
}))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({
  default: () => null,
}))

function cards(count, prefix) {
  return Array.from({ length: count }, (_item, index) => card({ display_title: `${prefix} ${index + 1}` }))
}

function hourSection(label) {
  return screen.getByRole('heading', { level: 2, name: label }).closest('section')
}

describe('Browse results', () => {
  it('F15-16: an hour shows its total games, and hours with no loaded cards have no section', async () => {
    loadBrowseGamesPage.mockResolvedValue(page({
      games: cards(2, 'Six PM Field'),
      timeGroups: [
        { group_key: '18:00', total_games: 5 },
        { group_key: '20:00', total_games: 2 },
      ],
      hasMore: true,
      nextCursor: 'cursor-1',
    }))
    renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    expect(within(hourSection('6 PM')).getByText('5 games')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { level: 2, name: '8 PM' })).not.toBeInTheDocument()
  })

  it('F15-17: a day with no games shows a short message and no cards or Load More', async () => {
    loadBrowseGamesPage.mockResolvedValue(page({ games: [] }))
    renderBrowse(`/games/browse?date=${TODAY}`)

    expect(await screen.findByRole('heading', { name: 'No games found' })).toBeInTheDocument()
    expect(screen.getByText('Try another date or check back soon.')).toBeInTheDocument()
    expect(cardTitles()).toEqual([])
    expect(screen.queryByRole('button', { name: 'Load More' })).not.toBeInTheDocument()
  })

  it('F15-18: Load More adds the later games in order, without duplicates, then disappears', async () => {
    const user = userEvent.setup()
    const firstBatch = cards(40, 'Field')
    const lastGame = card({ display_title: 'Field 41' })
    loadBrowseGamesPage
      .mockResolvedValueOnce(page({ games: firstBatch, hasMore: true, nextCursor: 'cursor-1' }))
      .mockResolvedValueOnce(page({ games: [firstBatch[39], lastGame], hasMore: false }))
    renderBrowse(`/games/browse?date=${TODAY}`)
    expect(await waitForCards()).toHaveLength(40)

    await user.click(screen.getByRole('button', { name: 'Load More' }))

    expect(await screen.findByRole('heading', { name: 'Field 41' })).toBeInTheDocument()
    expect(cardTitles()).toEqual(Array.from({ length: 41 }, (_item, index) => `Field ${index + 1}`))
    expect(loadBrowseGamesPage).toHaveBeenLastCalledWith(
      expect.objectContaining({ cursor: 'cursor-1', startsOn: TODAY }),
    )
    expect(screen.queryByRole('button', { name: 'Load More' })).not.toBeInTheDocument()
  })

  it('F15-23: exactly 40 games show with no Load More', async () => {
    loadBrowseGamesPage.mockResolvedValue(page({ games: cards(40, 'Field'), hasMore: false }))
    renderBrowse(`/games/browse?date=${TODAY}`)

    expect(await waitForCards()).toHaveLength(40)
    expect(screen.queryByRole('button', { name: 'Load More' })).not.toBeInTheDocument()
  })

  it.each([
    ['the day\'s games', page({ games: [card({ display_title: 'Recovered Field' })] }), 'Recovered Field'],
    ['the empty message', page({ games: [] }), 'No games found'],
  ])('F15-24: a failed first load shows an error with Retry, and a successful retry shows %s', async (_label, retryResponse, expectedHeading) => {
    const user = userEvent.setup()
    loadBrowseGamesPage
      .mockRejectedValueOnce(new Error('Server unavailable'))
      .mockResolvedValueOnce(retryResponse)
    renderBrowse(`/games/browse?date=${TODAY}`)

    expect(await screen.findByRole('heading', { name: 'Could not load games' })).toBeInTheDocument()
    expect(screen.getByText('Server unavailable')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Retry' }))

    expect(await screen.findByRole('heading', { name: expectedHeading })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Could not load games' })).not.toBeInTheDocument()
  })

  it('F15-25: a failed Load More keeps the loaded cards, offers Retry, and the retry adds the rest', async () => {
    const user = userEvent.setup()
    const firstBatch = cards(2, 'Field')
    loadBrowseGamesPage
      .mockResolvedValueOnce(page({ games: firstBatch, hasMore: true, nextCursor: 'cursor-1' }))
      .mockRejectedValueOnce(new Error('Network trouble'))
      .mockResolvedValueOnce(page({ games: [firstBatch[1], card({ display_title: 'Field 3' })] }))
    renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    await user.click(screen.getByRole('button', { name: 'Load More' }))

    expect(await screen.findByText('Network trouble')).toBeInTheDocument()
    expect(cardTitles()).toEqual(['Field 1', 'Field 2'])
    expect(screen.queryByRole('heading', { name: 'Could not load games' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Retry' }))

    expect(await screen.findByRole('heading', { name: 'Field 3' })).toBeInTheDocument()
    expect(cardTitles()).toEqual(['Field 1', 'Field 2', 'Field 3'])
    expect(screen.queryByText('Network trouble')).not.toBeInTheDocument()
  })

  it('F15-32: Load More is disabled while loading', async () => {
    const user = userEvent.setup()
    const nextBatch = deferred()
    loadBrowseGamesPage
      .mockResolvedValueOnce(page({ games: cards(2, 'Field'), hasMore: true, nextCursor: 'cursor-1' }))
      .mockReturnValueOnce(nextBatch.promise)
    renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    await user.click(screen.getByRole('button', { name: 'Load More' }))

    expect(screen.getByRole('button', { name: 'Loading...' })).toBeDisabled()
    await act(async () => nextBatch.resolve(page({ games: [card({ display_title: 'Field 3' })] })))
    expect(await screen.findByRole('heading', { name: 'Field 3' })).toBeInTheDocument()
  })

  it('F15-32: Retry can be used with the keyboard', async () => {
    const user = userEvent.setup()
    loadBrowseGamesPage
      .mockRejectedValueOnce(new Error('Server unavailable'))
      .mockResolvedValueOnce(page({ games: [card({ display_title: 'Recovered Field' })] }))
    renderBrowse(`/games/browse?date=${TODAY}`)
    const retry = await screen.findByRole('button', { name: 'Retry' })

    retry.focus()
    await user.keyboard('{Enter}')

    expect(await screen.findByRole('heading', { name: 'Recovered Field' })).toBeInTheDocument()
  })
})
