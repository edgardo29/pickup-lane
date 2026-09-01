# WS03-05A - Versioned Moderation Taxonomy And Finding-Evidence Lifecycle

This work gives every deterministic moderation finding a governed taxonomy,
complete scanner provenance, content-bound evidence, and a durable current or
historical lifecycle.

This document is the engineering blueprint for this pass.

## 1. What This Work Does

Pickup Lane currently scans saved Community Game and Need a Sub text into
structured content findings, and scans game-chat and Need a Sub chat messages
into separate detection records and review signals. The scanners are
deterministic and already preserve useful rule IDs, content hashes, evidence,
and current or cleared finding state. Their rule definitions and finite sets are
spread across multiple modules and database constraints, however, and the
persistent records do not consistently identify the taxonomy, scanner
configuration, canonicalization rules, language and context limits, or scan
execution that produced them.

This work establishes one versioned taxonomy registry for both deterministic
scanner representations. It records enough immutable provenance on every saved
finding or chat detection to reproduce which rule configuration ran, binds
evidence to an exact target field and source-text hash, and makes
duplicate scan, edit, clearing, reappearance, and concurrent reconciliation
behavior deterministic.

Existing moderation categories, priorities, message review status, review-case
presentation, and public behavior remain compatible. This work does not design
review-case assignment or transitions, enforcement actions, user notices,
minimum-necessary admin responses, controlled unmasking, durable scanner
failure and backlog states, delivery jobs, or production monitoring.

## 2. What Must Be True

These requirements define when a moderation finding is attributable and
truthful. A reviewer must be able to distinguish a current match from historical
evidence and identify exactly which scanner contract produced either one.

### 2.1 One Governed, Versioned Taxonomy

All rules used by the saved-content and chat-message scanners must come from one
canonical registry. Each rule must have a stable rule ID and version, scanner
profile, category or finding type, priority or severity, evidence type,
execution kind, applicable target contexts, applicable field purposes, language
limits, and any supporting-only behavior. The registry must support both
span-producing regular-expression rules and deterministic contextual predicates
without pretending that a predicate has a compiled expression or text span.

The registry must identify the taxonomy version, scanner identity and version,
canonicalization version, evidence format version, enabled rules, and the
accountable Identity and Application Security owner role. It must also define
which changes require a rule, taxonomy, scanner, canonicalization, or evidence
format version to advance. A stable rule ID must never silently acquire new
meaning.

The registry must preserve the current finite rule behavior unless a change is
required to make attribution or evidence safe. This pass must not add policy
categories, machine-learning behavior, or broader moderation coverage without
separate authority.

### 2.2 Every Finding Has Complete Scan Provenance

Every persisted saved-content finding and chat-message detection must record:

- the scanner identity and version;
- the taxonomy version and exact rule versions that matched;
- a deterministic configuration hash for the scanner profile that ran;
- the target context, field purpose, and declared language/context limits;
- the canonicalization and evidence format versions;
- the UTC scan timestamp and non-negative monotonic execution duration.

The configuration hash must cover the behavior-bearing registry data, including
each rule's execution kind; regular-expression source and flags or contextual-
predicate identity, version, input-selection rules, and comparison behavior;
category mappings; priorities; contexts; supporting-only behavior; evidence
limits; and format versions. It must not contain source text, user identifiers,
credentials, or other sensitive runtime data.

The two scanner representations must use the same provenance contract. Chat
review signals may mirror that contract for display and review, but their
metadata must be derived from the persisted chat detections rather than from a
separate scanner-version constant.

### 2.3 Findings Are Bound To Exact Content And Evidence

Every finding must identify the exact source field and a `source_content_hash`
computed as SHA-256 over the original field value encoded as UTF-8, with no
normalization. That exact hash binds evidence and offsets to the source text
that was scanned. Separately, span matched-value and evidence-fingerprint
comparisons use a named canonicalization version. The current span-evidence
canonical form continues to trim and collapse whitespace, apply Unicode case
folding, and perform no additional Unicode normalization. Any future change to
those rules requires a new canonicalization version. A contextual predicate
uses its own registered and versioned comparison contract instead; the repeated-
message rule therefore keeps `strip().casefold()` equality without internal
whitespace collapse.

