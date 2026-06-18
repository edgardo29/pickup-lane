export const UPCOMING_MY_GAME_STATUSES = new Set(['pending_payment', 'confirmed', 'waitlisted'])
export const HISTORY_MY_GAME_STATUSES = new Set(['confirmed'])
export const GAME_CANCELLED_TYPES = new Set(['host_cancelled', 'admin_cancelled'])
export const UPCOMING_WINDOW_DAYS = 14

export const myGamesTabs = [
  { key: 'upcoming', label: 'Upcoming' },
  { key: 'history', label: 'History' },
]
