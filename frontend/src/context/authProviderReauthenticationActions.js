import {
  EmailAuthProvider,
  GoogleAuthProvider,
  reauthenticateWithCredential,
  reauthenticateWithPopup,
} from 'firebase/auth'
import {
  getReauthenticationProviderId,
  reauthenticateWithEmailPassword,
  reauthenticateWithGoogle,
} from '../lib/reauthentication.js'

const googleProvider = new GoogleAuthProvider()
const authApi = {
  EmailAuthProvider,
  reauthenticateWithCredential,
  reauthenticateWithPopup,
}

export function buildAuthProviderReauthenticationActions({ firebaseUser }) {
  return {
    getReauthenticationProviderId: () => getReauthenticationProviderId(firebaseUser),
    reauthenticateWithPassword: async (password) => {
      await reauthenticateWithEmailPassword({
        authApi,
        firebaseUser,
        password,
      })
    },
    reauthenticateWithGoogle: async () => {
      await reauthenticateWithGoogle({
        authApi,
        firebaseUser,
        googleProvider,
      })
    },
  }
}
