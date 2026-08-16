# Pickup Lane Production-Readiness Program Context

## 1. Purpose And How To Use This Document

This is the starting point for continuing Pickup Lane production-readiness
work in a new ChatGPT/Codex conversation, engineering session, or review.

It provides:

- the program story;
- terminology;
- a document map;
- required reading order;
- workflow overview;
- trusted evidence overview;
- pass-ordering guidance;
- mandatory gate document inputs.

This document is orientation and navigation only. It does not override
`docs/production-readiness/00-READ-ME-FIRST.md`, higher-authority controls or
decisions, accepted pass plans, or the current accepted repository truth. If
this document conflicts with authority or current repository truth, follow the
authority/current truth and report that this context document is stale.

## 2. Pickup Lane At The Level Needed For This Work

Pickup Lane is a web application for organizing and operating basketball games.
The production-readiness program does not require a full product specification,
but a reviewer needs the shape of the system:

- Backend: FastAPI application code under `backend/`.
- Frontend: React/Vite browser application under `frontend/`.
- Database: PostgreSQL, managed through SQLAlchemy models and Alembic.
- Authentication: Firebase-backed user identity and admin access behavior.
- Payments: Stripe-backed payment and checkout flows.
- External providers: hosting, database provider, Firebase/GCP, Stripe,
  Cloudflare/R2, DNS/TLS, repository/CI, and future monitoring or backup
  providers.
- Product workflows: games, bookings, rosters, waitlists, Need-a-Sub, chats,
  notifications, venue images, credits, and payment-related state.
- Admin and operations: admin workflows, moderation, notices, deployment,
  health, evidence, ownership, incident, recovery, privacy, and provider
  control-plane behavior.

The program exists because production readiness depends on code, configuration,
tests, provider settings, runtime proof, operational ownership, and recovery
evidence all agreeing with the same authority.

## 3. How The Production-Readiness Program Came Together

The program follows this chain:

```text
Pickup Lane application
-> production-readiness audits
-> locked findings and control checklist
-> approved owner decisions
-> final remediation plan
-> master implementation blueprint
-> prerequisite EN work
-> WS implementation passes
-> EN-01 trusted evidence architecture
-> current pass-recheck program
-> independent review and Git/PR finalization
```

The locked audit set is the group of six audit reports plus the consolidated
control checklist under `docs/production-readiness/audit-research/`. The
checklist contains 163 consolidated controls. Those records capture the
original production-readiness findings and must not be casually reinterpreted
by later code or tests.

Owner decisions are the approved policy and ownership choices under
`docs/production-readiness/decisions/`. The current decision inventory records
27 approved decisions and 0 open decisions. These decisions unblock later
technical work without letting implementation invent policy.

The final remediation plan turns the audit findings into a dependency-aware
program. The master blueprint turns that program into ordered implementation
passes. The early EN passes establish foundations that later WS passes depend
on:

- EN-01: trusted backend test taxonomy, isolation, requirement metadata, and
  checker/traceability architecture.
- EN-02: safe observability/privacy primitives for correlation, events,
  redaction, public errors, and telemetry labels.
- EN-03: secrets, provider-control-plane, and safe evidence foundations.

WS passes then implement and revalidate production-readiness workstream slices.
Rechecks are needed because implementation may have evolved, original plans may
have omissions, current repository truth may differ from the original PR, old
evidence is not automatically trusted, fresh trusted evidence must be built
from current authority under EN-01, and external/provider facts cannot be
honestly proven by local tests.

## 4. Authority And Repository Truth

The authority entry point is
`docs/production-readiness/00-READ-ME-FIRST.md`.

At a high level:

- Authority determines what must be true.
- The accepted current `develop` branch is current repository truth.
- Plans must be reconciled against higher authority before implementation.
- Tests do not define product requirements.
- Historical PRs and implementation history are provenance, not authority.
- Current source does not define its own requirements.
- External facts remain unknown until accepted evidence exists.

