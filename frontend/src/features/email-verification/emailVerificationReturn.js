export const CREATE_GAME_RETURN = '/create-game'
export const CREATE_SUB_RETURN = '/need-a-sub?panel=create'
// The Edit Game page of one game; the game id is a UUID.
const EDIT_GAME_RETURN = /^\/games\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\/edit$/i

// Firebase's continueUrl is untrusted input, even when the email is genuine.
export function getVerificationReturnPath(value) {
  try {
    if (!value || typeof value !== 'string') return CREATE_GAME_RETURN
    const url = new URL(value, window.location.origin)
    if (url.origin !== window.location.origin) return CREATE_GAME_RETURN
    if (url.pathname === '/create-game') return CREATE_GAME_RETURN
    if (url.pathname === '/need-a-sub' && url.searchParams.get('panel') === 'create') {
      return CREATE_SUB_RETURN
    }
    if (EDIT_GAME_RETURN.test(url.pathname)) return url.pathname
  } catch { /* A malformed return value uses the existing Create Game entry. */ }
  return CREATE_GAME_RETURN
}

export function getVerificationReturnLabel(destination) {
  if (destination === CREATE_SUB_RETURN) return 'Create Sub Post'
  if (EDIT_GAME_RETURN.test(destination)) return 'Edit Game'
  return 'Create Game'
}

export function verificationReturnLink(destination) {
  const url = new URL(getVerificationReturnPath(destination), window.location.origin)
  url.searchParams.set('verification', 'return')
  return `${url.pathname}${url.search}`
}
