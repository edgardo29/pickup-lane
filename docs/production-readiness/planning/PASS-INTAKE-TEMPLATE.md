# Production-Readiness Pass Intake Template

Use this template during Stage 0 of `PASS-IMPLEMENTATION-WORKFLOW.md`.

The intake record decides what executable pass should be designed next from a
parent blueprint pass. It is not a pass plan, implementation prompt, testing
record, or approval to edit source.

If a section is not applicable, write `Not applicable - [reason]`.

## At A Glance

| Field | Value |
|---|---|
| Intake date | `[YYYY-MM-DD]` |
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
| `PASS-EXECUTION-REGISTER.md` | `[Current parent/executable-pass status]` |
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
`PASS-EXECUTION-REGISTER.md`.

| Register item | State |
|---|---|
| Parent pass status | `[not started / partially decomposed / decomposed / accepted / closed out]` |
| Accepted child passes | `[List or None]` |
| Known closeout records | `[List or None]` |
| Remaining parent scope | `[Summary]` |
| Register ambiguity | `[None or issue]` |

If the register is stale or ambiguous, stop and correct the register through an
approved documentation task before using it to authorize implementation.

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

## 6. Decomposition Decision

Choose one:

| Decision | Applies? | Reason |
|---|---|---|
| Implement parent as one executable pass | `[yes/no]` | `[Reason]` |
| Decompose into child passes | `[yes/no]` | `[Reason]` |
| Stop for prerequisite | `[yes/no]` | `[Reason]` |
| Stop for owner decision | `[yes/no]` | `[Reason]` |

When decomposing, provide the proposed child-pass map:

| Order | Proposed child pass | Scope | Depends on | Not owned |
|---|---|---|---|---|
| `1` | `[PASS-ID - title]` | `[Scope]` | `[Dependencies]` | `[Boundaries]` |

The child-pass map must be mutually exclusive enough that later implementation
does not hide unresolved work in overlapping scopes.

## 7. Proposed Executable Pass

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

## 8. Preliminary Requirement Shape

List draft requirement areas. Final requirement IDs and wording belong in Gate
A, but intake should identify the material obligation groups.

| Requirement area | Source | Expected evidence class |
|---|---|---|
| `[Area]` | `[Control/decision/source]` | `[pytest/provider/runtime/governance/manual/deferred]` |

Do not invent final requirements during intake merely to fill the table.

## 9. Evidence And Testing Expectations

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

## 10. Expected Artifacts

Describe likely artifacts without authorizing file edits.

| Artifact type | Expected? | Candidate owner/path |
|---|---|---|
| Canonical pass plan | `[yes/no]` | `[path]` |
| Requirement declaration | `[yes/no]` | `[path]` |
| `TESTING_RECORD.md` | `[yes/no]` | `[path]` |
| Source/configuration | `[yes/no]` | `[area]` |
| Documentation/governance | `[yes/no]` | `[area]` |
| Provider/runtime evidence | `[yes/no]` | `[external owner/evidence package]` |

If an expected artifact falls outside the parent pass, stop and resolve scope
before Gate A.

## 11. Non-Goals And Boundaries

List explicit non-goals.

- `[Boundary]`
- `[External evidence not claimed]`
- `[Later pass or owner]`

Include provider/runtime/migration/governance boundaries where they matter.

## 12. Dependencies And Readiness

| Dependency | Required state | Current state | Intake verdict |
|---|---|---|---|
| `[PASS/decision/provider/source]` | `[Needed]` | `[Current]` | `[ready/blocked/unknown]` |

If any dependency is blocked or unknown in a way that prevents honest Gate A
design, stop.

## 13. Stop Conditions For Gate A

List concrete conditions that should stop Gate A or route the work back to
intake/owner decision.

- `[Condition]`
- `[Condition]`

## 14. Intake Outcome

State one outcome:

- `READY FOR GATE A: [proposed executable pass]`
- `DECOMPOSITION REQUIRED BEFORE GATE A`
- `BLOCKED: PREREQUISITE REQUIRED`
- `BLOCKED: OWNER DECISION REQUIRED`
- `REGISTER CORRECTION REQUIRED`

Include the exact next allowed action.
