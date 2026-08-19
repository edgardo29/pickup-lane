# Pickup Lane Production-Readiness Program Context

## 1. Purpose

This document is the stable program overview and routing index for Pickup Lane
production-readiness work. It explains the system shape, program structure,
document locations, evidence model, pass ordering, terminology, and mandatory
gate inputs.

Startup, authority order, conflict handling, local handoff usage, tracked
documentation safety, and publication boundaries are owned by
`docs/production-readiness/00-READ-ME-FIRST.md`.

Gate prompts should reference `00-READ-ME-FIRST.md`,
`01-PROGRAM-CONTEXT.md`, and applicable current pass artifacts instead of
repeating common document lists. A prompt should name an additional file only
when that file is pass-specific, a frozen artifact, an explicit exception, or
needed to resolve an ambiguity not covered by durable routing. Short prompts do
not reduce Codex's responsibility to follow the routed workflow, standards,
governance, decisions, source, evidence, and frozen-artifact checks.

Optional local current-session orientation is described by
`00-READ-ME-FIRST.md`.

## 2. Pickup Lane And Production-Readiness Overview

Pickup Lane is a web application for organizing and operating pickup soccer games.
The production-readiness program spans code, configuration, tests, provider
settings, runtime proof, operational ownership, and recovery evidence.

System areas relevant to production-readiness planning include:

- Backend: FastAPI application code under `backend/`.
- Frontend: React/Vite browser application under `frontend/`.
- Database: PostgreSQL, SQLAlchemy models, and Alembic migrations.
- Authentication: Firebase-backed user identity and admin access behavior.
- Payments: Stripe-backed payment and checkout flows.
- External providers: hosting, database provider, Firebase/GCP, Stripe,
  Cloudflare/R2, DNS/TLS, repository/CI, monitoring, and backup providers.
- Product workflows: games, bookings, rosters, waitlists, Need-a-Sub, chats,
  notifications, venue images, credits, and payment-related state.
- Admin and operations: admin workflows, moderation, notices, deployment,
  health, evidence, ownership, incident, recovery, privacy, and provider
  control-plane behavior.

Production readiness requires these areas to agree with approved authority and
trusted evidence, not merely to pass local tests.

## 3. Program Structure

The program follows this durable chain:

```text
Pickup Lane application
-> production-readiness audits
-> locked findings and control checklist
-> approved owner decisions
-> final remediation plan
-> master implementation blueprint
-> prerequisite EN work
-> WS implementation passes
-> trusted evidence architecture
-> implementation or recheck workflow
-> independent review and Git/PR finalization
```

The locked audit set and consolidated checklist capture the original
production-readiness findings. Approved owner decisions define policy and
ownership choices. The final remediation plan turns findings into a
dependency-aware program. The master blueprint turns that program into ordered
implementation passes.

EN passes establish cross-cutting foundations such as trusted test
architecture, observability/privacy primitives, secrets/provider controls, and
safe evidence handling. WS passes implement and revalidate bounded workstream
slices against current authority and current repository truth.

## 4. Document Map And Routing Indexes

| Path | Purpose |
|---|---|
| `docs/production-readiness/00-READ-ME-FIRST.md` | Startup, authority, safety, handoff, and publication boundary entry point. |
| `docs/production-readiness/01-PROGRAM-CONTEXT.md` | Stable program overview and routing index. |
| `docs/production-readiness/audit-research/` | Locked audit reports, consolidated checklist, research consolidation, and static inventory crosswalk. |
| `docs/production-readiness/decisions/pickup-lane-master-decision-inventory-v4.md` | Owner-decision routing inventory. Use it to identify relevant approved decision records. |
| `docs/production-readiness/decisions/` | Approved decision records. Read only records relevant to the current pass after using the inventory. |
| `docs/production-readiness/governance/README.md` | Governance routing index. Use it to identify relevant governance records. |
| `docs/production-readiness/governance/` | Production ownership, environment, provider, secret, evidence, risk, exception, audit-process, and operational governance records. |
| `docs/production-readiness/planning/program/pickup-lane-production-readiness-remediation-plan-final.md` | Final remediation plan and dependency-aware workstream program. |
| `docs/production-readiness/planning/program/pickup-lane-master-production-readiness-blueprint.md` | Master implementation blueprint and planned pass register. |
| `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md` | Accepted execution-state register for parent and executable passes. |
| `docs/production-readiness/planning/workflows/PASS-IMPLEMENTATION-WORKFLOW.md` | First-time pass implementation workflow. |
| `docs/production-readiness/planning/workflows/PASS-RECHECK-WORKFLOW.md` | Historical or accepted-pass recheck workflow. |
| `docs/production-readiness/planning/templates/` | Intake, planning, testing-record, and PR-description templates. |
| `docs/production-readiness/planning/passes/` | Canonical pass intakes and plans grouped by pass family. |
| `docs/agent-notes/` | Durable repository engineering/testing standards used when their scope applies. |
| `backend/tests/README.md` | Trusted backend test/checker architecture, roots, requirement declarations, testing records, and checker command model. |
| `backend/tests/support/requirements/` | Machine-readable stable requirement declarations. |
| `backend/tests/checker/` | Checker and testing-foundation self-tests and evidence. |
| `backend/tests/compliance/` | Checker implementation modules used by trusted validation. |
| `backend/tests/platform/`, `backend/tests/domains/`, `backend/tests/workflows/`, `backend/tests/migrations/`, `backend/tests/provider_contract/` | Trusted backend evidence roots when present and relevant. |

