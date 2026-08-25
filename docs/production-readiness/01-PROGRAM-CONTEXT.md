# Pickup Lane Production-Readiness Program Context

## 1. Purpose

This document is the stable program overview and routing index for Pickup Lane
production-readiness work. It explains the system shape, program structure,
document locations, evidence model, pass ordering, terminology, and mandatory
gate inputs.

Startup, authority order, conflict handling, local handoff usage, automation
boundaries, tracked documentation safety, and publication boundaries are owned
by `docs/production-readiness/00-READ-ME-FIRST.md`.

Production-readiness assignments should reference `00-READ-ME-FIRST.md`,
`01-PROGRAM-CONTEXT.md`, and applicable current pass artifacts instead of
repeating common document lists. An assignment should name an additional file
only when that file is pass-specific, a frozen artifact, an explicit exception,
or needed to resolve an ambiguity not covered by durable routing. Short
assignments do not reduce Codex's responsibility to follow the routed workflow,
standards, governance, decisions, source, evidence, and frozen-artifact checks.

Optional local current-session orientation is described by
`00-READ-ME-FIRST.md`.

## 2. Pickup Lane And Production-Readiness Overview

Pickup Lane is a web application for organizing and operating pickup basketball games.
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


## 3. Final Infrastructure Timing And Late-Bound Production Evidence

Temporary development/demo infrastructure must not become permanent production
architecture merely because it exists in the repository or is currently used for
a portfolio/demo deployment.

Current Vercel frontend hosting, Render API hosting, and Neon PostgreSQL hosting
are temporary development/demo infrastructure. They may be referenced when
describing current repository or demo behavior, but they are not the selected
final production hosting/database topology and must not supply permanent
provider-specific architecture, capacity assumptions, or final production
configuration values.

Final production hosting, database hosting, edge/ingress/proxy/TLS topology,
process and instance topology, autoscaling and rolling-deployment behavior,
provider plan/capacity/region, provider-native deployment settings, concrete
production roles/grants, and other infrastructure-dependent production facts
remain late-bound until the final infrastructure is selected and evidence exists.

The program must preserve this boundary at Stage 0 and Gate A:

- Complete coherent provider-independent work when it can be implemented and
  proved without the final infrastructure. This may include portable source
  behavior, generic configuration interfaces, validation, formulas, evidence
  schemas/checkers, synthetic fixtures, and later-verification contracts.
- A generic setting or configuration interface may be implemented before final
  infrastructure selection when its existence and validation are provider
  independent. Concrete production values that depend on the final provider or
  topology remain deferred.
- Do not promote values from temporary providers, README examples, local/CI
  configuration, free-tier defaults, framework defaults, or demo deployments
  into final production assumptions.
- If a parent contains both executable-now work and work requiring intentionally
  unselected final infrastructure, Stage 0 must split them rather than force an
  early provider choice or leave unrelated work blocked.
- Every mandatory deferred follow-up must identify its owner/pass, exact trigger,
  preserved obligations, dependencies, and latest required completion boundary.
  The execution register must keep that follow-up visible.
- A deferred follow-up is not evidence and does not close its controls. Run it as
  soon as its trigger is satisfied and no later than the first downstream pass
  that genuinely needs those facts or `CLOSE-01`, whichever comes first.
- Downstream work may continue only when its own prerequisites are satisfied
  without the deferred provider/runtime facts. If it needs one of those facts,
  stop on that specific missing prerequisite instead of guessing or substituting
  temporary values.

The master blueprint must identify known final-infrastructure-dependent passes or
pass portions before normal progression reaches them, including the expected
trigger or late-bound placement. Stage 0 may refine that structure against
current repository truth, but it must not rediscover a known infrastructure
dependency only after Gate B begins.

This rule does not reopen provider-specific product integrations that higher
authority has already fixed. It governs final infrastructure selection and the
concrete production configuration/evidence that depends on that selection.

## 4. Program Structure

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
-> semantic review and Git/PR finalization
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

For automated first-time implementation, Stage 0 establishes the executable
parent/child structure. Each executable pass then moves through Gate A
planning/review, Gate B implementation/validation, Gate C semantic review, and
Gate D publication. After manual PR merge, progression resumes from current
accepted `develop`.

## 5. Document Map And Routing Indexes

