# WS09-02 Intake - Administrative Auditability

## 1. What Needs To Be Decided

This intake decides whether administrative auditability can be delivered as one
engineering pass or needs coherent executable children. The decision matters
because the reusable audit foundation is a prerequisite for `WS03-05D`, while
some sensitive-read consumers do not exist until that later moderation work is
implemented.

The parent work is `WS09-02 - Administrative Auditability`. It must harden the
existing administrative audit behavior so important privileged activity is
attributable, durable, append-only or tamper-resistant, safe to inspect, and
appropriately applied to especially sensitive staff reads without creating a
second universal audit store or a new investigation/search/export product.

## 2. What We Know

This section records the facts that determine the executable shape. They show
which audit guarantees can be established immediately and which coverage work
has a different dependency or failure model.

| Topic | Current fact or constraint | Why it affects execution |
|---|---|---|
| Existing audit foundation | `AdminAction` is the established cross-domain audit record and has a central action policy, typed target references, safe metadata handling, scoped list/detail reads, and writers across current admin domains. Current policy contains 60 action types. | The surviving work must harden and reuse this system rather than create a parallel universal ledger. |
| Missing canonical fields | `AdminAction` records actor, action, targets, reason/context, idempotency key, and database time, but have no explicit outcome or correlation identifier. | The reusable record contract is incomplete and must be corrected before new sensitive-read consumers rely on it. |
| Append-only gap | Application routes expose no normal update/delete operation, but the `admin_actions` table has no database guard against update or delete. Existing narrow rejected-attempt records also have no database immutability guard. | Append-only behavior is currently a convention rather than a durable invariant; foundation hardening is independently necessary. |
| Existing writer compatibility | Most domain writers add `AdminAction` in the owning transaction, but current refund, review-case, and financial-outcome paths can amend an audit object after it is added or flushed, and one refund checkpoint updates a previously committed audit row. | Database immutability cannot be enabled honestly without first preserving current workflows through a final-at-insert audit contract. This belongs with foundation hardening, not later coverage expansion. |
| Current mutation coverage | Important official-game, roster, user, money, moderation, notice, review, and storage workflows already call the central audit writer, while rejected attempts and some provider/failure outcomes also have narrow durable domain records. | Coverage reconciliation is cross-domain consumer work. It must use the hardened contract and must not duplicate every denial or provider failure into `AdminAction`. |
| Sensitive-read state | No `AdminAction` policy or service contract currently records a sensitive administrative read. Current admin surfaces can expose private chat content and detailed financial information, while `WS03-05D` still owns excerpt-first moderation responses, controlled full-content reveal, cache behavior, and its domain-specific audit emission. | Sensitive-read auditing has a distinct fail-closed disclosure model and cannot be completed before the reusable foundation and `WS03-05D` consumer exist. |
| Audit access | Current audit list/detail routes require the binary active-admin guard. The current product authority does not permit reintroducing moderator roles or named permissions. | Restricted audit access can be hardened within the reusable foundation while preserving the accepted active-admin model. |
| Accepted prerequisites | `EN-02`, `WS03-04`, `WS04-02A/B/C`, and `WS03-05A/B/C` are accepted. OPP-11 approves append-only, access-restricted audit records and linked follow-up corrections. | Schema, transaction, correlation/redaction, authorization, and policy inputs needed by the foundation are available. `WS03-05D` is not a prerequisite for that foundation. |
| Infrastructure timing | The required source, PostgreSQL invariant, service, and deterministic evidence work is provider-independent. Final concrete production database roles/grants remain owned by `WS04-01D` and provider/control-plane access evidence remains later-owned. | No final-infrastructure split or provider prerequisite blocks the current executable child. Temporary demo-provider facts are neither needed nor accepted as proof. |
| Execution register | Current Git truth at `31d3db4b2320a5656a081ac8f7bdc206c0b3cf7e` includes merged `WS03-05B` and `WS03-05C`, but the register still reports B as unmerged and C as remaining. | The factual reconciliation must travel with substantive WS09-02 work, not become a tracker-only pass. |

