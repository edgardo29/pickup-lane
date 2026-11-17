# Pass NN — [Official Production Launch Requirements name]: Stage 0

[Save as `docs/production-readiness/pass-records/pass-NN/pass-NN-stage-0.md`.
Replace all bracketed guidance with the actual assessment. This file records
what is done, what is missing, and whether the pass is split. It contains no
plan, design, review findings, or verification evidence.]

## Decision

**Result:** [One pass / Split into Pass NNA, Pass NNB, ... / Blocked]

**Why:** [One or two sentences. Split only for a reason listed in Stage 0 of
the workflow: different outcomes, dependencies, responsible people or passes,
failure or recovery behavior, or separate release.]

## Requirements

[List every requirement in the pass. Use one status per row.]

| Requirement | Status | What is missing | Done by |
|---|---|---|---|
| [PNN.R01 — Name] | [Status] | [Only what is missing, or "—"] | [This pass, Pass NNA, or a named later pass] |

Status is one of:

- **Done:** the existing document, code, or accepted evidence that proves it is
  named in "What is missing" as "Proven by [file and section]".
- **Partly done:** some of it exists; list only the missing part.
- **Missing:** nothing exists yet.
- **Later pass:** the Production Launch Requirements assign it to a named later
  pass.
- **Blocked:** a missing fact or decision prevents it; list it under Blockers.

[Also list each numbered verification scenario the pass owns, with the same
statuses. If the pass owns none, say so.]

## Connections to keep working

[Existing behavior, other passes, and features that depend on this work or
that this work must not break. One line each.]

## Decisions needed

[Each product, legal, security, or operational decision the pass needs from a
named person, and what it blocks. Write "None" if there are none.]

1. [Question] — [who decides] — [what it blocks]

## Blockers

[For each blocked or deferred item, give the fields required by Section 8 of
the workflow. Write "None" if there are none.]

| Requirement | Missing fact or decision | Responsible | Can start when | Latest completion point |
|---|---|---|---|---|

## Split

[Include only when the decision is to split. Every requirement must appear in
exactly one minor pass.]

| Minor pass | Requirements | Scope | Depends on | Order | Verification due |
|---|---|---|---|---|---|
| Pass NNA | [IDs] | [One line] | [— or Pass NNB] | 1 | [Checks or scenarios] |

[Name any check that a later pass must perform, and the pass that performs
it.]

---

**Writing rules — remove before saving**

- Do not repeat what an existing document already says. Name where it is.
- Use plain words. Write "Section 4.1 of system-architecture.md", not a symbol
  or shorthand.
- Do not include commit IDs, plan content, or guessed values.