| Path | Purpose |
|---|---|
| `docs/production-readiness/00-READ-ME-FIRST.md` | Startup, authority, automation, safety, handoff, and publication boundary entry point. |
| `docs/production-readiness/01-PROGRAM-CONTEXT.md` | Stable program overview and routing index. |
| `docs/production-readiness/audit-research/` | Locked audit reports, consolidated checklist, research consolidation, and static inventory crosswalk. |
| `docs/production-readiness/decisions/pickup-lane-master-decision-inventory-v4.md` | Owner-decision routing inventory. Use it to identify relevant approved decision records. |
| `docs/production-readiness/decisions/` | Approved decision records. Read only records relevant to the current pass after using the inventory. |
| `docs/production-readiness/governance/README.md` | Governance routing index. Use it to identify relevant governance records. |
| `docs/production-readiness/governance/` | Production ownership, environment, provider, secret, evidence, risk, exception, audit-process, and operational governance records. |
| `docs/production-readiness/planning/program/pickup-lane-production-readiness-remediation-plan-final.md` | Final remediation plan and dependency-aware workstream program. |
| `docs/production-readiness/planning/program/pickup-lane-master-production-readiness-blueprint.md` | Master implementation blueprint and planned pass register. |
| `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md` | Accepted execution-state register for parent and executable passes and current progression state. |
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

## 6. Supporting Engineering/Testing Standards

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

## 7. Workflow Selection

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
handling, validation responsibilities, review limits, and Git/PR finalization
rules live in the workflow files.

For first-time automated progression:

1. Stage 0 is run once for a parent unless a later structural correction requires
   revisiting the decomposition.
2. If the parent is decomposed, the first executable child begins Gate A.
3. After a child PR is manually merged, the next accepted current child whose
   prerequisites are satisfied begins a fresh Gate A from new accepted
   `develop`.
4. When every current executable child is accepted, reconcile the parent's
   remaining obligations, including any mandatory deferred follow-up.
5. If no mandatory deferred obligation remains, the parent may be recorded as
   complete. If a structurally approved follow-up is waiting on an unmet final-
   infrastructure or external-evidence trigger, keep that obligation and its
   controls open; program progression may continue only where downstream work
   does not require the deferred facts.
6. Determine the next executable work from the master blueprint, remediation
   plan, execution register, prerequisites, deferred-trigger state, and current
   repository truth.
7. If exactly one next unit is determined, begin it at the stage required by the
   applicable workflow.
8. If durable authority does not determine a unique next unit, stop for owner
   selection rather than inventing priority.

## 8. Trusted Evidence Model

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

## 9. Pass Families And Ordering

Each pass plan stays within the material scope of that pass. A pass may include
artifacts, requirements, dependencies, integrations, evidence, controls, and
ownership boundaries only when they materially define, implement, govern,
constrain, or prove that pass.

Parent blueprint passes may be implemented whole or decomposed into executable
children through Stage 0 intake. The execution register records accepted
intake/decomposition state, accepted child results, remaining parent
obligations, and completed parent scope. It does not alter the master blueprint
or close controls by itself.

Pass progression must be derived from current authority, the execution register,
accepted prerequisites, current `develop`, and accepted parent/child
dependencies. Do not choose the next pass from alphabetical filenames, stale
branch names, or old chat context.

When a parent has an accepted decomposition, the accepted child order and
dependencies govern progression. After one child merges, another child may
begin automatically only when its prerequisites are accepted and the intake
makes that child the deterministic next executable unit.

When all current executable child obligations are accepted, reconcile any
remaining deferred obligations before deciding whether the parent is fully
complete. A mandatory deferred follow-up with an unmet external trigger remains
visible and does not count as evidence or control closure. The program may move
to other work only when that work does not depend on the deferred facts.

Determine subsequent work from the master blueprint/remediation ordering, the
execution register, accepted dependencies, deferred-trigger state, and current
repository truth. If exactly one next unit is determined, begin it at the stage
required by the applicable workflow. If multiple next units are equally valid
and authority does not resolve their order, stop for owner selection.

By default, the first substantive child PR carries the Stage 0 intake record
and prepares the execution-register update that becomes true when that PR
merges. Later children update their accepted result and remaining parent state.
The final current child may mark the current executable child set complete only
after every current child obligation is accounted for. Any mandatory deferred
follow-up must remain explicitly recorded until its trigger is satisfied and the
follow-up itself is accepted.

