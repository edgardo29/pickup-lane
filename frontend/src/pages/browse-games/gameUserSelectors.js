export function hasCompleteProfile(user) {
  return Boolean(user?.first_name && user?.last_name && user?.date_of_birth)
}

export function getUserDisplayName(user) {
  return `${user?.first_name || ''} ${user?.last_name || ''}`.trim() || user?.email || ''
}
