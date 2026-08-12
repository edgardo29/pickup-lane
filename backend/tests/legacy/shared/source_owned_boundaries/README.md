# Source-Owned Boundary Tests

These tests protect source-owned limits approved for production-readiness pass
WS02-04B1.

Covered boundaries:

- Platform Notice selected-audience size, text fields, history, and recipient
  pagination.
- Public card pagination for Need a Sub cards.
- Need a Sub post, substitute, and waitlist limits.
- Saved-card active-card limits.
- Game and Need a Sub chat body, page, and history caps.
- Venue image declared upload size/type and stored-object verification.
- WS02-04B2A2B1 route lifecycle cleanup for retired body-bearing mutation
  scaffolds and their active replacement workflows.
- WS02-04B2A2B2 opaque provider/payment inputs, checkout return URL ownership,
  payment/refund/event generic mutation retirement, retained payment-event
  repair bounds, and source-derived game-credit issue/reverse behavior.
- WS02-04B2A2B3 policy/legal request ownership cleanup for retired generic
  policy document authoring and policy acceptance mutation routes while managed
  read behavior remains available.

This folder is cross-domain by design because WS02-04B1 is a governance pass
for source-owned API limits, and later WS02-04B2 splits continue that
cross-domain request-boundary work. Page-level browse and My Games pagination
coverage remains in `backend/tests/pages/`.
