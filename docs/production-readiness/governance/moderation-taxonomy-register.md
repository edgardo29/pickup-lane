# Moderation Taxonomy Register

Status: Active repository-owned contract for `WS03-05A`.

Primary controls: `ADM-009`, `ADM-010`.

Accountable role: Identity and application security, held by Project owner
(interim) under the Production Ownership Register.

## Purpose

This register publishes the governed identity and change rules for Pickup
Lane's deterministic moderation taxonomy. The executable source of current rule
behavior is `backend/services/moderation_taxonomy.py`; this record names its
ownership, supported contexts, limits, and version policy without duplicating
raw expressions or user evidence.

This is a repository-owned source contract. It is not provider, deployment,
runtime, policy-enforcement, notice-delivery, reviewer-state, or production
monitoring evidence.

## Active Contract

| Field | Active value |
|---|---|
| Scanner ID | `pickup-lane-deterministic-moderation` |
| Scanner version | `3` |
| Taxonomy version | `1` |
| Canonicalization version | `span-trim-collapse-casefold-v1` |
| Evidence format version | `1` |
| Scanner profiles | `saved_content`, `chat_message` |
| Registered rules | 23 unique stable rule IDs; 14 saved-content regex rules, 8 chat regex rules, and 1 contextual-predicate chat rule |
| Saved-content contexts | `community_game`, `need_a_sub` |
| Chat contexts | `game_chat`, `need_a_sub_chat` |
| Evidence kinds | `span`, `context_predicate` |

Every persisted finding or detection records the applicable scanner, taxonomy,
configuration, canonicalization, evidence-format, rule, target-context,
declared-limit, scan-time, and execution-duration provenance. The behavior-
bearing profile configuration is serialized as deterministic compact JSON and
identified by SHA-256.

## Context And Field Boundary

The saved-content profile scans only the authoritative current Community Game
and Need a Sub field inventories declared in the taxonomy source. Every field
has an explicit purpose: general, payment, payment method, location, or address.
Purpose-specific exclusions are part of the behavior-bearing configuration.

The chat profile scans only `message_body` in game chat and Need a Sub chat.
Its repeated-message rule is a contextual predicate over the latest visible
text message from the same sender and chat, ordered by creation time and then
message ID. Its evidence identifies the predicate and referenced message/hash;
it never fabricates a text span.

Adding a context or field is not implicit. It requires a reviewed taxonomy
change, corresponding ownership and field-purpose classification, configuration
identity update, and trusted evidence.

## Language And Capability Limits

- Structured phone, email, URL, handle, and other format matches are treated as
  language-independent only within their registered deterministic patterns.
- Phrase-based rules are English-only in the active taxonomy.
- The scanner is a bounded deterministic rule system. It is not a semantic,
  machine-learning, provider, or general-language moderation classifier.
- Saved-content evidence is bounded to eight items, with registered entity and
  phrase display limits.
- Chat evidence is one item per detection with a bounded safe preview.
- Repeated-message behavior is limited to the registered same-sender,
  same-chat, latest-visible-text comparison contract.

These limits are persisted as declared provenance. They are not claims of
comprehensive abuse, safety, language, or policy coverage.

## Version And Change Rules

Every behavior-bearing change produces a new profile configuration hash. The
following named versions also change when their owned contract changes:

| Change | Required version action |
|---|---|
| One rule's expression, flags, predicate selection/order/eligibility/comparison, outcome, priority, evidence type, purpose, context, supporting-only behavior, or language scope changes | Increment that stable rule's version. Do not silently reuse its prior version. |
| Rules are added, removed, enabled, disabled, or remapped; profile context/field inventory or taxonomy-wide classification changes | Increment the taxonomy version and affected rule versions where rule behavior changed. |
| Scanner orchestration or evaluation semantics change beyond a single registered rule | Increment the scanner version. |
| Source-span trimming, normalization, comparison, or fingerprint canonicalization changes | Create and activate a new canonicalization version. |
| Persisted evidence discriminator, required fields, interpretation, or validation contract changes | Increment the evidence format version. |
| Evidence limits or declared capability/language limits change | Produce a new configuration hash and increment any taxonomy, rule, scanner, canonicalization, or evidence version whose owned semantics changed. |

Historical persisted provenance and evidence remain immutable. A new active
version must not rewrite old findings or detections to look as though they were
produced under the new contract.

## Review And Evidence Duties

The Identity and application security owner approves taxonomy behavior,
context, purpose, language-limit, and version changes. The Database owner
reviews persistence and migration compatibility. The Quality and release
assurance owner reviews trusted rule parity, evidence validation, lifecycle,
concurrency, schema, migration, and compatibility proof. Those role hats may be
held by the same interim project owner but remain separate responsibilities.

Changes must update this register when its published contract changes, preserve
stable attribution, and include current requirement/test evidence. This record
must never contain raw user content, private chat material, secrets, provider-
private values, or unredacted production evidence.