Span evidence offsets must be zero-based, half-open Unicode code-point indexes
into the original uncanonicalized Python string. Each stored span must satisfy
`0 <= start < end <= len(source_text)`, and its recorded matched text or match
hash must correspond to `source_text[start:end]`. Display excerpts may be
trimmed and capped, but their offset basis must remain explicit and must not be
confused with canonicalized-text offsets.

Saved-content findings must retain the existing bounded, structured, unmasked
evidence required by the admin review contract. Span-producing chat detections
must retain a bounded safe preview, exact offsets, and a hash of matched
evidence; they do not need to duplicate the full chat message body.

The existing repeated-message rule is non-span evidence. Its evidence must
record the contextual-predicate key and version, a true outcome, the referenced
prior message ID, and the exact UTF-8 source hash of that prior message. The
detection's normal source field and source hash bind the current message. The
evidence must contain no fabricated start or end offset, matched text, or
matched-substring hash. Its bounded safe preview continues to use the current
whole-message preview behavior.

Evidence must never be emitted through player APIs, notifications, analytics,
or public logs.

The evidence fingerprint must be derived from stable evidence, not a display
sentence. Span-evidence fingerprints include the finding type or category,
source field, and sorted unique evidence-type/value pairs normalized under the
named canonicalization contract. Repeated-message fingerprints include the
category, source field and exact current source hash, contextual-predicate key
and version, true outcome, referenced prior message ID, and exact prior-message
source hash. Both forms serialize deterministically before hashing.

### 2.4 Duplicate Scans And Edits Preserve History

The durable identity of a finding must include the target scope, source field,
source content hash, finding type or category, evidence fingerprint, matched
rule versions, scanner identity/version, taxonomy version, configuration hash,
canonicalization version, evidence format version, and target context.

Repeating an identical scan while the same finding is current must reuse the
current finding identity. It may advance `last_detected_at` and the row's normal
update timestamp, but it must not replace the original evidence or provenance,
create a second current row, or emit another attachment event.

When the exact source text, matched evidence, taxonomy, rule version, scanner
configuration, canonicalization, evidence format, or target context changes,
the result is a different finding identity. This includes source edits that are
equivalent under canonicalization, such as case-only or whitespace-only edits,
because evidence offsets remain bound to the original string. Current findings
that are no longer present in the complete scan result for a field become
historical by setting
`current_match = false` and recording `cleared_at`. Their evidence and original
provenance remain unchanged.

A clean edit moves all affected current findings to history without closing the
review case. If the same evidence later reappears after clearance, it creates a
new current finding and a new attachment event rather than reactivating or
rewriting the historical row.

### 2.5 Persistence Is Atomic And Conflict-Safe

A saved-content scan may become current only for the target snapshot it
actually scanned. The reconciliation transaction must lock and re-read the
current target aggregate before deciding finding state. Community Game work
must lock the game before its detail and moderation case; Need a Sub work must
lock the post before its moderation case. Findings are then locked and
reconciled in stable creation and ID order.

The scan must use the locked current field inventory. A stale pre-lock scan must
not attach findings, clear newer findings, or update a case. Scanning is local,
deterministic, and bounded by existing field limits, so it may run while the
short target reconciliation lock is held. It must perform no network or
provider operation.

Concurrent identical reconciliations must leave one current finding per durable
identity and one attachment event. A unique conflict may be retried only after
rollback and a fresh locked read. A failed reconciliation must not commit a
partial mixture of new, cleared, or updated findings.

The scanner must continue to mutate findings only on an open content-moderation
case. A closed case and its findings remain historical. Risky content that is
still actionable after closure uses a new or other valid open case under the
existing one-open-case invariant.

Chat detections must commit atomically with their owning message and message
review status. Each persisted detection must be unique for its message and
durable detection identity. The later review-signal projection must not change
the detection record that proves what was scanned.

