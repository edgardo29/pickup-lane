import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { waitForCurrentFirebaseUser } from '../../../src/context/authProviderHelpers.js'
import { ApiRequestError, apiRequest } from '../../../src/lib/apiClient.js'
import {
  CARDS, EMAIL_AVAILABILITY, MY_REQUESTS, NOW, POST_DETAIL, REQUEST_SPOT, SAVE_PROFILE, VIEWER_ID, appUser, card,
  cardPage,
  completeSignIn, currentAuth, fakeApi, findCards, fullPost, renderNeedASub, signedOut, updateAuth,
} from './needASubTestKit.jsx'

vi.mock('../../../src/lib/apiClient.js', async (importOriginal) => ({
  ...(await importOriginal()),
  apiRequest: vi.fn(),
}))
vi.mock('../../../src/hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))
vi.mock('../../../src/context/authProviderHelpers.js', () => ({
  waitForCurrentFirebaseUser: vi.fn(),
}))

const POST_ID = '00000000-0000-4000-8000-0000000000c1'
const POST_PATH = `/need-a-sub/posts/${POST_ID}`

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(NOW))
})

afterEach(() => {
  vi.useRealTimers()
})

function postDetailRequests() {
  return vi.mocked(apiRequest).mock.calls.filter(([path]) => path === POST_PATH)
}

// An account before Finish Profile: no names or birthday yet.
const NEW_ACCOUNT = appUser({ email: 'new@example.test', first_name: null, last_name: null, date_of_birth: null })

// Saving a profile answers with the account, now holding the submitted names
// and birthday, as the server does.
function savedProfile(account) {
  return (_path, options) => ({ ...account, ...JSON.parse(options.body) })
}

// A guest on Need a Sub with one card for the post. `detail` is what post
// detail answers once the visitor is signed in.
function guestWithOneCard(detail, moreAnswers = {}) {
  signedOut()
  fakeApi({
    [CARDS]: cardPage({ posts: [card({ id: POST_ID, location_name: 'North Park' })] }),
    [POST_DETAIL]: detail,
    [MY_REQUESTS]: [],
    [EMAIL_AVAILABILITY]: { email: 'new@example.test', available: true },
    [SAVE_PROFILE]: savedProfile(NEW_ACCOUNT),
    ...moreAnswers,
  })
  return renderNeedASub()
}

async function selectTheCard(user) {
  const [northPark] = await findCards()
  await user.click(northPark)
}

async function signInWithEmail(user) {
  currentAuth().signInWithEmail.mockImplementation(async () => completeSignIn())
  await user.type(screen.getByLabelText('Email'), 'player@example.test')
  await user.type(screen.getByLabelText(/^Password/, { selector: 'input' }), 'correct-horse-1')
  await user.click(screen.getByRole('button', { name: 'Sign In' }))
}

async function fillProfile(user) {
  await user.type(screen.getByLabelText('First Name'), 'Jordan')
  await user.type(screen.getByLabelText('Last Name'), 'Player')
  await user.selectOptions(screen.getByLabelText('Birth month'), '01')
  await user.selectOptions(screen.getByLabelText('Birth day'), '01')
  await user.selectOptions(screen.getByLabelText('Birth year'), '1990')
  await user.click(screen.getByRole('button', { name: 'Continue' }))
}

async function createAccountAndFinishProfile(user) {
  await user.click(screen.getByRole('link', { name: 'Create Account' }))
  await screen.findByRole('heading', { name: 'Create Account' })
  currentAuth().beginEmailSignup.mockImplementation((signup) => updateAuth({ pendingSignup: signup }))
  await user.type(screen.getByLabelText('Email'), 'new@example.test')
  await user.type(screen.getByLabelText(/^Password/, { selector: 'input' }), 'correct-horse-1')
  await user.click(screen.getByRole('button', { name: 'Create Account' }))

  await screen.findByRole('heading', { name: 'Finish Profile' })
  const firebaseUser = { displayName: null, getIdToken: async () => 'new-id-token', uid: 'firebase-new' }
  currentAuth().signUpWithEmail.mockImplementation(async () => NEW_ACCOUNT)
  vi.mocked(waitForCurrentFirebaseUser).mockResolvedValue(firebaseUser)
  currentAuth().updateAppUser.mockImplementation((user_) => completeSignIn(user_))
  await user.type(screen.getByLabelText('First Name'), 'Jordan')
  await user.type(screen.getByLabelText('Last Name'), 'Player')
  await user.selectOptions(screen.getByLabelText('Birth month'), '01')
  await user.selectOptions(screen.getByLabelText('Birth day'), '01')
  await user.selectOptions(screen.getByLabelText('Birth year'), '1990')
  await user.click(screen.getByRole('button', { name: 'Continue' }))
}

