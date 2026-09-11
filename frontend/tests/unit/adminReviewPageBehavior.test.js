import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { after, before, test } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { createServer } from 'vite'

import {
  createAdminReviewCaseCloseHandler,
  createReviewCaseDetailState,
  reduceReviewCaseDetailState,
} from '../../src/pages/admin/review-cases/adminReviewLifecycle.js'

let AdminReviewCasePageView
let AdminReviewCasesPageView
let viteServer

before(async () => {
  viteServer = await createServer({
    appType: 'custom',
    logLevel: 'silent',
    root: fileURLToPath(new URL('../..', import.meta.url)),
    server: { middlewareMode: true },
  })
  ;({
    AdminReviewCasePageView,
  } = await viteServer.ssrLoadModule(
      '/src/pages/admin/review-cases/AdminReviewCasePage.jsx',
    ))
  ;({
    AdminReviewCasesPageView,
  } = await viteServer.ssrLoadModule(
    '/src/pages/admin/review-cases/AdminReviewCasesPage.jsx',
  ))
})

after(async () => {
  await viteServer?.close()
})

function buildReviewCase(overrides = {}) {
  return {
    case_category: 'chat_moderation',
    case_status: 'open',
    case_version: 2,
    created_at: '2038-03-01T18:00:00Z',
    events: [],
    findings: [],
    id: 'case-a',
    notes: [],
    priority: 'urgent',
    signals: [],
    summary: 'Review chat moderation signals.',
    target_current_status: 'active',
    target_game_id: 'game-a',
    title: 'Community Game chat needs review',
    updated_at: '2038-03-01T18:00:00Z',
    ...overrides,
  }
}

function renderReviewCasePage(reviewCase) {
  return renderToStaticMarkup(
    createElement(
      MemoryRouter,
      null,
      createElement(AdminReviewCasePageView, {
        closeConflictBlocked: false,
        closureOutcome: 'no_action_needed',
        closureReason: 'Reviewed current evidence.',
        detail: reviewCase,
        formStatus: { message: '', type: '' },
        isSubmitting: false,
        loadState: 'ready',
        noteBody: '',
        onAddNote() {},
        onClose() {},
        onCloseNotes() {},
        onClosureOutcomeChange() {},
        onClosureReasonChange() {},
        onNoteChange() {},
        onOpenNotes() {},
        pageError: '',
        showNotesModal: false,
      }),
    ),
  )
}

function renderReviewCaseList(overrides = {}) {
  return renderToStaticMarkup(
    createElement(
      MemoryRouter,
      null,
      createElement(AdminReviewCasesPageView, {
        caseCategory: '',
        cases: [],
        caseStatus: 'open',
        hasMoreCases: false,
        isLoadingMore: false,
        loadMoreError: '',
        loadState: 'ready',
        onCaseCategoryChange() {},
        onCaseStatusChange() {},
        onLoadMore() {},
        onTargetTypeChange() {},
        pageError: '',
        targetType: '',
        ...overrides,
      }),
    ),
  )
}

test('actual Review Cases list renders chat cases and category and target filters', () => {
  const markup = renderReviewCaseList({
    caseCategory: 'chat_moderation',
    cases: [{
      case_category: 'chat_moderation',
      case_status: 'open',
      finding_summary: {
        current_finding_count: 1,
        current_issue_labels: ['chat_moderation'],
        current_issue_type_count: 1,
        total_finding_count: 1,
      },
      case_type: 'community_game',
      id: 'chat-case-a',
      target_game_id: 'game-a',
      target_summary: { status: 'active' },
      updated_at: '2038-03-01T18:00:00Z',
    }],
    targetType: 'community_game',
  })

  assert.match(markup, /Review case filters/)
  assert.match(markup, /All categories/)
  assert.match(markup, /Content moderation/)
  assert.match(markup, /Chat moderation/)
  assert.match(markup, /All targets/)
  assert.match(markup, /Community games/)
  assert.match(markup, /Need a Sub posts/)
  assert.match(markup, /\/admin\/review-cases\/chat-case-a/)
  assert.match(markup, /1<\/span><div><span[^>]*>active finding/)
})