Use the governance README and decision inventory first, then read only the
records relevant to the current pass. Route backend evidence discovery through
`backend/tests/README.md`, trusted test roots, current requirement
declarations, current `TESTING_RECORD.md` files, and the applicable pass
artifacts.

## 5. Supporting Engineering/Testing Standards

Supporting standards are tracked durable repository standards. They support
implementation and evidence mechanics within their approved scope; they do not
override `00-READ-ME-FIRST.md` or higher production-readiness authority.

| Document | Read when |
|---|---|
| `docs/agent-notes/app-testing-standards.md` | Application behavior, safeguard review, scenario classification, or evidence adequacy is in scope. |
| `docs/agent-notes/backend-structure.md` | Backend source, backend ownership boundaries, imports, or file placement are in scope. |
| `docs/agent-notes/backend-testing.md` | Backend pytest, requirement declarations, testing records, checker, or trusted evidence are in scope. |
| `backend/tests/README.md` | Backend checker architecture, trusted roots, requirement mapping, testing records, or checker commands are in scope. |
| `docs/agent-notes/database.md` | PostgreSQL, SQLAlchemy models, Alembic, migrations, transaction behavior, or test database work is in scope. |
| `docs/agent-notes/frontend-structure.md` | Frontend source, routing, configuration, visual design, interaction behavior, or browser behavior is in scope. |
| `docs/agent-notes/playwright-structure.md` | Playwright, browser, or end-to-end evidence is explicitly in scope. |

For provider, runtime, migration, governance, owner-decision, or other
specialized evidence, use the durable indexes in this document and read only
the applicable records.

## 6. Workflow Selection

Use `PASS-IMPLEMENTATION-WORKFLOW.md` when a pass is being implemented for the
first time from current authority and current accepted `develop`.

Use `PASS-RECHECK-WORKFLOW.md` when a pass already accepted into `develop`, or
historical implementation that predates the current workflow, is being
revalidated against current repository truth and current evidence standards.

The execution register records accepted execution state. It distinguishes
original parent blueprint passes, accepted executable children, remaining
parent obligations, and completed parent scope.

Each executable child receives a fresh Gate A from the current accepted
baseline after prerequisites merge. Detailed stage/gate mechanics, correction
handling, validation responsibilities, and Git/PR finalization rules live in
the workflow files.

## 7. Trusted Evidence Model

The permanent traceability model is:

```text
PRODUCTION-READINESS PASS
-> STABLE REQUIREMENT ID
-> MEANINGFUL SCENARIOS / EDGE CASES
-> PYTEST TESTS OR OTHER EVIDENCE
```

Stable requirement declarations live under
`backend/tests/support/requirements/`. These JSON files store requirement
identity, owning pass, source controls, current state, owning scope when
needed, and reasons for states such as `covered_elsewhere`, `deferred`, or
`blocked`.

Pytest tests use requirement markers to declare which stable requirement IDs
they prove. Checker-generated metadata maps current pytest collection to
requirements so planning documents do not hand-maintain drifting node lists.

`TESTING_RECORD.md` files own human reasoning for one coherent trusted scope:
risks, invariants, scenario groups, proof layers, gaps, deferrals, and adequacy
conclusions. They explain why the evidence is meaningful.

Evidence can be executable or non-executable:

- Executable evidence is usually pytest, checker, static validation, or other
  deterministic local proof.
