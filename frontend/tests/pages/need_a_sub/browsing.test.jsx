import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  CARDS, NOW, TODAY, TOMORROW, card, cardPage, cardRequests, cardVenues, fakeApi, findCards, position,
  renderNeedASub, signedIn, signedInWithoutAccount, signedOut,
} from './needASubTestKit.jsx'

vi.mock('../../../src/lib/apiClient.js', async (importOriginal) => ({
  ...(await importOriginal()),
  apiRequest: vi.fn(),
}))
vi.mock('../../../src/hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))
vi.mock('../../../src/context/authProviderHelpers.js', () => ({
  waitForCurrentFirebaseUser: vi.fn(),
}))

const originalTimeZone = process.env.TZ

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(NOW))
})

afterEach(() => {
  vi.useRealTimers()
  process.env.TZ = originalTimeZone
})

// Card answers keyed by the date and view the page asked for.
function cardsByRequest(answers) {
  return (path) => {
    const params = new URL(path, 'http://test.local').searchParams
    return answers[`${params.get('view')} ${params.get('starts_on')}`] ?? cardPage()
  }
}

function dateButton(day) {
  return screen.getByRole('button', { name: `Need a Sub posts on ${day}` })
}

function dateButtonNames() {
  return within(screen.getByLabelText('Need a Sub posts by date'))
    .getAllByRole('button')
    .map((button) => button.getAttribute('aria-label').replace('Need a Sub posts on ', ''))
}

