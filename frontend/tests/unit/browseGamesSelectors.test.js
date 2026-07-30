import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  formatTimeGroupLabel,
  formatTimeRange,
} from '../../src/pages/browse-games/browseGameFormatters.js'
import {
  buildBrowseMetaFromPageData,
  buildDateOptions,
  buildSelectedDateResetMeta,
  getDatePageIndexForDate,
  getNextBrowseListGeneration,
  groupLoadedGamesByTimeGroups,
  isDateKey,
  resolveRequestedDateKey,
  shouldApplyBrowseRequest,
} from '../../src/pages/browse-games/browseGamesSelectors.js'

test('buildDateOptions builds the backend-owned inclusive browse window', () => {
  const dates = buildDateOptions({
    minimumDate: '2026-07-28',
    maximumDate: '2026-08-10',
    timeZone: 'America/Chicago',
  })

  assert.equal(dates.length, 14)
  assert.equal(dates[0].key, '2026-07-28')
  assert.equal(dates[13].key, '2026-08-10')
  assert.deepEqual(
    dates.map((date) => date.key).slice(0, 3),
    ['2026-07-28', '2026-07-29', '2026-07-30'],
  )
})

test('buildDateOptions uses calendar dates across DST boundaries', () => {
  const dates = buildDateOptions({
    minimumDate: '2026-03-07',
    maximumDate: '2026-03-20',
    timeZone: 'America/Chicago',
  })

  assert.equal(dates.length, 14)
  assert.equal(new Set(dates.map((date) => date.key)).size, 14)
  assert.equal(dates[1].key, '2026-03-08')
  assert.equal(dates[2].key, '2026-03-09')
})

test('isDateKey accepts real date keys only', () => {
  assert.equal(isDateKey('2026-07-28'), true)
  assert.equal(isDateKey('2026-02-30'), false)
  assert.equal(isDateKey('07/28/2026'), false)
  assert.equal(isDateKey('2026-7-28'), false)
})

test('resolveRequestedDateKey returns only valid URL date keys', () => {
  assert.equal(resolveRequestedDateKey('2026-07-28'), '2026-07-28')
  assert.equal(resolveRequestedDateKey('2026-02-30'), '')
  assert.equal(resolveRequestedDateKey('bad-date'), '')
})

test('getDatePageIndexForDate selects the visible page containing the active date', () => {
  const dates = buildDateOptions({
    minimumDate: '2026-07-28',
    maximumDate: '2026-08-10',
    timeZone: 'America/Chicago',
  })

  assert.equal(getDatePageIndexForDate(dates, '2026-07-28', 7), 0)
  assert.equal(getDatePageIndexForDate(dates, '2026-08-03', 7), 0)
  assert.equal(getDatePageIndexForDate(dates, '2026-08-04', 7), 1)
  assert.equal(getDatePageIndexForDate(dates, '2026-08-10', 7), 1)
  assert.equal(getDatePageIndexForDate(dates, '2026-08-11', 7), null)
})

test('buildBrowseMetaFromPageData keeps backend browse context and defaults groups', () => {
  assert.deepEqual(
    buildBrowseMetaFromPageData({
      browse_date: '2026-07-28',
      browse_timezone: 'America/Chicago',
      browse_today: '2026-07-28',
      maximum_browse_date: '2026-08-10',
      minimum_browse_date: '2026-07-28',
    }),
    {
      browse_date: '2026-07-28',
      browse_timezone: 'America/Chicago',
      browse_today: '2026-07-28',
      maximum_browse_date: '2026-08-10',
      minimum_browse_date: '2026-07-28',
      time_groups: [],
    },
  )
})

test('buildSelectedDateResetMeta clears stale time groups while keeping window context', () => {
  assert.deepEqual(
    buildSelectedDateResetMeta(
      {
        browse_date: '2026-07-28',
        browse_timezone: 'America/Chicago',
        browse_today: '2026-07-28',
        maximum_browse_date: '2026-08-10',
        minimum_browse_date: '2026-07-28',
        time_groups: [{ group_key: '18:00', total_games: 3 }],
      },
      '2026-07-29',
    ),
    {
      browse_date: '2026-07-29',
      browse_timezone: 'America/Chicago',
      browse_today: '2026-07-28',
      maximum_browse_date: '2026-08-10',
      minimum_browse_date: '2026-07-28',
      time_groups: [],
    },
  )
  assert.equal(buildSelectedDateResetMeta(null, '2026-07-29'), null)
})

