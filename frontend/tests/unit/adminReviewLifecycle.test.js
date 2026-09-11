import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import {
  buildReviewSignalGroups,
  buildReviewCaseClosePayload,
  buildReviewCaseNotePayload,
  canSubmitReviewCaseClose,
  createReviewCaseDetailState,
  isReviewCaseVersionConflict,
  reduceReviewCaseDetailState,
  requestReviewCaseDetail,
  sortReviewCaseEvents,
  submitReviewCaseClose,
} from '../../src/pages/admin/review-cases/adminReviewLifecycle.js'

test('review case mutation payloads keep version only on close', () => {
  assert.deepEqual(
    buildReviewCaseNotePayload({ body: 'Check completed', idempotencyKey: 'note-key' }),
    { body: 'Check completed', idempotency_key: 'note-key' },
  )
  assert.deepEqual(
    buildReviewCaseClosePayload({
      caseVersion: 7,
      idempotencyKey: 'close-key',
      outcome: 'no_action_needed',
      reason: 'Reviewed',
    }),
    {
      outcome: 'no_action_needed',
      reason: 'Reviewed',
      expected_case_version: 7,
      idempotency_key: 'close-key',
    },
  )
})

test('review case events order only by resulting case version', () => {
  assert.deepEqual(
    sortReviewCaseEvents([
      { id: 'c', case_version: 3 },
      { id: 'a', case_version: 1 },
      { id: 'b', case_version: 2 },
    ]).map((event) => event.id),
    ['a', 'b', 'c'],
  )
})

test('only the stale close conflict requires detail recovery', () => {
  assert.equal(
    isReviewCaseVersionConflict({
      status: 409,
      code: 'review_case_version_conflict',
    }),
    true,
  )
  assert.equal(
    isReviewCaseVersionConflict({
      status: 409,
      code: 'review_case_idempotency_conflict',
    }),
    false,
  )
})

test('chat signal rows expose current and historical decision details', () => {
  const groups = buildReviewSignalGroups([
    {
      id: 'current-signal-1234',
      metadata: { current_match: true },
      priority: 'critical',
      signal_status: 'attached',
      summary: 'Current abusive chat match.',
    },
    {
      id: 'historical-signal-5678',
      metadata: { current_match: false },
      priority: 'urgent',
      signal_status: 'attached',
      summary: 'Superseded chat match.',
    },
    {
      id: 'dismissed-signal-9012',
      metadata: { current_match: true },
      priority: 'attention',
      signal_status: 'dismissed',
      summary: 'Dismissed chat match.',
    },
  ])

  assert.deepEqual(groups.current, [{
    id: 'current-signal-1234',
    identity: 'current-',
    priority: 'critical',
    state: 'Current',
    summary: 'Current abusive chat match.',
  }])
  assert.deepEqual(
    groups.historical.map((signal) => ({
      identity: signal.identity,
      priority: signal.priority,
      state: signal.state,
      summary: signal.summary,
    })),
    [
      {
        identity: 'historic',
        priority: 'urgent',
        state: 'Historical / superseded',
        summary: 'Superseded chat match.',
      },
      {
        identity: 'dismisse',
        priority: 'attention',
        state: 'Dismissed',
        summary: 'Dismissed chat match.',
      },
    ],
  )
  assert.deepEqual(buildReviewSignalGroups(), { current: [], historical: [] })
})

test('stale close recovery stays blocked until fresh case detail loads', () => {
  const staleDetail = { case_status: 'open', case_version: 2, id: 'case-a' }
  const freshDetail = { case_status: 'open', case_version: 3, id: 'case-a' }
  let state = createReviewCaseDetailState('case-a')
  state = reduceReviewCaseDetailState(state, { type: 'reload_started' })
  state = reduceReviewCaseDetailState(state, {
    detail: staleDetail,
    reviewCaseId: 'case-a',
    type: 'reload_succeeded',
  })

  const canClose = () => canSubmitReviewCaseClose({
    isSubmitting: false,
    reason: 'Reviewed current evidence.',
    reviewCaseState: state,
  })
  let closeRequestCount = 0
  if (canClose()) closeRequestCount += 1
  assert.equal(closeRequestCount, 1)

  state = reduceReviewCaseDetailState(state, { type: 'version_conflict' })
  assert.equal(state.requiresFreshDetail, true)
  assert.equal(state.reloadState, 'required')
  assert.equal(canClose(), false)
  if (canClose()) closeRequestCount += 1
  assert.equal(closeRequestCount, 1)

  state = reduceReviewCaseDetailState(state, { type: 'reload_started' })
  state = reduceReviewCaseDetailState(state, { type: 'reload_failed' })
  assert.equal(state.requiresFreshDetail, true)
  assert.equal(state.reloadState, 'failed')
  assert.equal(state.detail, null)
  assert.equal(canClose(), false)

  state = reduceReviewCaseDetailState(state, { type: 'reload_started' })
  state = reduceReviewCaseDetailState(state, {
    detail: freshDetail,
    reviewCaseId: 'case-a',
    type: 'reload_succeeded',
  })
  assert.equal(state.requiresFreshDetail, false)
  assert.equal(state.reloadState, 'ready')
  assert.deepEqual(state.detail, freshDetail)
  assert.equal(state.detail.case_version, 3)
  assert.equal(state.detail.case_status, 'open')
  assert.equal(canClose(), true)
})