describe('Need a Sub browsing', () => {
  function guestWithOneCard() {
    signedOut()
    fakeApi({ [CARDS]: cardPage({ posts: [card({ location_name: 'North Park' })] }) })
    renderNeedASub()
  }

  it('F20-1: public summary cards and date controls appear without signing in', async () => {
    guestWithOneCard()

    expect(await screen.findByText('North Park')).toBeInTheDocument()
    expect(dateButton('Mon Jun 15')).toHaveAttribute('aria-current', 'date')
    expect(screen.getByRole('button', { name: 'Next week' })).toBeEnabled()
    expect(cardRequests()).toEqual([{ cursor: null, signedIn: false, startsOn: TODAY, view: 'all' }])
  })

  it('F20-1: My Posts is unavailable to a signed-out visitor', async () => {
    guestWithOneCard()
    await screen.findByText('North Park')

    expect(screen.queryByRole('tab', { name: 'My Posts' })).not.toBeInTheDocument()
  })

  it('F20-1: creation controls are unavailable to a signed-out visitor', async () => {
    guestWithOneCard()
    await screen.findByText('North Park')

    expect(screen.queryByRole('button', { name: 'Create Post' })).not.toBeInTheDocument()
  })

  it('F20-1: a sign-in without a finished account browses as a guest', async () => {
    signedInWithoutAccount()
    fakeApi({ [CARDS]: cardPage({ posts: [card({ location_name: 'North Park' })] }) })
    renderNeedASub()

    expect(await screen.findByText('North Park')).toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: 'My Posts' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Create Post' })).not.toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('F20-2: a signed-in visitor gets All Posts for today with the date strip', async () => {
    signedIn()
    fakeApi({ [CARDS]: cardPage({ posts: [card({ location_name: 'North Park' })] }) })
    renderNeedASub()

    expect(await screen.findByText('North Park')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'All Posts' })).toHaveAttribute('aria-selected', 'true')
    expect(dateButton('Mon Jun 15')).toHaveAttribute('aria-current', 'date')
    expect(cardRequests()).toEqual([{ cursor: null, signedIn: false, startsOn: TODAY, view: 'all' }])
  })

  it('F20-2: a signed-in visitor gets the Create Post action', async () => {
    signedIn()
    fakeApi({ [CARDS]: cardPage({ posts: [card({ location_name: 'North Park' })] }) })
    renderNeedASub()
    await screen.findByText('North Park')

    expect(screen.getByRole('button', { name: 'Create Post' })).toBeInTheDocument()
  })

  it('F20-2: an unverified email does not block public browsing', async () => {
    signedIn({ email_verified_at: null })
    fakeApi({ [CARDS]: cardPage({ posts: [card({ location_name: 'North Park' })] }) })
    renderNeedASub()

    expect(await screen.findByText('North Park')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'All Posts' })).toHaveAttribute('aria-selected', 'true')
  })

  it('F20-3: fourteen dates are offered in two sets of seven', async () => {
    const user = userEvent.setup()
    signedOut()
    fakeApi({ [CARDS]: cardPage() })
    renderNeedASub()
    await screen.findByText('No Need a Sub posts yet')

    expect(dateButtonNames()).toEqual([
      'Mon Jun 15', 'Tue Jun 16', 'Wed Jun 17', 'Thu Jun 18', 'Fri Jun 19', 'Sat Jun 20', 'Sun Jun 21',
    ])
    expect(screen.getByRole('button', { name: 'Previous week' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Next week' }))
    expect(dateButtonNames()).toEqual([
      'Mon Jun 22', 'Tue Jun 23', 'Wed Jun 24', 'Thu Jun 25', 'Fri Jun 26', 'Sat Jun 27', 'Sun Jun 28',
    ])
    expect(screen.getByRole('button', { name: 'Next week' })).toBeDisabled()
  })

  it('F20-3: changing the set selects its first date', async () => {
    const user = userEvent.setup()
    signedOut()
    fakeApi({ [CARDS]: cardPage() })
    renderNeedASub()
    await screen.findByText('No Need a Sub posts yet')
    await user.click(dateButton('Wed Jun 17'))

    await user.click(screen.getByRole('button', { name: 'Next week' }))

    expect(dateButton('Mon Jun 22')).toHaveAttribute('aria-current', 'date')
    await waitFor(() => expect(cardRequests().at(-1).startsOn).toBe('2026-06-22'))
    await user.click(screen.getByRole('button', { name: 'Previous week' }))
    expect(dateButton('Mon Jun 15')).toHaveAttribute('aria-current', 'date')
    await waitFor(() => expect(cardRequests().at(-1).startsOn).toBe(TODAY))
  })

  it('F20-3: selecting a date loads that day\'s posts from a fresh first batch', async () => {
    const user = userEvent.setup()
    signedOut()
    fakeApi({
      [CARDS]: cardsByRequest({
        [`all ${TODAY}`]: cardPage({
          posts: [card({ location_name: 'Today Field' })],
          hasMore: true,
          nextCursor: 'today-cursor',
        }),
        [`all ${TOMORROW}`]: cardPage({
          posts: [card({ location_name: 'Tomorrow Field', starts_at: '2026-06-16T23:00:00Z' })],
        }),
      }),
    })
    renderNeedASub()
    await screen.findByText('Today Field')

    await user.click(dateButton('Tue Jun 16'))

    expect(await screen.findByText('Tomorrow Field')).toBeInTheDocument()
    expect(screen.queryByText('Today Field')).not.toBeInTheDocument()
    expect(dateButton('Tue Jun 16')).toHaveAttribute('aria-current', 'date')
    expect(cardRequests().at(-1)).toEqual({ cursor: null, signedIn: false, startsOn: TOMORROW, view: 'all' })
  })

  // All Posts has a further batch; My Posts holds only the owner's post.
  function signedInOwner() {
    signedIn()
    fakeApi({
      [CARDS]: cardsByRequest({
        [`all ${TODAY}`]: cardPage({
          posts: [card({ location_name: 'Everyone Field' })],
          hasMore: true,
          nextCursor: 'all-cursor',
        }),
        [`mine ${TODAY}`]: cardPage({ posts: [card({ location_name: 'My Field' })] }),
      }),
    })
    renderNeedASub()
  }

  it('F20-4: My Posts shows only the signed-in owner\'s posts for that date', async () => {
    const user = userEvent.setup()
    signedInOwner()
    await screen.findByText('Everyone Field')

    await user.click(screen.getByRole('tab', { name: 'My Posts' }))

    expect(await screen.findByText('My Field')).toBeInTheDocument()
    expect(screen.queryByText('Everyone Field')).not.toBeInTheDocument()
    expect(cardRequests().at(-1)).toMatchObject({ signedIn: true, startsOn: TODAY, view: 'mine' })
  })

  it('F20-4: switching tab starts from its first batch', async () => {
    const user = userEvent.setup()
    signedInOwner()
    await screen.findByText('Everyone Field')

    await user.click(screen.getByRole('tab', { name: 'My Posts' }))

    await screen.findByText('My Field')
    expect(cardRequests().at(-1).cursor).toBeNull()
  })

  // Three posts, two starting in the 6 PM hour, sent in start-time order.
  function postsAcrossTwoHours() {
    signedOut()
    fakeApi({
      [CARDS]: cardPage({
        posts: [
          card({ location_name: 'Six Field', starts_at: '2026-06-15T23:00:00Z' }),
          card({ location_name: 'Six Thirty Field', starts_at: '2026-06-15T23:30:00Z' }),
          card({ location_name: 'Seven Field', starts_at: '2026-06-16T00:00:00Z' }),
        ],
      }),
    })
    renderNeedASub()
  }

  it('F20-5: posts are grouped by start hour', async () => {
    postsAcrossTwoHours()
    await findCards()

    const sixGroup = screen.getByRole('heading', { name: '6 PM' }).closest('section')
    const sevenGroup = screen.getByRole('heading', { name: '7 PM' }).closest('section')
    expect(within(sixGroup).getByText('2 posts')).toBeInTheDocument()
    expect(within(sixGroup).getByText('Six Thirty Field')).toBeInTheDocument()
    expect(within(sevenGroup).getByText('1 post')).toBeInTheDocument()
    expect(within(sevenGroup).getByText('Seven Field')).toBeInTheDocument()
  })

  it('F20-5: posts are shown in start-time order', async () => {
    const venues = ['Six Field', 'Six Thirty Field', 'Seven Field']
    postsAcrossTwoHours()
    await findCards()

    expect(cardVenues(venues)).toEqual(venues)
  })

  it.each([
    ['coed outdoor', 'coed', 'outdoor', 'Coed · 7v7 · Outdoor'],
    ['men\'s indoor', 'men', 'indoor', 'Men · 7v7 · Indoor'],
    ['women\'s outdoor', 'women', 'outdoor', 'Women · 7v7 · Outdoor'],
  ])('F20-6: a %s card shows venue, city/state, time, player group, format, and setting', async (
    _label, playerGroup, setting, traits,
  ) => {
    signedOut()
    fakeApi({
      [CARDS]: cardPage({
        posts: [card({ location_name: 'North Park', game_player_group: playerGroup, environment_type: setting })],
      }),
    })
    renderNeedASub()

    const [northPark] = await findCards()
    expect(within(northPark).getByText('North Park')).toBeInTheDocument()
    expect(within(northPark).getByText('Chicago, IL')).toBeInTheDocument()
    expect(within(northPark).getByText('6:00 PM-8:00 PM')).toBeInTheDocument()
    expect(within(northPark).getByText(traits)).toBeInTheDocument()
  })

  it('F20-6: each card retains its configured need labels, including a full need', async () => {
    signedOut()
    fakeApi({
      [CARDS]: cardPage({
        posts: [card({
          location_name: 'Mixed Field',
          positions: [
            position({ player_group: 'men', spots_needed: 2 }),
            position({ player_group: 'women', spots_needed: 1, confirmed_count: 1 }),
            position({ position_label: 'goalkeeper', player_group: 'open', spots_needed: 1 }),
          ],
        })],
      }),
    })
    renderNeedASub()

    const [mixedCard] = await findCards()
    expect(within(mixedCard).getByText(/Need/)).toHaveTextContent('Need 4 Subs')
    expect(mixedCard).toHaveTextContent(/Field Players\s*2 open\s*Men · Women/)
    expect(mixedCard).toHaveTextContent(/Goalkeepers\s*1 open\s*Any/)
  })

  it('F20-6: open and filled counts reflect confirmations rather than pending requests', async () => {
    signedOut()
    fakeApi({
      [CARDS]: cardPage({
        posts: [card({
          location_name: 'Busy Field',
          positions: [position({ player_group: 'open', spots_needed: 3, confirmed_count: 1, pending_count: 2 })],
        })],
      }),
    })
    renderNeedASub()

    const [busyCard] = await findCards()
    expect(busyCard).toHaveTextContent(/Field Players\s*2 open/)
    expect(within(busyCard).getByText('1/3 spots')).toBeInTheDocument()
  })

  it('F20-7: a signed-in visitor\'s card opens its Need a Sub post detail', async () => {
    const user = userEvent.setup()
    signedIn()
    const post = card({ location_name: 'North Park' })
    fakeApi({ [CARDS]: cardPage({ posts: [post] }) })
    const router = renderNeedASub()
    const [northPark] = await findCards()

    await user.click(northPark)

    expect(router.state.location.pathname).toBe(`/need-a-sub/posts/${post.id}`)
  })

  it.each([
    ['Enter', '{Enter}'],
    ['Space', ' '],
  ])('F20-7: pressing %s on a card opens its Need a Sub post detail', async (_label, key) => {
    const user = userEvent.setup()
    signedIn()
    const post = card({ location_name: 'North Park' })
    fakeApi({ [CARDS]: cardPage({ posts: [post] }) })
    const router = renderNeedASub()
    const [northPark] = await findCards()
    northPark.focus()

    await user.keyboard(key)

    expect(router.state.location.pathname).toBe(`/need-a-sub/posts/${post.id}`)
  })

  it('F20-7: Create Post opens the create panel on the same route', async () => {
    const user = userEvent.setup()
    signedIn()
    fakeApi({ [CARDS]: cardPage() })
    const router = renderNeedASub()
    await screen.findByText('No Need a Sub posts yet')

    await user.click(screen.getByRole('button', { name: 'Create Post' }))

    expect(screen.getByRole('heading', { name: 'Create Sub Post' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/need-a-sub')
  })

  // 10:30 PM on June 15 in Chicago is already June 16 on a device in Tokyo.
  function deviceInTokyoLateEvening() {
    process.env.TZ = 'Asia/Tokyo'
    vi.setSystemTime(new Date('2026-06-16T03:30:00Z'))
    signedOut()
    fakeApi({
      [CARDS]: cardPage({
        posts: [card({ location_name: 'Late Field', starts_at: '2026-06-16T04:00:00Z', ends_at: '2026-06-16T05:30:00Z' })],
      }),
    })
    renderNeedASub()
  }

  it('F20-16: the date strip follows the market time zone on any device', async () => {
    deviceInTokyoLateEvening()
    await findCards()

    expect(dateButton('Mon Jun 15')).toHaveAttribute('aria-current', 'date')
    expect(dateButtonNames()[0]).toBe('Mon Jun 15')
    expect(cardRequests()[0].startsOn).toBe(TODAY)
  })

  it('F20-16: card times and hour groups follow the market time zone on any device', async () => {
    deviceInTokyoLateEvening()
    const [lateCard] = await findCards()

    expect(within(lateCard).getByText('11:00 PM-12:30 AM')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '11 PM' })).toBeInTheDocument()
  })

  // Shows the page on June 15, then returns to it after midnight in Chicago.
  async function returnAfterMidnight() {
    signedOut()
    fakeApi({ [CARDS]: cardPage() })
    renderNeedASub()
    await screen.findByText('No Need a Sub posts yet')
    vi.setSystemTime(new Date('2026-06-16T05:30:00Z'))
    window.dispatchEvent(new Event('blur'))
    window.dispatchEvent(new Event('focus'))
  }

  it('F20-17: after midnight in the market time zone, the date strip starts at the new today', async () => {
    await returnAfterMidnight()

    await waitFor(() => expect(dateButtonNames()[0]).toBe('Tue Jun 16'))
    expect(dateButtonNames()).toHaveLength(7)
  })

  it('F20-17: a selected date that has not passed stays selected, on its set of dates', async () => {
    const user = userEvent.setup()
    signedOut()
    fakeApi({ [CARDS]: cardPage() })
    renderNeedASub()
    await screen.findByText('No Need a Sub posts yet')
    await user.click(screen.getByRole('button', { name: 'Next week' }))
    await user.click(dateButton('Tue Jun 23'))

    vi.setSystemTime(new Date('2026-06-16T05:30:00Z'))
    window.dispatchEvent(new Event('blur'))
    window.dispatchEvent(new Event('focus'))

    await waitFor(() => expect(dateButtonNames()[0]).toBe('Tue Jun 23'))
    expect(dateButton('Tue Jun 23')).toHaveAttribute('aria-current', 'date')
    await waitFor(() => expect(cardRequests().at(-1).startsOn).toBe('2026-06-23'))
  })

  it('F20-17: a selected date that has passed moves to today', async () => {
    await returnAfterMidnight()

    await waitFor(() => expect(dateButton('Tue Jun 16')).toHaveAttribute('aria-current', 'date'))
    await waitFor(() => expect(cardRequests().at(-1).startsOn).toBe(TOMORROW))
  })
})
