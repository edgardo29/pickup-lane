# Production-Readiness Pass Intake Template

Use this template during Stage 0 of
`docs/production-readiness/planning/workflows/PASS-IMPLEMENTATION-WORKFLOW.md`.

The intake record decides what executable pass should be designed next from a
parent blueprint pass. It is not a pass plan, implementation prompt, testing
record, or approval to edit source.

If a section is not applicable, write `Not applicable - [reason]`.

Intake records are tracked production-readiness artifacts. Do not include
literal credentials, credential-bearing URLs, secrets, private keys or tokens,
private provider values, personal or payment data, raw sensitive logs, local
machine paths, session state, internal chat material, or other local-only
sensitive information. When configuration must be referenced, use
environment-variable references or sanitized placeholders.

Intake records use this storage convention:

```text
docs/production-readiness/planning/passes/<family>/<parent-id>-intake.md
```

## At A Glance

| Field | Value |
|---|---|
| Intake date | `[YYYY-MM-DD]` |
| Intake record path | `docs/production-readiness/planning/passes/<family>/<parent-id>-intake.md` |
| Parent blueprint pass | `[PASS-ID and title]` |
| Proposed executable pass | `[PASS-ID and title]` |
| Track | `[WSxx / PROGRAM / GOVERNANCE / other canonical track]` |
| Intake outcome | `[implement parent / decompose child / stop for prerequisite / stop for owner decision]` |
| Current develop basis | `[origin/develop SHA or current accepted baseline]` |
| Intake sources | `[Blueprint, remediation plan, decisions, accepted prerequisites, current source]` |
| Proposed planning document | `[path or Not applicable]` |
| Proposed requirement declaration | `[path or Not applicable]` |
| Proposed trusted evidence scope | `[path or Not applicable]` |

## 1. Purpose

Explain why this intake exists and what parent pass or parent-pass remainder it
is evaluating.

State explicitly that this intake does not implement the pass and does not
select a later pass beyond the proposed executable scope.

## 2. Authority Read

List the authority and context reviewed.

| Source | Relevant meaning for this intake |
|---|---|
| `00-READ-ME-FIRST.md` | `[Authority rule or stop condition]` |
| `01-PROGRAM-CONTEXT.md` | `[Program navigation or pass-family rule]` |
| `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md` | `[Current parent/executable-pass status]` |
| Master blueprint parent entry | `[Original parent-level intent]` |
| Final remediation plan | `[Workstream/control relationship]` |
| Approved decisions / governance | `[Policy or ownership input]` |
| Accepted prerequisite pass plans | `[Dependency contracts]` |
| Current accepted repository truth | `[Current source/config/evidence state]` |

Do not use superseded prompts, old branch names, old PR descriptions, or
historical implementation as authority.

## 3. Parent Blueprint Pass

| Field | Value |
|---|---|
| Parent pass | `[PASS-ID]` |
| Parent title | `[Title]` |
| Parent track | `[Track]` |
| Parent type | `[Type]` |
| Primary controls | `[Controls]` |
| Blueprint dependencies | `[Dependencies]` |
| Blueprint maximum scope | `[Summary]` |

Explain the parent pass in plain language.

## 4. Current Execution Register State

Describe how the parent pass currently appears in
`docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md`.

| Register item | State |
|---|---|
| Parent pass status | `[not started / partially decomposed / decomposed / accepted / closed out]` |
| Accepted child passes | `[List or None]` |
| Known closeout records | `[List or None]` |
| Remaining parent scope | `[Summary]` |
| Register ambiguity | `[None or issue]` |

If the register needs a minor correction discovered during intake, that
correction may be included in the same first-child substantive PR when it does
not change higher authority. A material authority or structure conflict stops
intake. Do not require a separate tracker-only PR by default.

## 5. Current Repository Truth

Summarize current accepted source, configuration, documentation, requirement
declarations, testing records, and evidence that materially affect this parent
or child pass.

Classify facts as:

- repository truth;
- authoritative requirement;
- accepted external evidence;
- inference;
- unknown.

Do not claim provider, runtime, dashboard, account, deployment, backup, or
operational facts from repository source alone.

## 6. Executable-Pass Cohesion Assessment