### 2.6 Schema And Caller Compatibility

The finding and chat-detection tables must enforce non-empty identifiers,
well-formed 64-character lowercase SHA-256 values, non-negative execution
duration, non-empty bounded provenance/evidence structures, valid current or
cleared state, and the required uniqueness rules. SQLAlchemy models and their
canonical table migrations must describe the same final schema.

Because Pickup Lane is still under the approved clean-rebuild migration policy,
the canonical migrations that own the three existing moderation tables must be
updated directly. No patch migration or speculative production backfill is
part of this work. A database built from base to head must contain the complete
new schema.

Existing admin review responses must continue to provide their current finding
fields and current/previous grouping. New internal provenance does not require
new reviewer UI, and raw rule expressions or scanner debug data must not be
shown there. Existing game-chat and Need a Sub chat creation, rate limiting,
notifications, review-status behavior, and authorization must remain intact.

## 3. Design

The design separates immutable scanner definition, one scan's execution
provenance, evidence construction, and database lifecycle. That separation
prevents a rule change or content edit from silently rewriting what an earlier
finding meant.

### 3.1 Canonical Taxonomy Registry

Introduce a focused, side-effect-free moderation taxonomy module consumed by
both `content_moderation_scanner_service` and `chat_moderation_service`. It owns
the rule and scanner-profile definitions currently duplicated across those
services; orchestration and database work remain in their existing services.

Each rule definition contains:

- `rule_id` and `rule_version`;
- the saved-content finding type or chat category it produces;
- risk area and priority, or chat severity;
- an `execution_kind` selected from the finite `regex_search` and
  `context_predicate` set;
- an evidence type and kind-specific behavior definition: expression source and
  flags for `regex_search`, or predicate key, predicate version, deterministic
  input contract, and comparison contract for `context_predicate`;
- enabled scanner profile and target contexts;
- allowed field purposes;
- language scope, distinguishing structured language-independent matches from
  English phrase rules;
- supporting-only semantics where a match cannot create a finding alone.

Each scanner profile contains a stable scanner ID, scanner version, taxonomy
version, canonicalization version, evidence format version, enabled rule IDs,
context and field inventory, evidence limits, and configuration hash. The hash
is SHA-256 over canonical JSON generated from the complete behavior-bearing
profile. For regex rules that includes expression source and flags. For
contextual predicates it includes execution kind, predicate key and version,
candidate/reference selection, ordering, eligibility filters, comparison
normalization, and outcome semantics. Runtime message bodies, message IDs, chat
IDs, and sender IDs never enter the configuration hash.

Registry validation runs before a scan and rejects duplicate IDs, unknown rule
references, unsupported categories, missing language/context declarations,
invalid priorities or evidence types, a rule with missing or mixed execution-
kind configuration, and a context with no authoritative field inventory. A
regex rule must have an expression and span-evidence contract and no predicate
configuration. A contextual predicate must have its complete predicate and non-
span evidence contracts and no expression. The current model and database
finite sets remain explicit and are checked against the registry so a source-
only taxonomy change cannot drift from persistence constraints.

The existing `spam_or_repeated_message.same_sender_same_body` entry is a
`context_predicate` rule with its own stable rule and predicate versions. It
keeps category `spam_or_repeated_message`, low severity, and the current exact
behavior: compare the candidate text with the latest visible text message from
the same sender in the same chat, selected by descending creation time and then
descending message ID, after applying `strip().casefold()` to both values. When
evaluating an already-persisted candidate, that message is excluded from the
reference query. No other prior message, count threshold, time window, fuzzy
comparison, or spam policy is introduced.

A tracked human-readable taxonomy record explains the owner role, supported
contexts and language limitations, active versions, and version-bump rules. It
describes the same registry contract without publishing regular expressions or
user evidence.

### 3.2 Scan Result And Provenance Contract

Both scanner entry points return a scan result rather than an unqualified list
of matches. The result contains the complete scanned field inventory, findings
or detections, and one immutable execution-provenance value with:

