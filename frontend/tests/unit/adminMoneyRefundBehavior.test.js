import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'

import {
  buildRefundReconciliationRequestBody,
  reconcileAdminMoneyRefund,
} from '../../src/pages/admin/money/adminMoneyApi.js'
import {
  RefundDurableDiagnostic,
  RefundDurableListIndicator,
} from '../../src/pages/admin/money/adminMoneyRefundPresentation.js'
import {
  CancellationFollowUpLabel,
  getRemovalRefundCountLabel,
  RemovalRefundLabel,
} from '../../src/pages/admin/official-games/manage/adminOfficialGameFinancialPresentation.js'

const originalFetch = globalThis.fetch

afterEach(() => {
  globalThis.fetch = originalFetch
})

test('refund reconciliation executes the complete backend request contract', async () => {
  const requests = []
  globalThis.fetch = async (url, options) => {
    requests.push({ url, options })
    return {
      ok: true,
      status: 200,
      json: async () => ({ id: 'refund-1' }),
    }
  }
  const firebaseUser = { getIdToken: async () => 'admin-token' }

  const result = await reconcileAdminMoneyRefund({
    firebaseUser,
    idempotencyKey: 'reconcile-request-1',
    providerRefundId: 're_provider_1',
    reason: 'Confirm the provider result.',
    refundId: 'refund-1',
  })

  assert.deepEqual(result, { id: 'refund-1' })
  assert.equal(requests.length, 1)
  assert.match(requests[0].url, /\/admin\/money\/refunds\/refund-1\/reconcile$/)
  assert.equal(requests[0].options.method, 'POST')
  assert.deepEqual(JSON.parse(requests[0].options.body), {
    reason: 'Confirm the provider result.',
    idempotency_key: 'reconcile-request-1',
    provider_refund_id: 're_provider_1',
  })
  assert.equal(requests[0].options.headers.Authorization, 'Bearer admin-token')
  assert.equal(requests[0].options.headers['Content-Type'], 'application/json')
})

test('refund reconciliation normalizes an absent provider identity to null', () => {
  assert.deepEqual(
    buildRefundReconciliationRequestBody({
      idempotencyKey: 'reconcile-request-2',
      providerRefundId: '',
      reason: 'Check the stored provider identity.',
    }),
    {
      reason: 'Check the stored provider identity.',
      idempotency_key: 'reconcile-request-2',
      provider_refund_id: null,
    },
  )
})

test('official-game presenters distinguish queued cash from returned cash', () => {
  assert.equal(getRemovalRefundCountLabel(), 'Refunds queued')
  assert.equal(
    renderToStaticMarkup(createElement(CancellationFollowUpLabel, { reason: 'stripe_refund_queued' })),
    '<span>Stripe refund queued</span>',
  )
  assert.equal(
    renderToStaticMarkup(createElement(RemovalRefundLabel, { refundStatus: 'approved' })),
    '<small>Stripe refund queued</small>',
  )
  assert.equal(
    renderToStaticMarkup(createElement(RemovalRefundLabel, { refundStatus: 'succeeded' })),
    '<small>Stripe refund</small>',
  )
})

test('durable diagnostic presentation exposes only bounded safe fields', () => {
  assert.equal(
    renderToStaticMarkup(createElement(RefundDurableDiagnostic, {
      diagnostic: {
        status: 'exhausted',
        refund_attempt_number: 3,
        error_code: 'refund_outcome_unknown',
        payload: { secret: 'must not render' },
        durable_job_id: 'job-private',
      },
    })),
    '<span>Exhausted · attempt 3 · Refund Outcome Unknown</span>',
  )
  assert.equal(
    renderToStaticMarkup(createElement(RefundDurableDiagnostic, { diagnostic: null })),
    '',
  )
})

test('refund list indicator renders actionable exhausted fulfillment', () => {
  assert.equal(
    renderToStaticMarkup(createElement(RefundDurableListIndicator, {
      refund: {
        durable_job_diagnostic: {
          status: 'exhausted',
          refund_attempt_number: 2,
          error_code: 'refund_support_staging_failed',
          payload: { secret: 'must not render' },
          durable_job_id: 'job-private',
        },
      },
    })),
    '<span>Fulfillment: Exhausted · attempt 2 · Refund Support Staging Failed</span>',
  )
  assert.equal(
    renderToStaticMarkup(createElement(RefundDurableListIndicator, {
      refund: { durable_job_diagnostic: null },
    })),
    '',
  )
})
