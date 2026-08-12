# Authentication Shared Tests

Owner: Shared authentication and active-user dependencies

Affected pages/features:

- My Games: `/my-games` and `/my-games/need-a-sub` use `require_active_user`.
- Product actions that require an active Pickup Lane user.
- Account/support flows that deliberately use the broader authenticated-user
  dependency instead remain owned by their route families.

Rules covered here:

- Firebase bearer credentials must be structurally valid and verified before an
  app user is resolved.
- Invalid, expired, and revoked Firebase credentials fail closed.
- `require_active_user` allows only existing app users with
  `account_status = active` and no `deleted_at` timestamp.
- Suspended, deleted, and pending-deletion app users cannot pass active-product
  authorization.
