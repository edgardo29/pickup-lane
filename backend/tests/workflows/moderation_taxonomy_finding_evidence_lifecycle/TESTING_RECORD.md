# WS03-05A Moderation Taxonomy And Finding-Evidence Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS03-05A - Versioned moderation taxonomy and finding-evidence lifecycle` |
| Trusted test scope | `backend/tests/workflows/moderation_taxonomy_finding_evidence_lifecycle` |
| Requirement declaration | `backend/tests/support/requirements/ws03_05a.json` |
| Authoritative sources | Frozen WS03-05A plan, frozen WS03-05 intake, `ADM-009`, `ADM-010`, accepted WS03-04/WS04-02/WS04-03A contracts, and current source |
| Evidence layers | Pure pytest, PostgreSQL workflow and independent-session tests, live schema inspection, canonical migration rehearsal, focused compatibility suites, and governance review |

## 1. Scope

This record covers the canonical deterministic moderation registry, complete
finding/detection provenance, exact source binding, span and contextual-
predicate evidence, saved-content history, chat detection persistence,
transaction rollback, conflict-safe reconciliation, and model/migration schema
contract implemented by `WS03-05A`.

It does not claim review-case lifecycle expansion, enforcement, user notices,
minimum-necessary admin responses, controlled unmasking, reusable append-only
administrative audit, final provider/runtime behavior, browser behavior, or
production monitoring. Those remain with WS03-05B/C/D, WS09-02, and existing
later owners.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS03-05A-R1` | One finite validated registry owns every saved-content and chat rule, including the repeated-message predicate and stable public chat rule keys. | mutation pytest and governance |
| `WS03-05A-R2` | Persisted findings and detections retain complete immutable scanner/configuration provenance. | pytest and PostgreSQL |
| `WS03-05A-R3` | Exact source hashes, valid spans, fingerprints, and attributable non-span evidence bind detections to scanned content. | pytest and PostgreSQL |
| `WS03-05A-R4` | Rescan, edit, clear, configuration change, and reappearance preserve truthful current and historical state. | PostgreSQL pytest |
| `WS03-05A-R5` | Target-first locking, uniqueness, validation, and rollback converge under failure and concurrency. | independent-session and PostgreSQL pytest |
| `WS03-05A-R6` | Models, canonical migrations, admin/chat callers, authorization, notification, and rate-limit behavior remain compatible. | focused schema/migration/compatibility pytest, full trusted regression, and checker pass |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| R1-R2 | Every outcome is attributable to one validated rule/profile configuration. | A finite value, enabled-rule set, public rule key, or persistence constraint drifts. | Findings cannot be reproduced or governed. | Registry mutation validation, deterministic configuration hash, model/live-schema finite-set parity, one source module. | workflow/governance/PostgreSQL |
| R2-R3 | Evidence and provenance describe the exact source and contract that produced the row. | Field/purpose/context, rule version, evidence type, source hash, or offset is tampered. | Reviewers see misleading evidence. | Exact UTF-8 hash, authoritative profile inventory, exact rule-version equality, versioned canonicalization, strict shared validators. | workflow/PostgreSQL |
| R3 | Span and predicate evidence remain mutually exclusive, bounded, safe, and recomputable. | Repeated-message evidence fabricates offsets, span evidence changes type, or a preview exposes source content. | False attribution or sensitive-data exposure. | Exact per-kind field sets, rule/evidence equality, deterministic safe-preview validation, fingerprint recomputation, and PostgreSQL container checks. | workflow/PostgreSQL |
| R4 | Exact repeats update detection time only; changed identities preserve old rows. | Evidence is overwritten or historical rows reactivate. | Audit/history loss. | Durable identity hash, partial unique current identity, clear/new-row lifecycle. | workflow/PostgreSQL |
| R5 | Reconciliation scans a locked current target and commits atomically. | Source edits race scans; duplicate cases/events land; unrelated integrity errors are retried. | Stale or contradictory moderation state. | Target-first row locks, stable order, one retry only for the named open-case/current-identity constraints, full rollback, and a fresh locked reread. | independent-session/PostgreSQL |
| R6 | Migration-created tables enforce the same contract the models declare. | Clean rebuild differs from runtime metadata. | Deployment failure or unprotected rows. | Canonical migration edits, live inspector parity, migration rehearsal. | migration/workflow |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | System scanner, chat sender, admin review consumer | covered/grouped | Attribution is system-owned; accepted authorization suites protect caller access. |
| States / lifecycle | new, exact repeat, changed source/configuration, cleared, historical, reappeared | covered | These are the complete A-owned finding-history states. |
| Actions | scan, persist, reconcile, clear, rescan, project signal | covered | They are the mutation and projection boundaries changed here. |
| Inputs / boundaries | empty, Unicode, whitespace/case edits, structured/phrase matches, malformed evidence/hash | covered | They distinguish source identity, comparison, and validation. |
| Time | controlled scan clock/duration and detection ordering | covered | Provenance and latest-message ordering are behavior-bearing. |
| Dependencies | PostgreSQL and canonical Alembic migrations | covered | No external provider is needed. |
| Concurrency / idempotency | forced current-identity creation conflict and source-edit race | covered | Independent sessions prove the actual unique-conflict retry, fresh target reread, lock behavior, and converged row/event state. |
| Authorization / privacy / security | safe previews and no raw expressions in signals/governance | covered/covered elsewhere | Existing WS03-04 suites own route authorization. |
| Persistence / rollback | finding/case/event rows and chat message/detection/read/summary effects | covered | Failures must leave no partial state. |
| Recovery | retry after unique conflict and clean rescan | covered | One bounded retry and ordinary rescan are A's recovery paths. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit / empty | yes | Missing predicate fact, empty registry structures, empty JSON containers | Pure validation and PostgreSQL constraints. |
| corrupt / tamper | yes | Wrong source/profile/field/purpose, fields, offsets, rule version, evidence type, preview, hash, finite value, or discriminator | Pure mutation matrices and PostgreSQL rejection with no partial state. |
| exceed | yes | Evidence and provenance arrays exceed declared bounds | Named constraints and registry limits. |
| duplicate | yes | Identical scan or duplicate message detection identity | Deduplication and named uniqueness proof. |
| reorder | yes | Latest repeated-message candidates and finding lock order | Creation-time/ID ordering and stable reconciliation order. |
| interrupt | yes | Detection persistence fails during message creation | Both chat workflows roll back all owned effects. |
| race | yes | A separate session commits the exact current identity while the surfacing session blocks on its insert; a committed source edit also races a waiting scan. | PostgreSQL events and deterministic barriers, without sleeps. |
| retry / recover | yes | Named current-identity conflict, rollback, and second target lock/read; unrelated check/FK/unique failures are non-retryable. | Two observed target reads, one current finding, one historical row, one attachment for the winning identity, bounded completion, and explicit constraint classification. |
| delay / expire / revoke | no | No delay, expiry, or credential contract is owned by A. | Not applicable. |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| R1-R3 | Registry finite sets/profile relationships, stable public chat IDs, execution-kind, hash, offset, exclusion, exact attribution, preview, and tamper contracts | pure mutation pytest | This trusted workflow scope | Exercises every rejected finite-value and evidence-tampering class without persistence noise. |
| R2-R4 | Community Game and Need a Sub finding lifecycle | PostgreSQL pytest | Saved-content lifecycle contract | Proves persisted history and context ownership across both adapters. |
| R2-R3, R5-R6 | Game and Need a Sub chat detections | PostgreSQL pytest | Chat detection persistence contract | Proves both evidence kinds, provenance projection, query selection, constraints, and rollback. |
| R4-R5 | Forced current-identity creation conflict and source-edit race | independent-session PostgreSQL pytest | Saved-content lifecycle contract | Forces the actual named unique violation, proves rollback plus a second target lock/read and exact converged row/event state, and uses no sleeps. |
| R6 | Model, canonical migration, and live-schema parity | PostgreSQL inspection | Schema/model/migration contract | Compares complete columns and named declared safeguards. |
| R6 | Base/head/back migration behavior | migration pytest | `backend/tests/migrations/migration_policy_compatibility_rehearsal` | Existing isolated harness owns database reset and lifecycle proof. |
| R6 | Existing admin/chat/auth/notification/rate-limit behavior | focused and full trusted pytest | Focused compatibility is green. The prior complete trusted run's intermittent checkout failure was traced to and corrected as a UUID/phone-detection false positive, with focused and affected compatibility proof. | Focused proof protects changed callers, but a new completed full-suite run was not authorized after the correction. |
| R1 | Ownership, contexts, limits, and version policy | governance review | `docs/production-readiness/governance/moderation-taxonomy-register.md` | Publishes the operational contract without raw expressions or user data. |

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| Saved-content reconciliation | One open case as needed, one current identity, append-only attach/clear events | Stale current row, rewritten history, duplicate event | Exact repeat updates timestamps only; failed validation commits nothing. |
| Chat message creation | Message, detections, summary/read/notification effects, then signal projection | Message or auxiliary rows without valid detections | Owning transaction rolls back on any detection failure. |
| Source/configuration change | New current row and preserved historical row | Mutation of original evidence/provenance | Reappearance creates another row rather than reactivating history. |
| Concurrent reconciliation | One winning current state | Duplicate open case/current identity, stale current row, duplicate attachment, or deadlock | Only named creation races receive one bounded retry after rollback; the retry performs a second target lock/read and converges to the independent-session winner. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| Review assignment, merge/reopen, and decision concurrency | covered_elsewhere | A preserves current cases but does not expand their state machine. | `WS03-05B` |
| Enforcement and safe user notices | covered_elsewhere | Not part of taxonomy/finding identity. | `WS03-05C` |
| Minimum-necessary admin responses and audited sensitive access | covered_elsewhere | Requires B plus the applicable reusable WS09-02 audit capability. | `WS03-05D`, `WS09-02` |
| Final provider/runtime/browser/monitoring proof | not_applicable | This pass is deterministic repository and PostgreSQL work. | Existing WS08/WS09/closure owners where applicable |

## 9. Gate C Correction Round 1 Evidence

The five Gate C findings were corrected within the frozen design. The registry
now rejects invalid outcomes, priorities/severities, evidence types, risk areas,
field purposes, languages, contexts, profiles, incomplete or duplicate enabled
rules, invalid evidence limits, and persisted-key collisions. Model and live
database finite sets are compared with the registry, and canonical migrations
are checked for the same values.

Saved and chat validation now enforces exact kind-specific fields, authoritative
context/field/purpose relationships, bounds, source slices and hashes, safe
previews, registry outcome/severity/evidence relationships, and exact matched
rule-version attribution. The accepted external chat keys
`harassment_or_abuse.phrase` and `slur_or_hate.phrase` persist and serialize in
both chat domains while the registry retains unique internal IDs.

Integrity retries are limited to the two named open-case indexes and the named
current-finding identity index. The replacement concurrency proof forces the
current-identity index conflict between independent PostgreSQL sessions, then
observes rollback and two target lock/read statements before asserting one case,
one current finding, one historical row, exactly one attachment for the winning
identity, and bounded completion without deadlock. Separate tests prove check,
foreign-key, and unrelated unique constraints are not retryable.

Correction validation is green: 83 focused tests and 44 directly affected
compatibility tests pass. The one post-correction complete trusted backend run
passes 1,477 tests with zero failures and 13 warnings in 1,666.53 seconds.

## 10. Gate C Correction Round 2 Evidence

The eight Gate C Review 2 findings were corrected within the frozen design.
Database errors from both chat creation workflows and moderation integrity-error
logging now return or record only bounded safe text, with evidence-bearing
canaries proving that raw database detail does not escape. Saved-content
evidence preserves exact long atomic matches and offsets while bounding only
display text, retains every contributing rule/version under the item cap, and
rejects duplicate, reordered, misowned, miscounted, or blank-reference evidence.

The registry now enforces profile-specific field-purpose reachability and owns
the behavior-bearing evidence limits consumed by saved-content and chat code.
Chat signal projection validates and consumes persisted provenance and source
hashes, requires a common source contract across aggregated detections, and
normalizes controlled clocks to UTC while rejecting non-UTC persisted values.
Both chat-detection models and canonical migrations reject JSON-null evidence
discriminators and blank rule keys with matching named constraints.

Correction validation is green at the owned and affected layers: 102 focused
tests, 44 directly affected compatibility tests, and 26 isolated migration
rehearsal tests pass. The suite checker passes with 1,496 collected nodes, 39
traceability passes, and 347 requirement declarations. Scoped Ruff lint,
formatting, and diff checks for all Correction Round 2 Python files pass.

The single post-correction complete trusted backend run produced 1,495 passed,
1 failed, and 13 warnings in 1,302.74 seconds. The intermittent checkout HTTP
409 was subsequently reproduced through another checkout test and traced to a
production false positive: the generic phone detector matched `340077-7855`
inside the valid UUID `4b340077-7855-4d77-a0fb-558aba611ff5`. Durable-job
payload validation therefore rejected a safe payment identifier before
checkout could persist its reconciliation job.

The correction excludes only phone matches that overlap a validated canonical
UUID span. Phone detection outside that span and every other sensitive-text
detector remain active. Deterministic coverage proves the reproduced UUID is
accepted, malformed UUID-like text is not exempted, a real phone remains
detected, a UUID plus a real phone remains detected, and checkout persists the
reconciliation job under the reproduced payment UUID without a false HTTP 409.

Post-fix targeted validation passes 65 focused redaction, durable-job,
unknown-outcome checkout, and financial-response tests. Affected observability,
API-error, settings, and secrets compatibility validation passes 209 tests. An
attempted complete run was stopped at the owner's direction after 109 passing
tests and 12 warnings; it is not complete-suite evidence and no post-fix
zero-failure complete-suite result is claimed.

## 11. Owner-Directed Gate C Correction Evidence

The two remaining Gate C Review 3 findings were corrected within the frozen
design. Payment-pressure findings now derive priority and rule attribution from
all core pressure matches plus only payment-method or payment-handle matches
that satisfy the existing same-clause and distance rules. Support text outside
those contextual rules no longer invalidates an otherwise valid finding or
appears in its evidence or provenance.

Context-predicate validation now requires `reference_message_id` to be a
nonblank string and `reference_source_hash` to be a string containing lowercase
SHA-256. Neither field is coerced from another JSON type before validation or
fingerprint recomputation. Negative tests recompute fingerprints around the
tampered values and prove rejection at both record construction and persisted-
detection projection.

Defect-specific validation passed 13 pure contract cases and 5 PostgreSQL
persistence cases. The subsequent complete owned WS03-05A scope passed 120
tests. The affected admin-review, game-chat, Need a Sub relationship, and chat-
rate-limit compatibility set passed 31 tests with one botocore `utcnow()`
deprecation warning. The scoped backend-test checker passed with 120 collected
nodes, and Ruff lint/format plus `git diff --check` passed for the correction
files.

No complete trusted backend suite was run for this owner-directed correction,
following the owner's final instruction. This section therefore claims focused
and affected-compatibility validation only and does not add a new full-suite
result.

## 12. Final Gate C Owner-Directed Correction Evidence

The four findings from the latest complete Gate C review were corrected within
the frozen design. Fail-safe saved-content and chat-signal boundaries now log
only safe operation context, target identifiers, and exception class. Canary
tests use synthetic SQLAlchemy operational errors whose exception text, SQL
statement, and parameters all contain sensitive markers; both saved-content
adapters, chat-signal projection, and the reconciliation helper prove that none
of those values or traceback data reaches captured logs.

Nested saved-evidence `rule_id`, `rule_version`, and `evidence_type` values must
now be nonblank strings before registry validation. A numeric, boolean, JSON
null, list, or object value is rejected for each field by both the direct
validator and the PostgreSQL reconciliation boundary without partial review
state. The finite-set parity proof now compares registry, model, canonical
migration, and live-database `risk_area` values in addition to the existing
finding, priority, category, and severity contracts.

Repeated-message query proof now covers deterministic timestamp and ID ordering,
different-latest behavior, and persisted-candidate exclusion in both chat
domains. Need a Sub's database permits only text messages, and a query-shape
test separately proves that the service retains its explicit text-only filter;
sender, chat, and visibility isolation remain covered by PostgreSQL tests. No
production repeated-message query behavior changed.

Defect-specific validation passed 38 tests. After the database canaries were
strengthened, their four affected nodes passed again, and the complete owned
WS03-05A scope passed 155 tests. The directly affected admin review, game chat,
Need a Sub relationship, and chat-rate-limit compatibility selection passed 18
tests. The isolated migration policy and compatibility rehearsal passed 26
tests with 12 existing Alembic/index-comparison warnings. The scoped backend-
test checker passed with 155 collected nodes and all six WS03-05A requirements
mapped. Ruff lint, Ruff formatting, and `git diff --check` passed for the
correction files.

The complete trusted backend suite was not run, following the owner's explicit
instruction. This correction therefore claims focused, complete owned-scope,
affected-compatibility, live-schema, and migration evidence only; it does not
claim a current zero-failure full-suite result.

## 13. Adequacy Conclusion

Gate C Correction Round 1 has focused, compatibility, independent-session, live
schema, migration, and broad-regression evidence for all five findings. The
complete trusted backend suite passes 1,477 tests with zero failures. Its 13
warnings are the existing Alembic path-separator deprecations, one SQLAlchemy
index-comparison warning, and one botocore `utcnow()` deprecation; none is a
test failure or a new WS03-05A behavioral defect. The prior Gate B result remains
historical rather than being presented as proof of the corrected change set.

The prior Gate B broad-regression blocker was resolved. Its remaining 39 failures were
repaired through four shared test-infrastructure causes: stale production-like
settings builders, process-wide logger disabling during in-process Alembic
execution, dotenv leakage into migration fallback tests, and an overbroad admin
bootstrap route-source heuristic. Focused validation for each cause and the
Correction Round 1 complete trusted suite were green. Gate B remains a passing
historical verdict.
Later review, enforcement, privacy, audit, provider, and runtime obligations
remain explicitly outside A.

Correction Round 2 has complete focused, compatibility, live-schema, migration,
and checker evidence for all eight findings plus targeted proof of the corrected
UUID/phone false positive. The identified checkout blocker is resolved at the
focused and affected-compatibility layers. A post-fix zero-failure complete
suite remains unproven because the owner stopped and disallowed that run; no
full-suite success is claimed.

The owner-directed Gate C correction has complete focused and affected-
compatibility evidence for both Review 3 findings. Payment attribution remains
bounded to actual contextual contributors, and non-span reference fields retain
their exact string contracts at construction and projection boundaries. The
owner-directed correction did not rerun the complete trusted backend suite, so
the prior full-suite limitation remains explicitly unchanged.

The final owner-directed correction has complete focused, owned-scope,
affected-compatibility, live-schema, migration-rehearsal, checker, and static-
quality evidence for its four findings. Sensitive failure logs, nested evidence
types, `risk_area` parity, and repeated-message query behavior now have direct
adversarial proof. The owner-directed full-suite omission remains a disclosed
validation limitation rather than a claimed pass.

Checker `PASS` is structural compliance only and does not replace this human
adequacy assessment. This record contains no credentials, credential-bearing
URLs, raw sensitive logs, provider-private values, personal/payment data, local
machine paths, usernames, session state, internal chat material, or other
prohibited sensitive values.
