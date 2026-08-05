import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  AUDIENCE_TYPE_ALL_ELIGIBLE,
  AUDIENCE_TYPE_SELECTED,
  PLATFORM_NOTICE_SELECTED_USER_LIMIT,
  buildPlatformNoticeCancelPayload,
  buildPlatformNoticeCreatePayload,
  canAddPlatformNoticeSelectedUser,
  countPlatformNoticeHistorySearchMeaningfulCharacters,
  getActivePlatformNoticeHistorySearch,
  normalizePlatformNoticeHistorySearch,
  validatePlatformNoticeAudience,
  validatePlatformNoticeContent,
} from '../../src/pages/admin/platform-notices/adminPlatformNoticeData.js'

test('buildPlatformNoticeCreatePayload trims content and omits selected users for global notices', () => {
  const payload = buildPlatformNoticeCreatePayload({
    form: {
      audienceType: AUDIENCE_TYPE_ALL_ELIGIBLE,
      message: '  Line one\nLine two  ',
      title: '  Maintenance  ',
    },
    idempotencyKey: 'platform-notice-test-key',
    selectedUsers: [{ id: 'user-1' }],
  })

  assert.deepEqual(payload, {
    audience_type: AUDIENCE_TYPE_ALL_ELIGIBLE,
    idempotency_key: 'platform-notice-test-key',
    message: 'Line one\nLine two',
    selected_user_ids: [],
    title: 'Maintenance',
  })
})

test('buildPlatformNoticeCreatePayload includes selected user ids for selected notices', () => {
  const payload = buildPlatformNoticeCreatePayload({
    form: {
      audienceType: AUDIENCE_TYPE_SELECTED,
      message: 'Selected notice',
      title: 'Selected',
    },
    idempotencyKey: 'platform-notice-selected-key',
    selectedUsers: [{ id: 'user-1' }, { id: 'user-2' }],
  })

  assert.deepEqual(payload.selected_user_ids, ['user-1', 'user-2'])
})

test('validatePlatformNoticeContent requires title and message', () => {
  assert.equal(
    validatePlatformNoticeContent({ message: ' ', title: ' ' }),
    'Enter title, message.',
  )
})

test('validatePlatformNoticeAudience enforces selected recipients and cap', () => {
  assert.equal(PLATFORM_NOTICE_SELECTED_USER_LIMIT, 500)
  assert.equal(
    validatePlatformNoticeAudience(
      { audienceType: AUDIENCE_TYPE_SELECTED },
      [],
    ),
    'Select at least one active user.',
  )

  assert.equal(
    validatePlatformNoticeAudience(
      { audienceType: AUDIENCE_TYPE_SELECTED },
      Array.from(
        { length: PLATFORM_NOTICE_SELECTED_USER_LIMIT + 1 },
        (_, index) => ({ id: `user-${index}` }),
      ),
    ),
    `Selected notices cannot include more than ${PLATFORM_NOTICE_SELECTED_USER_LIMIT} users.`,
  )
})

test('buildPlatformNoticeCancelPayload trims cancellation reason', () => {
  assert.deepEqual(
    buildPlatformNoticeCancelPayload('  Wrong window.  '),
    { cancellation_reason: 'Wrong window.' },
  )
})

test('canAddPlatformNoticeSelectedUser blocks missing, duplicate, and capped users', () => {
  assert.equal(canAddPlatformNoticeSelectedUser(null, []), false)
  assert.equal(
    canAddPlatformNoticeSelectedUser(
      { id: 'user-1' },
      [{ id: 'user-1' }],
    ),
    false,
  )
  assert.equal(
    canAddPlatformNoticeSelectedUser(
      { id: 'user-over-limit' },
      Array.from(
        { length: PLATFORM_NOTICE_SELECTED_USER_LIMIT },
        (_, index) => ({ id: `user-${index}` }),
      ),
    ),
    false,
  )
  assert.equal(
    canAddPlatformNoticeSelectedUser(
      { id: 'user-2' },
      [{ id: 'user-1' }],
    ),
    true,
  )
})

test('platform notice history search normalizes whitespace and case', () => {
  assert.equal(
    normalizePlatformNoticeHistorySearch('  MAINT   Window  '),
    'maint window',
  )
  assert.equal(
    getActivePlatformNoticeHistorySearch('  MAINT   Window  '),
    'maint window',
  )
})

test('platform notice history search requires meaningful letters or numbers', () => {
  assert.equal(countPlatformNoticeHistorySearchMeaningfulCharacters('___'), 0)
  assert.equal(countPlatformNoticeHistorySearchMeaningfulCharacters('%%a_'), 1)
  assert.equal(getActivePlatformNoticeHistorySearch('ab'), '')
  assert.equal(getActivePlatformNoticeHistorySearch('___'), '')
  assert.equal(getActivePlatformNoticeHistorySearch('%%%'), '')
  assert.equal(getActivePlatformNoticeHistorySearch('--'), '')
  assert.equal(getActivePlatformNoticeHistorySearch('abc_def'), 'abc_def')
})