- scanner, taxonomy, configuration, canonicalization, and evidence versions;
- context and declared language limits;
- UTC `scanned_at`;
- elapsed microseconds measured with a monotonic clock.

The wall clock and monotonic clock are injectable at the scan boundary so tests
can assert exact timestamps and durations without sleeping. Duration is measured
around the complete deterministic rule evaluation and evidence construction,
not database reconciliation or later signal projection.

Each emitted finding carries the matching rule-version pairs and field purpose.
Persistence copies provenance from the scan result; callers must not reconstruct
it from module constants. A scan that emits several findings may attach the same
execution timestamp and duration to each because they came from one execution.

Chat scan orchestration supplies contextual rules with typed predicate facts,
not unqualified booleans. For the repeated-message rule, a true fact contains
the predicate key/version and the selected prior message's ID and exact source
hash. An absent prior message or a false comparison supplies no matching fact
and emits no repeated-message detection. Building this deterministic fact is
inside the timed chat scan operation; the pure rule evaluator consumes it
without querying a provider or inventing a regex match.

### 3.3 Canonicalization, Evidence, And Fingerprints

Keep source hashing and canonicalization in one side-effect-free evidence
utility. It returns the exact SHA-256 of the original UTF-8 source text and the
separately versioned canonical comparison form. Finding builders, stale checks,
chat signal projections, and persistence identities use the exact source hash;
span matched-value and evidence-fingerprint normalization use the canonical
form. Contextual-predicate evaluation uses the comparison contract identified
and versioned by its registry entry.

Evidence construction keeps offsets in the original string. Before a finding
can be persisted, a strict validator checks:

- the evidence collection is non-empty and within the existing item cap;
- every item and nested match has the expected fields and finite evidence type;
- span-evidence offsets are ordered and in range, and nested matches lie inside
  their item span;
- unmasked saved-content `matched_text` equals the original source slice;
- span-producing chat matched-evidence hashes equal the source slice hash;
- contextual-predicate evidence has the registered predicate key/version, true
  outcome, required reference ID and exact reference source hash, and no span-
  only fields;
- rule IDs and evidence types agree with the active registry entry;
- display text and truncation markers remain within existing display limits;
- the supplied exact source content hash and evidence fingerprint recompute
  exactly.

Evidence fingerprints use canonical JSON with sorted keys and compact
separators. Span payloads contain the source field, finding type or chat
category, and sorted unique evidence-type/value pairs. Contextual-predicate
payloads contain the complete non-span evidence contract defined in requirement
2.3. Rule and scanner versions remain separate identity inputs so a registry
change produces a new durable identity even when the matched text or predicate
inputs are unchanged.

### 3.4 Persistent Provenance And Identity

The content-finding row keeps its existing review-case, risk, finding type,
priority, source field/hash, evidence, current/cleared, detection timestamps,
scanner version, and audit timestamps. Add explicit persistence for:

- scanner ID;
- taxonomy version;
- configuration hash;
- canonicalization and evidence format versions;
- target context and field purpose;
- matched rule IDs and versions;
- declared language/context limits;
- scan timestamp and execution duration;
- a deterministic finding identity hash.

The identity hash is SHA-256 over canonical JSON containing every durable
identity input listed in requirement 2.4. A partial unique index on review case
and identity hash enforces one current row for that identity. The existing
metadata object remains available only where the current response contract uses
it. New provenance must not be copied into response metadata merely for
convenience, and metadata is not an independent source of scanner truth.

Both chat-detection tables gain the same scanner/taxonomy/configuration/context
provenance plus `source_field`, `source_content_hash`,
`evidence_fingerprint`, bounded evidence, scan timestamp, execution duration,
and a deterministic detection identity hash. A unique constraint on message and
detection identity prevents duplicate rows. Existing category, severity,
rule-key, preview, and creation fields remain available to current callers.

