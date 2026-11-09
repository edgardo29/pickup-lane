# Pickup Lane Production Launch Passes

Start here for the 21 production-launch passes. For feature passes based on
page specifications, start with `docs/production-readiness/feature-pages/README.md`.

## 1. Start or resume a production-launch pass

### Starting a new pass

1. Identify the selected major pass in
   `docs/production-readiness/production-launch/production-launch-requirements.md`.
   Read Sections 1, 3, and 4, then the entire selected pass, including its
   requirements, dependencies, verification, and completion condition. Read
   any exact upstream requirement the pass cites.
2. Check `docs/production-readiness/production-launch/production-launch-pass-completion-log.md`
   and any existing major-pass record under
   `docs/production-readiness/pass-records/` (named `pass-NN.md`). The log
   records completed major passes; a blank date does not identify active work.
3. Read `docs/production-readiness/production-launch/production-launch-pass-workflow.md`
   and begin at Stage 0. Read
   `docs/production-readiness/production-launch/production-launch-pass-planning-template.md`
   in full when you reach Gate A. Read the supporting documents in Section 2
   that apply to this pass.

### Resuming an unfinished pass

1. Use the handoff in the new request to identify the major or minor pass,
   stage or gate, next action, and branch or pull request, if one exists.
2. Read the complete selected major pass in the Production Launch Requirements,
   the Production Launch Pass Workflow, and its existing major-pass record.
   Read the plan, review results, verification evidence, and deferred
   obligations that record identifies when they apply to the remaining work.
3. Check the handoff against the current repository and actual verification
   results before continuing at the identified stage. Read the supporting
   documents in Section 2 that apply. If the handoff is missing or inaccurate,
   establish what the repository shows and obtain the missing pass or next
   action before continuing. Previously merged work starts at Stage 0 under
   the Production Launch Pass Workflow.

Before switching chats during an unfinished pass, provide a short handoff
with the pass, stage or gate, next action, and branch or pull request, if one
exists. Keep temporary progress out of this README.

## 2. Documents and boundaries

- `docs/production-readiness/production-launch/production-launch-requirements.md` —
  production-launch requirements, pass order, verification, and completion
  conditions.
- `docs/production-readiness/production-launch/production-launch-pass-workflow.md` —
  assessment, planning, implementation, review, and finalization steps.
- `docs/production-readiness/production-launch/production-launch-pass-planning-template.md`
  — structure for a major- or minor-pass engineering plan.
- `docs/production-readiness/production-launch/production-launch-pass-completion-log.md`
  — completed major passes and dates only.
- `docs/production-readiness/system-architecture.md` — approved system
  and operational design.
- `docs/production-readiness/feature-pages/page-inventory.md` — finds the Product &
  Functional Specifications under `docs/production-readiness/feature-pages/pages/`.
- `docs/production-readiness/database-architecture.md` — approved database
  design; `docs/production-readiness/data-model-baseline.md` describes
  existing repository schema declarations.
- `docs/coding-standards/coding-standards-README.md` — location of coding and testing standards.
  Read only the standards that apply to the selected work.

The Production Launch Requirements define launch outcomes; the applicable
page specifications define product behavior. Architecture documents describe
approved designs, and standards guide implementation and verification. Code
and tests show what exists, not what is required. If these sources conflict,
identify the exact passages and stop the affected work for a decision. Do not
invent a rule or change a Production Launch Requirement without amending it.

Major-pass records under `docs/production-readiness/pass-records/` hold plans,
verification evidence, and deferred obligations. Pass 03 creates
`docs/production-readiness/verification-map.md` for planned coverage; a
planned check is not completed evidence. The completion log stays limited to
completed passes and dates.

Follow the request for the work and the Production Launch Pass Workflow for
edit, review, publication, and stop boundaries. Preserve unrelated changes
and protect credentials and private information. External-service changes,
deployment, Git publication, and other consequential actions require
authorization. Pull requests are merged manually. Finishing one pass does
not automatically start another.
