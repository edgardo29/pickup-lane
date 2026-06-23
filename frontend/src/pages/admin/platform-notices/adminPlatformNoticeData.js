export const EMPTY_PLATFORM_NOTICE_FILTERS = {
  campaignStatus: '',
  search: '',
}

export const EMPTY_PLATFORM_NOTICE_FORM = {
  audienceType: 'all_active_users',
  body: '',
  deliveryClass: 'mandatory',
  internalName: '',
  summary: '',
  title: '',
}

export const PLATFORM_NOTICE_STATUS_OPTIONS = [
  { label: 'All statuses', value: '' },
  { label: 'Draft', value: 'draft' },
  { label: 'Sending', value: 'sending' },
  { label: 'Completed', value: 'completed' },
  { label: 'Completed with failures', value: 'completed_with_failures' },
  { label: 'Failed', value: 'failed' },
  { label: 'Cancelled', value: 'cancelled' },
]

export const PLATFORM_NOTICE_DELIVERY_STATUS_OPTIONS = [
  { label: 'All recipients', value: '' },
  { label: 'Delivered', value: 'delivered' },
  { label: 'Skipped', value: 'skipped' },
  { label: 'Failed', value: 'failed' },
  { label: 'Pending', value: 'pending' },
]

export function createPlatformNoticeIdempotencyKey() {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return `platform-notice-${globalThis.crypto.randomUUID()}`
  }

  return `platform-notice-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function createPlatformNoticeDeliveryIdempotencyKey(campaignId, operation) {
  const suffix = globalThis.crypto?.randomUUID?.()
    || `${Date.now()}-${Math.random().toString(16).slice(2)}`
  return `platform-notice-${operation}:${campaignId}:${suffix}`
}

export function mapPlatformNoticeCampaignToForm(campaign) {
  return {
    audienceType: campaign?.audience_type || 'all_active_users',
    body: campaign?.body || '',
    deliveryClass: campaign?.delivery_class || 'mandatory',
    internalName: campaign?.internal_name || '',
    summary: campaign?.summary || '',
    title: campaign?.title || '',
  }
}

export function buildPlatformNoticePayload({
  form,
  idempotencyKey,
  selectedUsers,
}) {
  const payload = {
    internal_name: form.internalName.trim(),
    title: form.title.trim(),
    summary: form.summary.trim(),
    body: form.body.trim(),
    audience_type: form.audienceType,
    delivery_class: form.deliveryClass,
    target_user_ids: form.audienceType === 'selected_users'
      ? selectedUsers.map((user) => user.id)
      : [],
  }

  return idempotencyKey
    ? { ...payload, idempotency_key: idempotencyKey }
    : payload
}

export function validatePlatformNoticeForm(form, selectedUsers) {
  const missingFields = [
    !form.internalName.trim() && 'internal name',
    !form.title.trim() && 'title',
    !form.summary.trim() && 'summary',
    !form.body.trim() && 'body',
  ].filter(Boolean)

  if (missingFields.length) {
    return `Enter ${missingFields.join(', ')}.`
  }

  if (form.audienceType === 'selected_users' && selectedUsers.length === 0) {
    return 'Select at least one active user.'
  }

  return ''
}

export function formatPlatformNoticeLabel(value) {
  return String(value || '')
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ') || 'Unknown'
}

export function formatPlatformNoticeDateTime(value) {
  if (!value) {
    return 'No date'
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function shortPlatformNoticeId(value) {
  return value ? String(value).slice(0, 8) : 'Unknown'
}