test('review case navigation resets stale recovery and signal state', () => {
  let firstCase = createReviewCaseDetailState('case-a')
  firstCase = reduceReviewCaseDetailState(firstCase, { type: 'version_conflict' })

  const secondCase = createReviewCaseDetailState('case-b')
  assert.equal(firstCase.requiresFreshDetail, true)
  assert.deepEqual(secondCase, {
    detail: null,
    reloadState: 'idle',
    requiresFreshDetail: false,
    reviewCaseId: 'case-b',
  })
  assert.deepEqual(buildReviewSignalGroups(secondCase.detail?.signals), {
    current: [],
    historical: [],
  })
})

test('close conflict executes API and reload workflow without duplicate submission', async () => {
  const staleDetail = { case_status: 'open', case_version: 2, id: 'case-a' }
  const freshDetail = { case_status: 'open', case_version: 3, id: 'case-a' }
  let state = createReviewCaseDetailState('case-a')
  const initialLoad = await requestReviewCaseDetail({
    getReviewCase: async () => staleDetail,
    request: { reviewCaseId: 'case-a' },
    reviewCaseId: 'case-a',
  })
  state = reduceReviewCaseDetailState(state, { type: 'reload_started' })
  state = reduceReviewCaseDetailState(state, initialLoad.action)

  const closeRequests = []
  const closeReviewCase = async (request) => {
    closeRequests.push(request)
    if (closeRequests.length === 1) {
      throw {
        code: 'review_case_version_conflict',
        message: 'Review case changed.',
        status: 409,
      }
    }
    return {
      audit_action_id: 'action-1',
      case_status: 'closed',
      case_version: 4,
      closure_outcome: 'no_action_needed',
      idempotent_replay: false,
      review_case_id: 'case-a',
    }
  }
  const buildCloseRequest = () => ({
    expectedCaseVersion: state.detail.case_version,
    reason: 'Reviewed fresh evidence.',
    reviewCaseId: state.reviewCaseId,
  })

  const conflict = await submitReviewCaseClose({
    closeReviewCase,
    request: buildCloseRequest(),
  })
  assert.equal(conflict.status, 'version_conflict')
  assert.equal(conflict.reloadRequired, true)
  assert.equal(conflict.result, undefined)
  state = reduceReviewCaseDetailState(state, conflict.action)
  assert.equal(state.requiresFreshDetail, true)
  assert.equal(canSubmitReviewCaseClose({
    isSubmitting: false,
    reason: 'Reviewed fresh evidence.',
    reviewCaseState: state,
  }), false)
  assert.equal(closeRequests.length, 1)

  let reloadRequests = 0
  const failedReload = await requestReviewCaseDetail({
    getReviewCase: async () => {
      reloadRequests += 1
      throw new Error('Reload unavailable.')
    },
    request: { reviewCaseId: 'case-a' },
    reviewCaseId: 'case-a',
  })
  state = reduceReviewCaseDetailState(state, { type: 'reload_started' })
  state = reduceReviewCaseDetailState(state, failedReload.action)
  assert.equal(failedReload.status, 'failed')
  assert.equal(reloadRequests, 1)
  assert.equal(state.requiresFreshDetail, true)
  assert.equal(state.detail, null)
  assert.equal(canSubmitReviewCaseClose({
    isSubmitting: false,
    reason: 'Reviewed fresh evidence.',
    reviewCaseState: state,
  }), false)
  assert.equal(closeRequests.length, 1)

  const successfulReload = await requestReviewCaseDetail({
    getReviewCase: async () => {
      reloadRequests += 1
      return freshDetail
    },
    request: { reviewCaseId: 'case-a' },
    reviewCaseId: 'case-a',
  })
  state = reduceReviewCaseDetailState(state, { type: 'reload_started' })
  state = reduceReviewCaseDetailState(state, successfulReload.action)
  assert.equal(successfulReload.status, 'succeeded')
  assert.equal(reloadRequests, 2)
  assert.deepEqual(state.detail, freshDetail)
  assert.equal(state.requiresFreshDetail, false)
  assert.equal(canSubmitReviewCaseClose({
    isSubmitting: false,
    reason: 'Reviewed fresh evidence.',
    reviewCaseState: state,
  }), true)

  const closed = await submitReviewCaseClose({
    closeReviewCase,
    request: buildCloseRequest(),
  })
  assert.equal(closed.status, 'closed')
  assert.equal(closeRequests.length, 2)
  assert.equal(closeRequests[1].expectedCaseVersion, 3)
  assert.equal(closed.result.case_version, 4)
  assert.equal(closed.result.case_status, 'closed')
  assert.equal(closed.result.review_case, undefined)

  const nextCase = createReviewCaseDetailState('case-b')
  assert.deepEqual(nextCase, {
    detail: null,
    reloadState: 'idle',
    requiresFreshDetail: false,
    reviewCaseId: 'case-b',
  })
})

test('review case clients and page contain no rejected workflow surface', () => {
  const apiSource = readFileSync(
    new URL('../../src/pages/admin/shared/adminApi.js', import.meta.url),
    'utf8',
  )
  const pageSource = readFileSync(
    new URL(
      '../../src/pages/admin/review-cases/AdminReviewCasePage.jsx',
      import.meta.url,
    ),
    'utf8',
  )
  const rejectedTokens = [
    'assignAdminReviewCase',
    'reopenAdminReviewCase',
    'mergeAdminReviewCase',
    'corrects_note_id',
    'resolution_references',
    'linked_case',
  ]

  for (const token of rejectedTokens) {
    assert.equal(apiSource.includes(token), false)
    assert.equal(pageSource.includes(token), false)
  }
})
