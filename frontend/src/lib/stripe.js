import { loadStripe } from '@stripe/stripe-js'

export const STRIPE_PUBLISHABLE_KEY = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || ''

export const stripePromise = STRIPE_PUBLISHABLE_KEY
  ? loadStripe(STRIPE_PUBLISHABLE_KEY)
  : null

export function hasStripePublishableKey() {
  return Boolean(STRIPE_PUBLISHABLE_KEY)
}
