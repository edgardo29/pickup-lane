export function buildReviewCaseNotePayload({ body, idempotencyKey }) {
  return {
    body,
    idempotency_key: idempotencyKey,
  }
}

export function buildReviewCaseClosePayload({
  caseVersion,
  idempotencyKey,
  outcome,
  reason,
}) {
  return {
    outcome,
    reason,
    expected_case_version: caseVersion,
    idempotency_key: idempotencyKey,
  }
}

export function sortReviewCaseEvents(events = []) {
  return [...events].sort((first, second) => {
    const versionDifference = Number(first.case_version) - Number(second.case_version)
    if (versionDifference !== 0) return versionDifference
    return String(first.id).localeCompare(String(second.id))
  })
}

export function isReviewCaseVersionConflict(error) {
  return error?.status === 409 && error?.code === 'review_case_version_conflict'
}

export function buildReviewSignalGroups(signals = []) {
  return signals.reduce(
    (groups, signal) => {
      const isCurrent = (
        signal.signal_status !== 'dismissed'
        && signal.metadata?.current_match !== false
      )
      const row = {
        id: signal.id,
        identity: String(signal.id || '').slice(0, 8) || 'Unknown',
        priority: signal.priority || 'attention',
        state: isCurrent
          ? 'Current'
          : signal.signal_status === 'dismissed'
            ? 'Dismissed'
            : 'Historical / superseded',
        summary: signal.summary || 'No signal summary available.',
      }
      groups[isCurrent ? 'current' : 'historical'].push(row)
      return groups
    },
    { current: [], historical: [] },
  )
}

export function createReviewCaseDetailState(reviewCaseId) {
  return {
    detail: null,
    reloadState: 'idle',
    requiresFreshDetail: false,
    reviewCaseId,
  }
}

export function reduceReviewCaseDetailState(state, action) {
  switch (action.type) {
    case 'version_conflict':
      return {
        ...state,
        reloadState: 'required',
        requiresFreshDetail: true,
      }
    case 'reload_started':
      return {
        ...state,
        reloadState: 'loading',
      }
    case 'reload_failed':
      return {
        ...state,
        detail: null,
        reloadState: 'failed',
      }
    case 'reload_succeeded':
      if (action.reviewCaseId !== state.reviewCaseId) return state
      return {
        ...state,
        detail: action.detail,
        reloadState: 'ready',
        requiresFreshDetail: false,
      }
    default:
      return state
  }
}

export function canSubmitReviewCaseClose({ isSubmitting, reason, reviewCaseState }) {
  return Boolean(
    reason.trim()
    && !isSubmitting
    && !reviewCaseState.requiresFreshDetail
    && reviewCaseState.reloadState === 'ready'
    && reviewCaseState.detail,
  )
}

export async function requestReviewCaseDetail({ getReviewCase, request, reviewCaseId }) {
  try {
    const detail = await getReviewCase(request)
    return {
      action: { detail, reviewCaseId, type: 'reload_succeeded' },
      detail,
      status: 'succeeded',
    }
  } catch (error) {
    return {
      action: { type: 'reload_failed' },
      error,
      status: 'failed',
    }
  }
}

export async function submitReviewCaseClose({ closeReviewCase, request }) {
  try {
    return {
      result: await closeReviewCase(request),
      status: 'closed',
    }
  } catch (error) {
    if (isReviewCaseVersionConflict(error)) {
      return {
        action: { type: 'version_conflict' },
        error,
        reloadRequired: true,
        status: 'version_conflict',
      }
    }
    return { error, status: 'failed' }
  }
}

export function createAdminReviewCaseCloseHandler({
  closeReviewCase,
  currentUser,
  getCloseInput,
  getIsSubmitting,
  getReviewCase,
  getReviewCaseState,
  onCloseSucceeded,
  onFormStatus,
  onLoadState,
  onPageError,
  onReviewCaseAction,
  onSubmitting,
  reviewCaseId,
}) {
  let submissionInFlight = false

  return async function handleClose(event) {
    event.preventDefault()
    const reviewCaseState = getReviewCaseState()
    const closeInput = getCloseInput()
    if (!canSubmitReviewCaseClose({
      isSubmitting: getIsSubmitting() || submissionInFlight,
      reason: closeInput.reason,
      reviewCaseState,
    })) {
      return { status: 'blocked' }
    }

    submissionInFlight = true
    onSubmitting(true)
    onFormStatus({ message: '', type: '' })
    try {
      const closeResult = await submitReviewCaseClose({
        closeReviewCase,
        request: {
          expectedCaseVersion: reviewCaseState.detail.case_version,
          firebaseUser: currentUser,
          idempotencyKey: closeInput.idempotencyKey,
          outcome: closeInput.outcome,
          reason: closeInput.reason.trim(),
          reviewCaseId,
        },
      })
      if (closeResult.status === 'closed') {
        onCloseSucceeded(closeResult.result)
        return closeResult
      }

      if (!closeResult.reloadRequired) {
        onFormStatus({
          message: closeResult.error.message || 'Review case could not be closed.',
          type: 'error',
        })
        return closeResult
      }

      onReviewCaseAction(closeResult.action)
      onReviewCaseAction({ type: 'reload_started' })
      onLoadState('loading')
      onPageError('')
      const reloadResult = await requestReviewCaseDetail({
        getReviewCase,
        request: { firebaseUser: currentUser, reviewCaseId },
        reviewCaseId,
      })
      onReviewCaseAction(reloadResult.action)
      if (reloadResult.status === 'succeeded') {
        onLoadState('ready')
      } else {
        onPageError(
          reloadResult.error.message || 'Review case could not be reloaded.',
        )
        onLoadState('error')
      }
      onFormStatus({
        message: closeResult.error.message || 'Review case changed and was reloaded.',
        type: 'error',
      })
      return { ...closeResult, reloadResult }
    } finally {
      submissionInFlight = false
      onSubmitting(false)
    }
  }
}
