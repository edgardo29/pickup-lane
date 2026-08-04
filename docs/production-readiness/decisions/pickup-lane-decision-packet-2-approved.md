# Pickup Lane Decision Packet 2: Approved Record

## Status

**APPROVED**

Approval date: August 3, 2026

This record locks the five decisions from Decision Packet 2. It records policy and architecture direction only. It does not claim implementation, tests, provider configuration, runtime evidence, or production readiness.

## Approved decisions

### IDB-01 / IAM-003: Browser authentication persistence and retry behavior

Approved direction:

- Normal player sessions may persist across browser restarts through explicit Firebase browser authentication persistence.
- Pickup Lane continues using Firebase ID tokens sent to FastAPI as bearer tokens.
- Ordinary browser caching is not the authentication mechanism.
- Logout and account switching must clear user-specific frontend state and cached private data.
- Authentication refresh and safe reads may use bounded retries.
- Payments, bookings, messages, cancellations, admin actions, and other mutations must never be blindly replayed.
- A mutation may be retried only when protected by idempotency or when the system can safely determine the original outcome.
- Sensitive account and administrative actions may later require recent authentication or step-up controls.

Still requires later technical design:

- exact Firebase persistence initialization
- frontend state and cache reset contract
- retry classification and bounded retry rules
- idempotency-key coverage
- recent-authentication triggers
- browser and cross-tab test coverage

### IDB-02 / IAM-006: Identity and profile source of truth

Approved direction:

- Firebase is authoritative for authentication identity and authentication facts.
- PostgreSQL is authoritative for Pickup Lane business identity, profile data, roles, permissions, account restrictions, and resource ownership.
- No field may have two independent authorities.
- Provider-derived values stored in PostgreSQL are snapshots or references, not independent authentication authority.
- Users may not directly write provider-controlled or administrator-controlled fields.
- Synchronization conflicts must fail safely and produce an auditable outcome.

### IDB-03 / IAM-007: Verified-email policy

Approved direction:

- Unverified users may sign in, complete limited profile setup, browse generally available game information, access verification and recovery flows, and sign out.
- Verified email is required before hosting, joining, booking, paying, using Need a Sub interactions, sending private messages, receiving elevated privileges, or performing admin actions.
- Firebase remains authoritative for email-verification state.
- Ordinary users may not write verification timestamps or equivalent verifier-controlled fields.
- Every administrator must use a currently verified identifier.

### IDB-04 / IAM-010: Firebase App Check applicability

Approved direction:

- Firebase App Check is applicable to the supported Pickup Lane web client as defense in depth.
- It does not replace authentication, authorization, rate limiting, idempotency, or replay protection.
- Adoption must proceed through provider sandbox or staging validation, observation, failure testing, staged enforcement, and documented rollback.
- Production enforcement must not begin until false-positive behavior and recovery procedures are understood.

### IDB-05 / FE-M09: Third-party browser code and provider-failure policy

Approved direction:

- Only necessary and explicitly approved third-party browser code may run.
- Every third-party browser dependency, SDK, script, widget, analytics tool, and provider integration must be inventoried.
- The inventory must record purpose, owner, data received, contacted domains, loading method, failure behavior, and removal procedure.
- Personal data sharing must be minimized and documented.
- CSP restrictions are based on actual approved dependencies.
- SRI is used where technically compatible and operationally maintainable.
- Third-party failure must remain isolated and must not expose secrets, corrupt state, duplicate payments, or break unrelated areas.
- Advertising, unrelated tracking, and unnecessary third-party widgets are not approved by default.

## Approval impact

Decision count after this approval:

- Total owner-decision register entries: **27**
- Approved: **12**
- Open: **15**

Previously approved foundation decisions remain unchanged:

- FDN-01 through FDN-07

Newly approved decisions:

- IDB-01 through IDB-05

## Supersession rule

A later change to any decision in this record requires a new superseding decision record. This approved record remains preserved.

## Implementation restriction

This approval does not authorize application code changes, Git branch changes, worktree creation, provider configuration, deployment changes, migrations, or CI changes.
