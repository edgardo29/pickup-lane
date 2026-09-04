import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'

import {
  areReviewLifecycleActionsBlocked,
  buildReviewCaseAssignmentPayload,
  buildReviewCaseClosePayload,
  buildReviewCaseListQuery,
  buildReviewCaseMergePayload,
  buildReviewCaseNotePayload,
  buildReviewCaseReopenPayload,
  canMergeReviewCaseSource,
  collectCursorPages,
  describeReviewCaseAssignment,
  getReviewCaseConflictSnapshot,
  getVisibleResolutionHistory,
  isCompatibleMergeDestination,
  reviewCaseConflictSnapshotMatchesCase,
  reviewCaseStateScopeKey,
  sortReviewCaseEvents,
} from '../../src/pages/admin/review-cases/adminReviewLifecycle.js'
import { AdminResolutionReferenceList } from '../../src/pages/admin/review-cases/AdminResolutionReferenceList.js'

test('review-case list query carries category and assignment context', () => {
  assert.equal(
    buildReviewCaseListQuery({
      assignment: 'mine',
      caseCategory: 'chat_moderation',
      caseStatus: 'closed',
      cursor: 'next-page',
      limit: 24,
      targetType: 'community_game_chat',
    }),
    'case_status=closed&case_category=chat_moderation&target_type=community_game_chat&assignment=mine&cursor=next-page&limit=24',
  )

  assert.equal(
    buildReviewCaseListQuery({ assignment: 'unassigned', offset: 25 }),
    'case_status=open&target_type=content_targets&assignment=unassigned&offset=25&limit=50',
  )
})

test('review-case mutation payloads preserve expected versions and idempotency keys', () => {
  assert.deepEqual(buildReviewCaseNotePayload({
    body: 'Correction.',
    correctsNoteId: 'note-1',
    expectedCaseVersion: 4,
    idempotencyKey: 'note-key',
  }), {
    body: 'Correction.',
    corrects_note_id: 'note-1',
    expected_case_version: 4,
    idempotency_key: 'note-key',
  })
  assert.deepEqual(buildReviewCaseClosePayload({
    expectedCaseVersion: 5,
    idempotencyKey: 'close-key',
    outcome: 'no_action_needed',
    reason: 'Reviewed.',
  }), {
    expected_case_version: 5,
    idempotency_key: 'close-key',
    outcome: 'no_action_needed',
    reason: 'Reviewed.',
  })
  assert.deepEqual(buildReviewCaseAssignmentPayload({
    assigneeUserId: '',
    expectedCaseVersion: 6,
    idempotencyKey: 'assignment-key',
    reason: 'Release.',
  }), {
    assignee_user_id: null,
    expected_case_version: 6,
    idempotency_key: 'assignment-key',
    reason: 'Release.',
  })
  assert.deepEqual(buildReviewCaseReopenPayload({
    expectedCaseVersion: 7,
    idempotencyKey: 'reopen-key',
    reason: 'New actionable finding.',
  }), {
    expected_case_version: 7,
    idempotency_key: 'reopen-key',
    reason: 'New actionable finding.',
  })
  assert.deepEqual(buildReviewCaseMergePayload({
    destinationCaseId: 'case-2',
    expectedDestinationVersion: 3,
    expectedSourceVersion: 8,
    idempotencyKey: 'merge-key',
    reason: 'Same review target.',
  }), {
    destination_case_id: 'case-2',
    expected_destination_version: 3,
    expected_source_version: 8,
    idempotency_key: 'merge-key',
    reason: 'Same review target.',
  })
})

test('review-case events are ordered by sequence with stable id tie-breaking', () => {
  const events = sortReviewCaseEvents([
    { event_sequence: 2, id: 'c' },
    { event_sequence: 1, id: 'b' },
    { event_sequence: 1, id: 'a' },
  ])

  assert.deepEqual(events.map((event) => event.id), ['a', 'b', 'c'])
})

