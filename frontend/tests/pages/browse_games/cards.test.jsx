import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { loadBrowseGamesPage } from '../../../src/pages/browse-games/browseGamesApi.js'
import { card, page, renderBrowse, TODAY, waitForCards } from './browseTestKit.jsx'

vi.mock('../../../src/pages/browse-games/browseGamesApi.js', () => ({
  loadBrowseGamesPage: vi.fn(),
}))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({
  default: () => null,
}))

function cardLink(title) {
  return screen.getByRole('heading', { level: 3, name: title }).closest('a')
}

const originalTimeZone = process.env.TZ

afterEach(() => {
  process.env.TZ = originalTimeZone
})

describe('Browse game cards', () => {
  it.each([
    ['with an accepting waitlist', 'waitlist_open'],
    ['without a waitlist', 'full'],
  ])('F15-8: a full game %s shows Full and no waitlist badge', async (_label, status) => {
    loadBrowseGamesPage.mockResolvedValue(page({
      games: [card({ display_title: 'Packed Field', occupied: 14, total: 14, availabilityStatus: status })],
    }))
    renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    const link = cardLink('Packed Field')
    expect(within(link).getByText('Full')).toBeInTheDocument()
    expect(within(link).queryByText(/waitlist/i)).not.toBeInTheDocument()
  })

  it('F15-11: an official card shows type, venue title, location, market time, details, spots, and price', async () => {
    loadBrowseGamesPage.mockResolvedValue(page({
      games: [card({
        display_title: 'Lakefront Turf',
        starts_at: '2026-06-15T23:30:00Z',
        ends_at: '2026-06-16T00:30:00Z',
        game_player_group: 'women',
        format_label: '5v5',
        environment_type: 'indoor',
        occupied: 3,
        total: 10,
        price_label: '$12.50',
      })],
    }))
    renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    const link = cardLink('Lakefront Turf')
    expect(within(link).getByText('Official')).toBeInTheDocument()
    expect(within(link).getByText('Chicago, IL')).toBeInTheDocument()
    expect(within(link).getByText('6:30 PM - 7:30 PM')).toBeInTheDocument()
    expect(within(link).getByText('Women · 5v5 · Indoor')).toBeInTheDocument()
    expect(within(link).getByText('3/10')).toBeInTheDocument()
    expect(within(link).getByText('$12.50')).toBeInTheDocument()
    expect(within(link).queryByText('Full')).not.toBeInTheDocument()
  })

  it('F15-11: a community card shows its type, host title, and Free', async () => {
    loadBrowseGamesPage.mockResolvedValue(page({
      games: [card({ game_type: 'community', display_title: 'Sunday Night Run', price_label: 'Free' })],
    }))
    renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    const link = cardLink('Sunday Night Run')
    expect(within(link).getByText('Community')).toBeInTheDocument()
    expect(within(link).getByText('Free')).toBeInTheDocument()
  })

  it('F15-12: a card shows its game or venue image when one exists', async () => {
    loadBrowseGamesPage.mockResolvedValue(page({
      games: [card({ display_title: 'Pictured Field', primary_image_url: 'https://cdn.example.test/field.jpg' })],
    }))
    renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    expect(cardLink('Pictured Field').querySelector('img')).toHaveAttribute(
      'src',
      'https://cdn.example.test/field.jpg',
    )
  })

  it('F15-12: a card without an image keeps its default visual', async () => {
    loadBrowseGamesPage.mockResolvedValue(page({
      games: [
        card({ game_type: 'community', display_title: 'Community Field' }),
        card({ display_title: 'Official Field' }),
      ],
    }))
    renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    const communityImage = cardLink('Community Field').querySelector('img')
    expect(communityImage.getAttribute('src')).toMatch(/default-venue-wide/)
    const officialCard = cardLink('Official Field')
    expect(officialCard.querySelector('img')).toBeNull()
    expect(officialCard.querySelector('.game-card__fallback svg')).not.toBeNull()
  })

  it('F15-14: selecting a card opens its Game Details page without reserving anything', async () => {
    const user = userEvent.setup()
    const game = card({ display_title: 'Open Field' })
    loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
    const router = renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    await user.click(cardLink('Open Field'))

    expect(await screen.findByRole('heading', { name: `Game details ${game.id}` })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe(`/games/${game.id}`)
    expect(loadBrowseGamesPage).toHaveBeenCalledTimes(1)
    expect(fetch).not.toHaveBeenCalled()
  })

  it('F15-22: card times and hour headings use market time, not the device timezone', async () => {
    process.env.TZ = 'Asia/Tokyo'
    loadBrowseGamesPage.mockResolvedValue(page({
      games: [card({
        display_title: 'Evening Field',
        starts_at: '2026-06-15T23:30:00Z',
        ends_at: '2026-06-16T00:30:00Z',
        time_group_key: '18:00',
      })],
    }))
    renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    expect(within(cardLink('Evening Field')).getByText('6:30 PM - 7:30 PM')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: '6 PM' })).toBeInTheDocument()
  })
})
