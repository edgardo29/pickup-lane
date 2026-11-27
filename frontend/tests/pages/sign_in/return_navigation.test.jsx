import { screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { server, renderSignIn, signIn, at, unfinished, firebaseUser, finishProfile, error, GAME_ID, POST_ID, GAME_PATH } from './signInTestKit.jsx'

it.each(['email', 'google', 'new-google'].flatMap((method) => [undefined, GAME_PATH].map((from) => [method, from])))('F07-3: incomplete sign-in retains its destination through Finish Profile (%s, %s)', async (method, from) => {
  server.account = method === 'new-google' ? null : unfinished()
  const router = renderSignIn({ from }); await signIn(method === 'email' ? 'email' : 'google'); await at(router, '/finish-profile')
  expect(router.state.location.state?.from).toBe(from)
  expect(await screen.findByRole('heading', { name: 'Finish Profile' })).toBeInTheDocument()
})
it.each([false, true].flatMap((missing) => [undefined, GAME_PATH].map((from) => [missing, from])))('F07-3: saving the profile returns to its destination or discovery (new account=%s, %s)', async (missing, from) => {
  server.account = missing ? null : unfinished(); const router = renderSignIn({ path: '/finish-profile', from, initialUser: firebaseUser() })
  await finishProfile(); await at(router, from || '/games')
})
it('F07-3: protected entry survives sign-in and profile completion', async () => {
  server.account = unfinished(); const router = renderSignIn({ path: GAME_PATH })
  await at(router, '/sign-in'); expect(router.state.location.state.from).toBe(GAME_PATH)
  await signIn(); await at(router, '/finish-profile'); expect(router.state.location.state.from).toBe(GAME_PATH)
  await finishProfile(); await at(router, GAME_PATH)
})
it.each([undefined, GAME_PATH])('F07-9: an already signed-in complete account uses its destination or discovery (%s)', async (from) => {
  const router = renderSignIn({ from, initialUser: firebaseUser() }); await at(router, from || '/games')
})
it.each([undefined, GAME_PATH])('F07-9: an already signed-in incomplete account keeps its destination (%s)', async (from) => {
  server.account = unfinished(); const router = renderSignIn({ from, initialUser: firebaseUser() }); await at(router, '/finish-profile')
  expect(router.state.location.state?.from).toBe(from)
})
const recordPaths = [`/games/${GAME_ID}`, `/games/${GAME_ID}/checkout`, `/games/${GAME_ID}/edit`, `/need-a-sub/posts/${POST_ID}`, `/need-a-sub/posts/${POST_ID}/edit`, `/need-a-sub/posts/${POST_ID}/published`]
it.each([...recordPaths.map((path) => [path, 'missing']), ...recordPaths.filter((path) => /\/edit$/.test(path)).map((path) => [path, 'not owner']), ...['official', 'inactive', 'unpublished', 'started'].map((reason) => [`/games/${GAME_ID}/edit`, reason])])('F07-11: an unavailable destination falls back after authentication (%s, %s)', async (from, reason) => {
  if (reason === 'missing') server.returnError = error(from.startsWith('/games/') ? 'Game not found.' : 'Need a Sub post not found.', 404)
  else if (reason === 'not owner') server.resourceOwner = '00000000-0000-4000-8000-000000000099'
  else server.gameOverrides = { official: { game_type: 'official' }, inactive: { game_status: 'cancelled' }, unpublished: { publish_status: 'draft' }, started: { starts_at: '2020-06-15T23:00:00Z' } }[reason]
  const router = renderSignIn({ from }); await signIn(); await at(router, '/games')
  expect(screen.queryByText(new RegExp(from))).not.toBeInTheDocument()
})
it('F07-11: a destination lost during profile completion falls back to discovery', async () => {
  server.account = unfinished(); const router = renderSignIn({ path: '/finish-profile', from: GAME_PATH, initialUser: firebaseUser() })
  server.returnError = error('Game not found.', 404); await finishProfile(); await at(router, '/games')
})
it.each(['https://example.test/private', '//example.test/private', '/sign-in', '/create-account', '/finish-profile', '/reset-password?mode=verifyEmail', '/not-a-page', '/games/invalid', '/games/../admin', '/games/%2fadmin', '/games\\admin'].flatMap((from) => ['sign-in', 'finish-profile', 'already signed-in'].map((stage) => [from, stage])))('F07-1, F07-3, F07-9: an invalid saved destination uses discovery (%s, %s)', async (from, stage) => {
  if (stage === 'finish-profile') server.account = unfinished()
  const router = renderSignIn({ from, path: stage === 'finish-profile' ? '/finish-profile' : '/sign-in', initialUser: stage === 'sign-in' ? null : firebaseUser() })
  if (stage === 'sign-in') await signIn()
  if (stage === 'finish-profile') await finishProfile()
  await at(router, '/games')
})
it.each(recordPaths.filter((path) => !path.endsWith('/published')).flatMap((path) => ['sign-in', 'finish-profile', 'already signed-in'].map((stage) => [`${path}?intent=resume&tab=details`, stage])))('F07-1, F07-3, F07-9: a supported destination keeps its query (%s, %s)', async (from, stage) => {
  if (stage === 'finish-profile') server.account = unfinished()
  const router = renderSignIn({ from, path: stage === 'finish-profile' ? '/finish-profile' : '/sign-in', initialUser: stage === 'sign-in' ? null : firebaseUser() })
  if (stage === 'sign-in') await signIn()
  if (stage === 'finish-profile') await finishProfile()
  await at(router, from)
  if (from.startsWith(`/games/${GAME_ID}/edit`)) {
    expect(await screen.findByRole('combobox', { name: 'Total spots' })).toHaveValue('14')
    expect(screen.getByRole('heading', { name: 'Edit Game' })).toBeInTheDocument()
  } else expect(await screen.findByRole('heading')).toHaveTextContent(from)
})
