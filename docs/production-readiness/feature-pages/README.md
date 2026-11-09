# Pickup Lane Feature Passes

Start here for a feature pass. For the 21 production-launch passes, start with
`docs/production-readiness/production-launch/README.md`.

## 1. Start or resume a feature pass

### Starting a new pass

1. Find the page in `docs/production-readiness/feature-pages/page-inventory.md`. Read its
   complete specification under `docs/production-readiness/feature-pages/pages/` and any other
   specification it names as the source of a shared rule.
2. Check `docs/production-readiness/feature-pages/feature-pass-completion-log.md` and any
   existing assessment for that page under
   `docs/production-readiness/feature-pages/feature-pass-plans/`.
3. Read `docs/production-readiness/feature-pages/feature-pass-workflow.md` and follow Gate A
   onward. Read `docs/production-readiness/feature-pages/feature-pass-planning-template.md`
   in full when you reach Gate B. Read the supporting documents in Section 2
   that apply to the selected page.

### Resuming an unfinished pass

1. Use the handoff in the new request to identify the page specification, gate,
   next action, and branch or pull request, if one exists. The completion log
   does not identify unfinished work.
2. Read that page's complete specification, its existing assessment if one was
   created, and `docs/production-readiness/feature-pages/feature-pass-workflow.md`. Check the
   current branch, implementation, and verification results before continuing
   at the gate identified in the handoff.
3. Read the supporting documents in Section 2 that apply to the remaining
   work. If the handoff is missing or inaccurate, establish what the repository
   shows and obtain the missing page or next action before continuing.

Before switching chats during an unfinished pass, provide a short handoff with
the page specification, gate, next action, and branch or pull request, if one
exists. Keep temporary progress out of this README.

The selected page specification defines required behavior in Sections 3 and 4
and verification scenarios in Section 5. Existing code and tests show what is
present; they do not replace the specification.

## 2. Supporting documents

- `docs/production-readiness/system-architecture.md` — approved system
  design and external-service boundaries.
- `docs/production-readiness/database-architecture.md` — approved database
  design, including changes awaiting implementation.
- `docs/production-readiness/data-model-baseline.md` — existing repository
  schema declarations, not a verified deployed database.
- `docs/coding-standards/coding-standards-README.md` — location of coding and testing standards. Read
  the standards that apply to the work.
- `docs/production-readiness/feature-pages/page-specification-template.md` — format for new
  page specifications; it is not an implementation plan.

If requirement documents conflict, identify the exact passages and stop the
affected work for a decision. Do not invent a product rule. Follow the request
for this work and the feature-pass workflow for edit, review, publication, and manual
merge boundaries. Do not include credentials or private information in changes
or review evidence.

Final legal wording remains open in the Terms of Service, Privacy Policy, and
Cancellation & Refunds Policy specifications under
`docs/production-readiness/feature-pages/pages/public/`. Each specification's Section 6
identifies its unresolved items.
