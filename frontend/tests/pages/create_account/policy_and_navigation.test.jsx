import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import { LEGAL_POLICIES } from '../../../src/features/legal/legalPolicies.js'
import { at, enterEmail, GAME_PATH, PASSWORD, ready, renderSignup } from './createAccountTestKit.jsx'

it('F05-4: Terms opens the shared current policy and development notice', async () => {
  renderSignup(); await ready(); await userEvent.setup().click(screen.getByRole('button', { name: 'Terms of Service' }))
  const dialog = screen.getByRole('dialog', { name: 'Terms of Service' })
  for (const section of LEGAL_POLICIES.terms.sections) expect(within(dialog).getByText(section.body)).toBeInTheDocument()
  expect(dialog).toHaveTextContent('Final legal language should be reviewed before launch.')
})
it('F05-4: Privacy opens the shared current policy and development notice', async () => {
  renderSignup(); await ready(); await userEvent.setup().click(screen.getByRole('button', { name: 'Privacy Policy' }))
  const dialog = screen.getByRole('dialog', { name: 'Privacy Policy' })
  for (const section of LEGAL_POLICIES.privacy.sections) expect(within(dialog).getByText(section.body)).toBeInTheDocument()
  expect(dialog).toHaveTextContent('Final legal language should be reviewed before launch.')
})
it.each(['Terms of Service', 'Privacy Policy'].flatMap((policy) => ['close', 'escape', 'backdrop'].map((how) => [policy, how])))('F05-4: dismissing a policy retains signup details (%s, %s)', async (policy, how) => {
  renderSignup(); const user = await enterEmail(); await user.click(screen.getByRole('button', { name: policy }))
  if (how === 'close') await user.click(screen.getByRole('button', { name: `Close ${policy}` }))
  else if (how === 'escape') await user.keyboard('{Escape}')
  else await user.click(screen.getByRole('dialog'))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(screen.getByLabelText(/^Password/, { selector: 'input' })).toHaveValue(PASSWORD)
})
it('F05-4: switching to Sign In retains the requested destination', async () => {
  const router = renderSignup({ from: GAME_PATH }); await ready(); await userEvent.setup().click(screen.getByRole('link', { name: 'Sign In' })); await at(router, '/sign-in')
  expect(router.state.location.state.from).toBe(GAME_PATH)
})
it.each(['Terms of Service', 'Privacy Policy'])('F05-4: the policy modal contains focus and restores its opener (%s)', async (policy) => {
  renderSignup(); await ready(); const user = userEvent.setup(); const opener = screen.getByRole('button', { name: policy })
  await user.click(opener); const close = screen.getByRole('button', { name: `Close ${policy}` })
  const content = screen.getByRole('region', { name: `${policy} text` })
  expect(content).toHaveAttribute('tabindex', '0')
  expect(close).toHaveFocus(); await user.tab(); expect(content).toHaveFocus(); await user.tab(); expect(close).toHaveFocus(); await user.tab({ shift: true }); expect(content).toHaveFocus()
  await user.keyboard('{Escape}'); expect(opener).toHaveFocus()
})
