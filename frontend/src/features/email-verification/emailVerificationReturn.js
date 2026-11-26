export const CREATE_GAME_RETURN = '/create-game'
export const CREATE_SUB_RETURN = '/need-a-sub?panel=create'

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
  } catch { /* A malformed return value uses the existing Create Game entry. */ }
  return CREATE_GAME_RETURN
}

export function verificationReturnLink(destination) {
  const url = new URL(getVerificationReturnPath(destination), window.location.origin)
  url.searchParams.set('verification', 'return')
  return `${url.pathname}${url.search}`
}
