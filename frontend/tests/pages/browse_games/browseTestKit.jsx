// Helpers for Browse Games tests: fake API responses and a page with a router.
//
// Each test file must also mock the API module and the navigation bar:
//   vi.mock('../../../src/pages/browse-games/browseGamesApi.js', () => ({
//     loadBrowseGamesPage: vi.fn(),
//   }))
//   vi.mock('../../../src/components/app/AppNav.jsx', () => ({
//     default: () => null,
//   }))

import { act, render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider, useParams } from 'react-router-dom'
import { afterEach, vi } from 'vitest'
import { loadBrowseGamesPage } from '../../../src/pages/browse-games/browseGamesApi.js'
import BrowseGamesPage from '../../../src/pages/browse-games/BrowseGamesPage.jsx'
import { checkBackendAnswer } from '../../backendFields.js'
import backendFields from './backend_fields.json'

// After each test, check every answer the faked API gave the page against the
// fields the backend really sends. Failed answers (simulated errors) and
// answers still waiting when the test ended are skipped. Don't change an
// answer after the page has received it: this check reads the same object.
afterEach(() => {
  for (const result of vi.mocked(loadBrowseGamesPage).mock.settledResults) {
    if (result.type === 'fulfilled') {
      checkBackendAnswer(backendFields, 'GET /games/browse', result.value)
    }
  }
})

export const TODAY = '2026-06-15'

export function addDays(dateKey, days) {
  const date = new Date(`${dateKey}T12:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

let nextCardNumber = 1

// Game IDs are UUIDs, as the backend sends them: gameId(1) is
// 00000000-0000-4000-8000-000000000001.
function gameId(number) {
  return `00000000-0000-4000-8000-${String(number).padStart(12, '0')}`
}

// One game card as the API returns it. Defaults: an official 6 PM game with
// 3 of 14 spots filled.
export function card(overrides = {}) {
  const number = nextCardNumber++
  const { occupied = 3, total = 14, availabilityStatus, ...rest } = overrides
  return {
    id: gameId(number),
    game_type: 'official',
    game_status: 'active',
    title: `Field ${number}`,
    display_title: `Field ${number}`,
    venue_name_snapshot: `Field ${number}`,
    city_snapshot: 'Chicago',
    state_snapshot: 'IL',
    location_label: 'Chicago, IL',
    starts_at: '2026-06-15T23:00:00Z',
    ends_at: '2026-06-16T00:00:00Z',
    starts_on_local: '2026-06-15',
    time_group_key: '18:00',
    timezone: 'America/Chicago',
    game_player_group: 'coed',
    format_label: '7v7',
    environment_type: 'outdoor',
    total_spots: total,
    participant_count: occupied,
    availability: {
      status: availabilityStatus ?? (occupied >= total ? 'full' : 'open'),
      occupied_spots: occupied,
      total_spots: total,
      spots_remaining: Math.max(total - occupied, 0),
    },
    price_per_player_cents: 1000,
    currency: 'USD',
    price_label: '$10',
    registration_closes_at: '2026-06-15T23:00:00Z',
    primary_image_url: null,
    ...rest,
  }
}

// One Browse API response. Hour totals default to the cards given.
export function page({
  date = TODAY,
  today = TODAY,
  games = [],
  timeGroups,
  hasMore = false,
  nextCursor = null,
} = {}) {
  return {
    browse_today: today,
    browse_timezone: 'America/Chicago',
    minimum_browse_date: today,
    maximum_browse_date: addDays(today, 13),
    browse_date: date,
    time_groups: timeGroups ?? groupsFor(games),
    games,
    next_cursor: nextCursor,
    has_more: hasMore,
    limit: 40,
  }
}

function groupsFor(games) {
  const totals = new Map()
  for (const game of games) {
    totals.set(game.time_group_key, (totals.get(game.time_group_key) ?? 0) + 1)
  }
  return [...totals].map(([groupKey, total]) => ({ group_key: groupKey, total_games: total }))
}

// A promise the test resolves or rejects later, to control response timing.
export function deferred() {
  let resolve
  let reject
  const promise = new Promise((promiseResolve, promiseReject) => {
    resolve = promiseResolve
    reject = promiseReject
  })
  return { promise, resolve, reject }
}

function GameDetailsStub() {
  const { gameId } = useParams()
  return <h1>Game details {gameId}</h1>
}

// Render Browse at `path`, after a previous page so Back can be tested.
export function renderBrowse(path = '/games/browse') {
  const router = createMemoryRouter(
    [
      { path: '/', element: <p>Previous page</p> },
      { path: '/games/browse', element: <BrowseGamesPage /> },
      { path: '/games/:gameId', element: <GameDetailsStub /> },
    ],
    { initialEntries: ['/', path], initialIndex: 1 },
  )
  render(<RouterProvider router={router} />)
  return router
}

export function linkDate(router) {
  return new URLSearchParams(router.state.location.search).get('date')
}

export function cardTitles() {
  return screen.queryAllByRole('heading', { level: 3 }).map((heading) => heading.textContent)
}

// Wait for cards, then let the page finish its follow-up work (such as starting
// the refresh timer) so the test continues from a settled page.
export async function waitForCards() {
  await screen.findAllByRole('heading', { level: 3 })
  await act(async () => {})
  return cardTitles()
}

export function selectedDateButton() {
  return document.querySelector('[aria-current="date"]')
}