## 3. Execution Decision

This section states the selected execution shape and why it is necessary. The
parent is split because its foundation, privileged-mutation coverage, and
sensitive-read coverage have different prerequisites and failure/evidence
models, while each leaves a safe independently useful result.

Outcome: split `WS09-02` into three executable children.

| Order | Work | Depends on |
|---:|---|---|
| 1 | `WS09-02A - Reusable append-only administrative audit foundation` | Accepted `EN-02`, `WS03-04`, `WS04-02A/B/C`, `WS03-05A/B/C`, and OPP-11 |
| 2 | `WS09-02B - Important privileged-mutation audit coverage` | Accepted `WS09-02A` |
| 3 | `WS09-02C - Sensitive administrative-read audit coverage` | Accepted `WS09-02A` and `WS03-05D` |

`WS09-02A` is the earliest coherent executable work. It hardens the one
reusable audit record and access contract used by existing mutation writers and
future sensitive-read consumers. It is useful immediately because it makes
current records tamper-resistant and preserves atomic mutation recording, and
it unblocks `WS03-05D` without claiming that all audit consumers are complete.

After A is accepted, B and `WS03-05D` have separate consumer work and may be
selected from their actual dependency state. C waits for `WS03-05D` because D
owns the moderation response/reveal behavior and domain-specific emission;
C owns the remaining cross-domain sensitive-read audit coverage and parent
accounting, not D's privacy behavior.

### Cohesion Results

The whole parent does not pass the cohesion test. This is an engineering split,
not a size-only split.

| Cohesion question | Whole-parent verdict | Split implication |
|---|---|---|
| One primary outcome | Partial - all work serves administrative auditability, but it delivers a reusable invariant, mutation attribution, and disclosure accountability as independently useful outcomes. | Separate foundation and consumer outcomes. |
| One coherent requirement/invariant family | No - immutable record construction, mutation atomicity, and sensitive-read fail-closed disclosure have different invariants. | Keep the three invariant families separate. |
| One prerequisite state | No - A is ready now, B requires A, and C also requires the not-yet-implemented `WS03-05D`. | A split is required by the workflow cohesion rule. |
| One safe merge/rollback or forward-fix unit | No - delaying append-only hardening until D exists leaves current audit rows mutable, while merging read consumers before the durable foundation would permit unaudited disclosure. | Foundation must merge first; consumers follow only when safe. |
| One coherent evidence model | No - A needs model/migration/transaction/access proof, B needs cross-domain mutation proof, and C needs disclosure/read-audit proof. | Use three evidence boundaries. |
| One semantic review model | No - A reviews record integrity, B reviews privileged state attribution, and C reviews sensitive disclosure accountability. | Use three semantic review boundaries. |
| Safe and useful intermediate state | Yes - A hardens current audit records and provides the reusable contract; B closes current mutation coverage; C closes sensitive-read coverage after D. | Every child is independently acceptable while the parent remains open until all three are accepted. |

Each child is cohesive on its own:

| Cohesion question | `WS09-02A` | `WS09-02B` | `WS09-02C` |
|---|---|---|---|
| One primary outcome | Yes - one reusable tamper-resistant audit foundation. | Yes - attributable important privileged mutations. | Yes - attributable especially sensitive staff reads. |
| One coherent requirement/invariant family | Yes - final-at-insert records, canonical fields, durability, access restriction, and append-only correction behavior. | Yes - current privileged workflows either record atomically or have an explicit non-duplicative durable disposition. | Yes - sensitive content is not disclosed unless the authorized access is durably recorded. |
| One prerequisite state | Yes - all prerequisites are accepted. | Yes - begins after A. | Yes - begins after A and `WS03-05D`. |
| One safe merge/rollback or forward-fix unit | Yes - schema, writer compatibility, and access guarantees move together. | Yes - consumer coverage can be changed without weakening the accepted foundation. | Yes - read-audit consumers move with their fail-closed disclosure behavior. |
| One coherent evidence model | Yes - PostgreSQL, service transaction, API access, and compatibility evidence. | Yes - finite current privileged-action inventory plus focused domain behavior. | Yes - sensitive-read authorization, durability, redaction, and response behavior. |
| One semantic review model | Yes - can persisted audit truth be rewritten, omitted, or exposed improperly? | Yes - can an important privileged mutation succeed without attributable audit truth or create duplicate noise? | Yes - can especially sensitive data be revealed without a safe durable access record? |
| Safe and useful intermediate state | Yes - protects existing writers and unblocks D. | Yes - closes mutation coverage while sensitive-read work remains explicit. | Yes - completes the remaining read-coverage outcome without adding an audit product. |