Do not duplicate or override the complete authority hierarchy here. Read
`docs/production-readiness/00-READ-ME-FIRST.md` before doing pass work.

## 5. Production-Readiness Document Map

| Path | Purpose |
|---|---|
| `docs/production-readiness/00-READ-ME-FIRST.md` | Authority entry point and bundle rules. |
| `docs/production-readiness/01-PROGRAM-CONTEXT.md` | This onboarding and navigation document. |
| `docs/production-readiness/audit-research/` | Locked audit reports, consolidated 163-control checklist, research consolidation, and static inventory crosswalk. |
| `docs/production-readiness/decisions/` | Approved decision records and final decision inventory. |
| `docs/production-readiness/governance/` | Production ownership, environment, provider, secret, evidence, risk, exception, audit-process, and operational governance records. |
| `docs/production-readiness/planning/pickup-lane-production-readiness-remediation-plan-final.md` | Final remediation plan and dependency-aware workstream program. |
| `docs/production-readiness/planning/pickup-lane-master-production-readiness-blueprint.md` | Master implementation blueprint and planned pass register. |
| `docs/production-readiness/planning/PASS-RECHECK-WORKFLOW.md` | Four-gate workflow for rechecking already implemented passes. |
| `docs/production-readiness/planning/PASS-PLANNING-TEMPLATE.md` | Canonical reusable planning-document structure for production-readiness passes. |
| `docs/production-readiness/planning/TESTING-RECORD-TEMPLATE.md` | Canonical reusable testing/risk-record structure. |
| `docs/production-readiness/planning/PASS-PR-DESCRIPTION-TEMPLATE.md` | Standard PR description template for production-readiness passes. |
| `docs/production-readiness/planning/` | Individual canonical pass plans. |
| `docs/agent-notes/` | Selectively tracked durable repository engineering/testing standards used by this program. |
| `backend/tests/support/requirements/` | Machine-readable stable requirement declarations. |
| `backend/tests/checker/` | EN-01 checker and testing-foundation self-tests and testing record. |
| `backend/tests/compliance/` | Checker implementation modules used by trusted validation. |
| `backend/tests/platform/` | Trusted platform-scope production-readiness tests and testing records. |
| `backend/tests/checker/TESTING_RECORD.md` | Human testing/risk record for the EN-01 checker/foundation scope. |
| `backend/tests/platform/settings/TESTING_RECORD.md` | Human testing/risk record for typed settings/environment evidence. |
| `backend/tests/platform/runtime/TESTING_RECORD.md` | Human testing/risk record for runtime lifecycle/health evidence. |
| `backend/tests/platform/http_security/TESTING_RECORD.md` | Human testing/risk record for HTTP security evidence. |
| `backend/tests/platform/observability/TESTING_RECORD.md` | Human testing/risk record for EN-02 observability/privacy evidence. |
| `backend/tests/platform/secrets/TESTING_RECORD.md` | Human testing/risk record for EN-03 secret-contract evidence. |
| `backend/tests/platform/api_errors/TESTING_RECORD.md` | Human testing/risk record for WS02-04A API error-contract evidence. |

The production-readiness planning documents explain what must be true and why.
Requirement declaration JSON gives tooling stable machine-readable identity.
`TESTING_RECORD.md` files explain human risk/evidence reasoning. Pytest files
prove executable behavior where local executable proof is the honest evidence
layer. The checker validates machine-verifiable structure and traceability; it
does not replace human adequacy review.

## 6. Required Supporting Repository Documents

These supporting engineering and testing standards are tracked durable
repository standards. After this branch is merged, they are available to a
GitHub-connected ChatGPT/Codex session from the repository. They support
implementation and evidence mechanics within their approved scope; they are
not production-readiness authority and do not override
`docs/production-readiness/00-READ-ME-FIRST.md` or higher authority.

