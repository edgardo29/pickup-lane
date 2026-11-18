import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { loadBrowseGamesPage } from '../../../src/pages/browse-games/browseGamesApi.js'
import {
  card,
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

function visibleDateLabels() {
  return screen
    .getAllByRole('button', { name: /^Browse games on/ })
    .map((button) => button.getAttribute('aria-label').replace('Browse games on ', ''))
}

const originalTimeZone = process.env.TZ

afterEach(() => {
  process.env.TZ = originalTimeZone
})

describe('Browse date strip', () => {
  it('F15-4: fourteen dates come in two sets of seven; arrows switch sets without changing the date', async () => {
    const user = userEvent.setup()
    loadBrowseGamesPage.mockResolvedValue(page({ games: [card()] }))
    const router = renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()
    const previous = screen.getByRole('button', { name: 'Previous week' })
    const next = screen.getByRole('button', { name: 'Next week' })

    const firstSet = visibleDateLabels()
    expect(previous).toBeDisabled()
    expect(next).toBeEnabled()

    await user.click(next)
    const secondSet = visibleDateLabels()
    expect(next).toBeDisabled()
    expect(previous).toBeEnabled()

    expect(firstSet).toEqual([
      'MON Jun 15', 'TUE Jun 16', 'WED Jun 17', 'THU Jun 18', 'FRI Jun 19', 'SAT Jun 20', 'SUN Jun 21',
    ])
    expect(secondSet).toEqual([
      'MON Jun 22', 'TUE Jun 23', 'WED Jun 24', 'THU Jun 25', 'FRI Jun 26', 'SAT Jun 27', 'SUN Jun 28',
    ])
    expect(linkDate(router)).toBe(TODAY)
    expect(loadBrowseGamesPage).toHaveBeenCalledTimes(1)
  })

  it('F15-22: across the daylight-saving change the strip still has 14 consecutive market dates', async () => {
    const user = userEvent.setup()
    process.env.TZ = 'Asia/Tokyo'
    loadBrowseGamesPage.mockResolvedValue(
      page({ today: '2026-10-25', date: '2026-10-25', games: [card()] }),
    )
    renderBrowse('/games/browse?date=2026-10-25')
    await waitForCards()

    const firstSet = visibleDateLabels()
    await user.click(screen.getByRole('button', { name: 'Next week' }))
    const secondSet = visibleDateLabels()

    expect([...firstSet, ...secondSet]).toEqual([
      'SUN Oct 25', 'MON Oct 26', 'TUE Oct 27', 'WED Oct 28', 'THU Oct 29', 'FRI Oct 30', 'SAT Oct 31',
      'SUN Nov 1', 'MON Nov 2', 'TUE Nov 3', 'WED Nov 4', 'THU Nov 5', 'FRI Nov 6', 'SAT Nov 7',
    ])
  })

  it('F15-32: dates and arrows have clear labels and show selected and disabled states', async () => {
    loadBrowseGamesPage.mockResolvedValue(page({ games: [card()] }))
    renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    const strip = screen.getByLabelText('Browse games by date')
    const dateButtons = within(strip).getAllByRole('button')
    expect(dateButtons).toHaveLength(7)
    expect(selectedDateButton()).toHaveAccessibleName('Browse games on MON Jun 15')
    expect(dateButtons.filter((button) => button.getAttribute('aria-current') === 'date')).toHaveLength(1)
    expect(screen.getByRole('button', { name: 'Previous week' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Next week' })).toBeEnabled()
  })

  it('F15-32: a date can be chosen with the keyboard', async () => {
    const user = userEvent.setup()
    loadBrowseGamesPage
      .mockResolvedValueOnce(page({ games: [card()] }))
      .mockResolvedValueOnce(page({ date: '2026-06-16', games: [card({ display_title: 'Tuesday Field' })] }))
    const router = renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    screen.getByRole('button', { name: 'Browse games on TUE Jun 16' }).focus()
    await user.keyboard('{Enter}')

    expect(await screen.findByRole('heading', { name: 'Tuesday Field' })).toBeInTheDocument()
    expect(linkDate(router)).toBe('2026-06-16')
  })
})