Chat evidence uses a discriminated structure whose `evidence_kind` is `span` or
`context_predicate`. Span evidence requires offsets and a matched-source hash.
Contextual-predicate evidence requires its predicate and reference fields and
forbids every span-only field. Database checks enforce the finite discriminator
and JSON container shape; application validation enforces the kind-specific
field contract before persistence.

Database checks enforce lowercase SHA-256 shape, non-empty version and context
fields, non-negative duration, non-empty rule/evidence arrays, and valid JSON
container types. Application validation remains responsible for cross-field
semantics that cannot be expressed clearly as maintainable table checks.

### 3.5 Reconciliation And Concurrency

Saved-content surfacing uses one ordered transaction:

1. lock and load the current target aggregate in the accepted target-first
   order;
2. confirm that the content is still actionable and build the complete current
   field inventory;
3. run the deterministic scanner against that locked snapshot;
4. find or create the valid open content-moderation case under the existing
   one-open-case constraint;
5. lock current and historical findings in stable order;
6. match incoming and current rows by identity hash;
7. update only repeat-detection timestamps for exact current matches;
8. insert genuinely new identities and one attachment event each;
9. clear current rows absent from the complete field result and emit one clear
   event each;
10. recompute case priority from current findings and commit once.

If another transaction wins open-case or finding creation, rollback the whole
attempt, reacquire the target and case state, and reconcile once more from the
current locked snapshot. The retry does not reuse ORM objects or decisions from
the failed transaction.

The complete field inventory is important when a value becomes empty or a
field ceases to be applicable: an old current finding must not survive merely
because no incoming finding mentions that field. Historical rows are never
selected as update targets. Reappearance therefore follows the normal insert
path.

Chat detection remains inside message creation. The scanner result determines
the message review status and detection rows in the same transaction. After
commit, chat surfacing reads persisted detections and projects review-signal
metadata from their common provenance. Signal projection never recalculates
scanner identity, taxonomy, content hashes, or rule versions.

### 3.6 Compatibility And Change Discipline

The current rule expressions, category mappings, priorities, evidence caps,
field-purpose exclusions, supporting-only payment behavior, and contextual
repeated-message predicate become the initial versioned registry state.
Consolidation must be behavior-preserving, with comparison tests proving the
current finite examples, exclusions, latest-message selection, and exact
repetition comparison before old duplicated definitions are removed.

Admin review serialization continues to expose the existing response contract.
Current and previous findings remain determined by `current_match`; display
timestamps and structured evidence remain usable without frontend changes.
Chat services continue to create the same messages, notifications, reads, and
review statuses, with the new detection provenance added inside the existing
transaction.

Taxonomy changes follow the tracked owner and version rules. Historical rows
are not rewritten when a new taxonomy or scanner configuration ships. A rescan
under the new version creates new current identities and moves no-longer-current
identities to history through the normal reconciliation path.

## 4. Failures And Edge Cases

These cases protect attribution and history when content, configuration, or
concurrent execution changes around a scan.

1. **Registry definition is internally inconsistent**
   - **Condition:** A rule ID is duplicated, a profile references an unknown
     rule, a finite category is missing, or language/context limits are absent.
   - **Required behavior:** Reject the registry before scanning. Do not persist
     attribution-free or partially defined findings.

2. **Evidence offsets do not match source text**
   - **Condition:** An offset is negative, reversed, outside the original
     string, or does not identify the recorded match.
   - **Required behavior:** Reject the finding before persistence and roll back
     its reconciliation transaction.

3. **Display truncation changes identity**
   - **Condition:** The same underlying match produces a differently clipped
     display excerpt.
   - **Required behavior:** Compute identity from atomic matched evidence, not
     display text, so harmless display clipping does not create another finding.

4. **Identical scan repeats**
   - **Condition:** The same content is scanned again with the same complete
     scanner contract.
   - **Required behavior:** Keep one current row, advance only allowed repeat-
     detection timestamps, preserve original evidence/provenance, and emit no
     duplicate attachment event.