| Document | Why it must be read |
|---|---|
| `docs/agent-notes/global-rules.md` | Repo-wide working rules, secrets hygiene, Git hygiene, and command expectations. |
| `docs/agent-notes/app-testing-standards.md` | Application-wide risk discovery, scenario classification, safeguard reasoning, and evidence adequacy rules. |
| `docs/agent-notes/backend-testing.md` | Backend pytest ownership, EN-01 architecture, requirement traceability, test isolation, and coverage expectations. |
| `backend/tests/README.md` | Current backend checker architecture, trusted roots, requirement declarations, `TESTING_RECORD.md` ownership, and checker command model. |
| `docs/agent-notes/backend-structure.md` | Backend ownership boundaries, layer responsibilities, import direction, and file placement. |
| `docs/agent-notes/database.md` | PostgreSQL, Alembic, migration ownership, and test database safety. |
| `docs/agent-notes/frontend-structure.md` | Required when a pass touches frontend source, frontend configuration, routing, or browser behavior. |
| `docs/agent-notes/playwright-structure.md` | Required only when a pass explicitly needs Playwright, browser, or end-to-end evidence. |

`backend/tests/README.md` remains the current tracked backend test/checker
guide. Frontend and Playwright standards are required only when their scopes
apply.

## 7. Four-Gate Recheck Workflow

The exact process is defined by
`docs/production-readiness/planning/PASS-RECHECK-WORKFLOW.md`.

Gate A is reconciliation and design. It performs the zero-trust audit,
reconciles the canonical pass plan, and freezes the exact implementation and
evidence design after human approval.

Gate B is approved implementation and trusted evidence. It implements only the
frozen Gate A file set, creates or updates requirement declarations/testing
records/tests/evidence as approved, validates the result, and stops before Git
publication.

Gate C is independent semantic read-only review. It verifies authority,
implementation, evidence adequacy, scope, traceability, confidentiality, and
the complete local pass state. It does not edit files.

Gate D is mechanical Git and PR finalization after Gate C approval. It verifies
the approved change set, stages approved files, commits, pushes normally,
creates or updates the intended PR, reviews the remote PR, and stops before
merge. The owner merges manually.

The run that modifies files owns post-change validation. The read-only reviewer
owns semantic review.

## 8. Trusted Evidence Model

EN-01 establishes the trusted backend evidence architecture.

The permanent traceability model is:

```text
PRODUCTION-READINESS PASS
-> STABLE REQUIREMENT ID
-> MEANINGFUL SCENARIOS / EDGE CASES
-> PYTEST TESTS OR OTHER EVIDENCE
```

Stable requirement declarations live under
`backend/tests/support/requirements/`. These JSON files are not product specs.
They store the minimum identity the checker needs: requirement ID, owning pass,
source controls, current state, owning scope when needed, and a reason when a
requirement is `covered_elsewhere`, `deferred`, `blocked`, or otherwise not
directly executable in the current pytest scope.

Pytest tests use requirement markers to declare which stable requirement IDs
they prove. Exact current pytest node IDs are generated from pytest collection
and checker metadata, so permanent planning documents do not hand-maintain
node lists that will drift when test files or test names change.

`TESTING_RECORD.md` files own human reasoning for one coherent trusted scope:
risks, invariants, scenario groups, proof layers, gaps, deferrals, and adequacy
conclusions. They explain why the evidence is meaningful; they do not duplicate
every Python assertion.

Evidence can be executable or non-executable:

- Executable evidence is usually pytest, checker, or other deterministic local
  validation.
- Non-executable evidence can be source review, governance records, sanitized
  provider evidence, runtime observations, manual review, or later controlled
  evidence packages.

`covered_elsewhere` means the requirement is intentionally proved by another
accepted scope or artifact. `deferred` means the requirement remains for a
later owner or evidence source. Provider/external facts remain unknown until
sanitized, attributable evidence exists from the correct environment or
control plane.

