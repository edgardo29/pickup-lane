import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import {
  confirmReset, invalidPasswords, passwordInput, readyPasswordForm,
  renderResetPassword, savePassword,
} from './resetPasswordTestKit.jsx'

it('F10-3: revealing and hiding preserves the entered password', async () => {
  const user = userEvent.setup()
  renderResetPassword()
  await readyPasswordForm()
  await user.type(passwordInput(), 'Example1!')
  expect(passwordInput()).toHaveAttribute('type', 'password')
  await user.click(screen.getByRole('button', { name: 'Show password' }))
  expect(passwordInput()).toHaveAttribute('type', 'text')
  expect(passwordInput()).toHaveValue('Example1!')
  await user.click(screen.getByRole('button', { name: 'Hide password' }))
  expect(passwordInput()).toHaveAttribute('type', 'password')
  expect(passwordInput()).toHaveValue('Example1!')
})

it.each(invalidPasswords)('F10-5: an invalid password shows its requirements (%s)', async (password) => {
  renderResetPassword()
  const user = userEvent.setup()
  if (password) await savePassword(user, password)
  else { await readyPasswordForm(); await user.click(screen.getByRole('button', { name: 'Save Password' })) }
  expect(screen.getByRole('alert')).toHaveTextContent('Password must be at least 8 characters and include a number or symbol.')
})

it.each(invalidPasswords)('F10-5: an invalid password never reaches Firebase (%s)', async (password) => {
  const user = userEvent.setup()
  renderResetPassword()
  await readyPasswordForm()
  if (password) await user.type(passwordInput(), password)
  await user.click(screen.getByRole('button', { name: 'Save Password' }))
  expect(confirmReset).not.toHaveBeenCalled()
})

it('F10-5: validation marks the password invalid and associates its error', async () => {
  const user = userEvent.setup()
  renderResetPassword()
  await savePassword(user, 'short')
  expect(passwordInput()).toHaveAttribute('aria-invalid', 'true')
  expect(passwordInput()).toHaveAccessibleDescription(/Password must be at least 8 characters and include a number or symbol/)
})

it('F10-1: password requirements describe the input accessibly', async () => {
  renderResetPassword()
  expect(await readyPasswordForm()).toHaveAccessibleDescription('At least 8 characters with a number or symbol')
  expect(passwordInput()).not.toHaveAttribute('aria-invalid', 'true')
})
