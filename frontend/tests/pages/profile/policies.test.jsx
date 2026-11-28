import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { expect, it } from 'vitest'
import SettingsContent from '../../../src/pages/profile/SettingsContent.jsx'

// The real Profile settings surface owns these actions. No HTTP calls occur.
function ProfilePolicies() {
  const [policy, setPolicy] = useState('')
  return <SettingsContent
    activeLegalPolicyId={policy} setActiveLegalPolicyId={setPolicy}
    accountRows={[]} accountAccessRows={[]} preferenceRows={[]}
    supportRows={[
      { title: 'Terms of Service', onClick: () => setPolicy('terms') },
      { title: 'Privacy Policy', onClick: () => setPolicy('privacy') },
    ]}
  />
}

it.each(['Terms of Service', 'Privacy Policy'])('F12-5: a policy modal contains focus and returns to Profile (%s)', async (policy) => {
  render(<ProfilePolicies />); const user = userEvent.setup()
  const opener = screen.getByRole('button', { name: policy }); await user.click(opener)
  const close = screen.getByRole('button', { name: `Close ${policy}` })
  const content = screen.getByRole('region', { name: `${policy} text` })
  expect(content).toHaveAttribute('tabindex', '0')
  expect(close).toHaveFocus(); await user.tab(); expect(content).toHaveFocus(); await user.tab(); expect(close).toHaveFocus()
  await user.keyboard('{Escape}')
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument(); expect(opener).toHaveFocus()
})