Passing tests alone never proves production readiness. Tests must be derived
from current authority and accepted current source, mapped to stable
requirements, reviewed for semantic adequacy, and combined with any required
repository, runtime, provider, operational, or recovery evidence.

## 9. Excluded-Test Rule

For production-readiness work, `backend/tests/legacy/` is treated as
nonexistent.

It must not be read, searched, executed, listed, cited, used for provenance, or
used to derive requirements, scenarios, assertions, implementation decisions,
or evidence.

## 10. Pass Plans, Pass Families, And Ordering

Each pass plan stays within the material scope of that pass. A pass plan may
include artifacts, requirements, dependencies, integrations, evidence,
controls, and ownership boundaries only when they materially define,
implement, govern, constrain, or prove that pass.

Parent or closeout documents are not automatically the next implementation
target. Large pass families may have ordered child passes. Agents must verify
the actual intended order before selecting the next pass and must not jump
ahead based on alphabetical filenames.

The current WS02-04 child-pass sequence is verified from
`docs/production-readiness/planning/ws02-04-source-owned-closeout.md`:

| Order | Pass | Planning document |
|---|---|---|
| 1 | WS02-04A - Stable Backend Error Contracts | `docs/production-readiness/planning/ws02-04a-stable-error-contracts.md` |
| 2 | WS02-04B1 - Source-Owned Boundaries | `docs/production-readiness/planning/ws02-04b1-source-owned-boundaries.md` |
| 3 | WS02-04B2A1 - Portable Request Boundaries | `docs/production-readiness/planning/ws02-04b2a1-portable-request-boundaries.md` |
| 4 | WS02-04B2A2A - Active Workflow Schema Bounds | `docs/production-readiness/planning/ws02-04b2a2a-active-workflow-schema-bounds.md` |
| 5 | WS02-04B2A2B1 - Route Lifecycle Cleanup | `docs/production-readiness/planning/ws02-04b2a2b1-route-lifecycle-cleanup.md` |
| 6 | WS02-04B2A2B2 - Opaque Provider Payment Inputs | `docs/production-readiness/planning/ws02-04b2a2b2-opaque-provider-payment-inputs.md` |
| 7 | WS02-04B2A2B3 - Policy Legal Request Ownership | `docs/production-readiness/planning/ws02-04b2a2b3-policy-legal-request-ownership.md` |
| 8 | WS02-04B2A2C - Ordinary JSON Request Body Limit | `docs/production-readiness/planning/ws02-04b2a2c-ordinary-json-request-body-limit.md` |
| 9 | WS02-04C1 - Operation Timeouts Cancellation | `docs/production-readiness/planning/ws02-04c1-operation-timeouts-cancellation.md` |
| 10 | WS02-04C2 - Retry Reconciliation Backpressure | `docs/production-readiness/planning/ws02-04c2-retry-reconciliation-backpressure.md` |
| 11 | WS02-04C3A - Chat Rate Limit Contract | `docs/production-readiness/planning/ws02-04c3a-chat-rate-limit-contract.md` |
| 12 | WS02-04C3B - Provider Cost Rate Limit Deferral | `docs/production-readiness/planning/ws02-04c3b-provider-cost-rate-limit-deferral.md` |

After WS02-04A, the next planned child pass is WS02-04B1 using
`docs/production-readiness/planning/ws02-04b1-source-owned-boundaries.md`.

## 11. Key Terminology

