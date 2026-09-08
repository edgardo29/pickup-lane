export const REVIEW_CASE_CATEGORY_FILTERS = [
  { label: 'All categories', value: '' },
  { label: 'Content moderation', value: 'content_moderation' },
  { label: 'Chat moderation', value: 'chat_moderation' },
]

export const REVIEW_CASE_TARGET_FILTERS = [
  { label: 'All targets', value: '' },
  { label: 'Community games', value: 'community_game' },
  { label: 'Need a Sub posts', value: 'need_a_sub' },
]

export async function requestAdminReviewCaseListPage({
  caseCategory = '',
  caseStatus = 'open',
  cursor = '',
  firebaseUser,
  limit = 24,
  listReviewCases,
  targetType = '',
} = {}) {
  const response = await listReviewCases({
    caseCategory,
    caseStatus,
    cursor,
    firebaseUser,
    limit,
    targetType,
  })

  return {
    cases: response?.cases ?? [],
    hasMore: Boolean(response?.has_more),
    nextCursor: response?.next_cursor ?? '',
  }
}
