// Cancellation and payment wording shared by Game Details and Game Checkout.

export const COMMUNITY_PAYMENT_RESPONSIBILITY_TEXT =
  'Payment happens outside Pickup Lane, directly with the organizer. Payment disputes ' +
  'and refunds remain between you and the original organizer; Pickup Lane does not ' +
  'process or guarantee refunds.'

const COMMUNITY_CANCELLATION_FALLBACK_TEXT =
  'Review the host payment note before canceling, and confirm payment and refund ' +
  'arrangements with the organizer. Pickup Lane does not refund off-app payments.'

// A community game's cancellation terms: the organizer's own, or wording that
// promises no refund when the organizer gave none.
export function getCommunityCancellationText(game) {
  return game.custom_cancellation_text || COMMUNITY_CANCELLATION_FALLBACK_TEXT
}
