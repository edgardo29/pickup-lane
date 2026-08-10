import assert from 'node:assert/strict'
import { test } from 'node:test'

import { getApiErrorCode } from '../../src/lib/apiClient.js'
import {
  STEP_UP_REQUIRED_CODE,
  StepUpCancelledError,
  isStepUpCancelledError,
  isStepUpRequiredError,
  runStepUpProtectedAction,
} from '../../src/lib/stepUpAction.js'

test('step-up required errors are detected from public envelope codes', () => {
  assert.equal(isStepUpRequiredError({ code: STEP_UP_REQUIRED_CODE }), true)
  assert.equal(
    isStepUpRequiredError({ detail: { code: STEP_UP_REQUIRED_CODE } }),
    true,
  )
  assert.equal(isStepUpRequiredError({ code: 'AUTH.FORBIDDEN' }), false)
})

test('api client preserves public error codes from top-level and detail fields', () => {
  assert.equal(getApiErrorCode({ code: STEP_UP_REQUIRED_CODE }), STEP_UP_REQUIRED_CODE)
  assert.equal(
    getApiErrorCode({ detail: { code: STEP_UP_REQUIRED_CODE } }),
    STEP_UP_REQUIRED_CODE,
  )
  assert.equal(getApiErrorCode({ detail: 'Permission denied.' }), '')
})

test('step-up protected action retries only after successful reauth request', async () => {
  const calls = []
  const result = await runStepUpProtectedAction({
    action: async () => {
      calls.push('action')
      if (calls.length === 1) {
        throw { code: STEP_UP_REQUIRED_CODE }
      }
      return 'saved'
    },
    requestStepUp: async () => {
      calls.push('step-up')
    },
  })

  assert.equal(result, 'saved')
  assert.deepEqual(calls, ['action', 'step-up', 'action'])
})

test('step-up cancellation does not replay the original action', async () => {
  const calls = []

  await assert.rejects(
    () => runStepUpProtectedAction({
      action: async () => {
        calls.push('action')
        throw { code: STEP_UP_REQUIRED_CODE }
      },
      requestStepUp: async () => {
        calls.push('step-up')
        throw new StepUpCancelledError()
      },
    }),
    (error) => isStepUpCancelledError(error),
  )

  assert.deepEqual(calls, ['action', 'step-up'])
})

test('non-step-up errors are not retried by the helper', async () => {
  const calls = []

  await assert.rejects(
    () => runStepUpProtectedAction({
      action: async () => {
        calls.push('action')
        throw { code: 'API.CONFLICT' }
      },
      requestStepUp: async () => {
        calls.push('step-up')
      },
    }),
    { code: 'API.CONFLICT' },
  )

  assert.deepEqual(calls, ['action'])
})
