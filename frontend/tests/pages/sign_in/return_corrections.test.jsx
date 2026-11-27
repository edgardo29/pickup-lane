import { screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import {
  at, firebaseUser, finishProfile, GAME_ID, http, POST_ID,
  renderSignIn, server, signIn, unfinished,
} from './signInTestKit.jsx'

it.each(['sign-in', 'finish-profile'])('F07-11: an expired post editor falls back to discovery (%s)', async (stage) => {
  server.postOverrides = {
    post_status: 'expired', starts_at: '2026-06-15T16:00:00Z',
    ends_at: '2026-06-15T18:00:00Z', expires_at: '2026-06-15T16:00:00Z',
  }
  if (stage === 'finish-profile') server.account = unfinished()
  const router = renderSignIn({
    from: `/need-a-sub/posts/${POST_ID}/edit`,
    path: stage === 'finish-profile' ? '/finish-profile' : '/sign-in',
    initialUser: stage === 'finish-profile' ? firebaseUser() : null,
    realDestination: 'post edit',
  })
  if (stage === 'finish-profile') await finishProfile()
  else await signIn()
  await at(router, '/games')
  expect(screen.queryByText('This post cannot be edited.')).not.toBeInTheDocument()
})

it.each(['sign-in', 'finish-profile', 'already signed-in'].flatMap((stage) => ['self', 'other'].map((owner) => [stage, owner])))('F07-1, F07-3, F07-9: a publication URL return opens ordinary post detail (%s, %s)', async (stage, owner) => {
  if (stage === 'finish-profile') server.account = unfinished()
  if (owner === 'other') server.resourceOwner = '00000000-0000-4000-8000-000000000099'
  const query = '?tab=details'
  const router = renderSignIn({
    from: `/need-a-sub/posts/${POST_ID}/published${query}`,
    path: stage === 'finish-profile' ? '/finish-profile' : '/sign-in',
    initialUser: stage === 'sign-in' ? null : firebaseUser(),
    realDestination: 'publication',
  })
  if (stage === 'finish-profile') await finishProfile()
  else if (stage === 'sign-in') await signIn()
  await at(router, `/need-a-sub/posts/${POST_ID}${query}`)
  expect(screen.queryByRole('heading', { name: 'Sub post published' })).not.toBeInTheDocument()
})

it.each(['sign-in', 'finish-profile'])('F07-1, F07-3: a hidden-game checkout return loads the connected booking (%s)', async (stage) => {
  if (stage === 'finish-profile') server.account = unfinished()
  server.gameOverrides = { public_visibility_status: 'hidden' }
  server.resourceOwner = '00000000-0000-4000-8000-000000000099'
  const from = `/games/${GAME_ID}/checkout?mode=add-guests&guest_count=1`
  const router = renderSignIn({
    from, path: stage === 'finish-profile' ? '/finish-profile' : '/sign-in',
    initialUser: stage === 'finish-profile' ? firebaseUser() : null,
    realDestination: 'checkout',
  })
  if (stage === 'finish-profile') await finishProfile()
  else await signIn()
  expect(await screen.findByRole('heading', { name: 'Add Guests', level: 1 })).toBeInTheDocument()
  expect(screen.getByText('Evening Pickup')).toBeInTheDocument()
  await at(router, from)
  const gameReads = http.mock.calls.filter(([path]) => path === `/games/${GAME_ID}`)
  expect(gameReads.length).toBeGreaterThanOrEqual(2)
  for (const [, options] of gameReads) expect(options.headers.Authorization).toBe('Bearer synthetic-synthetic-f07-user')
})
