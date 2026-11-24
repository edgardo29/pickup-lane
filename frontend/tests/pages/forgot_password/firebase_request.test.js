import { describe, expect, it } from 'vitest'
import {
  buildCredentialActions as buildAuthProviderCredentialActions,
  requestResetEmail as sendPasswordResetEmail,
} from './forgotPasswordTestKit.jsx'

describe('Forgot Password reset link', () => {
  it('F08-1: the reset email uses the application Reset Password route', async () => {
    const actions = buildAuthProviderCredentialActions({})

    await actions.sendPasswordReset('player@example.com')

    expect(sendPasswordResetEmail).toHaveBeenCalledWith(
      expect.anything(), expect.any(String), {
        url: `${window.location.origin}/reset-password`,
        handleCodeInApp: true,
      },
    )
  })
})