## 4. Where The Parent Work Goes

This section accounts for every surviving parent responsibility. Shared edges
are named explicitly so that the children reuse one contract without claiming
the same implementation work.

| Parent work | Goes to | Remaining boundary |
|---|---|---|
| Append-only or tamper-resistant administrative audit records | `WS09-02A` | Harden the existing `AdminAction` system and retained narrow rejected-attempt records; do not create a second universal store. |
| Canonical actor, action, target/reference, time, explicit outcome, bounded reason/context, and correlation contract | `WS09-02A` | A owns the reusable schema/service contract; B and C populate it for their consumers. |
| Atomic recording for privileged mutations and explicit audit-write failure semantics | `WS09-02A` for the mechanism and existing writer compatibility; `WS09-02B` for current important consumer coverage | A does not claim every privileged workflow is covered merely because a helper exists. |
| Durable fail-closed recording before especially sensitive content is returned | `WS09-02A` for the reusable mechanism; `WS09-02C` for cross-domain consumer coverage | `WS03-05D` owns its moderation response minimization, reveal decision, no-store behavior, and domain-specific audit emission. |
| Important privileged-action coverage | `WS09-02B` | Reconcile the accepted current surface; future passes that add privileged actions must consume the accepted audit contract within their own domain scope. |
| Denial, conflict, and provider-failure attribution | `WS09-02B` | Reuse `AdminRejectedAttempt` and authoritative domain histories where they already preserve truthful outcomes; do not duplicate every failure in `AdminAction`. |
| Sensitive-read auditing where private messages or detailed financial data are exposed | `WS09-02C`, consuming `WS03-05D` for moderation-specific behavior | Audit only actual sensitive disclosure, with safe metadata rather than copied content or detailed financial data. |
| Restricted audit lookup/access | `WS09-02A` | Preserve binary active-admin authorization; no moderator/named-permission hierarchy or new audit investigation UI. |
| Linked append-only corrections | `WS09-02A` | Preserve correction-by-follow-up capability without restoring retired generic mutation UI or building an export product. |
| Factual register reconciliation for merged `WS03-05B` and `WS03-05C` | Substantive `WS09-02A` change set | Update accepted/current/remaining state and directly affected counts in the execution register; no tracker-only pass. |
| Audit retention, archival, deletion/anonymization, legal holds, and export process | `WS10-01` and later operational/legal ownership under OPP-11 | Exact durations, archive technology, hold process, and export process are intentionally not invented by WS09-02. |
| Final production database roles/grants and provider control-plane access proof | `WS04-01D` and `WS10-02` | WS09-02 supplies provider-independent schema and behavior; temporary provider settings are not final proof. |
| High-risk audit alerts and operational monitoring | `WS09-03` | WS09-02 records safe attributable truth but does not create dashboards or alert proliferation. |

The allocation is complete: A owns the reusable store and recording/access
guarantees, B owns current mutation consumers, and C owns current sensitive-read
consumers outside D's already assigned moderation behavior. Their only overlap
is deliberate contract consumption and compatibility regression coverage.

## 5. What Happens Next