| Term | Meaning |
|---|---|
| Control | A production-readiness control from the locked checklist, such as `API-M12`. |
| Requirement | A stable pass-owned obligation that states what must be true for that pass. |
| Pass | A bounded production-readiness work unit with its own plan, evidence, review, and Git/PR finalization. |
| Pass family | A larger workstream slice split into ordered child passes, such as WS02-04. |
| Recheck | A zero-trust revalidation of an already implemented pass against current authority, source, and evidence standards. |
| Accepted baseline | The exact accepted `develop` commit used as the starting point for a pass branch. |
| Frozen plan | The approved Gate A plan, requirement set, correction design, evidence design, and file set. |
| Repository truth | The current accepted source/configuration/documentation state at the trusted baseline and accepted pass commits. |
| Provenance | Historical evidence of what happened, such as PRs, commits, and diffs; provenance does not define requirements. |
| Trusted evidence | Evidence produced from current authority under the accepted evidence architecture. |
| Executable evidence | Deterministic local proof such as pytest, checker, or static validation. |
| Non-executable evidence | Reviewable proof such as governance records, source review, sanitized provider evidence, or runtime observations. |
| Requirement declaration | A small JSON entry under `backend/tests/support/requirements/` declaring stable machine-readable requirement identity. |
| `TESTING_RECORD` | A human testing/risk record explaining adequacy for one trusted scope. |
| Checker | The backend compliance checker that verifies machine-readable structure, markers, scope policy, and traceability. |
| Traceability | Generated mapping from pass requirements to current collected pytest metadata and declaration state. |
| `covered_elsewhere` | A requirement state meaning accepted evidence exists in another scope or artifact. |
| `deferred` | A requirement state meaning proof or completion belongs to a later owner/evidence source. |
| Provider/external evidence | Sanitized, attributable proof from a provider, runtime, dashboard, account, or operational environment outside local source. |
| Gate A | Reconciliation and design. |
| Gate B | Approved implementation and trusted evidence. |
| Gate C | Independent semantic read-only review. |
| Gate D | Mechanical Git and PR finalization. |

## 12. Mandatory Gate Document Matrix

Applicable repository templates and standards are mandatory gate inputs, not
optional references. A gate instruction is incomplete when an applicable
repository template or required standard was not reviewed before drafting it.

| Gate | Mandatory gate inputs |
|---|---|
| Gate A | `PASS-PLANNING-TEMPLATE.md`, `TESTING-RECORD-TEMPLATE.md`, the current pass plan, and applicable engineering/testing standards. |
| Gate B | The frozen plan, `TESTING-RECORD-TEMPLATE.md`, and applicable engineering/testing standards. |
| Gate C | The frozen plan, requirement declaration, `TESTING_RECORD.md`, implemented evidence, and current validation. Use `TESTING-RECORD-TEMPLATE.md` when reviewing testing-record compliance. |
| Gate D | The frozen plan, Gate C approval, and `PASS-PR-DESCRIPTION-TEMPLATE.md`. |

Gate-specific prompts may require additional authority, source, governance,
testing, or evidence documents. The matrix is the durable minimum, not a cap.

## 13. New-Agent Bootstrap Reading Order

1. Read `docs/production-readiness/00-READ-ME-FIRST.md` and follow its
   authority rules.
2. Read `docs/production-readiness/01-PROGRAM-CONTEXT.md` completely.
3. Read `docs/production-readiness/planning/PASS-RECHECK-WORKFLOW.md`.
4. Verify current Git/repository state and determine the current pass and gate
   from current repository truth and the current approved instruction.
5. Read the current or frozen canonical pass plan.
6. Read the applicable gate templates and required engineering/testing
   standards from the matrix above.
7. Read only the authority/control/decision material relevant to that pass.
8. Report that you are caught up.
9. Do not begin implementation until explicitly instructed.

## 14. Suggested New-Chat Prompt

> We're continuing Pickup Lane production-readiness work. Start from
> `docs/production-readiness/00-READ-ME-FIRST.md`, then read
> `docs/production-readiness/01-PROGRAM-CONTEXT.md` and
> `docs/production-readiness/planning/PASS-RECHECK-WORKFLOW.md`. Verify current
> repository truth, current pass, and current gate before relying on historical
> chat, PR, branch, or SHA information. Load the gate-specific templates and
> required standards for the current task, then tell me when you're caught up.
> Do not start work yet.