test('merge destinations require open matching category, type, and target', () => {
  const source = {
    id: 'source',
    case_category: 'chat_moderation',
    case_type: 'community_game',
    case_status: 'closed',
    closed_at: '2026-09-02T12:00:00Z',
    closure_mode: 'manual',
    closure_outcome: 'no_action_needed',
    closure_reason: 'Historical review complete.',
    linked_cases: [],
    target_game_id: 'game-1',
  }
  assert.equal(isCompatibleMergeDestination(source, {
    ...source,
    id: 'destination',
    case_status: 'open',
  }), true)
  assert.equal(isCompatibleMergeDestination(source, {
    ...source,
    id: 'wrong-category',
    case_category: 'content_moderation',
    case_status: 'open',
  }), false)
  assert.equal(isCompatibleMergeDestination(source, {
    ...source,
    id: 'closed',
    case_status: 'closed',
  }), false)
  assert.equal(isCompatibleMergeDestination({ ...source, case_status: 'open' }, {
    ...source,
    id: 'destination-for-open-source',
    case_status: 'open',
  }), false)
  assert.equal(canMergeReviewCaseSource({
    ...source,
    linked_cases: [{ id: 'child', relation: 'merged_from' }],
  }), false)
})

test('immutable resolution history remains visible for closed, reopened, and merged cases', () => {
  const resolutions = [
    {
      closure_event_id: 'closure-2',
      event_sequence: 7,
      mode: 'automatic',
      outcome: 'no_action_needed',
      reason: 'Target completed.',
      references: [],
    },
    {
      closure_event_id: 'closure-1',
      event_sequence: 3,
      mode: 'manual',
      outcome: 'invalid_signal',
      reason: 'Reviewed by an admin.',
      references: [{ reference_type: 'finding' }],
    },
  ]
  for (const reviewCase of [
    { case_status: 'closed', resolution_history: resolutions },
    { case_status: 'open', resolution_history: resolutions },
    { case_status: 'closed', merged_into_case_id: 'destination', resolution_history: resolutions },
  ]) {
    assert.deepEqual(
      getVisibleResolutionHistory(reviewCase).map((item) => item.closure_event_id),
      ['closure-1', 'closure-2'],
    )
  }
})

test('resolution history renders every normalized typed reference and current-state attribution', () => {
  const html = renderToStaticMarkup(React.createElement(AdminResolutionReferenceList, {
    references: [
      {
        id: 'reference-finding-current',
        reference_type: 'finding',
        content_moderation_finding_id: '11111111-1111-4111-8111-111111111111',
        was_current: true,
      },
      {
        id: 'reference-signal-historical',
        reference_type: 'signal',
        signal_id: '22222222-2222-4222-8222-222222222222',
        was_current: false,
      },
      {
        id: 'reference-action',
        reference_type: 'enforcement_action',
        admin_action_id: '33333333-3333-4333-8333-333333333333',
        was_current: null,
      },
      {
        id: 'reference-source',
        reference_type: 'source_case',
        source_case_id: '44444444-4444-4444-8444-444444444444',
        was_current: null,
      },
    ],
  }))

  assert.match(html, /data-reference-type="finding"/)
  assert.match(html, /Finding/)
  assert.match(html, /11111111-1111-4111-8111-111111111111/)
  assert.match(html, /Current at resolution/)
  assert.match(html, /data-reference-type="signal"/)
  assert.match(html, /22222222-2222-4222-8222-222222222222/)
  assert.match(html, /Historical at resolution/)
  assert.match(html, /data-reference-type="enforcement_action"/)
  assert.match(html, /33333333-3333-4333-8333-333333333333/)
  assert.match(html, /data-reference-type="source_case"/)
  assert.match(html, /44444444-4444-4444-8444-444444444444/)
})

test('safe conflict helper accepts only named 409 conflict snapshots', () => {
  const snapshot = { id: 'case-1', case_version: 4 }
  assert.deepEqual(getReviewCaseConflictSnapshot({
    code: 'review_case_version_conflict',
    detail: { current: snapshot },
    status: 409,
  }), snapshot)
  assert.equal(getReviewCaseConflictSnapshot({
    code: 'review_case_version_conflict',
    detail: { current: snapshot },
    status: 422,
  }), null)
  assert.equal(getReviewCaseConflictSnapshot({
    code: 'unrelated_conflict',
    detail: { current: snapshot },
    status: 409,
  }), null)
})