test('shouldApplyBrowseRequest rejects stale versions and stale date responses', () => {
  assert.equal(
    shouldApplyBrowseRequest({
      currentDateKey: '2026-07-28',
      currentVersion: 2,
      requestDateKey: '2026-07-28',
      requestVersion: 2,
    }),
    true,
  )
  assert.equal(
    shouldApplyBrowseRequest({
      currentDateKey: '2026-07-29',
      currentVersion: 2,
      requestDateKey: '2026-07-28',
      requestVersion: 2,
    }),
    false,
  )
  assert.equal(
    shouldApplyBrowseRequest({
      currentDateKey: '2026-07-28',
      currentVersion: 3,
      requestDateKey: '2026-07-28',
      requestVersion: 2,
    }),
    false,
  )
})

test('getNextBrowseListGeneration changes for list resets and replacements', () => {
  assert.equal(getNextBrowseListGeneration(0), 1)
  assert.equal(getNextBrowseListGeneration(4), 5)
  assert.equal(getNextBrowseListGeneration(4, { append: true }), 4)
})

test('shouldApplyBrowseRequest rejects load-more responses from an old list generation', () => {
  assert.equal(
    shouldApplyBrowseRequest({
      currentDateKey: '2026-07-28',
      currentGeneration: 3,
      currentVersion: 5,
      requestDateKey: '2026-07-28',
      requestGeneration: 3,
      requestVersion: 5,
    }),
    true,
  )
  assert.equal(
    shouldApplyBrowseRequest({
      currentDateKey: '2026-07-28',
      currentGeneration: 4,
      currentVersion: 5,
      requestDateKey: '2026-07-28',
      requestGeneration: 3,
      requestVersion: 5,
    }),
    false,
  )
})

test('shouldApplyBrowseRequest allows load-more validation without refresh versions', () => {
  assert.equal(
    shouldApplyBrowseRequest({
      currentDateKey: '2026-07-28',
      currentGeneration: 7,
      requestDateKey: '2026-07-28',
      requestGeneration: 7,
    }),
    true,
  )
  assert.equal(
    shouldApplyBrowseRequest({
      currentDateKey: '2026-07-28',
      currentGeneration: 8,
      requestDateKey: '2026-07-28',
      requestGeneration: 7,
    }),
    false,
  )
})

test('groupLoadedGamesByTimeGroups uses backend totals and skips unloaded groups', () => {
  const grouped = groupLoadedGamesByTimeGroups(
    [
      { id: 'game-1', time_group_key: '18:00' },
      { id: 'game-2', time_group_key: '18:00' },
      { id: 'game-3', time_group_key: '19:00' },
    ],
    [
      { group_key: '18:00', total_games: 45 },
      { group_key: '19:00', total_games: 1 },
      { group_key: '20:00', total_games: 8 },
    ],
  )

  assert.deepEqual(
    grouped.map((group) => ({
      key: group.key,
      totalGames: group.totalGames,
      gameIds: group.games.map((game) => game.id),
    })),
    [
      {
        key: '18:00',
        totalGames: 45,
        gameIds: ['game-1', 'game-2'],
      },
      {
        key: '19:00',
        totalGames: 1,
        gameIds: ['game-3'],
      },
    ],
  )
})

test('groupLoadedGamesByTimeGroups falls back safely for unknown group keys', () => {
  const grouped = groupLoadedGamesByTimeGroups(
    [{ id: 'game-1', time_group_key: '21:00' }],
    [{ group_key: '18:00', total_games: 2 }],
  )

  assert.deepEqual(grouped, [
    {
      key: '21:00',
      label: '21:00',
      totalGames: 1,
      games: [{ id: 'game-1', time_group_key: '21:00' }],
    },
  ])
})

test('formatTimeGroupLabel formats stable backend group keys', () => {
  assert.equal(formatTimeGroupLabel('00:00'), '12 AM')
  assert.equal(formatTimeGroupLabel('12:00'), '12 PM')
  assert.equal(formatTimeGroupLabel('18:00'), '6 PM')
  assert.equal(formatTimeGroupLabel('18:30'), '6:30 PM')
  assert.equal(formatTimeGroupLabel('bad-key'), 'bad-key')
})

test('formatTimeRange uses the returned browse timezone', () => {
  assert.equal(
    formatTimeRange(
      '2026-07-28T23:00:00Z',
      '2026-07-29T00:30:00Z',
      { separator: ' - ', timeZone: 'America/Chicago' },
    ),
    '6:00 PM - 7:30 PM',
  )
})
