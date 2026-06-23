export const NOTIFICATION_LIMIT_OPTIONS = [25, 50, 100]

export const NOTIFICATION_CATEGORY_OPTIONS = [
  { label: 'All categories', value: '' },
  { label: 'App', value: 'app' },
  { label: 'Game activity', value: 'game_activity' },
]

export const NOTIFICATION_DOMAIN_OPTIONS = [
  { label: 'All domains', value: '' },
  { label: 'App', value: 'app' },
  { label: 'Account', value: 'account' },
  { label: 'Admin', value: 'admin' },
  { label: 'Support', value: 'support' },
  { label: 'Game', value: 'game' },
  { label: 'Need a Sub', value: 'need_a_sub' },
]

export const NOTIFICATION_SOURCE_TYPE_OPTIONS = [
  { label: 'All sources', value: '' },
  { label: 'Pickup Lane', value: 'pickup_lane' },
  { label: 'Official game', value: 'official_game' },
  { label: 'Community game', value: 'community_game' },
  { label: 'Game', value: 'game' },
  { label: 'Need a Sub', value: 'need_a_sub' },
  { label: 'Policy', value: 'policy' },
  { label: 'Support', value: 'support' },
  { label: 'Account', value: 'account' },
  { label: 'Payment', value: 'payment' },
]

export const NOTIFICATION_READ_OPTIONS = [
  { label: 'All read states', value: '' },
  { label: 'Unread', value: 'false' },
  { label: 'Read', value: 'true' },
]

export const NOTIFICATION_ACTION_KEY_OPTIONS = [
  { label: 'All action keys', value: '' },
  { label: 'View game', value: 'view_game' },
  { label: 'View Need a Sub post', value: 'view_sub_post' },
  { label: 'View policy', value: 'view_policy' },
  { label: 'Payment methods', value: 'payment_methods' },
  { label: 'View profile', value: 'view_profile' },
]

export const EMPTY_ADMIN_NOTIFICATION_FILTERS = {
  user_id: '',
  notification_type: '',
  notification_category: '',
  notification_domain: '',
  source_type: '',
  is_read: '',
  action_key: '',
  aggregation_key: '',
  related_game_id: '',
  related_chat_id: '',
  related_booking_id: '',
  related_payment_id: '',
  related_refund_id: '',
  related_participant_id: '',
  related_message_id: '',
  related_sub_post_id: '',
  related_sub_post_chat_id: '',
  related_sub_post_chat_message_id: '',
  related_sub_post_request_id: '',
  related_sub_post_position_id: '',
}

export const ADMIN_NOTIFICATION_RELATED_FIELDS = [
  ['related_game_id', 'Game'],
  ['related_chat_id', 'Game chat'],
  ['related_booking_id', 'Booking'],
  ['related_payment_id', 'Payment'],
  ['related_refund_id', 'Refund'],
  ['related_participant_id', 'Participant'],
  ['related_message_id', 'Game message'],
  ['related_sub_post_id', 'Need a Sub post'],
  ['related_sub_post_chat_id', 'Need a Sub chat'],
  ['related_sub_post_chat_message_id', 'Need a Sub chat message'],
  ['related_sub_post_request_id', 'Need a Sub request'],
  ['related_sub_post_position_id', 'Need a Sub position'],
]

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

export function formatAdminNotificationActionState(actionState) {
  return formatAdminNotificationLabel(actionState?.status || 'unknown')
}

export function getAdminNotificationRelatedEntries(notification) {
  return ADMIN_NOTIFICATION_RELATED_FIELDS
    .map(([field, label]) => ({
      field,
      label,
      value: notification?.[field],
    }))
    .filter((entry) => Boolean(entry.value))
}

export function getAdminNotificationPrimaryReference(notification) {
  const [primaryReference] = getAdminNotificationRelatedEntries(notification)
  return primaryReference || null
}

export function shortAdminNotificationId(value) {
  const stringValue = String(value || '')
  if (stringValue.length <= 12) {
    return stringValue || 'None'
  }

  return `${stringValue.slice(0, 8)}...${stringValue.slice(-4)}`
}

export function sanitizeAdminNotificationFilters(filters) {
  return Object.fromEntries(
    Object.entries(filters).map(([key, value]) => [key, String(value ?? '').trim()]),
  )
}
