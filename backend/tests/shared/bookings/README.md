# Booking Shared Tests

Owner: Booking rules

Affected pages/features:

- Browse Games: capacity counts valid pending holds and excludes invalid or
  expired holds.
- Game Details/Checkout: checkout creates and releases pending holds.
- Waitlist promotion: promoted users can receive temporary payment-processing
  holds.
- Stripe webhooks: payment events update booking state and must not revive
  expired holds.
- My Games/Admin money views: booking status affects list membership and money
  inspection.

Rules covered here:

- `pending_payment` bookings require `expires_at`.
- Valid pending-payment bookings can exist when `expires_at` is present.

