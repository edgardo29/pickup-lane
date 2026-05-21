export function getDisplayName(appUser, firebaseUser) {
  const fullName = `${appUser?.first_name || ''} ${appUser?.last_name || ''}`.trim()

  if (fullName) {
    return fullName
  }

  return appUser?.email || firebaseUser?.email || 'Sign In'
}

export function getInitials(appUser, firebaseUser) {
  const first = appUser?.first_name?.[0]
  const last = appUser?.last_name?.[0]

  if (first || last) {
    return `${first || ''}${last || ''}`.toUpperCase()
  }

  return (appUser?.email || firebaseUser?.email || 'PL').slice(0, 2).toUpperCase()
}