5. **Content changes but matched evidence is the same**
   - **Condition:** Surrounding text, letter case, or whitespace changes while
     the same normalized phone number, link, phrase, or other atomic evidence
     remains.
   - **Required behavior:** The changed exact source hash creates a new finding
     identity; the former row becomes historical with its evidence unchanged.

6. **Content becomes clean or a field becomes empty**
   - **Condition:** A previously matching scanned field no longer produces a
     finding.
   - **Required behavior:** Clear each affected current finding exactly once,
     retain it as previous evidence, and leave review-case closure to the
     existing review workflow.

7. **Historical evidence reappears**
   - **Condition:** Cleared matched evidence later appears again.
   - **Required behavior:** Insert a new current row and attachment event. Do not
     reactivate or overwrite the historical row.

8. **Scanner or taxonomy changes against unchanged content**
   - **Condition:** A rule version, taxonomy, configuration hash,
     canonicalization version, evidence format, or context changes.
   - **Required behavior:** Treat resulting matches as new identities and
     reconcile earlier current identities to history where they no longer
     represent the active scan contract.

9. **Content changes during reconciliation**
   - **Condition:** One request scans while another request updates the same
     Community Game, detail, or Need a Sub post.
   - **Required behavior:** Decide from the locked current aggregate. A stale
     pre-lock snapshot must neither attach nor clear findings.

10. **Concurrent identical reconciliation races**
    - **Condition:** Independent PostgreSQL sessions attempt to create the same
      open case or current finding.
    - **Required behavior:** Commit one current finding and one event. The losing
      transaction rolls back, rereads under lock, and converges without partial
      writes.

11. **Case was closed before a scan reconciles**
    - **Condition:** A scanner invocation reaches a case that is no longer open.
    - **Required behavior:** Do not mutate that case or its findings. If the
      target remains actionable and risky, use the existing open-case creation
      rules without reopening the closed case.

12. **Finding persistence fails**
    - **Condition:** Evidence validation, a database constraint, or the commit
      fails after reconciliation begins.
    - **Required behavior:** Roll back all finding and case-event changes from
      that attempt. Durable timeout, outage, retry-exhaustion, backlog, and
      operator failure states are not invented by this pass.

13. **Contextual-predicate evidence is incomplete or masquerades as a span**
    - **Condition:** A repeated-message detection lacks its registered predicate
      version or prior-message reference/hash, records a false outcome, or
      supplies offsets, matched text, or a matched-substring hash.
    - **Required behavior:** Reject the detection before persistence. Do not
      fabricate a match location for a relationship between two messages.

## 5. Testing

Testing must prove that scanner definitions are finite and attributable, that
evidence points to the content actually scanned, and that PostgreSQL preserves
one truthful current state under edits and races.

### 5.1 Taxonomy And Pure Scanner Tests

Registry tests must cover every current saved-content and chat rule exactly
once and verify unique IDs/versions, finite category parity, enabled contexts,
field-purpose exclusions, language limits, supporting-only behavior, evidence
types, execution kinds, priorities, and deterministic configuration hashes.
They must prove that regex and contextual-predicate definitions are mutually
exclusive and that changing any repeated-message selection, ordering,
eligibility, normalization, or comparison setting changes the configuration
hash.

Pure scanner tests must preserve the current positive and negative behavior for
Community Game fields, Need a Sub fields, game chat, Need a Sub chat, and the
repeated-message signal. They must also cover empty input, collapsed whitespace,
case folding, punctuation trimming, overlapping email/link matches, payment
support without a core pressure phrase, and field-purpose exclusions. The pure
chat evaluator must emit the repeated-message rule only from a complete true
typed predicate fact and must emit no result for an absent or false fact.

Canonicalization and evidence tests must use controlled clocks and durations.
They must prove stable hashes and fingerprints, compact deterministic JSON,
raw-string half-open offsets with multibyte Unicode characters, exact source
slices, distinct exact source hashes for case-only and whitespace-only edits,
stable normalized fingerprints where appropriate, evidence item and display
caps, and rejection of malformed or tampered evidence. Non-span tests must prove
that the repeated-message fingerprint is bound to both exact message hashes,
the prior message ID, and the predicate version; that it changes when any of
those inputs changes; and that its evidence contains no offset or matched-text
field.