describe('Need a Sub guest selection and sign-in', () => {
  it('F20-14: a guest selecting a card is sent to Sign In without seeing the post', async () => {
    const user = userEvent.setup()
    const router = guestWithOneCard(fullPost({ id: POST_ID }))

    await selectTheCard(user)

    expect(await screen.findByRole('button', { name: 'Sign In' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/sign-in')
    expect(router.state.location.state).toEqual({ backTo: '/need-a-sub', from: POST_PATH })
    expect(postDetailRequests()).toHaveLength(0)
  })

  it('F20-14: after signing in, the guest returns to the selected post', async () => {
    const user = userEvent.setup()
    const router = guestWithOneCard(fullPost({ id: POST_ID }))
    await selectTheCard(user)
    await screen.findByRole('button', { name: 'Sign In' })

    await signInWithEmail(user)

    await waitFor(() => expect(router.state.location.pathname).toBe(POST_PATH))
    expect(await screen.findByText('200 Test Avenue', { exact: false })).toBeInTheDocument()
    expect(postDetailRequests().at(-1)[1].headers.Authorization).toBe('Bearer test-id-token')
  })

  it('F20-14: after creating an account, the guest returns to the selected post', async () => {
    const user = userEvent.setup()
    const router = guestWithOneCard(fullPost({ id: POST_ID }))
    await selectTheCard(user)
    await screen.findByRole('button', { name: 'Sign In' })

    await createAccountAndFinishProfile(user)

    await waitFor(() => expect(router.state.location.pathname).toBe(POST_PATH))
    expect(await screen.findByText('200 Test Avenue', { exact: false })).toBeInTheDocument()
  })

  it('F20-14: after signing in with Google, the guest returns to the selected post', async () => {
    const user = userEvent.setup()
    const router = guestWithOneCard(fullPost({ id: POST_ID }))
    await selectTheCard(user)
    await screen.findByRole('button', { name: 'Sign In' })
    currentAuth().signInWithGoogle.mockImplementation(async () => completeSignIn())

    await user.click(screen.getByRole('button', { name: 'Continue with Google' }))

    await waitFor(() => expect(router.state.location.pathname).toBe(POST_PATH))
    expect(await screen.findByText('200 Test Avenue', { exact: false })).toBeInTheDocument()
  })

  it('F20-14: a guest signing in with an unfinished profile finishes it first, then returns to the selected post', async () => {
    const user = userEvent.setup()
    const unfinished = appUser({ first_name: null, last_name: null, date_of_birth: null })
    const router = guestWithOneCard(fullPost({ id: POST_ID }), { [SAVE_PROFILE]: savedProfile(unfinished) })
    await selectTheCard(user)
    await screen.findByRole('button', { name: 'Sign In' })
    currentAuth().signInWithEmail.mockImplementation(async () => completeSignIn(unfinished))
    currentAuth().updateAppUser.mockImplementation((finished) => completeSignIn(finished))

    await user.type(screen.getByLabelText('Email'), 'player@example.test')
    await user.type(screen.getByLabelText(/^Password/, { selector: 'input' }), 'correct-horse-1')
    await user.click(screen.getByRole('button', { name: 'Sign In' }))

    expect(await screen.findByRole('heading', { name: 'Finish Profile' })).toBeInTheDocument()
    expect(postDetailRequests()).toHaveLength(0)
    await fillProfile(user)
    await waitFor(() => expect(router.state.location.pathname).toBe(POST_PATH))
    expect(await screen.findByText('200 Test Avenue', { exact: false })).toBeInTheDocument()
  })

  it('F20-14: a guest creating an account with Google finishes the profile, then returns to the selected post', async () => {
    const user = userEvent.setup()
    const googleAccount = appUser({ first_name: null, last_name: null, date_of_birth: null })
    const router = guestWithOneCard(fullPost({ id: POST_ID }), { [SAVE_PROFILE]: savedProfile(googleAccount) })
    await selectTheCard(user)
    await screen.findByRole('button', { name: 'Sign In' })
    await user.click(screen.getByRole('link', { name: 'Create Account' }))
    await screen.findByRole('heading', { name: 'Create Account' })
    // A new Google account: Firebase signs in, but no Pickup Lane account exists yet.
    const firebaseUser = { displayName: null, getIdToken: async () => 'new-id-token', uid: 'firebase-new' }
    currentAuth().signInWithGoogle.mockImplementation(async () => {
      updateAuth({ currentUser: firebaseUser, pendingGoogleSignup: true })
      return null
    })
    currentAuth().syncCurrentFirebaseUser.mockImplementation(async () => googleAccount)
    currentAuth().updateAppUser.mockImplementation((finished) => completeSignIn(finished))

    await user.click(screen.getByRole('button', { name: 'Continue with Google' }))

    expect(await screen.findByRole('heading', { name: 'Finish Profile' })).toBeInTheDocument()
    await fillProfile(user)
    await waitFor(() => expect(router.state.location.pathname).toBe(POST_PATH))
    expect(await screen.findByText('200 Test Avenue', { exact: false })).toBeInTheDocument()
  })

  it('F20-15: a post that became unavailable during sign-in sends the visitor to game discovery', async () => {
    const user = userEvent.setup()
    const router = guestWithOneCard(new ApiRequestError('Need a Sub post not found.', { status: 404 }))
    await selectTheCard(user)
    await screen.findByRole('button', { name: 'Sign In' })

    await signInWithEmail(user)

    expect(await screen.findByRole('heading', { name: 'Game discovery' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/games')
    expect(screen.queryByText('North Park')).not.toBeInTheDocument()
  })

  it('F20-15: a post that became unavailable during account creation sends the visitor to game discovery', async () => {
    const user = userEvent.setup()
    const router = guestWithOneCard(new ApiRequestError('Need a Sub post not found.', { status: 404 }))
    await selectTheCard(user)
    await screen.findByRole('button', { name: 'Sign In' })

    await createAccountAndFinishProfile(user)

    expect(await screen.findByRole('heading', { name: 'Game discovery' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/games')
  })

  it('F20-15: a post that becomes unavailable later in the same visit shows its unavailable message', async () => {
    const user = userEvent.setup()
    const post = fullPost({ id: POST_ID })
    let postIsGone = false
    // The post is cancelled while the request is sent, so the refreshed post
    // detail is no longer available.
    const router = guestWithOneCard(
      () => (postIsGone ? new ApiRequestError('Need a Sub post not found.', { status: 404 }) : post),
      {
        [REQUEST_SPOT]: () => {
          postIsGone = true
          return {
            id: '00000000-0000-4000-8000-0000000000d1',
            sub_post_id: POST_ID,
            sub_post_position_id: post.positions[0].id,
            requester_user_id: VIEWER_ID,
            request_status: 'pending',
            confirmed_at: null,
            declined_at: null,
            sub_waitlisted_at: null,
            canceled_at: null,
            expired_at: null,
            no_show_reported_at: null,
            created_at: NOW,
            updated_at: NOW,
          }
        },
      },
    )
    await selectTheCard(user)
    await screen.findByRole('button', { name: 'Sign In' })
    await signInWithEmail(user)
    await screen.findByText('200 Test Avenue', { exact: false })

    await user.click(screen.getByRole('button', { name: 'Request Spot' }))

    expect(await screen.findByText("This post isn't available right now.")).toBeInTheDocument()
    expect(router.state.location.pathname).toBe(POST_PATH)
  })

  it('F20-15: opening an unavailable post directly still shows its unavailable message', async () => {
    signedOut()
    completeSignIn()
    fakeApi({ [POST_DETAIL]: new ApiRequestError('Need a Sub post not found.', { status: 404 }) })
    const router = renderNeedASub(POST_PATH)

    expect(await screen.findByText("This post isn't available right now.")).toBeInTheDocument()
    expect(router.state.location.pathname).toBe(POST_PATH)
  })
})
