const REVIEW_CASE_CONFLICT_CODES = new Set([
  'review_case_version_conflict',
  'review_case_idempotency_conflict',
  'review_case_assignment_conflict',
  'review_case_open_identity_conflict',
  'review_case_transition_conflict',
])

export function reviewCaseStateScopeKey(reviewCaseId) {
  return `admin-review-case:${String(reviewCaseId ?? '')}`
}

export function buildReviewCaseListQuery({
  assignment = 'all',
  caseCategory = '',
  caseStatus = 'open',
  cursor = '',
  limit = 50,
  offset = 0,
  targetType = 'content_targets',
} = {}) {
  const searchParams = new URLSearchParams()
  if (caseStatus) searchParams.set('case_status', caseStatus)
  if (caseCategory) searchParams.set('case_category', caseCategory)
  if (targetType) searchParams.set('target_type', targetType)
  if (assignment) searchParams.set('assignment', assignment)
  if (cursor) {
    searchParams.set('cursor', cursor)
  } else {
    searchParams.set('offset', String(offset))
  }
  searchParams.set('limit', String(limit))
  return searchParams.toString()
}

export function buildReviewCaseNotePayload({
  body,
  correctsNoteId = null,
  expectedCaseVersion,
  idempotencyKey,
}) {
  return {
    body,
    corrects_note_id: correctsNoteId,
    expected_case_version: expectedCaseVersion,
    idempotency_key: idempotencyKey,
  }
}

export function buildReviewCaseClosePayload({
  expectedCaseVersion,
  idempotencyKey,
  outcome,
  reason,
}) {
  return {
    outcome,
    reason,
    expected_case_version: expectedCaseVersion,
    idempotency_key: idempotencyKey,
  }
}

export function buildReviewCaseAssignmentPayload({
  assigneeUserId,
  expectedCaseVersion,
  idempotencyKey,
  reason,
}) {
  return {
    assignee_user_id: assigneeUserId || null,
    expected_case_version: expectedCaseVersion,
    idempotency_key: idempotencyKey,
    reason,
  }
}

export function buildReviewCaseReopenPayload({
  expectedCaseVersion,
  idempotencyKey,
  reason,
}) {
  return {
    expected_case_version: expectedCaseVersion,
    idempotency_key: idempotencyKey,
    reason,
  }
}

export function buildReviewCaseMergePayload({
  destinationCaseId,
  expectedDestinationVersion,
  expectedSourceVersion,
  idempotencyKey,
  reason,
}) {
  return {
    destination_case_id: destinationCaseId,
    expected_destination_version: expectedDestinationVersion,
    expected_source_version: expectedSourceVersion,
    idempotency_key: idempotencyKey,
    reason,
  }
}

export function sortReviewCaseEvents(events = []) {
  return [...events].sort((first, second) => {
    const sequenceDifference = Number(first.event_sequence) - Number(second.event_sequence)
    if (sequenceDifference !== 0) return sequenceDifference
    return String(first.id).localeCompare(String(second.id))
  })
}

export function getReviewCaseConflictSnapshot(error) {
  if (error?.status !== 409 || !REVIEW_CASE_CONFLICT_CODES.has(error?.code)) {
    return null
  }
  const snapshot = error?.detail?.current
  return snapshot && typeof snapshot === 'object' ? snapshot : null
}

export function reviewCaseConflictSnapshotMatchesCase(snapshot, reviewCaseId) {
  return Boolean(
    snapshot
    && typeof snapshot === 'object'
    && typeof snapshot.id === 'string'
    && snapshot.id === reviewCaseId,
  )
}

export async function collectCursorPages(loadPage, itemsKey) {
  const items = []
  const seenCursors = new Set()
  let cursor = ''

  while (true) {
    const page = await loadPage(cursor)
    const pageItems = page?.[itemsKey]
    if (!Array.isArray(pageItems)) {
      throw new Error(`Paginated response is missing ${itemsKey}.`)
    }
    items.push(...pageItems)
    if (!page.has_more) return items

    const nextCursor = page.next_cursor
    if (
      typeof nextCursor !== 'string'
      || !nextCursor
      || seenCursors.has(nextCursor)
    ) {
      throw new Error('Paginated response did not advance its cursor.')
    }
    seenCursors.add(nextCursor)
    cursor = nextCursor
  }
}

export function areReviewLifecycleActionsBlocked({
  conflictRecoveryBlocked = false,
  isSubmitting = false,
} = {}) {
  return conflictRecoveryBlocked || isSubmitting
}

export function isCompatibleMergeDestination(sourceCase, candidateCase) {
  if (!canMergeReviewCaseSource(sourceCase)) return false
  if (!sourceCase || !candidateCase || sourceCase.id === candidateCase.id) return false
  if (candidateCase.case_status !== 'open') return false
  if (candidateCase.merged_into_case_id) return false
  if (sourceCase.case_type !== candidateCase.case_type) return false
  if (sourceCase.case_category !== candidateCase.case_category) return false

  const targetFields = ['target_game_id', 'target_sub_post_id']
  return targetFields.some(
    (field) => sourceCase[field] && sourceCase[field] === candidateCase[field],
  )
}

export function canMergeReviewCaseSource(reviewCase) {
  if (!reviewCase || reviewCase.case_status !== 'closed') return false
  if (!['manual', 'automatic'].includes(reviewCase.closure_mode)) return false
  if (!reviewCase.closure_outcome || !reviewCase.closure_reason || !reviewCase.closed_at) {
    return false
  }
  if (reviewCase.merged_into_case_id) return false
  return !(reviewCase.linked_cases ?? []).some(
    (linkedCase) => linkedCase.relation === 'merged_from',
  )
}

export function getVisibleResolutionHistory(reviewCase) {
  return [...(reviewCase?.resolution_history ?? [])].sort((first, second) => {
    const sequenceDifference = Number(first.event_sequence) - Number(second.event_sequence)
    if (sequenceDifference !== 0) return sequenceDifference
    return String(first.closure_event_id).localeCompare(String(second.closure_event_id))
  })
}

export function describeReviewCaseAssignment(reviewCase) {
  if (!reviewCase?.assigned_to_user_id) return 'Unassigned'
  const name = reviewCase.assignee_display_name || `Admin ${String(reviewCase.assigned_to_user_id).slice(0, 8)}`
  return reviewCase.assignee_is_eligible === false ? `${name} (inactive)` : name
}
