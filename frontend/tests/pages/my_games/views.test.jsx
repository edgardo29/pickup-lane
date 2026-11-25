import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  fakePageApi, GAMES, gameItem, NEED_A_SUB, page, postItem, renderMyGames, requestsTo, signIn,
} from './myGamesTestKit.jsx'

vi.mock('../../../src/lib/apiClient.js', async (importOriginal) => ({
  ...(await importOriginal()),
  apiRequest: vi.fn(),
}))
vi.mock('../../../src/hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))

beforeEach(() => signIn())

// One card in each area and view, so each view's items can be told apart.
function fakeEveryView() {
  fakePageApi({
    [GAMES]: ({ view }) => page(view === 'upcoming'
      ? [gameItem({ venue: 'Upcoming Field' })]
      : [gameItem({ venue: 'Past Field', bucket: 'history', startsAt: '2030-05-01T23:00:00Z' })]),
    [NEED_A_SUB]: ({ view }) => page(view === 'history'
      ? [postItem({ location: 'Past Sub Field', bucket: 'history', startsAt: '2030-05-02T23:00:00Z' })]
      : [postItem({ location: 'Upcoming Sub Field' })]),
  })
}

describe('My Games views and cards', () => {
  it('F19-1: Games/Upcoming opens first', async () => {
    fakeEveryView()
    renderMyGames()

    expect(await screen.findByRole('heading', { name: 'Upcoming Field' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Games' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tab', { name: 'Upcoming' })).toHaveAttribute('aria-selected', 'true')
    expect(requestsTo(GAMES).map((request) => request.view)).toEqual(['upcoming'])
    expect(requestsTo(NEED_A_SUB)).toEqual([])
  })

  it('F19-1: switching areas and views shows only the matching items', async () => {
    const user = userEvent.setup()
    fakeEveryView()
    renderMyGames()
    await screen.findByRole('heading', { name: 'Upcoming Field' })

    await user.click(screen.getByRole('tab', { name: 'History' }))
    expect(await screen.findByRole('heading', { name: 'Past Field' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Upcoming Field' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Need a Sub' }))
    expect(await screen.findByText('Past Sub Field')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Past Field' })).not.toBeInTheDocument()
    expect(screen.queryByText('Upcoming Sub Field')).not.toBeInTheDocument()
  })

  it('F19-1: each view shows its own empty message', async () => {
    const user = userEvent.setup()
    fakePageApi()
    renderMyGames()

    expect(await screen.findByText('Games you host or are confirmed for will show up here.')).toBeInTheDocument()
    await user.click(screen.getByRole('tab', { name: 'History' }))
    expect(await screen.findByText('Hosted or confirmed games from the last 60 days will show up here.'))
      .toBeInTheDocument()
    await user.click(screen.getByRole('tab', { name: 'Need a Sub' }))
    expect(await screen.findByText('Games you own or are confirmed for from the last 60 days will show up here.'))
      .toBeInTheDocument()
    await user.click(screen.getByRole('tab', { name: 'Upcoming' }))
    expect(await screen.findByText('Games you own or are confirmed for will show up here.')).toBeInTheDocument()
  })

  it('F19-2: a game card opens Game Details', async () => {
    const user = userEvent.setup()
    fakePageApi({ [GAMES]: page([gameItem({ venue: 'Central Field' })]) })
    renderMyGames()

    await user.click(await screen.findByRole('link', { name: /Central Field/ }))

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
  })

  function fakePostHistory() {
    fakePageApi({
      [NEED_A_SUB]: ({ view }) => page(view === 'history' ? [
        postItem({ location: 'Open Post Field', bucket: 'history', startsAt: '2030-05-02T23:00:00Z' }),
        postItem({
          location: 'Closed Post Field', bucket: 'history', canViewDetail: false,
          startsAt: '2030-05-01T23:00:00Z',
        }),
      ] : []),
    })
  }

  async function openPostHistory(user) {
    await user.click(await screen.findByRole('tab', { name: 'Need a Sub' }))
    await user.click(screen.getByRole('tab', { name: 'History' }))
  }

  it('F19-2: an accessible post card opens Post Detail', async () => {
    const user = userEvent.setup()
    fakePostHistory()
    renderMyGames()
    await openPostHistory(user)

    await user.click(await screen.findByRole('link', { name: /Open Post Field/ }))

    expect(await screen.findByRole('heading', { name: 'Post Detail' })).toBeInTheDocument()
  })

  it('F19-2: an inaccessible historical post card is shown but not linked', async () => {
    const user = userEvent.setup()
    fakePostHistory()
    renderMyGames()
    await openPostHistory(user)

    expect(await screen.findByText('Closed Post Field')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Closed Post Field/ })).not.toBeInTheDocument()
  })

  // Times near noon UTC fall on the same calendar date in almost every time zone.
  function fakeTwoDays() {
    fakePageApi({
      [GAMES]: page([
        gameItem({ venue: 'Early Field', startsAt: '2030-06-15T11:00:00Z' }),
        gameItem({ venue: 'Late Field', startsAt: '2030-06-15T13:00:00Z' }),
        gameItem({ venue: 'Next Day Field', startsAt: '2030-06-16T12:00:00Z' }),
      ]),
    })
  }

  function dayHeadings() {
    return screen.getAllByRole('heading', { level: 2 }).filter((heading) => /JUN/.test(heading.textContent))
  }

  it('F19-3: Upcoming cards group by scheduled date', async () => {
    fakeTwoDays()
    renderMyGames()
    await screen.findByRole('heading', { name: 'Next Day Field' })

    const days = dayHeadings()

    expect(days.map((day) => day.textContent)).toEqual(['SAT, JUN 15', 'SUN, JUN 16'])
    expect(within(days[1].closest('section')).getAllByRole('heading', { level: 3 })
      .map((heading) => heading.textContent)).toEqual(['Next Day Field'])
  })

  it('F19-3: Upcoming cards within a date run earliest first', async () => {
    fakeTwoDays()
    renderMyGames()
    await screen.findByRole('heading', { name: 'Next Day Field' })

    const firstDay = dayHeadings()[0].closest('section')

    expect(within(firstDay).getAllByRole('heading', { level: 3 }).map((heading) => heading.textContent))
      .toEqual(['Early Field', 'Late Field'])
  })

  // The server sends History newest first.
  function fakeTwoPastDays() {
    fakePageApi({
      [GAMES]: ({ view }) => page(view === 'history' ? [
        gameItem({ venue: 'Next Day Field', bucket: 'history', startsAt: '2030-06-16T12:00:00Z' }),
        gameItem({ venue: 'Late Field', bucket: 'history', startsAt: '2030-06-15T13:00:00Z' }),
        gameItem({ venue: 'Early Field', bucket: 'history', startsAt: '2030-06-15T11:00:00Z' }),
      ] : []),
    })
  }

  it('F19-3: History cards group by scheduled date', async () => {
    const user = userEvent.setup()
    fakeTwoPastDays()
    renderMyGames()
    await user.click(await screen.findByRole('tab', { name: 'History' }))
    await screen.findByRole('heading', { name: 'Next Day Field' })

    const days = dayHeadings()

    expect(days.map((day) => day.textContent)).toEqual(['SUN, JUN 16', 'SAT, JUN 15'])
    expect(within(days[0].closest('section')).getAllByRole('heading', { level: 3 })
      .map((heading) => heading.textContent)).toEqual(['Next Day Field'])
  })

  it('F19-3: History cards within a date run newest first', async () => {
    const user = userEvent.setup()
    fakeTwoPastDays()
    renderMyGames()
    await user.click(await screen.findByRole('tab', { name: 'History' }))
    await screen.findByRole('heading', { name: 'Next Day Field' })

    const secondDay = dayHeadings()[1].closest('section')

    expect(within(secondDay).getAllByRole('heading', { level: 3 }).map((heading) => heading.textContent))
      .toEqual(['Late Field', 'Early Field'])
  })

  it('F19-3: Load More appends later items without duplicates', async () => {
    const user = userEvent.setup()
    const first = gameItem({ venue: 'First Field', startsAt: '2030-06-15T12:00:00Z' })
    const second = gameItem({ venue: 'Second Field', startsAt: '2030-06-16T12:00:00Z' })
    fakePageApi({
      // The second batch repeats the first card, which must not appear twice.
      [GAMES]: ({ cursor }) => (cursor === 'cursor-2' ? page([first, second]) : page([first], { nextCursor: 'cursor-2' })),
    })
    renderMyGames()
    await screen.findByRole('heading', { name: 'First Field' })

    await user.click(screen.getByRole('button', { name: 'Load More' }))

    expect(await screen.findByRole('heading', { name: 'Second Field' })).toBeInTheDocument()
    expect(screen.getAllByRole('heading', { level: 3 }).map((heading) => heading.textContent))
      .toEqual(['First Field', 'Second Field'])
    expect(requestsTo(GAMES).map((request) => request.cursor)).toEqual([null, 'cursor-2'])
  })
})
