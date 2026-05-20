export function buildPostHeadline(post) {
  return `Need ${post.subs_needed} ${post.subs_needed === 1 ? 'Sub' : 'Subs'}`
}

export function buildPostSubtitle(post) {
  return `${formatStatus(post.game_player_group)} · ${post.format_label} · ${formatSkillLabel(post.skill_level)}`
}

export function formatNeedLabel(position) {
  const spots = Number(position.spots_needed || 0)

  return `${spots} ${spots === 1 ? 'Sub' : 'Subs'} · ${formatNeedType(position)}`
}

export function formatNeedType(position) {
  const playerLabel = {
    men: "Men's",
    women: "Women's",
    open: 'Any',
  }[position.player_group] || formatPlayerType(position.player_group)

  return `${playerLabel} ${formatPositionLabel(position.position_label)}`
}

export function formatNeedCompactLabel(position) {
  return `${formatCompactPlayerType(position.player_group)} ${formatCompactPositionLabel(position.position_label)}`
}

export function formatPlayerType(value) {
  if (value === 'open') {
    return 'Any Player'
  }

  return formatStatus(value)
}

export function formatPositionLabel(value) {
  return {
    field_player: 'Field Player',
    goalkeeper: 'Goalkeeper',
  }[value] || formatStatus(value)
}

function formatCompactPlayerType(value) {
  if (value === 'open') {
    return 'Any'
  }

  return formatStatus(value)
}

function formatCompactPositionLabel(value) {
  if (value === 'field_player') {
    return 'FP'
  }
  if (value === 'goalkeeper') {
    return 'GK'
  }

  return formatStatus(value)
}

export function formatSkillLabel(value) {
  if (value === 'any') {
    return 'Any Skill'
  }

  return formatStatus(value)
}

export function formatStatus(value) {
  return String(value || '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function formatDate(value) {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value))
}

export function formatDateWithYear(value) {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(value))
}

export function formatTime(value) {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

export function formatTimeRange(post) {
  return `${formatTime(post.starts_at)}-${formatTime(post.ends_at)} · ${getDurationMinutes(post)} min`
}

export function formatTimeRangeOnly(post) {
  return `${formatTime(post.starts_at)}-${formatTime(post.ends_at)}`
}

export function getDurationMinutes(post) {
  const startsAt = new Date(post.starts_at)
  const endsAt = new Date(post.ends_at)
  return Math.max(0, Math.round((endsAt - startsAt) / 60000))
}

export function formatPrice(cents) {
  const amount = Number(cents || 0) / 100
  if (amount <= 0) {
    return 'Free'
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount)
}

export function formatLocation(post, { includeStreet = false } = {}) {
  const cityLine = [post.city, post.state].filter(Boolean).join(', ')
  const publicLine = [post.location_name, cityLine].filter(Boolean).join(' · ')

  if (includeStreet && post.address_line_1) {
    return `${post.address_line_1} · ${publicLine}`
  }

  return publicLine
}

export function getRequesterName(request) {
  return request.requester_display_name || 'Pickup Lane Player'
}

export function getRequesterInitials(request) {
  return request.requester_initials || 'PL'
}