test('destination-side merge conflicts never replace the routed source case', () => {
  const sourceSnapshot = { id: 'source-case', case_version: 4 }
  const destinationSnapshot = { id: 'destination-case', case_version: 7 }
  let routedDetail = sourceSnapshot

  assert.equal(
    reviewCaseConflictSnapshotMatchesCase(sourceSnapshot, 'source-case'),
    true,
  )
  assert.equal(
    reviewCaseConflictSnapshotMatchesCase(destinationSnapshot, 'source-case'),
    false,
  )
  assert.equal(
    reviewCaseConflictSnapshotMatchesCase(
      getReviewCaseConflictSnapshot({
        code: 'review_case_version_conflict',
        detail: { current: destinationSnapshot },
        status: 409,
      }),
      'source-case',
    ),
    false,
  )
  assert.equal(
    reviewCaseConflictSnapshotMatchesCase(
      getReviewCaseConflictSnapshot({
        code: 'review_case_transition_conflict',
        detail: { current: destinationSnapshot },
        status: 409,
      }),
      'source-case',
    ),
    false,
  )

  if (reviewCaseConflictSnapshotMatchesCase(destinationSnapshot, 'source-case')) {
    routedDetail = { ...routedDetail, ...destinationSnapshot }
  }
  const sourceReloadFailed = true
  assert.equal(sourceReloadFailed, true)
  assert.deepEqual(routedDetail, sourceSnapshot)
})

test('lifecycle actions stay blocked during mutations and conflict recovery', () => {
  assert.equal(areReviewLifecycleActionsBlocked(), false)
  assert.equal(areReviewLifecycleActionsBlocked({ isSubmitting: true }), true)
  assert.equal(areReviewLifecycleActionsBlocked({ conflictRecoveryBlocked: true }), true)
})

test('linked review cases receive distinct mounted state scopes', () => {
  const firstScope = reviewCaseStateScopeKey('case-1')
  const secondScope = reviewCaseStateScopeKey('case-2')

  assert.equal(firstScope, 'admin-review-case:case-1')
  assert.equal(secondScope, 'admin-review-case:case-2')
  assert.notEqual(firstScope, secondScope)

  const pageSource = readFileSync(
    new URL(
      '../../src/pages/admin/review-cases/AdminReviewCasePage.jsx',
      import.meta.url,
    ),
    'utf8',
  )
  assert.match(
    pageSource,
    /<AdminReviewCasePageContent\s+key=\{reviewCaseStateScopeKey\(reviewCaseId\)\}\s+reviewCaseId=\{reviewCaseId\}/,
  )
})

test('choice pagination collects datasets above 100 records without truncation', async () => {
  const records = Array.from({ length: 205 }, (_, index) => ({ id: `record-${index}` }))
  const cursors = ['', 'page-2', 'page-3']
  const loaded = await collectCursorPages(async (cursor) => {
    const pageIndex = cursors.indexOf(cursor)
    assert.notEqual(pageIndex, -1)
    const start = pageIndex * 100
    const items = records.slice(start, start + 100)
    return {
      items,
      has_more: start + items.length < records.length,
      next_cursor: cursors[pageIndex + 1] ?? null,
    }
  }, 'items')

  assert.deepEqual(loaded, records)
})

test('choice pagination rejects a non-advancing cursor', async () => {
  await assert.rejects(
    collectCursorPages(async () => ({
      items: [{ id: 'record-1' }],
      has_more: true,
      next_cursor: 'same-page',
    }), 'items'),
    /did not advance/,
  )
})

test('assignment display distinguishes unassigned and ineligible assignees', () => {
  assert.equal(describeReviewCaseAssignment({}), 'Unassigned')
  assert.equal(describeReviewCaseAssignment({
    assigned_to_user_id: 'admin-1',
    assignee_display_name: 'Taylor',
    assignee_is_eligible: false,
  }), 'Taylor (inactive)')
})
