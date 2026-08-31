import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  buildIdempotencyHeaders,
  createPaymentMethodOperationId,
} from '../../src/lib/paymentMethodsApi.js'
import { STEP_UP_REQUIRED_CODE, runStepUpProtectedAction } from '../../src/lib/stepUpAction.js'

test('saved-card mutations require an explicit stable operation id', () => {
  assert.throws(
    () => buildIdempotencyHeaders(),
    /Payment-method operation id is required/,
  )
  assert.throws(
    () => buildIdempotencyHeaders('   '),
    /Payment-method operation id is required/,
  )
  assert.deepEqual(buildIdempotencyHeaders(' operation-123 '), {
    'Idempotency-Key': 'operation-123',
  })
})

test('one user action keeps one operation id across a step-up replay', async () => {
  const operationId = createPaymentMethodOperationId()
  const observedIds = []

  await runStepUpProtectedAction({
    action: async () => {
      observedIds.push(buildIdempotencyHeaders(operationId)['Idempotency-Key'])
      if (observedIds.length === 1) {
        throw { code: STEP_UP_REQUIRED_CODE }
      }
      return 'saved'
    },
    requestStepUp: async () => {},
  })

  assert.match(operationId, /^[0-9a-f-]{36}$/i)
  assert.deepEqual(observedIds, [operationId, operationId])
})
