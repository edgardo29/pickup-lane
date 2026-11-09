# Pickup Lane Production Launch Pass Workflow

This document explains how to assess, plan, carry out, verify, review, and
finish a pass in the 21-pass
[Production Launch Requirements](production-launch-requirements.md) document.
That document defines pass requirements, order, dependencies, verification,
and completion conditions.

A **major pass** is one of the 21 production launch passes. A **minor pass** is a
lettered subdivision, such as `Pass 01A`, created when a major pass must be
split. The [Production Launch Pass Completion
Log](production-launch-pass-completion-log.md) records completed major passes.
Each major pass has a main record under
`docs/production-readiness/pass-records/`, such as `pass-01.md`. The
`docs/production-readiness/verification-map.md` file, created in Pass 03,
connects numbered production-launch requirements to their planned checks.

**Accepted repository state** means the code and documentation currently
merged into `develop`. Preserve any existing unmerged changes. The **current
assignment** means the user's current instruction, including its scope and
limits on editing, verification, publication, and when to stop.

This workflow creates no product requirements. Previously completed work does
not satisfy the Production Launch Requirements until it has been verified
against the current requirements.

## 1. Start from the current work

1. Read the selected **entire major pass**, including its requirements,
   connections to other passes and features, verification, and completion
   condition. Read Sections 1, 3, and 4 of the Production Launch Requirements
   and any exact upstream requirement the pass cites. Follow the current
   assignment's scope and stop conditions.
2. Read the product specifications, architecture documents, and engineering
   and testing standards that apply. When the plan relies on a requirement
   outside the Production Launch Requirements, cite its file and section and
   confirm under Section 3.4 of that document that it applies. Existing code
   and tests show what currently exists; they do not define the required
   behavior.
3. Start from the accepted repository state while preserving existing unmerged
   changes. Do not discard, overwrite, or publish someone else's work to
   prepare a pass.
4. Separate what the repository can verify from what requires checking an
   external service or deployed environment, or a decision from the person
   responsible for that product, legal, security, or operational area. Do not
   assume local or staging settings apply to production.

Finishing a stage does not automatically authorize the next. Start new
implementation at Stage 0. For corrections, return to the relevant gate if
the work is unmerged. Start previously merged work at Stage 0.

## 2. Stage 0 — Assess the pass and decide whether to split it

Stage 0 determines which requirements are already satisfied, what remains, and
whether to complete the work as one major pass or several minor passes. It does
not design the implementation.

1. Compare every requirement and verification obligation with the existing
   code, configuration, documents, tests, and accepted evidence. For each one,
   record whether current evidence proves it is satisfied, implementation
   remains, it is assigned to a named later pass, or a specific prerequisite
   blocks it.
   A past completion claim is not evidence by itself.
2. Identify existing behavior and connections that must keep working,
   including product, security, privacy, financial, operational, and
   external-service concerns. Distinguish an unavailable production fact from
   a design choice that can already be made.
3. Decide whether the pass can produce one result that can be implemented,
   verified, reviewed, and released safely. Split it only when the pieces have
   different outcomes, dependencies, responsible people or passes, failure or
   recovery behavior, or must be released separately. Do not split it only
   because it is large, touches many files, or includes frontend and backend work.
4. If splitting, record each minor pass's requirements, scope, prerequisites,
   order, and required verification. If another pass must perform a later
   check, name that pass explicitly. Identify connections between minor passes.
   Confirm that the minor passes cover the entire major pass without losing or
   needlessly duplicating work. Each later minor pass starts from the accepted
   repository state that exists when its work begins.
5. Record blocked or deferred work as described in Section 8 of this workflow.
   Deferral never counts as
   implementation or verification. Other work may proceed only when it does
   not depend on the missing fact or decision.

Create the main major-pass record under
`docs/production-readiness/pass-records/` as `pass-01.md` through `pass-21.md`
when that major pass begins. State whether it will run as one major pass, be
divided into minor passes, or is blocked, and explain why. Assign every
major-pass requirement to the pass responsible for completing it. Name minor
passes with letters, such as `Pass 01A` and `Pass 01B`. A separate minor-pass
record is optional; when used, name it `pass-01a.md`, `pass-01b.md`, and so on,
and link it from the major-pass record.

Keep the major-pass record complete enough for a future session to continue
without relying on chat history. Do not require a separate intake document.
Reassess the Stage 0 scope and pass-splitting decision only when current
requirements, dependencies, or the accepted repository state make it
inaccurate. If no safe work is ready, record the specific blocker and stop.

Leave the major pass's completion date blank in the Production Launch Pass
Completion Log while work is underway. The log does not track active work or
minor-pass progress; the major-pass record preserves the Stage 0 result and
later evidence.