This section identifies the first executable result and any genuine blocker.
It distinguishes the ready foundation from later consumers whose prerequisites
are not yet accepted.

`WS09-02A - Reusable append-only administrative audit foundation` is the first
executable unit. Its authorization, transaction, PostgreSQL, correlation,
redaction, and policy prerequisites are accepted, and its implementation does
not require final hosting/provider facts.

There is no blocker to planning A. `WS09-02B` waits only for A.
`WS09-02C` waits for A and `WS03-05D`; after A is accepted, D can use the
foundation to implement its controlled sensitive-access behavior. The missing D
consumer does not block A and is not a reason to weaken or postpone current
append-only guarantees.

## 6. Internal Record

| Detail | Value |
|---|---|
| Parent pass | `WS09-02 - Administrative Auditability` |
| Stage 0 outcome | Decompose into three executable children |
| Accepted baseline | `31d3db4b2320a5656a081ac8f7bdc206c0b3cf7e` |
| Working branch | `pr/WS09-02` |
| Intake path | `docs/production-readiness/planning/passes/ws09/ws09-02-intake.md` |
| Authority sources | `docs/production-readiness/00-READ-ME-FIRST.md`; `docs/production-readiness/01-PROGRAM-CONTEXT.md`; corrected master sections 5.11 and 8.7; implementation workflow section 6; current accepted repository truth |
| Supporting sources | OPP-11 in approved Decision Packet 4; current admin audit policy; accepted `EN-02`, `WS03-04D`, `WS03-05` intake and A/B/C artifacts; accepted `WS04-02A/B/C`; applicable backend, database, and testing standards |
| Execution-register state | Stale after merged PR #178. Current Git truth is 41 accepted executable passes, 0 implemented-but-unmerged passes, and 26 genuinely unimplemented corrected-master units; `WS03-05A/B/C` are accepted and only `WS03-05D` remains from that parent. |
| Register reconciliation owner | The substantive `WS09-02A` pass must update the register for merged `WS03-05B` and `WS03-05C`, including the reconciliation SHA, current-state text, accepted/unmerged/remaining counts, accepted executable table, WS03-05 parent/dependency text, and other directly affected summaries. It must not be split into tracker-only work. |
| Child dependency graph | `WS09-02A -> WS09-02B`; `WS09-02A -> WS03-05D -> WS09-02C` |
| Selected executable child | `WS09-02A - Reusable append-only administrative audit foundation` |
| Exact capability supplied to `WS03-05D` | One canonical `AdminAction`-based service and persistence contract that creates a redaction-safe record containing the authenticated admin actor, sensitive-read action, typed target/reference, database time, explicit outcome, optional bounded reason/context, and current correlation identifier; prevents ordinary update/delete of persisted audit truth; restricts audit lookup to active admins; commits the read-audit record before full sensitive content is returned; and fails the disclosure closed if durable recording cannot complete. |
| Provider/runtime classification | All A/B/C source work is provider-independent. Final concrete DB role/grant proof remains `WS04-01D`-owned and provider/control-plane access proof remains `WS10-02`-owned; no new WS09-02 deferred infrastructure child is created. |
| Expected evidence layers for A | Source/model/migration inspection, real PostgreSQL immutability and transaction evidence, service failure/compatibility evidence, and focused API authorization/response evidence. |
| Non-goals | A new universal audit store; duplicate audit rows for every denial/provider failure; moderator or named permissions; raw sensitive content in audit metadata; audit search/export/investigation product; retention/archive/legal-hold design; dashboards/alerts; final-provider configuration or proof. |
| Proposed Gate A plan path | `docs/production-readiness/planning/passes/ws09/ws09-02a-reusable-append-only-administrative-audit-foundation.md` |
| Blockers | None for `WS09-02A`; `WS09-02C` is prerequisite-blocked until both A and `WS03-05D` are accepted. |
| Exact next allowed action | Stop after Stage 0. Begin Gate A for `WS09-02A` only when separately authorized; do not begin planning or implementation in this run. |
