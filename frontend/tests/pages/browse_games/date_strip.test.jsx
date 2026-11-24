import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { loadBrowseGamesPage } from '../../../src/pages/browse-games/browseGamesApi.js'
import { card, linkDate, page, renderBrowse, selectedDateButton, TODAY, waitForCards } from './browseTestKit.jsx'

vi.mock('../../../src/pages/browse-games/browseGamesApi.js', () => ({ loadBrowseGamesPage: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))

const originalTimeZone = process.env.TZ
afterEach(() => { process.env.TZ = originalTimeZone })

function visibleDateLabels() {
  return screen.getAllByRole('button', { name: /^Browse games on/ }).map((button) => button.textContent)
}

async function openToday() {
  loadBrowseGamesPage.mockResolvedValue(page({ games: [card()] }))
  const view = renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  return view
}

it("F15-4: the strip offers exactly fourteen dates in two sets of seven", async () => {
  const user = userEvent.setup()
  await openToday()
  expect(visibleDateLabels()).toEqual(['MONJun15', 'TUEJun16', 'WEDJun17', 'THUJun18', 'FRIJun19', 'SATJun20', 'SUNJun21'])
  await user.click(screen.getByRole('button', { name: 'Next week' }))
  expect(visibleDateLabels()).toEqual(['MONJun22', 'TUEJun23', 'WEDJun24', 'THUJun25', 'FRIJun26', 'SATJun27', 'SUNJun28'])
})

it("F15-4: arrows change sets without changing the selected date", async () => {
  const user = userEvent.setup()
  const { router } = await openToday()
  loadBrowseGamesPage.mockImplementation(({ startsOn }) => Promise.resolve(page({ date: startsOn, games: [card({ date: startsOn })] })))
  await user.click(screen.getByRole('button', { name: 'Next week' }))
  expect(linkDate(router)).toBe(TODAY)
  await user.click(screen.getByRole('button', { name: 'Previous week' }))
  expect(selectedDateButton()).toHaveAccessibleName('Browse games on MON Jun 15')
  expect(loadBrowseGamesPage).toHaveBeenCalledTimes(1)
})

it("F15-4: arrows are disabled at the ends", async () => {
  const user = userEvent.setup()
  await openToday()
  expect(screen.getByRole('button', { name: 'Previous week' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Next week' })).toBeEnabled()
  await user.click(screen.getByRole('button', { name: 'Next week' }))
  expect(screen.getByRole('button', { name: 'Next week' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Previous week' })).toBeEnabled()
})

it.each([['spring', '2026-03-01', ['SUNMar1', 'MONMar2', 'TUEMar3', 'WEDMar4', 'THUMar5', 'FRIMar6', 'SATMar7', 'SUNMar8', 'MONMar9', 'TUEMar10', 'WEDMar11', 'THUMar12', 'FRIMar13', 'SATMar14']], ['fall', '2026-10-25', ['SUNOct25', 'MONOct26', 'TUEOct27', 'WEDOct28', 'THUOct29', 'FRIOct30', 'SATOct31', 'SUNNov1', 'MONNov2', 'TUENov3', 'WEDNov4', 'THUNov5', 'FRINov6', 'SATNov7']]])("F15-22: fourteen consecutive market dates span the %s daylight-saving change", async (_label, today, expected) => {
  process.env.TZ = 'Asia/Tokyo'
  const user = userEvent.setup()
  loadBrowseGamesPage.mockResolvedValue(page({ today, date: today, games: [card({ date: today })] }))
  renderBrowse(`/games/browse?date=${today}`)
  await waitForCards()
  const first = visibleDateLabels()
  await user.click(screen.getByRole('button', { name: 'Next week' }))
  expect([...first, ...visibleDateLabels()]).toEqual(expected)
})

it("F15-32: dates and arrows have clear accessible labels", async () => {
  await openToday()
  const strip = screen.getByLabelText('Browse games by date')
  expect(within(strip).getAllByRole('button').map((button) => button.getAttribute('aria-label'))).toEqual([
    'Browse games on MON Jun 15', 'Browse games on TUE Jun 16', 'Browse games on WED Jun 17', 'Browse games on THU Jun 18', 'Browse games on FRI Jun 19', 'Browse games on SAT Jun 20', 'Browse games on SUN Jun 21',
  ])
  expect(screen.getByRole('button', { name: 'Previous week' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Next week' })).toBeInTheDocument()
})

it("F15-32: assistive technology can identify the selected date", async () => {
  await openToday()
  expect(document.querySelectorAll('[aria-current="date"]')).toHaveLength(1)
  expect(selectedDateButton()).toHaveAccessibleName('Browse games on MON Jun 15')
})

it("F15-32: the keyboard can select another date", async () => {
  const user = userEvent.setup()
  loadBrowseGamesPage.mockResolvedValueOnce(page({ games: [card()] }))
    .mockResolvedValueOnce(page({ date: '2026-06-16', games: [card({ date: '2026-06-16', display_title: 'Tuesday Field' })] }))
  const { router } = renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  screen.getByRole('button', { name: 'Browse games on TUE Jun 16' }).focus()
  await user.keyboard('{Enter}')
  expect(await waitForCards()).toEqual(['Tuesday Field'])
  expect(linkDate(router)).toBe('2026-06-16')
})