- Non-executable evidence can be source review, governance records, sanitized
  provider evidence, runtime observations, manual review, or later controlled
  evidence packages.

Passing tests alone never proves production readiness. Evidence must be derived
from current authority and accepted current source, mapped to stable
requirements, reviewed for semantic adequacy, and combined with required
repository, runtime, provider, operational, or recovery evidence.

## 8. Pass Families And Ordering

Each pass plan stays within the material scope of that pass. A pass may include
artifacts, requirements, dependencies, integrations, evidence, controls, and
ownership boundaries only when they materially define, implement, govern,
constrain, or prove that pass.

Parent blueprint passes may be implemented whole or decomposed into executable
children through approved intake. The execution register records accepted
intake/decomposition state and remaining parent obligations, but it does not
alter the master blueprint, close controls by itself, or choose the next pass.

Agents must verify intended order from current authority, the execution
register, accepted prerequisites, current `develop`, and explicit owner
direction. Do not choose the next pass from alphabetical filenames, stale
branch names, or old chat context.

By default, the first substantive child PR carries the approved intake record
and prepares the execution-register update that becomes true when that PR
merges. Later children update their accepted result and remaining parent state.
The final child marks the parent complete when every approved child obligation
is accounted for.

## 9. Essential Terminology

| Term | Meaning |
|---|---|
| Parent blueprint pass | One of the original parent-level planned passes in the master blueprint. |
| Executable pass | A bounded parent or child pass that can be planned, implemented, evidenced, reviewed, and finalized as a coherent PR. |
| Intake | Stage 0 parent-pass readiness and decomposition work performed before Gate A for first-time implementation. |
| Accepted baseline | The exact accepted `develop` commit used as the starting point for a pass branch. |
| Frozen intake | An owner-approved Stage 0 intake artifact identified by exact path and SHA-256. |
| Frozen plan | The approved Gate A canonical plan, requirement set, correction design, evidence design, file sets, and SHA-256. |
| Gate B editable file set | The exact repository-relative paths Gate B may modify. |
| Expected final changed-file set | The complete repository-relative path set expected at Gate D, including frozen artifacts when applicable plus Gate B editable files. |
| Repository truth | Current accepted source, configuration, documentation, and evidence state at the trusted baseline and accepted pass commits. |
| Provenance | Historical evidence of what happened, such as PRs, commits, and diffs; provenance does not define requirements. |
| Trusted evidence | Evidence produced from current authority under the accepted evidence architecture. |
| Requirement declaration | A JSON entry under `backend/tests/support/requirements/` declaring stable machine-readable requirement identity. |
| `covered_elsewhere` | A requirement state meaning accepted evidence exists in another scope or artifact. |
| `deferred` | A requirement state meaning proof or completion belongs to a later owner or evidence source. |

## 10. Mandatory Gate Document Matrix

Applicable repository templates and standards are mandatory gate inputs, not
optional references. A gate instruction is incomplete when an applicable
template, standard, authority record, source area, or evidence artifact was not
reviewed before drafting or executing that gate.

| Gate | Mandatory document inputs |
|---|---|
| Stage 0 intake | Implementation workflow, intake template, execution register, master blueprint parent entry, final remediation plan, applicable decisions/governance records, accepted prerequisite plans/evidence, and applicable engineering/testing standards. |
| Gate A for first-time implementation | Implementation workflow, approved intake record when applicable, planning template, testing-record template, current planning file when one exists, applicable authority/source/evidence, and applicable engineering/testing standards. |
| Gate A for recheck | Recheck workflow, planning template, testing-record template, current pass plan, applicable authority/source/evidence, and applicable engineering/testing standards. |
| Gate B | Applicable workflow, frozen intake when applicable, frozen canonical plan, testing-record template, applicable authority/source/evidence, and applicable engineering/testing standards. |
| Gate C for first-time implementation | Applicable workflow, frozen intake when applicable, frozen canonical plan, requirement declaration, testing record, implementation, executable and non-executable evidence, current validation, execution-register proposal when in scope, and expected final changed-file set. |
| Gate C for historical recheck | Recheck workflow, frozen canonical plan, requirement declaration, testing record, implementation, executable and non-executable evidence, current validation, and expected final changed-file set. |
| Gate D | Applicable workflow, frozen intake when applicable, frozen canonical plan, Gate C approval, explicit owner Gate D instruction, and PR-description template. |

Gate-specific prompts may require additional pass-specific authority, source,
governance, testing, or evidence documents. This matrix is the durable minimum,
not a cap.
