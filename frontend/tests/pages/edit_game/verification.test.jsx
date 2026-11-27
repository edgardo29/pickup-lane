import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { applyActionCode } from 'firebase/auth'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../../../src/hooks/useAuth.js'
import EmailVerificationAction from '../../../src/pages/auth/EmailVerificationAction.jsx'
import { fakePageApi, GAME_ID, game, renderEditGame, signIn } from './editGameTestKit.jsx'

vi.mock('../../../src/lib/apiClient.js', async (importOriginal) => ({
  ...(await importOriginal()),
  apiRequest: vi.fn(),
}))
vi.mock('../../../src/hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))
vi.mock('../../../src/lib/stripe.js', () => ({
  areStripePaymentsEnabled: () => true,
  hasStripeCheckoutSupport: () => true,
  hasStripePublishableKey: () => true,
  stripePromise: null,
}))
vi.mock('firebase/auth', async (importOriginal) => ({
  ...(await importOriginal()),
  applyActionCode: vi.fn(),
}))
vi.mock('../../../src/lib/firebase.js', () => ({ auth: { currentUser: null } }))

const EDIT_PAGE = `/games/${GAME_ID}/edit`

beforeEach(() => signIn({ email_verified_at: null }))

describe('Edit Game email verification', () => {
  it("F18-16: the verification email returns the owner to this game's Edit Game page", async () => {
    const user = userEvent.setup()
    fakePageApi(game())
    renderEditGame()

    await user.click(await screen.findByRole('button', { name: 'Send verification email' }))

    expect(vi.mocked(useAuth)().sendCurrentUserVerificationEmail)
      .toHaveBeenCalledExactlyOnceWith(EDIT_PAGE)
  })

  it("F18-16: after verifying, the link continues to this game's Edit Game page", async () => {
    vi.mocked(applyActionCode).mockResolvedValue(undefined)
    render(
      <MemoryRouter>
        <EmailVerificationAction
          code="verification-code"
          continueUrl={`${window.location.origin}${EDIT_PAGE}?verification=return`}
          isAuthLoading={false}
          refreshCurrentUserVerification={async () => ({ email_verified_at: '2029-06-15T18:00:00Z' })}
        />
      </MemoryRouter>,
    )

    expect(await screen.findByRole('link', { name: 'Continue' }))
      .toHaveAttribute('href', `${EDIT_PAGE}?verification=return`)
  })

  it('F18-20: a visitor who cannot edit the game and has an unverified email sees only the access error', async () => {
    // The server shows the host and the host's guest limit only to the host and staff.
    fakePageApi(game({ host_user_id: null, host_guest_max: 0 }))
    renderEditGame()

    expect(await screen.findByText('Only the host of a community game can edit it.')).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Email verification' })).not.toBeInTheDocument()
  })
})
