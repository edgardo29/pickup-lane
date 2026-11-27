import { act, screen, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { unfinished, finishProfile, GAME_PATH, account, server, renderSignIn, firebaseUser, deferred, emit, settle, http, fakeApi, at, sdkEmail, signIn } from './signInTestKit.jsx'

it.each(['another account', 'signed out'].flatMap((next) => ['account read', 'Firebase credential'].map((stage) => [next, stage])))('F07-1, F07-2: late account reads cannot replace the current session (%s, %s)', async (next, stage) => {
  const oldRead = deferred()
  const credential = deferred()
  const first = firebaseUser('synthetic-first')
  vi.mocked(http).mockImplementation((path, options) => options?.headers?.Authorization === 'Bearer synthetic-synthetic-first' ? oldRead.promise : fakeApi(path, options))
  if (stage === 'Firebase credential') vi.mocked(sdkEmail).mockReturnValueOnce(credential.promise)
  const router = renderSignIn({ initialUser: stage === 'account read' ? first : null })
  if (stage === 'account read') await waitFor(() => expect(http).toHaveBeenCalled())
  else {
    await signIn()
    // The earlier sign-in published A; B/sign-out then replaces it before
    // the original credential promise and account read finish.
    await emit(first)
    await waitFor(() => expect(http).toHaveBeenCalled())
  }
  if (next === 'another account') {
    server.account = account({ id: '00000000-0000-4000-8000-000000000012', email: 'second@example.test' })
    await emit(firebaseUser('synthetic-second')); await at(router, '/games')
  } else await emit(null)
  if (stage === 'Firebase credential') await settle(credential, { user: first })
  await settle(oldRead, account({ email: 'first@example.test' }))
  expect(screen.getByLabelText('Current account')).toHaveTextContent(next === 'another account' ? 'second@example.test' : 'Signed out')
  expect(screen.getByLabelText('Current account')).not.toHaveTextContent('first@example.test')
})

it.each(['another account', 'signed out'])('F07-3: a late profile save cannot replace or navigate the current session (%s)', async (next) => {
  server.account = unfinished()
  const previousSave = deferred()
  vi.mocked(http).mockImplementation((path, options) => path === '/users/me' ? previousSave.promise : fakeApi(path, options))
  const router = renderSignIn({ path: '/finish-profile', from: GAME_PATH, initialUser: firebaseUser() })
  await finishProfile()
  await waitFor(() => expect(http.mock.calls.some(([path]) => path === '/users/me')).toBe(true))
  if (next === 'another account') {
    server.account = account({ id: '00000000-0000-4000-8000-000000000012', email: 'second@example.test' })
    await emit(firebaseUser('synthetic-second'))
    await waitFor(() => expect(screen.getByLabelText('Current account')).toHaveTextContent('second@example.test'))
  } else {
    await emit(null)
    await waitFor(() => expect(screen.getByLabelText('Current account')).toHaveTextContent('Signed out'))
  }
  const destination = next === 'another account' ? '/profile' : '/sign-in'
  await act(async () => router.navigate(destination))
  await settle(previousSave, account({ email: 'first@example.test' }))
  expect(screen.getByLabelText('Current account')).toHaveTextContent(next === 'another account' ? 'second@example.test' : 'Signed out')
  expect(screen.getByLabelText('Current account')).not.toHaveTextContent('first@example.test')
  expect(router.state.location.pathname).toBe(destination)
})