## 3. Gate A — Write the engineering plan

Before implementation, read the complete
`production-launch-pass-planning-template.md` document,
then use it to write the engineering plan for the executable major or minor
pass. Inspect the relevant code and documents while preparing the plan.

Store the plan in the major-pass record or record the exact path of its
separate planning document there. Gate A is complete when the plan is ready
for Gate B review.

## 4. Gate B — Review and approve the engineering plan

Review the complete plan against the Production Launch Requirements, the
Stage 0 scope and pass-splitting decision, applicable specifications, the
accepted repository state, and relevant standards. Check coverage, design consistency,
compatibility, failure handling, and whether the planned checks could prove
each claim. Report every important problem and cite the requirement or source
that demonstrates it.
Fix all identified plan problems in Gate A. After the problems are fixed, a
new Gate B review of the complete corrected plan must be completed. If the pass
scope or pass split changes, repeat Stage 0. If implementation depends on an
unresolved product, legal, security, or operational decision, stop the affected
work until the decision is resolved.

Gate B is approved only when the plan has no important omission or conflict,
each requirement has a workable design and verification method, and every
delayed obligation still identifies who or which pass will complete it and by
when. Save the findings, corrections, and approval or blocker reason in the
major-pass record or a linked review document. Gate B approval does not itself
authorize changes to an external service, publishing Git changes, or starting
work beyond the current assignment.

## 5. Gate C — Carry out the plan and verify the result

Implement the engineering plan approved in Gate B. Follow the coding,
database, testing, security, and operational standards that apply to the work.
Change only what the pass requirements and current assignment allow.

For each planned change:

1. Make the change. Check the affected code and data, and confirm that existing
   behavior that must remain unchanged still works.
2. Run tests or inspections that prove the required result. Also check that the
   change does not cause prohibited results, such as unauthorized access,
   duplicate charges, missing audit records, or incomplete database updates.
   Test relevant limits, failures, retries, simultaneous actions, and recovery.
   Use isolated test data and services for checks that change data or force a
   failure. Follow the production-safety rules in the Production Launch Requirements.
3. Record the check that was run, where it was run, its expected result, its
   observed result, the commit or release tested, and anything the check could
   not prove. Follow Section 8 of this workflow when recording this evidence.
   A planned check or a check that has not run is not a passing result. Run any
   additional tests needed to confirm that related behavior still works.

For every affected requirement, update the major-pass record or its related
evidence file. State whether each required check passed, failed, has not run,
cannot run because a specific external fact or setting is unavailable, or is
assigned to a named later pass. Record what was observed. If a verification
method or the pass assigned to perform it changes, update the verification map.
A minor-pass record may contain the details, but the major-pass record must name
that file and show the state of every major-pass requirement.

Before Gate D, inspect the complete change and the related code. Fix
implementation problems and repeat the affected checks. If implementation
reveals an important problem in the approved plan, stop the affected work,
correct the plan in Gate A, and complete a new Gate B review before resuming
Gate C. If the pass scope or pass split changes, repeat Stage 0. If work depends
on an unavailable external fact or unresolved decision, leave that requirement
open and stop the work that depends on it. Gate C is complete only after the
implementation and required verification are finished.

## 6. Gate D — Review the completed work

Gate D is a read-only review. Do not correct the work while reviewing it.

Read the complete engineering plan approved in Gate B. Review the completed
work against each section of that plan:

1. **Section 1 — Purpose, scope, and starting point:** Confirm that the work
   delivers the stated result, stays within the approved scope, preserves the
   behavior identified in the plan, and accounts for the stated starting point
   and prerequisites.
2. **Section 2 — Required results and safeguards:** Confirm that every required
   result was produced, every prohibited result was prevented, and every
   preserved behavior still works.
3. **Section 3 — Chosen design or operational approach:** Confirm that the work
   follows the approved approach, responsibilities, data handling, interfaces,
   and order of operations.
4. **Section 4 — Failures, boundaries, and simultaneous events:** Confirm that
   every condition, response, retry or recovery rule, and safety check listed
   in the plan is implemented correctly.
5. **Section 5 — Verification plan:** Confirm that every planned check was run,
   produced its expected observation, checked the listed prohibited effects,
   and stayed within its stated proof limit. A planned check that did not run is
   not a passing check.
6. **Section 6 — Finish line and handoffs:** Confirm that the required result,
   safeguards, compatibility, and verification due now are complete. Confirm
   that work assigned to a later pass has not been claimed as complete.

