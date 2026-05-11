import { expect, test } from '@playwright/test'

test('signed-out landing page shows public navigation and entry points', async ({ page }) => {
  await page.goto('/')

  await expect(
    page.getByRole('heading', { name: /find and join pickup soccer games near you/i }),
  ).toBeVisible()

  await expect(page.getByRole('link', { name: 'Pickup Lane home' })).toBeVisible()
  await expect(page.getByRole('navigation', { name: 'Main navigation' })).toContainText(
    'Browse Games',
  )
  await expect(page.locator('header').getByRole('link', { name: 'Sign In' })).toHaveAttribute(
    'href',
    '/sign-in',
  )
  await expect(page.getByRole('region', { name: 'Get started' })).toContainText('Create Account')
})