Assess the parent or proposed child against the implementation workflow's
seven-question cohesion test.

| Cohesion question | Verdict | Evidence/reason | Split implication |
|---|---|---|---|
| One primary outcome |  |  |  |
| One requirement/invariant family |  |  |  |
| One prerequisite state |  |  |  |
| One safe merge/rollback or forward-fix unit |  |  |  |
| One coherent evidence model |  |  |  |
| One semantic review model |  |  |  |
| Safe/useful intermediate state |  |  |  |

Split the parent or candidate child when either one prerequisite state or one
safe merge/rollback or forward-fix unit is false. Normally recommend a split
when two or more other cohesion questions fail.

Warning signals such as file count, changed-line count, requirement count,
test count, frontend plus backend, or prompt length are not automatic split
rules.

## 7. Decomposition Decision

Choose one:

| Decision | Applies? | Reason |
|---|---|---|
| Implement parent as one executable pass | `[yes/no]` | `[Reason]` |
| Decompose into child passes | `[yes/no]` | `[Reason]` |
| Stop for prerequisite | `[yes/no]` | `[Reason]` |
| Stop for owner decision | `[yes/no]` | `[Reason]` |

When decomposing, provide the proposed child-pass map:

| Order | Child ID | Title | One primary outcome | Allocated controls/requirement areas | Prerequisites | Produced capability | Handoff to later child | Safe merged intermediate state | Evidence profile | Explicit non-goals |
|---|---|---|---|---|---|---|---|---|---|---|
| `1` | `[PASS-ID]` | `[Title]` | `[Outcome]` | `[Controls/areas]` | `[Dependencies]` | `[Capability]` | `[Handoff]` | `[Safe state]` | `[Evidence]` | `[Boundaries]` |

The child-pass map must be mutually exclusive enough that later implementation
does not hide unresolved work in overlapping scopes.

Do not split one coherent outcome merely into backend, frontend, tests, or
documentation. Required frontend behavior, production behavior, requirement
metadata, testing record, trusted evidence, and compatibility updates travel
with the contract they establish.

## 8. Parent Obligation Allocation

Every parent obligation must appear in this no-gap/no-overlap matrix.

| Parent obligation/control | Primary child/owner | Supporting child/evidence | Overlap reason, if any | Final disposition |
|---|---|---|---|---|
| `[Obligation/control]` | `[Child or owner]` | `[Support or None]` | `[Shared prerequisite / compatibility / cross-cutting evidence / None]` | `[Implemented / governance / deferred / blocked / covered elsewhere]` |

The union of child ownership must equal complete parent ownership. Child
ownership may overlap only for explicitly documented shared prerequisites,
compatibility regression responsibility, or cross-cutting evidence.

## 9. Ordering, Shared Responsibility, And Completion

Describe:

- child ordering/dependency graph;
- shared prerequisites;
- compatibility responsibilities;
- parent completion rule;
- execution-register update plan.

A decomposed parent is complete only when all approved children are complete
and every parent obligation is accounted for.

## 10. Proposed Executable Pass

| Field | Value |
|---|---|
| Pass ID | `[PASS-ID]` |
| Title | `[Plain-English title]` |
| Parent pass | `[PASS-ID]` |
| Primary controls | `[Controls]` |
| Supporting controls / decisions | `[Controls or decisions]` |
| Dependencies | `[Accepted prerequisites]` |
| Expected pass type | `[Domain / API / Provider / Frontend / CI / Operations / other]` |

Explain why this proposed pass is a coherent implementation and review unit.

## 11. Preliminary Requirement Shape

List draft requirement areas. Final requirement IDs and wording belong in Gate
A, but intake should identify the material obligation groups.

| Requirement area | Source | Expected evidence class |
|---|---|---|
| `[Area]` | `[Control/decision/source]` | `[pytest/provider/runtime/governance/manual/deferred]` |

Do not invent final requirements during intake merely to fill the table.

## 12. Evidence And Testing Expectations

Classify expected proof layers.

