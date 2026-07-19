const REVIEW_STATUS_LABELS = {
  chat_moderation: 'Chat Moderation',
  content_moderation: 'Content Moderation',
}

const REVIEW_TARGET_TYPE_LABELS = {
  community_game: 'Community Game',
  need_a_sub: 'Need a Sub Post',
  money: 'Money Review',
  user: 'User Review',
  system: 'System Review',
}

const REVIEW_ISSUE_LABELS = {
  chat_moderation: 'Chat moderation',
  harassment_or_abuse: 'Harassment or abuse',
  off_app_contact: 'Personal info · Off-app contact',
  payment_pressure: 'Payment pressure',
  sexual_or_explicit: 'Sexual or explicit',
  slur_or_hate: 'Hate or slur',
  spam_or_scam: 'Spam or scam',
  threat_or_violence: 'Threat or violence',
  unsafe_payment_text: 'Payment text',
  unsafe_post_text: 'Post text',
}

export function formatAdminReviewStatus(value) {
  if (REVIEW_STATUS_LABELS[value]) {
    return REVIEW_STATUS_LABELS[value]
  }

  return String(value || '')
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ') || 'Unknown'
}

export function formatAdminReviewDateTime(value) {
  if (!value) return 'No date'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Invalid date'

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

export function formatAdminReviewUpdated(value) {
  return `Updated ${formatAdminReviewDateTime(value)}`
}

export function formatAdminReviewClosed(value) {
  return `Closed ${formatAdminReviewDateTime(value)}`
}

export function formatAdminReviewTargetType(reviewCase) {
  if (reviewCase.target_sub_post_id || reviewCase.target_sub_post_request_id) {
    return 'Need a Sub Post'
  }
  if (reviewCase.target_game_id && reviewCase.case_type === 'community_game') {
    return 'Community Game'
  }
  return REVIEW_TARGET_TYPE_LABELS[reviewCase.case_type] || 'Review Case'
}

export function formatAdminReviewTargetCurrentStatus(reviewCase) {
  const status = reviewCase.target_summary?.status
  return status ? formatAdminReviewStatus(status) : ''
}

export function formatAdminReviewTargetTypeWithStatus(reviewCase) {
  const targetType = formatAdminReviewTargetType(reviewCase)
  const targetStatus = formatAdminReviewTargetCurrentStatus(reviewCase)

  if (targetStatus.toLowerCase() === 'active') {
    return targetType
  }

  return targetStatus ? `${targetType} · ${targetStatus}` : targetType
}

export function formatAdminReviewIssueLabel(value) {
  if (REVIEW_ISSUE_LABELS[value]) {
    return REVIEW_ISSUE_LABELS[value]
  }

  return formatAdminReviewStatus(value)
}

export function formatAdminReviewIssueLabels(values = [], maxLabels = 2) {
  const labels = values.map(formatAdminReviewIssueLabel).filter(Boolean)
  if (labels.length <= maxLabels) {
    return labels.join(' · ')
  }
  return `${labels.slice(0, maxLabels).join(' · ')} (+${labels.length - maxLabels} more)`
}

export function getAdminReviewFindingCountParts(reviewCase) {
  const summary = reviewCase.finding_summary || {}
  const currentCount = summary.current_finding_count || 0
  const totalCount = summary.total_finding_count || currentCount
  const isClosed = reviewCase.case_status === 'closed'
  const count = isClosed ? totalCount : currentCount
  const label = count === 1 ? 'finding' : 'findings'
  const activeLabel = currentCount === 1 ? 'active finding' : 'active findings'

  return {
    count,
    label: isClosed ? label : activeLabel,
  }
}

export function formatAdminReviewClosureDetail(reviewCase) {
  return formatAdminReviewStatus(reviewCase.closure_outcome || 'closed')
}

export function formatAdminReviewFindingDetail(reviewCase) {
  const summary = reviewCase.finding_summary || {}
  const currentCount = summary.current_finding_count || 0
  const issueTypeCount = summary.current_issue_type_count || 0
  const currentLabels = summary.current_issue_labels || []
  const previousLabels = summary.previous_issue_labels || []

  if (currentCount >= 25 || issueTypeCount >= 4) {
    const issueLabel = issueTypeCount === 1 ? 'issue type' : 'issue types'
    return `${issueTypeCount} ${issueLabel}`
  }
  if (currentLabels.length > 0) {
    return formatAdminReviewIssueLabels(currentLabels)
  }
  if (previousLabels.length > 0) {
    return `Previously: ${formatAdminReviewIssueLabels(previousLabels)}`
  }
  return 'No issue labels available'
}

export function shortAdminReviewId(value) {
  return value ? String(value).slice(0, 8) : 'None'
}

export function getAdminReviewTargetPath(reviewCase) {
  if (reviewCase.target_game_id) {
    return `/admin/community-games/${reviewCase.target_game_id}`
  }
  if (reviewCase.target_sub_post_request_id) {
    return `/admin/need-a-sub/requests/${reviewCase.target_sub_post_request_id}`
  }
  if (reviewCase.target_sub_post_id) {
    return `/admin/need-a-sub/${reviewCase.target_sub_post_id}`
  }
  if (reviewCase.target_financial_outcome_id) {
    return `/admin/money/financial-outcomes/${reviewCase.target_financial_outcome_id}`
  }
  if (reviewCase.target_payment_id) {
    return `/admin/money/payments/${reviewCase.target_payment_id}`
  }
  if (reviewCase.target_user_id) {
    return `/admin/users/${reviewCase.target_user_id}`
  }
  return ''
}

export function canOpenAdminReviewTarget(reviewCase) {
  const targetStatus = String(reviewCase.target_summary?.status || '').toLowerCase()
  if (targetStatus === 'unavailable' || targetStatus === 'deleted') {
    return false
  }

  return Boolean(getAdminReviewTargetPath(reviewCase))
}