test('actual Review Case signal sections render current historical and dismissed signals', () => {
  const markup = renderReviewCasePage(buildReviewCase({
    signals: [
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
    ],
  }))

  assert.match(markup, /Current Signals/)
  assert.match(markup, /Previous Signals/)
  assert.match(markup, /Signal current-/)
  assert.match(markup, /Current abusive chat match\./)
  assert.match(markup, /Critical priority/)
  assert.match(markup, />Current</)
  assert.match(markup, /Signal historic/)
  assert.match(markup, /Superseded chat match\./)
  assert.match(markup, /Historical \/ superseded/)
  assert.match(markup, /Signal dismisse/)
  assert.match(markup, /Dismissed chat match\./)
  assert.match(markup, />Dismissed</)
})

test('actual Review Case signal sections render both empty states', () => {
  const markup = renderReviewCasePage(buildReviewCase({
    id: 'case-empty',
    signals: [],
  }))

  assert.match(markup, /No current signals\./)
  assert.match(markup, /No previous signals\./)
})

test('rendering another case replaces the prior signal presentation', () => {
  const firstMarkup = renderReviewCasePage(buildReviewCase({
    signals: [{
      id: 'case-a-signal',
      metadata: { current_match: true },
      priority: 'urgent',
      signal_status: 'attached',
      summary: 'Signal belonging only to case A.',
    }],
  }))
  const secondMarkup = renderReviewCasePage(buildReviewCase({
    id: 'case-b',
    target_game_id: 'game-b',
    signals: [{
      id: 'case-b-signal',
      metadata: { current_match: true },
      priority: 'attention',
      signal_status: 'attached',
      summary: 'Signal belonging only to case B.',
    }],
  }))

  assert.match(firstMarkup, /Signal belonging only to case A\./)
  assert.doesNotMatch(firstMarkup, /Signal belonging only to case B\./)
  assert.match(secondMarkup, /Signal belonging only to case B\./)
  assert.doesNotMatch(secondMarkup, /Signal belonging only to case A\./)
})

test('actual page close handler blocks stale retries and keeps failed reload blocked', async () => {
  const staleDetail = buildReviewCase()
  let state = {
    ...createReviewCaseDetailState(staleDetail.id),
    detail: staleDetail,
    reloadState: 'ready',
  }
  let isSubmitting = false
  let closeRequestCount = 0
  let reloadRequestCount = 0
  let closeSuccessCount = 0
  let loadState = 'ready'
  let pageError = ''

  const handler = createAdminReviewCaseCloseHandler({
    closeReviewCase: async () => {
      closeRequestCount += 1
      throw {
        code: 'review_case_version_conflict',
        message: 'Review case changed.',
        status: 409,
      }
    },
    currentUser: { uid: 'admin-user' },
    getCloseInput: () => ({
      idempotencyKey: 'stale-close-key',
      outcome: 'no_action_needed',
      reason: 'Reviewed current evidence.',
    }),
    getIsSubmitting: () => isSubmitting,
    getReviewCase: async () => {
      reloadRequestCount += 1
      throw new Error('Reload unavailable.')
    },
    getReviewCaseState: () => state,
    onCloseSucceeded: () => {
      closeSuccessCount += 1
    },
    onFormStatus: () => {},
    onLoadState: (value) => {
      loadState = value
    },
    onPageError: (value) => {
      pageError = value
    },
    onReviewCaseAction: (action) => {
      state = reduceReviewCaseDetailState(state, action)
    },
    onSubmitting: (value) => {
      isSubmitting = value
    },
    reviewCaseId: staleDetail.id,
  })

  const firstRequest = handler({ preventDefault() {} })
  const duplicateRequest = await handler({ preventDefault() {} })
  const result = await firstRequest

  assert.equal(duplicateRequest.status, 'blocked')
  assert.equal(result.status, 'version_conflict')
  assert.equal(result.reloadResult.status, 'failed')
  assert.equal(closeRequestCount, 1)
  assert.equal(reloadRequestCount, 1)
  assert.equal(closeSuccessCount, 0)
  assert.equal(state.requiresFreshDetail, true)
  assert.equal(state.reloadState, 'failed')
  assert.equal(state.detail, null)
  assert.equal(loadState, 'error')
  assert.equal(pageError, 'Reload unavailable.')

  const blockedRetry = await handler({ preventDefault() {} })
  assert.equal(blockedRetry.status, 'blocked')
  assert.equal(closeRequestCount, 1)
})

