import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { loadBrowseGamesPage } from '../../../src/pages/browse-games/browseGamesApi.js'
import { card, cardLink, page, renderBrowse, TODAY, waitForCards } from './browseTestKit.jsx'

vi.mock('../../../src/pages/browse-games/browseGamesApi.js', () => ({ loadBrowseGamesPage: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))

const originalTimeZone = process.env.TZ
afterEach(() => { process.env.TZ = originalTimeZone })

it("F15-1: guests and signed-in visitors see the same Browse cards", async () => {
  const game = card({ display_title: 'Public Field' })
  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  const guest = renderBrowse(`/games/browse?date=${TODAY}`, { signedIn: false })
  await waitForCards()
  const guestCard = cardLink('Public Field').outerHTML
  guest.unmount()
  renderBrowse(`/games/browse?date=${TODAY}`, { signedIn: true })
  await waitForCards()
  expect(cardLink('Public Field').outerHTML).toBe(guestCard)
})

it("F15-1: public cards display no personal participation or hosting state", async () => {
  const game = card({ game_type: 'community', display_title: 'Public Run' })
  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  renderBrowse(`/games/browse?date=${TODAY}`, { signedIn: true })
  await waitForCards()
  expect(cardLink('Public Run')).not.toHaveTextContent(/you are hosting|your game|joined|on the waitlist|your booking/i)
})

it("F15-6: official and community games share the list", async () => {
  loadBrowseGamesPage.mockResolvedValue(page({ games: [
    card({ display_title: 'Official Field' }),
    card({ game_type: 'community', display_title: 'Community Run' }),
  ] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  expect(await waitForCards()).toEqual(['Official Field', 'Community Run'])
})

it.each(['full', 'waitlist_open'])("F15-8: a full game with availability %s shows Full", async (status) => {
  const game = card({ display_title: 'Packed Field', occupied: 14, availabilityStatus: status })

  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  const link = cardLink(game.display_title)
  expect(within(link).getByText('Full')).toBeInTheDocument()
})

it.each(['full', 'waitlist_open'])("F15-8: a full game with availability %s has no separate waitlist badge", async (status) => {
  const game = card({ display_title: 'Packed Field', occupied: 14, availabilityStatus: status })

  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  const link = cardLink(game.display_title)
  expect(link).not.toHaveTextContent(/waitlist/i)
})

it.each([['official', 'Official'], ['community', 'Community']])("F15-11: a %s card shows its game type", async (type, label) => {
  const game = card({ game_type: type })

  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  const link = cardLink(game.display_title)
  expect(within(link).getByText(label)).toBeInTheDocument()
})

it("F15-11: an official card uses the venue title", async () => {
  const game = card({ display_title: 'Lakefront Turf', venue_name_snapshot: 'Lakefront Turf', title: 'Internal game title' })

  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  const link = cardLink(game.display_title)
  expect(within(link).getByRole('heading', { level: 3 })).toHaveTextContent('Lakefront Turf')
})

it("F15-11: a community card uses the host game title", async () => {
  const game = card({ game_type: 'community', display_title: 'Sunday Night Run', title: 'Sunday Night Run', venue_name_snapshot: 'Lakefront Turf' })

  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  const link = cardLink(game.display_title)
  expect(within(link).getByRole('heading', { level: 3 })).toHaveTextContent('Sunday Night Run')
})

it.each(['official', 'community'])("F15-11: a %s card shows city and state", async (type) => {
  const game = card({ game_type: type, city_snapshot: 'Evanston', state_snapshot: 'IL', location_label: 'Evanston, IL' })

  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  const link = cardLink(game.display_title)
  expect(within(link).getByText('Evanston, IL')).toBeInTheDocument()
})

it.each(['official', 'community'].flatMap((type) => [
  [type, 'summer', '2026-06-15', '2026-06-15T23:30:00Z', '2026-06-16T00:30:00Z', '6:30 PM - 7:30 PM'],
  [type, 'spring', '2026-03-08', '2026-03-08T07:30:00Z', '2026-03-08T08:30:00Z', '1:30 AM - 3:30 AM'],
  [type, 'fall', '2026-11-01', '2026-11-01T06:30:00Z', '2026-11-01T07:30:00Z', '1:30 AM - 1:30 AM'],
]))("F15-11 F15-22: %s card times use Chicago time on a Tokyo device in %s", async (type, _season, date, startsAt, endsAt, expected) => {
  process.env.TZ = 'Asia/Tokyo'
  const game = card({ game_type: type, date, starts_at: startsAt, ends_at: endsAt })
  loadBrowseGamesPage.mockResolvedValue(page({ date, today: date, games: [game] }))
  renderBrowse(`/games/browse?date=${date}`)
  await waitForCards()
  expect(within(cardLink(game.display_title)).getByText(expected)).toBeInTheDocument()
})

it.each(['official', 'community'].flatMap((type) => [['men', 'Men'], ['women', 'Women'], ['coed', 'Coed']].map(([group, label]) => [type, group, label])))("F15-11: a %s card shows player group %s", async (type, group, label) => {
  const game = card({ game_type: type, game_player_group: group })

  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  const link = cardLink(game.display_title)
  expect(link).toHaveTextContent(label)
})

it.each(['official', 'community'].flatMap((type) => ['5v5', '7v7', '11v11'].map((format) => [type, format])))("F15-11: a %s card shows format %s", async (type, format) => {
  const game = card({ game_type: type, format_label: format })

  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  const link = cardLink(game.display_title)
  expect(link).toHaveTextContent(format)
})

it.each(['official', 'community'].flatMap((type) => [['indoor', 'Indoor'], ['outdoor', 'Outdoor']].map(([environment, label]) => [type, environment, label])))("F15-11: a %s card shows its %s setting", async (type, environment, label) => {
  const game = card({ game_type: type, environment_type: environment })

  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  const link = cardLink(game.display_title)
  expect(link).toHaveTextContent(label)
})

it.each(['official', 'community'])("F15-11: a %s card shows filled spots out of capacity", async (type) => {
  const game = card({ game_type: type, occupied: 3, total: 10 })

  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  const link = cardLink(game.display_title)
  expect(within(link).getByText('3/10')).toBeInTheDocument()
})

it.each(['official', 'community'])("F15-11: a paid %s card shows its per-player price", async (type) => {
  const game = card({ game_type: type, price_per_player_cents: 1250, price_label: '$12.50' })

  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  const link = cardLink(game.display_title)
  expect(within(link).getByText('$12.50')).toBeInTheDocument()
})

it.each(['official', 'community'])("F15-11: a free %s card shows Free", async (type) => {
  const game = card({ game_type: type, price_per_player_cents: 0, price_label: 'Free' })

  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  const link = cardLink(game.display_title)
  expect(within(link).getByText('Free')).toBeInTheDocument()
})

it("F15-11: a game with an available spot has no Full badge", async () => {
  const game = card({ occupied: 13, total: 14 })

  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  const link = cardLink(game.display_title)
  expect(within(link).queryByText('Full')).not.toBeInTheDocument()
})

it.each(['official', 'community'])("F15-12: a %s card shows the API image", async (type) => {
  const game = card({ game_type: type, primary_image_url: 'https://cdn.example.test/field.jpg' })

  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  const link = cardLink(game.display_title)
  expect(link.querySelector('img')).toHaveAttribute('src', 'https://cdn.example.test/field.jpg')
})

it.each(['official', 'community'])("F15-12: a %s card without media keeps its default visual", async (type) => {
  const game = card({ game_type: type })

  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  const link = cardLink(game.display_title)

  if (type === 'community') {
    expect(link.querySelector('img')).toHaveAttribute('src', expect.stringMatching(/default-venue-wide/))
  } else {
    expect(link.querySelector('img')).toBeNull()
    expect(link.querySelector('.game-card__fallback svg')).not.toBeNull()
  }
})

it("F15-13: community cards do not show host payment instructions", async () => {
  const game = card({ game_type: 'community' })

  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  const link = cardLink(game.display_title)
  expect(link).not.toHaveTextContent(/payment instructions|pay the host|venmo|zelle/i)
})

it("F15-13: cards do not show skill level", async () => {
  const game = card()

  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  const link = cardLink(game.display_title)
  expect(link).not.toHaveTextContent(/skill level|beginner|intermediate|competitive/i)
})

it("F15-14: choosing a card opens its Game Details page", async () => {
  const user = userEvent.setup()
  const game = card({ display_title: 'Open Field' })
  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  const { router } = renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  await user.click(cardLink('Open Field'))
  expect(await screen.findByRole('heading', { name: `Game details ${game.id}` })).toBeInTheDocument()
  expect(router.state.location.pathname).toBe(`/games/${game.id}`)
})

it("F15-14: choosing a card sends no reservation or notification request", async () => {
  const user = userEvent.setup()
  const game = card({ display_title: 'Open Field' })

  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  const link = cardLink(game.display_title)

  await user.click(link)
  await screen.findByRole('heading', { name: `Game details ${game.id}` })
  expect(fetch).not.toHaveBeenCalled()
  expect(loadBrowseGamesPage).toHaveBeenCalledTimes(1)
})

it("F15-22: hour headings use market hours on a Tokyo device", async () => {
  process.env.TZ = 'Asia/Tokyo'
  const game = card({ starts_at: '2026-06-15T23:30:00Z', ends_at: '2026-06-16T00:30:00Z' })
  loadBrowseGamesPage.mockResolvedValue(page({ games: [game] }))
  renderBrowse(`/games/browse?date=${TODAY}`)
  await waitForCards()
  expect(screen.getByRole('heading', { level: 2, name: '6 PM' })).toBeInTheDocument()
})
