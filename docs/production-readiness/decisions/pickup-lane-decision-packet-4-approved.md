# Pickup Lane Decision Packet 4: Approved Record

## Status

**APPROVED**

Approval date: August 3, 2026

This record locks the final eleven owner decisions covering accessibility, browser support, enforcement notices, recovery, retention, database lifecycle, service objectives, capacity planning, and audit-record governance.

It records product, policy, and architecture direction only. It does not claim implementation, testing, provider configuration, runtime evidence, legal compliance, or production readiness.

## Approved decisions

### OPP-01 / FE-M12: Accessibility target and verification scope

Approved direction:

- Pickup Lane targets WCAG 2.2 Level AA across player-facing and administrative workflows.
- Verification includes automated checks and documented manual testing for keyboard operation, focus, dialogs, forms, status messages, contrast, zoom, reflow, reduced motion, and supported screen-reader behavior.
- No formal conformance claim may be made until the defined application scope has actually been verified.
- Individual AAA practices may be adopted where useful, but full Level AAA conformance is not required.

### OPP-02 / FE-M13: Browser support, performance, source maps, and frontend telemetry

Approved direction:

- Pickup Lane supports defined modern desktop and mobile browsers rather than every historical browser.
- The supported set includes current and previous major versions of Chrome, Edge, Firefox, and Safari, including modern mobile Safari and Chrome.
- Performance budgets will be selected only after production-build testing on realistic devices and networks.
- Production source maps remain private, access-controlled, and linked to the exact frontend release.
- Frontend telemetry collects only minimum necessary technical data and must not capture passwords, tokens, private messages, payment details, unrestricted form contents, or unrestricted session recordings.

### OPP-03 / ADM-014: Enforcement notice and review policy

Approved direction:

- Enforcement notices are sent after the action takes effect by default.
- Notices explain the action, affected area, general reason category, duration where relevant, and appropriate next step.
- Notices must not expose reporters, private information, exact detection rules, fraud signals, security-investigation details, or other information that could create risk or help bypass controls.
- Delayed or suppressed notice requires a structured internal reason.
- Users may request a basic manual review when appropriate.
- Exact notice wording, review channel, response timing, and non-reviewable cases remain later implementation and policy details.

### OPP-04 / OPS-018: Tiered recovery requirements, RPO, RTO, and PITR

Approved direction:

- Pickup Lane uses tiered recovery requirements.
- Critical financial, booking, identity, authorization, and audit data receive the strongest protection.
- Important application data receives managed backup and tested restoration.
- Replaceable caches and image derivatives may be regenerated.
- Recovery must verify Firebase-to-user mapping, roles, restrictions, bookings, participant capacity, Stripe reconciliation, R2 references, migration compatibility, deletion reapplication, and duplicate-job prevention.
- Exact RPO, RTO, backup windows, retention periods, PITR settings, provider plans, and regional-failover requirements remain evidence-based later decisions.

### OPP-05 / OPS-020: R2 recovery classification

Approved direction:

- Venue images are important but replaceable assets.
- Missing R2 objects must not break venue or game records.
- The frontend uses a default venue presentation when an image is unavailable.
- Missing or inconsistent objects create a detectable repair condition.
- Administrators can upload replacements.
- One approved sanitized master may be retained for active images so derivatives can be regenerated.
- Zero-loss recovery guarantees are not required unless later business evidence justifies them.

### OPP-06 / OPS-021: Recovery exercise policy

Approved direction:

- Pickup Lane must complete both a recovery tabletop and an isolated technical restore exercise before production sign-off.
- Exercises repeat after major recovery-related changes or serious incidents and later follow an approved recurring schedule.
- Every exercise records the scenario, participants, results, failures, owners, corrective actions, and closure evidence.
- Backups cannot be treated as proven until restoration and post-restore verification succeed.

### OPP-07 / OPS-022: Purpose-based retention schedules

Approved direction:

- Pickup Lane uses purpose-based retention schedules rather than one universal duration.
- Each data category requires a documented purpose, owner, retention or review rule, deletion or anonymization outcome, backup treatment, and exception process.
- Data may not be kept indefinitely without a justified purpose.
- Deletion from the live system does not imply immediate removal from protected backups; backup expiry and deletion reapplication must be handled explicitly.
- Security investigations, payment reconciliation, disputes, and authorized legal holds may temporarily preserve relevant records through a documented exception.
- Exact durations require business, privacy, provider, financial, and where appropriate qualified legal input.

### OPP-08 / DB-011: Table-by-table database lifecycle matrix

Approved direction:

- Each significant PostgreSQL table must explicitly use hard deletion, anonymization, restricted retention, or justified soft deletion.
- Soft deletion is not the default for every table.
- Lifecycle design must account for foreign keys, uniqueness, historical records, restoration, backups, deletion reapplication, and financial or legal exceptions.
- Financial, refund, credit, dispute, security, and selected audit data may require restricted retention.
- Temporary and replaceable records may be hard-deleted.
- Public identity should be removed or anonymized when the continuing business record does not require it.

### OPP-09 / OPS-012: Service indicators and objectives

Approved direction:

- Pickup Lane defines a focused set of indicators and objectives for availability, speed, correctness, payment reliability, background-job delay, and data freshness.
- Critical workflow health matters more than merely proving the server responds.
- Launch-blocking thresholds focus on bookings, payments, authorization, capacity, workers, and other critical outcomes.
- Exact numeric targets are selected only after realistic measurements and testing.
- Error-budget rules prevent recurring reliability failures from being ignored in favor of new feature work.

### OPP-10 / OPS-016: Capacity and cost model

Approved direction:

- Pickup Lane maintains an evidence-based capacity and cost model covering hosting, PostgreSQL, workers, Firebase, Stripe, R2, logs, monitoring, CI, and backups.
- Every major resource requires a known provider limit, tested operating range, warning signal, failure behavior, scaling path, and accountable cost owner.
- The model must warn before provider rejection or uncontrolled cost growth.
- Critical financial and booking workflows must not be the first functions sacrificed under pressure.
- Exact thresholds, monthly budgets, traffic limits, and provider plans remain later evidence-based decisions.

### OPP-11 / ADM-008: Audit-record lifecycle, review, legal hold, and export handling

Approved direction:

- Audit records are append-only and access-restricted.
- Past audit entries are not edited; corrections use linked follow-up records.
- High-risk events receive appropriate review or alerts.
- Audit retention depends on purpose and category rather than one universal duration.
- Older records may be archived in protected storage.
- Deletion or anonymization occurs only through controlled retention processes and produces evidence.
- Properly authorized legal, security, financial, or investigation holds temporarily suspend normal deletion for the scoped records.
- Audit exports must be authorized, minimized, access-controlled, protected, time-bounded or securely disposed of, and themselves audited.
- Exact retention durations, alert thresholds, archive technology, export process, and legal-hold details remain later operational and legal design items.

## Approval impact

Decision count after this approval:

- Total owner-decision register entries: **27**
- Approved: **27**
- Open: **0**

Previously approved decisions remain unchanged:

- FDN-01 through FDN-07
- IDB-01 through IDB-05
- DBP-01 through DBP-04

Newly approved decisions:

- OPP-01 through OPP-11

## Supersession rule

A later change to any decision in this record requires a new superseding decision record. This approved record remains preserved.

## Implementation restriction

This approval does not authorize application code changes, Git branch changes, worktree creation, provider configuration, deployment changes, migrations, worker changes, storage mutations, monitoring changes, backup changes, or CI changes.
