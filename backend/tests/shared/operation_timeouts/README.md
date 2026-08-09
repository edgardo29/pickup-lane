# Operation Timeout Tests

These tests cover WS02-04C1 operation-specific timeout ownership and
cancellation semantics.

They verify typed timeout settings, Stripe read versus mutation ownership,
Firebase shared HTTP timeout behavior, R2 metadata timeout behavior, stable
public timeout contracts, cancellation classification, and PostgreSQL
pool/statement/lock timeout behavior against the dedicated backend test
database.

Provider tests use fakes only. They must not call live Stripe, Firebase, R2, or
any other external provider.
