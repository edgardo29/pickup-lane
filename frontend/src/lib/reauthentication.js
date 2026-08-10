export const EMAIL_PASSWORD_PROVIDER_ID = 'password'
export const GOOGLE_PROVIDER_ID = 'google.com'

export function getReauthenticationProviderId(firebaseUser) {
  const providerIds = new Set(
    firebaseUser?.providerData?.map((provider) => provider?.providerId).filter(Boolean)
      ?? [],
  )

  if (providerIds.has(EMAIL_PASSWORD_PROVIDER_ID)) {
    return EMAIL_PASSWORD_PROVIDER_ID
  }

  if (providerIds.has(GOOGLE_PROVIDER_ID)) {
    return GOOGLE_PROVIDER_ID
  }

  return ''
}

export async function reauthenticateWithEmailPassword({
  authApi,
  firebaseUser,
  password,
}) {
  if (!firebaseUser?.email) {
    throw new Error('Sign in before continuing.')
  }
  if (!password) {
    throw new Error('Password is required.')
  }

  const credential = authApi.EmailAuthProvider.credential(firebaseUser.email, password)
  await authApi.reauthenticateWithCredential(firebaseUser, credential)
  await firebaseUser.getIdToken(true)
}

export async function reauthenticateWithGoogle({
  authApi,
  firebaseUser,
  googleProvider,
}) {
  if (!firebaseUser) {
    throw new Error('Sign in before continuing.')
  }

  await authApi.reauthenticateWithPopup(firebaseUser, googleProvider)
  await firebaseUser.getIdToken(true)
}