### 5.2 Saved-Content PostgreSQL Lifecycle Tests

PostgreSQL-backed tests must exercise both Community Game and Need a Sub target
adapters. They must prove complete provenance persistence, one current finding
for an identical rescan, no duplicate attachment event, clean-edit clearing,
same-evidence/different-content replacement, configuration-version replacement,
unchanged historical evidence, reappearance as a new row, and priority derived
only from current findings.

Rejected or failed reconciliation must prove that no partial finding or case-
event effects committed. Closed-case scans must leave the closed case and its
findings unchanged.

Independent-session tests must force duplicate open-case/finding creation and a
source-edit/reconciliation race at deterministic barriers. They must assert the
winning persisted state, event count, stale-row disposition, and absence of
deadlock or stale-snapshot mutation without relying on sleeps.

### 5.3 Chat Detection Tests

Game-chat and Need a Sub chat tests must prove that each detection stores the
same complete provenance contract, source field/hash, bounded evidence,
fingerprint, and execution metadata. Category, severity, safe preview,
review-status, notification, read, and rate-limit behavior must remain
compatible.

Tests must cover multiple matches in one message, a repeated-message detection,
safe previews for phone/email/link evidence, unique detection identity, and
rollback when a detection row cannot be persisted. Review-signal projection
must use the persisted detection provenance and must not expose raw rule
expressions or introduce a second scanner version.

Both chat domains must prove the repeated-message reference query selects only
the latest visible text message from the same sender and chat, uses creation
time then message ID as its deterministic ordering, excludes the candidate when
applicable, and preserves exact `strip().casefold()` equality. Different senders
or chats, non-text or non-visible messages, a different latest body, and an
absent prior message must not produce the detection. Persistence tests must
assert the contextual-predicate discriminator, prior-message ID/hash, safe
whole-message preview, lack of span fields, and rejection of mixed or incomplete
predicate evidence.

### 5.4 Schema, Migration, And Compatibility Tests

Schema tests must prove model/migration parity, named checks and uniqueness,
hash-shape rejection, non-negative duration, valid JSON container requirements,
and the current/cleared finding invariant. Migration validation must build the
approved dedicated migration database from base to head and back through the
normal isolated rehearsal path.

Focused compatibility tests must verify existing admin review serialization and
current/previous grouping, both chat creation workflows, accepted admin and
relationship authorization contracts, chat rate-limit side effects, and the
one-open-content-case behavior. The full trusted backend suite must then confirm
that no unrelated API, database, payment, notification, or lifecycle contract
regressed.

No provider, browser, final-hosting, or production-runtime test is needed for
this deterministic backend and PostgreSQL result.

## 6. Done When

This checklist defines the engineering completion bar for the pass.

- [ ] One validated, versioned taxonomy registry governs every current saved-
      content and chat-message moderation rule.
- [ ] The tracked taxonomy record names ownership, supported contexts,
      language limitations, active versions, and version-change rules.
- [ ] Every persisted finding and chat detection records complete immutable
      scanner, rule, configuration, context, canonicalization, evidence, and
      execution provenance.
- [ ] Content hashes, applicable span offsets, evidence fingerprints, and
      identity hashes recompute under explicit versioned contracts; contextual
      predicate evidence remains attributable without fabricated spans.
- [ ] Exact rescans deduplicate, edits clear or replace current findings, and
      historical or reappearing evidence is preserved correctly.
- [ ] Target-first locking and database uniqueness make concurrent scans
      converge without stale current findings, duplicate events, or partial
      writes.
- [ ] SQLAlchemy models and canonical migrations agree and a clean database
      rebuild produces the complete constrained schema.
- [ ] Existing admin review, chat, authorization, notification, and rate-limit
      behavior remains compatible.
- [ ] Focused pure, PostgreSQL, independent-session, migration, and compatibility
      tests pass and protect the complete taxonomy/finding-evidence contract.
