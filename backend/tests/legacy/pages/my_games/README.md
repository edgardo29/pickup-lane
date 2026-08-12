# My Games Backend Tests

These tests own the authenticated My Games page API contract:

- `GET /my-games`
- `GET /my-games/need-a-sub`

They cover page-owned read behavior: eligibility, response shape, status labels,
hidden/removed filtering, scheduled history windows, sorting, cursor pagination,
and card metadata loading.

Shared lifecycle writers stay with their owning domains. My Games can assert
that it reads durable cancellation proof correctly, but it does not own the full
checkout, payment, waitlist, game-cancellation, or Need a Sub cancellation
mutation lifecycle.