## 10. Essential Terminology

| Term | Meaning |
|---|---|
| Parent blueprint pass | One of the original parent-level planned passes in the master blueprint. |
| Executable pass | A bounded parent or child pass that can be planned, implemented, evidenced, reviewed, and finalized as a coherent PR. |
| Intake | Stage 0 parent-pass readiness and decomposition work performed before Gate A for first-time implementation. |
| Accepted baseline | The exact accepted `develop` commit used as the starting point for a pass branch. |
| Frozen intake | The exact Stage 0 intake artifact/path/SHA accepted for the current automated run or already accepted in current `develop`. |
| Frozen plan | The exact Gate A canonical plan SHA that passed Gate A review and therefore governs Gate B. |
| Gate B implementation scope | The frozen engineering scope and design that govern which repository files Gate B may modify. Gate B may change any file genuinely necessary to implement and prove the frozen design. |
| Changed-file scope justification | Gate C and Gate D review the actual changed files for justification against the frozen pass scope and design rather than equality with a predicted filename list. |
| Repository truth | Current accepted source, configuration, documentation, and evidence state at the trusted baseline and accepted pass commits. |
| Provenance | Historical evidence of what happened, such as PRs, commits, and diffs; provenance does not define requirements. |
| Trusted evidence | Evidence produced from current authority under the accepted evidence architecture. |
| Requirement declaration | A JSON entry under `backend/tests/support/requirements/` declaring stable machine-readable requirement identity. |
| `covered_elsewhere` | A requirement state meaning accepted evidence exists in another scope or artifact. |
| `deferred` | A requirement state meaning proof or completion belongs to a later owner or evidence source. |
| Mandatory deferred follow-up | A Stage 0-allocated later unit whose required provider/runtime/configuration evidence cannot honestly be completed until an explicit external trigger is satisfied. It remains mandatory and does not count as proof while deferred. |
| Final-infrastructure trigger | The recorded condition that makes late-bound production work executable, such as final provider/topology selection plus availability of the required sanitized evidence. |
| Current executable child set | The child work whose prerequisites are presently satisfied. Completing this set does not erase or close a separately recorded mandatory deferred follow-up. |

## 11. Mandatory Gate Document Matrix

Applicable repository templates and standards are mandatory gate inputs, not
optional references. A gate assignment is incomplete when an applicable
template, standard, authority record, source area, or evidence artifact was not
reviewed before drafting or executing that gate.

| Gate | Mandatory document inputs |
|---|---|
| Stage 0 intake | Implementation workflow, intake template, execution register, master blueprint parent entry including any late-bound infrastructure marker, final remediation plan, applicable decisions/governance records, accepted prerequisite plans/evidence, final-infrastructure timing rule, and applicable engineering/testing standards. |
| Gate A for first-time implementation | Implementation workflow, accepted intake record when applicable, planning template, testing-record template, current planning file when one exists, applicable authority/source/evidence, any deferred handoff/trigger owned by the intake, and applicable engineering/testing standards. |
| Gate A review | Applicable workflow, accepted intake when applicable, complete current canonical plan and SHA, planning/testing-record templates, applicable authority/source/evidence, current repository truth, prerequisites/handoffs, and applicable engineering/testing standards. |
| Gate A for recheck | Recheck workflow, planning template, testing-record template, current pass plan, applicable authority/source/evidence, and applicable engineering/testing standards. |
| Gate B | Applicable workflow, frozen intake when applicable, frozen canonical plan, testing-record template, applicable authority/source/evidence, and applicable engineering/testing standards. |
| Gate C for first-time implementation | Applicable workflow, frozen intake when applicable, frozen canonical plan, requirement declaration, testing record, implementation, executable and non-executable evidence, current validation, execution-register proposal when in scope, and actual changed-file scope justification. |
| Gate C for historical recheck | Recheck workflow, frozen canonical plan, requirement declaration, testing record, implementation, executable and non-executable evidence, current validation, and actual changed-file scope justification. |
| Gate D | Applicable workflow, frozen intake when applicable, frozen canonical plan, clean Gate C approval for the exact current pass state, and PR-description template. |

Gate-specific assignments may require additional pass-specific authority,
source, governance, testing, or evidence documents. This matrix is the durable
minimum, not a cap.
