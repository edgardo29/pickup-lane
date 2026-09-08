import assert from 'node:assert/strict'
import test from 'node:test'

import {
  requestAdminReviewCaseListPage,
} from '../../src/pages/admin/review-cases/adminReviewList.js'

test('default Review Cases request includes every category and target type', async () => {
  const firebaseUser = { uid: 'admin-user' }
  const requests = []
  const result = await requestAdminReviewCaseListPage({
    firebaseUser,
    listReviewCases: async (request) => {
      requests.push(request)
      return {
        cases: [{ case_category: 'chat_moderation', id: 'chat-case-a' }],
        has_more: false,
        next_cursor: null,
      }
    },
  })

  assert.deepEqual(requests, [{
    caseCategory: '',
    caseStatus: 'open',
    cursor: '',
    firebaseUser,
    limit: 24,
    targetType: '',
  }])
  assert.deepEqual(result, {
    cases: [{ case_category: 'chat_moderation', id: 'chat-case-a' }],
    hasMore: false,
    nextCursor: '',
  })
})

test('cursor loading preserves the selected category and target context', async () => {
  const firebaseUser = { uid: 'admin-user' }
  const requests = []
  const responses = [
    {
      cases: [{ id: 'chat-case-a' }],
      has_more: true,
      next_cursor: 'cursor-a',
    },
    {
      cases: [{ id: 'chat-case-b' }],
      has_more: false,
      next_cursor: null,
    },
  ]
  const listReviewCases = async (request) => {
    requests.push(request)
    return responses.shift()
  }
  const context = {
    caseCategory: 'chat_moderation',
    caseStatus: 'closed',
    firebaseUser,
    limit: 24,
    listReviewCases,
    targetType: 'need_a_sub',
  }

  const firstPage = await requestAdminReviewCaseListPage(context)
  const secondPage = await requestAdminReviewCaseListPage({
    ...context,
    cursor: firstPage.nextCursor,
  })

  assert.deepEqual(requests, [
    {
      caseCategory: 'chat_moderation',
      caseStatus: 'closed',
      cursor: '',
      firebaseUser,
      limit: 24,
      targetType: 'need_a_sub',
    },
    {
      caseCategory: 'chat_moderation',
      caseStatus: 'closed',
      cursor: 'cursor-a',
      firebaseUser,
      limit: 24,
      targetType: 'need_a_sub',
    },
  ])
  assert.deepEqual(
    [...firstPage.cases, ...secondPage.cases].map((reviewCase) => reviewCase.id),
    ['chat-case-a', 'chat-case-b'],
  )
  assert.equal(secondPage.hasMore, false)
  assert.equal(secondPage.nextCursor, '')
})
