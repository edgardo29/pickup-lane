import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  fakePageApi, GAMES, gameItem, NEED_A_SUB, page, postItem, renderMyGames, signIn,
} from './myGamesTestKit.jsx'

vi.mock('../../../src/lib/apiClient.js', async (importOriginal) => ({
  ...(await importOriginal()),
  apiRequest: vi.fn(),
}))
vi.mock('../../../src/hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))

beforeEach(() => signIn())

// 23:00 UTC on June 15 is 6:00 PM in Chicago.
const STARTS_AT = '2030-06-15T23:00:00Z'

describe('My Games card contents', () => {
  it('F19-1: a game card shows its type, venue, time, location, format, spots, price, and status', async () => {
    fakePageApi({
      [GAMES]: page([gameItem({
        venue: 'Harrison Park', startsAt: STARTS_AT, isHost: true,
        game: { game_type: 'community', participant_count: 6, total_spots: 14, price_per_player_cents: 1000 },
      })]),
    })
    renderMyGames()

    const card = await screen.findByRole('link', { name: /Harrison Park/ })

    expect(within(card).getByText('Community')).toBeInTheDocument()
    expect(within(card).getByRole('heading', { name: 'Harrison Park' })).toBeInTheDocument()
    expect(within(card).getByText('6:00 PM - 7:00 PM')).toBeInTheDocument()
    expect(within(card).getByText('Chicago, IL')).toBeInTheDocument()
    expect(within(card).getByText('Coed · 7v7 · Outdoor')).toBeInTheDocument()
    expect(card).toHaveTextContent('6/14 spots')
    expect(within(card).getByText('$10')).toBeInTheDocument()
    expect(within(card).getByText('Hosting')).toBeInTheDocument()
  })

  it('F19-1: an official game card shows the Official type', async () => {
    fakePageApi({ [GAMES]: page([gameItem({ venue: 'Central Field' })]) })
    renderMyGames()

    const card = await screen.findByRole('link', { name: /Central Field/ })

    expect(within(card).getByText('Official')).toBeInTheDocument()
  })

  it.each([
    ['Men', 'men', 'indoor', 'Men · 7v7 · Indoor'],
    ['Women', 'women', 'outdoor', 'Women · 7v7 · Outdoor'],
  ])('F19-1: a game card shows the %s player group', async (_label, playerGroup, setting, format) => {
    fakePageApi({
      [GAMES]: page([gameItem({
        venue: 'Central Field', game: { game_player_group: playerGroup, environment_type: setting },
      })]),
    })
    renderMyGames()

    const card = await screen.findByRole('link', { name: /Central Field/ })

    expect(within(card).getByText(format)).toBeInTheDocument()
  })

  it('F19-1: a Need a Sub card shows goalkeeper needs and men\'s and women\'s needs', async () => {
    const user = userEvent.setup()
    const postId = '00000000-0000-4000-8000-0000000000a0'
    const position = (id, positionLabel, playerGroup, sortOrder, confirmedCount = 0) => ({
      id, sub_post_id: postId, position_label: positionLabel, player_group: playerGroup,
      spots_needed: 1, confirmed_count: confirmedCount, pending_count: 0, sub_waitlist_count: 0,
      sort_order: sortOrder, created_at: '2029-06-15T18:00:00Z', updated_at: '2029-06-15T18:00:00Z',
    })
    fakePageApi({
      [NEED_A_SUB]: page([postItem({
        id: postId, location: 'Union Park',
        post: {
          subs_needed: 3,
          confirmed_count: 1,
          positions: [
            position('00000000-0000-4000-8000-0000000000a1', 'field_player', 'men', 1),
            position('00000000-0000-4000-8000-0000000000a2', 'field_player', 'women', 2, 1),
            position('00000000-0000-4000-8000-0000000000a3', 'goalkeeper', 'open', 3),
          ],
        },
      })]),
    })
    renderMyGames()

    await user.click(await screen.findByRole('tab', { name: 'Need a Sub' }))
    const card = await screen.findByRole('link', { name: /Union Park/ })

    expect(card).toHaveTextContent(/Field Players\s*1 open\s*Men · Women/)
    expect(card).toHaveTextContent(/Goalkeepers\s*1 open\s*Any/)
  })

  it('F19-1: a hosted game card in History shows the Hosted status', async () => {
    const user = userEvent.setup()
    fakePageApi({
      [GAMES]: ({ view }) => page(view === 'history' ? [gameItem({
        venue: 'Hosted Past Field', bucket: 'history', isHost: true, startsAt: '2030-05-01T23:00:00Z',
        game: { game_type: 'community' },
      })] : []),
    })
    renderMyGames()

    await user.click(await screen.findByRole('tab', { name: 'History' }))
    const card = await screen.findByRole('link', { name: /Hosted Past Field/ })

    expect(within(card).getByText('Hosted')).toBeInTheDocument()
  })

  it('F19-1: a Need a Sub card shows the outside game, sub needs, confirmed and open counts, and status', async () => {
    const user = userEvent.setup()
    fakePageApi({ [NEED_A_SUB]: page([postItem({ location: 'Union Park', startsAt: STARTS_AT })]) })
    renderMyGames()

    await user.click(await screen.findByRole('tab', { name: 'Need a Sub' }))
    const card = await screen.findByRole('link', { name: /Union Park/ })

    expect(card).toHaveTextContent('Need 2 Subs')
    expect(within(card).getByText('Union Park')).toBeInTheDocument()
    expect(within(card).getByText('Chicago, IL')).toBeInTheDocument()
    expect(within(card).getByText('6:00 PM - 7:00 PM')).toBeInTheDocument()
    expect(within(card).getByText('Coed · 7v7 · Outdoor')).toBeInTheDocument()
    expect(within(card).getByText('1 open')).toBeInTheDocument()
    expect(card).toHaveTextContent('1/2 spots')
    expect(within(card).getByText('Owner')).toBeInTheDocument()
  })

  // 04:30 UTC on June 16 is 11:30 PM on June 15 in Chicago, where these games
  // and posts are, but 1:30 PM on June 16 on a device set to Tokyo time.
  const LATE_EVENING = '2030-06-16T04:30:00Z'

  function useDeviceInTokyo() {
    const DeviceDateTimeFormat = Intl.DateTimeFormat
    vi.spyOn(Intl, 'DateTimeFormat').mockImplementation(function deviceFormat(locale, options) {
      return new DeviceDateTimeFormat(locale, { timeZone: 'Asia/Tokyo', ...options })
    })
  }

  function dateGroupOf(card) {
    return card.closest('section').querySelector('h2').textContent
  }

  it('F19-14: a game card\'s date, time, and date group follow the game\'s local time zone', async () => {
    useDeviceInTokyo()
    fakePageApi({ [GAMES]: page([gameItem({ venue: 'Late Field', startsAt: LATE_EVENING })]) })
    renderMyGames()

    const card = await screen.findByRole('link', { name: /Late Field/ })

    expect(within(card).getByText('11:30 PM - 12:30 AM')).toBeInTheDocument()
    expect(dateGroupOf(card)).toBe('SAT, JUN 15')
  })

  it('F19-14: a Need a Sub card\'s date, time, and date group follow the post\'s local time zone', async () => {
    const user = userEvent.setup()
    useDeviceInTokyo()
    fakePageApi({ [NEED_A_SUB]: page([postItem({ location: 'Late Park', startsAt: LATE_EVENING })]) })
    renderMyGames()

    await user.click(await screen.findByRole('tab', { name: 'Need a Sub' }))
    const card = await screen.findByRole('link', { name: /Late Park/ })

    expect(within(card).getByText('11:30 PM - 12:30 AM')).toBeInTheDocument()
    expect(dateGroupOf(card)).toBe('SAT, JUN 15')
  })

  it('F19-6: a cancelled card shows the cancellation status', async () => {
    const user = userEvent.setup()
    const cancelled = { status_label: 'Cancelled', status_tone: 'cancelled' }
    fakePageApi({
      [GAMES]: ({ view }) => page(view === 'history' ? [gameItem({
        venue: 'Cancelled Field', bucket: 'history', startsAt: '2030-05-01T23:00:00Z',
        game: { game_status: 'cancelled' },
        card: { ...cancelled, participant_status: 'cancelled', cancellation_type: 'host_cancelled' },
      })] : []),
      [NEED_A_SUB]: ({ view }) => page(view === 'history' ? [postItem({
        location: 'Cancelled Sub Field', bucket: 'history', canViewDetail: false, isOwner: false,
        startsAt: '2030-05-01T23:00:00Z', post: { post_status: 'cancelled' },
        card: { ...cancelled, request_status: 'canceled_by_owner' },
      })] : []),
    })
    renderMyGames()

    await user.click(await screen.findByRole('tab', { name: 'History' }))
    const gameCard = await screen.findByRole('link', { name: /Cancelled Field/ })
    expect(within(gameCard).getByText('Cancelled')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Need a Sub' }))
    const postCard = (await screen.findByText('Cancelled Sub Field')).closest('article')
    expect(within(postCard).getByText('Cancelled')).toBeInTheDocument()
  })
})
