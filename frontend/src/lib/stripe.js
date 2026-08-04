import { loadStripe } from '@stripe/stripe-js'

export const STRIPE_PUBLISHABLE_KEY = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || ''
export const STRIPE_PAYMENTS_ENABLED = import.meta.env.VITE_ENABLE_STRIPE_PAYMENTS === 'true'

export const stripePromise = STRIPE_PAYMENTS_ENABLED && STRIPE_PUBLISHABLE_KEY
  ? loadStripe(STRIPE_PUBLISHABLE_KEY)
  : null

export function areStripePaymentsEnabled() {
  return STRIPE_PAYMENTS_ENABLED
}

export function hasStripePublishableKey() {
  return Boolean(STRIPE_PUBLISHABLE_KEY)
}

export function hasStripeCheckoutSupport() {
  return areStripePaymentsEnabled() && hasStripePublishableKey()
}