Review the complete implementation and verification results needed to make
these decisions. Do not invent new scenarios, redesign the work, or expand the
pass during Gate D. A newly discovered issue blocks approval only when it shows
that the completed work violates the approved plan or an assigned requirement.

Gate D returns one result:

- **Approved for Gate E:** The completed work matches the approved plan.
- **Corrections required:** The implementation or verification does not match
  the approved plan.
- **Blocked:** A required check cannot run or a required decision is unresolved.

Send implementation problems to Gate C for correction and verification. After
the corrections, complete a new Gate D review of the entire corrected work. If
the approved design must change, return to Gate A and complete a new Gate B
review before continuing through Gates C and D. If the pass scope or pass split
must change, repeat Stage 0.

## 7. Gate E — Finalize, publish when authorized, and record completion

Gate E begins only after Gate D approval.

Before publishing repository changes, confirm the correct branch. Review the
final and staged changes for unrelated edits, secrets, personal or payment
data, and private external-service values. Stop if any are present. Do not
automatically reset, rebase, stash, force-push, or discard changes.

If the current assignment authorizes publication:

1. Read the complete `docs/production-readiness/pass-pr-description-template.md` document and use it to
   write the PR title and description.
2. Stage only the approved files, commit them, push normally, and create or
   update the intended PR.
3. Confirm the PR base, branch, title, and description, and review the complete
   PR changes. Do not change the approved behavior in Gate E.

Leave the PR open for manual merge. Before merge, every required check must run
and pass. A failed, cancelled, missing, or unexplained rerun remains blocking
under P03.R14–R16 and P03.R22. Follow the review rules in P03.R04. For a
high-risk change, obtain qualified independent review when available. If none
is available, complete the allowed solo-maintainer review and additional
checks, and obtain explicit production authorization.

If the pass produces no repository change or PR, save its approved operational
or verification result. Do not create an unnecessary commit. Changing an
external service, deploying, or performing a production, destructive, or
irreversible action requires explicit authorization in the current assignment.

After manual merge, confirm that the intended change reached `develop` and that
its verification evidence still applies. For work without a PR, confirm the
accepted result and evidence directly. Enter the major pass's completion date
in `production-launch-pass-completion-log.md` only after its completion
condition in the Production Launch Requirements is satisfied. If the major
pass has minor passes, all work required by that condition must be complete.

Checks assigned to a later pass remain open. Do not mark them passed, claim
final production acceptance early, or automatically start another pass. Pass
20 may authorize deployment only after its required checks. Final production
acceptance occurs only after the required Pass 21 checks on the deployed
release.

## 8. Evidence and open obligations

The Production Launch Pass Completion Log stays a two-column major-pass
completion record; it does not track individual requirements or evidence. Each major pass has one
main record at
`docs/production-readiness/pass-records/pass-NN.md`, where `NN` is its two-digit
requirement number. That record tracks only deferred obligations assigned by
the major pass or assigned to it by another pass. Separate minor-pass records are
optional and append a
lowercase letter to the major-pass number, such as `pass-01a.md` and
`pass-01b.md`. The major-pass record remains the starting point. Link to
existing authoritative documents instead of copying their full contents.

Pass 03 creates `docs/production-readiness/verification-map.md` and maps every
applicable numbered requirement in Passes 01–21 to its planned numbered
scenario, manual procedure, or named production-setting check, with method,
test layer (such as unit, service, API, database, browser, or operational),
environment, expected result, outcomes that must not occur, and evidence
location. Later passes keep those references and responsible-pass assignments
current while recording observed results in their own records. Planned
coverage, passed checks, checks not yet run, failed checks, and invalidated
evidence remain distinct. The mapping does not itself prove that a check ran.

Each verification record must identify the exact production-launch requirement
and scenario, method, expected and actual result, outcomes that must not occur and
what was observed, environment, affected commit or release, and the person who
performed a manual check when applicable. Record external settings against the
named environment and service, with the time and method of inspection. Apply
the redaction and evidence-validity rules in Section 3.5 of the Production
Launch Requirements. A link to a command, test name, PR, or plan without these
observations is not sufficient proof.

For each blocked or deferred obligation, the originating major-pass record must
state:

- the requirement ID and missing fact or decision;
- the person or pass responsible;
- the condition that allows work to begin;
- the result and verification still required; and
- the latest pass or release point by which it must be completed.

The receiving major-pass record links back and records the actual verification
and completion. Until then, the obligation remains incomplete and blocks the
completion or release decision assigned to it. Pass 20 checks the verification
map, every major-pass record, linked evidence, and deferred obligation against
the exact release candidate. Pass 21 adds the production-safe post-deployment
evidence required before final acceptance. A completed log entry cannot make
incomplete or outdated evidence valid.
