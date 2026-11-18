import { act, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
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

function requestedDates() {
  return loadBrowseGamesPage.mock.calls.map(([options]) => options.startsOn)
}

describe('Browse date links', () => {
  it('F15-2: no date in the link loads today and writes today into the link', async () => {
    const response = deferred()
    loadBrowseGamesPage.mockReturnValueOnce(response.promise)

    const router = renderBrowse('/games/browse')

    expect(await screen.findByRole('status')).toHaveTextContent('Loading games')
    await act(async () => response.resolve(page({ games: [card({ display_title: 'Today Field' })] })))
    expect(await waitForCards()).toEqual(['Today Field'])
    expect(requestedDates()).toEqual([undefined])
    expect(linkDate(router)).toBe(TODAY)
    expect(router.state.historyAction).toBe('REPLACE')
  })

  it('F15-3: a valid date link selects that date and shows its seven-date set', async () => {
    const linkedDate = addDays(TODAY, 9)
    loadBrowseGamesPage.mockResolvedValue(
      page({ date: linkedDate, games: [card({ display_title: 'Later Field' })] }),
    )

    renderBrowse(`/games/browse?date=${linkedDate}`)

    expect(await waitForCards()).toEqual(['Later Field'])
    expect(requestedDates()).toEqual([linkedDate])
    expect(await screen.findByRole('button', { name: 'Browse games on WED Jun 24' }))
      .toHaveAttribute('aria-current', 'date')
    const visibleDates = screen.getAllByRole('button', { name: /^Browse games on/ })
    expect(visibleDates.map((button) => button.textContent)).toEqual([
      'MONJun22', 'TUEJun23', 'WEDJun24', 'THUJun25', 'FRIJun26', 'SATJun27', 'SUNJun28',
    ])
  })

  it('F15-5: choosing another date adds a history entry, clears the list while loading, and Back returns', async () => {
    const user = userEvent.setup()
    const nextDate = addDays(TODAY, 2)
    const nextDateResponse = deferred()
    loadBrowseGamesPage
      .mockResolvedValueOnce(page({ games: [card({ display_title: 'Today Field' })] }))
      .mockReturnValueOnce(nextDateResponse.promise)
      .mockResolvedValueOnce(page({ games: [card({ display_title: 'Today Field Again' })] }))
    const router = renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    await user.click(screen.getByRole('button', { name: 'Browse games on WED Jun 17' }))

    expect(router.state.historyAction).toBe('PUSH')
    expect(linkDate(router)).toBe(nextDate)
    expect(await screen.findByRole('status')).toHaveTextContent('Loading games')
    expect(cardTitles()).toEqual([])

    await act(async () => nextDateResponse.resolve(
      page({ date: nextDate, games: [card({ display_title: 'Wednesday Field' })] }),
    ))
    expect(await waitForCards()).toEqual(['Wednesday Field'])

    await act(async () => router.navigate(-1))
    expect(linkDate(router)).toBe(TODAY)
    expect(await screen.findByRole('heading', { name: 'Today Field Again' })).toBeInTheDocument()
    expect(requestedDates()).toEqual([TODAY, nextDate, TODAY])
  })

  it.each([
    ['an impossible date', '2026-02-30'],
    ['text that is not a date', 'soon'],
  ])('F15-19: opening a link with %s shows today and replaces the link', async (_label, badDate) => {
    loadBrowseGamesPage.mockResolvedValue(page({ games: [card({ display_title: 'Today Field' })] }))

    const router = renderBrowse(`/games/browse?date=${badDate}`)

    expect(await waitForCards()).toEqual(['Today Field'])
    expect(requestedDates()).toEqual([undefined])
    expect(linkDate(router)).toBe(TODAY)
    expect(router.state.historyAction).toBe('REPLACE')
    await act(async () => router.navigate(-1))
    expect(router.state.location.pathname).toBe('/')
  })

  it.each([
    ['before today', addDays(TODAY, -3), TODAY],
    ['after the last available day', addDays(TODAY, 30), addDays(TODAY, 13)],
  ])('F15-20: a link to a date %s is replaced with the nearest available day', async (_label, linkedDate, shownDate) => {
    loadBrowseGamesPage.mockResolvedValue(page({ date: shownDate, games: [card()] }))

    const router = renderBrowse(`/games/browse?date=${linkedDate}`)

    await waitForCards()
    expect(linkDate(router)).toBe(shownDate)
    expect(router.state.historyAction).toBe('REPLACE')
  })

  it('F15-36: an invalid link while today is open keeps today and replaces the link', async () => {
    loadBrowseGamesPage.mockResolvedValue(page({ games: [card({ display_title: 'Today Field' })] }))
    const router = renderBrowse(`/games/browse?date=${TODAY}`)
    await waitForCards()

    await act(async () => router.navigate('/games/browse?date=not-a-date'))

    expect(linkDate(router)).toBe(TODAY)
    expect(router.state.historyAction).toBe('REPLACE')
    expect(cardTitles()).toEqual(['Today Field'])
    await act(async () => router.navigate(-1))
    expect(linkDate(router)).toBe(TODAY)
  })

  it('F15-36: an invalid link while another date is open switches to today', async () => {
    const otherDate = addDays(TODAY, 2)
    loadBrowseGamesPage
      .mockResolvedValueOnce(page({ date: otherDate, games: [card({ display_title: 'Wednesday Field' })] }))
      .mockResolvedValueOnce(page({ games: [card({ display_title: 'Today Field' })] }))
    const router = renderBrowse(`/games/browse?date=${otherDate}`)
    await waitForCards()

    await act(async () => router.navigate('/games/browse?date=not-a-date'))

    expect(await screen.findByRole('heading', { name: 'Today Field' })).toBeInTheDocument()
    expect(cardTitles()).toEqual(['Today Field'])
    expect(requestedDates()).toEqual([otherDate, undefined])
    expect(linkDate(router)).toBe(TODAY)
    expect(router.state.historyAction).toBe('REPLACE')
    expect(selectedDateButton()).toHaveAccessibleName('Browse games on MON Jun 15')
  })
})