| Evidence class | Needed? | Reason |
|---|---|---|
| Backend pytest | `[yes/no/tbd]` | `[Reason]` |
| Frontend unit/component | `[yes/no/tbd]` | `[Reason]` |
| Browser / Playwright | `[yes/no/tbd]` | `[Reason]` |
| PostgreSQL / concurrency | `[yes/no/tbd]` | `[Reason]` |
| Migration rehearsal | `[yes/no/tbd]` | `[Reason]` |
| Provider evidence | `[yes/no/tbd]` | `[Reason]` |
| Runtime/staging evidence | `[yes/no/tbd]` | `[Reason]` |
| Governance/manual review | `[yes/no/tbd]` | `[Reason]` |

Gate A must refine this into requirement-by-requirement evidence design.

## 13. Expected Artifacts

Describe likely artifacts without authorizing file edits.

| Artifact type | Expected? | Candidate owner/path |
|---|---|---|
| Canonical pass plan | `[yes/no]` | `[path]` |
| Requirement declaration | `[yes/no]` | `[path]` |
| `TESTING_RECORD.md` | `[yes/no]` | `[path]` |
| Source/configuration | `[yes/no]` | `[area]` |
| Documentation/governance | `[yes/no]` | `[area]` |
| Provider/runtime evidence | `[yes/no]` | `[external owner/evidence package]` |
| Execution-register update | `yes for every substantive first-time executable pass` | `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md` |

The execution register is a mandatory cross-cutting program artifact for
substantive first-time passes. Its presence does not mean the parent pass
improperly owns the program register. Gate A must include its exact path in Gate
B scope, Gate B prepares only the pass-specific accepted-state update, Gate C
reviews it, and Gate D never authors it.

Unexpected artifacts outside the parent outcome require scope resolution before
Gate A. Explicitly mandated cross-cutting artifacts such as the execution
register, requirement metadata, testing records, and approved compatibility
evidence do not create a scope violation when the workflow requires them. Do not
weaken this stop rule for genuinely unrelated artifacts.

## 14. Non-Goals And Boundaries

List explicit non-goals.

- `[Boundary]`
- `[External evidence not claimed]`
- `[Later pass or owner]`

Include provider/runtime/migration/governance boundaries where they matter.

## 15. Dependencies And Readiness

| Dependency | Required state | Current state | Intake verdict |
|---|---|---|---|
| `[PASS/decision/provider/source]` | `[Needed]` | `[Current]` | `[ready/blocked/unknown]` |

If any dependency is blocked or unknown in a way that prevents honest Gate A
design, stop.

## 16. Stop Conditions For Gate A

List concrete conditions that should stop Gate A or route the work back to
intake/owner decision.

- `[Condition]`
- `[Condition]`

## 17. Human Approval And Intake Outcome

State one outcome:

- `READY FOR GATE A: [proposed executable pass]`
- `DECOMPOSITION REQUIRED BEFORE GATE A`
- `BLOCKED: PREREQUISITE REQUIRED`
- `BLOCKED: OWNER DECISION REQUIRED`
- `REGISTER CORRECTION REQUIRED`

Include the exact next allowed action.

Before reporting any intake for approval, confirm that the completed intake
contains no literal credentials, credential-bearing URLs, secrets, private keys
or tokens, private provider values, personal or payment data, raw sensitive
logs, local/session-only information, or other prohibited sensitive values.

When the outcome is ready for Gate A, report:

- final intake-record path;
- intake-record SHA-256;
- exact approved parent/child structure;
- exact next executable child authorized for Gate A.

Compute the SHA-256 after completing the intake record and before human
approval. Human approval applies to the exact reported path and SHA. Do not
embed the SHA as mutable status inside the intake document; the SHA belongs in
Stage 0 reports and approved instructions.

Human intake approval authorizes:

- child structure;
- ordering;
- obligation allocation;
- the next executable child's Gate A.

It does not authorize implementation, Gate B, or later-child Gate A work.

After human approval of the exact path and SHA, the approved intake record is
frozen. It is read-only during Gate A and Gate B, and a content change produces
a new SHA and requires a Stage 0 revision plus new human approval. When a new
intake record is created, it belongs in the first substantive child pass's
expected final changed-file set but is not a Gate B-editable file. If the parent
is implemented whole, the same rule applies to the approved intake record. Later
children consume the accepted intake record from current `develop` and do not
edit it unless the parent structure itself requires a Stage 0 revision.