test('actual page close handler reloads fresh detail before allowing another close', async () => {
  const staleDetail = buildReviewCase()
  const freshDetail = buildReviewCase({ case_version: 3 })
  const closedDetail = buildReviewCase({ case_status: 'closed', case_version: 4 })
  let state = {
    ...createReviewCaseDetailState(staleDetail.id),
    detail: staleDetail,
    reloadState: 'ready',
  }
  let isSubmitting = false
  const closeRequests = []
  let reloadRequestCount = 0
  let closeSuccess = null

  const handler = createAdminReviewCaseCloseHandler({
    closeReviewCase: async (request) => {
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
        review_case_id: staleDetail.id,
      }
    },
    currentUser: { uid: 'admin-user' },
    getCloseInput: () => ({
      idempotencyKey: 'recover-close-key',
      outcome: 'no_action_needed',
      reason: 'Reviewed refreshed evidence.',
    }),
    getIsSubmitting: () => isSubmitting,
    getReviewCase: async () => {
      reloadRequestCount += 1
      return reloadRequestCount === 1 ? freshDetail : closedDetail
    },
    getReviewCaseState: () => state,
    onCloseSucceeded: (acknowledgement, refreshedDetail) => {
      closeSuccess = { acknowledgement, refreshedDetail }
    },
    onFormStatus: () => {},
    onLoadState: () => {},
    onPageError: () => {},
    onReviewCaseAction: (action) => {
      state = reduceReviewCaseDetailState(state, action)
    },
    onSubmitting: (value) => {
      isSubmitting = value
    },
    reviewCaseId: staleDetail.id,
  })

  const conflict = await handler({ preventDefault() {} })
  assert.equal(conflict.status, 'version_conflict')
  assert.equal(conflict.reloadResult.status, 'succeeded')
  assert.equal(reloadRequestCount, 1)
  assert.equal(state.requiresFreshDetail, false)
  assert.equal(state.reloadState, 'ready')
  assert.equal(state.detail.case_version, 3)
  assert.equal(closeSuccess, null)

  const closed = await handler({ preventDefault() {} })
  assert.equal(closed.status, 'closed')
  assert.equal(closeRequests.length, 2)
  assert.equal(closeRequests[0].expectedCaseVersion, 2)
  assert.equal(closeRequests[1].expectedCaseVersion, 3)
  assert.equal(reloadRequestCount, 2)
  assert.equal(closeSuccess.acknowledgement.case_version, 4)
  assert.equal(closeSuccess.acknowledgement.review_case, undefined)
  assert.equal(closeSuccess.refreshedDetail.case_status, 'closed')
  assert.equal(closeSuccess.refreshedDetail.case_version, 4)
})

test('page wires actual signal rendering and close conflict orchestration', () => {
  const pageSource = readFileSync(
    new URL(
      '../../src/pages/admin/review-cases/AdminReviewCasePage.jsx',
      import.meta.url,
    ),
    'utf8',
  )
  const lifecycleSource = readFileSync(
    new URL(
      '../../src/pages/admin/review-cases/adminReviewLifecycle.js',
      import.meta.url,
    ),
    'utf8',
  )

  assert.match(pageSource, /<ReviewCaseSignalSections reviewCase=\{detail\} \/>/)
  assert.match(pageSource, /<AdminReviewCasePageView/)
  assert.match(pageSource, /onClose=\{handleClose\}/)
  assert.match(pageSource, /onSubmit=\{onClose\}/)
  assert.match(pageSource, /createAdminReviewCaseCloseHandler\(\{/)
  assert.match(lifecycleSource, /await submitReviewCaseClose\(/)
  assert.match(lifecycleSource, /await requestReviewCaseDetail\(/)
  assert.match(pageSource, /key=\{reviewCaseId\}/)
})
