const AGGREGATE_COUNT_NOTIFICATION_TYPES = new Set([
  'chat_message',
  'sub_chat_message',
])

const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
})

export function formatAdminNotificationDateTime(value) {
  if (!value) {
    return 'No date'
  }

  return dateTimeFormatter.format(new Date(value))
}

export function formatAdminNotificationLabel(value) {
  return String(value || '')
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function formatAdminNotificationReadState(notification) {
  if (!notification) {
    return 'Unknown'
  }

  return notification.is_read ? 'Read' : 'Unread'
}

export function shouldShowAdminNotificationAggregateCount(notification) {
  return (
    notification?.aggregate_count != null
    && AGGREGATE_COUNT_NOTIFICATION_TYPES.has(notification.notification_type)
  )
}

export function formatAdminNotificationActionState(actionState) {
  if (actionState?.status === 'not_evaluated') {
    return 'Stored Action'
  }

  return formatAdminNotificationLabel(actionState?.status || 'unknown')
}

export function shouldApplyAdminNotificationResponse({
  activeRequestId,
  requestId,
  signal,
} = {}) {
  return !signal?.aborted && activeRequestId === requestId
}

export function beginAdminNotificationRequest(requestRef) {
  requestRef.current.controller?.abort()
  const requestId = requestRef.current.id + 1
  const controller = new AbortController()
  requestRef.current = { controller, id: requestId }

  return { controller, requestId }
}

export function cancelAdminNotificationRequest(requestRef) {
  requestRef.current.controller?.abort()
  requestRef.current = {
    controller: null,
    id: requestRef.current.id + 1,
  }
}

export function buildAdminNotificationClearedDetailState() {
  return {
    detailError: '',
    detailLoadState: 'idle',
    selectedNotification: null,
    selectedNotificationId: null,
  }
}

export function buildAdminNotificationClearedCollectionState() {
  return {
    ...buildAdminNotificationClearedDetailState(),
    cursor: '',
    cursorStack: [],
    listError: '',
    listLoadState: 'idle',
    nextCursor: '',
    notifications: [],
  }
}

export function getAdminNotificationRelatedEntries(notification) {
  if (Array.isArray(notification?.related_records)) {
    return notification.related_records
  }

  return []
}

export function getAdminNotificationPrimaryReference(notification) {
  return (
    notification?.primary_related_record
    || getAdminNotificationRelatedEntries(notification)[0]
    || null
  )
}

export function buildAdminNotificationCollectionFilters({ selectedRecipientId = '' } = {}) {
  return {
    user_id: String(selectedRecipientId ?? '').trim(),
  }
}
