# WS03-05 Intake - Moderation States, Safe Notices, And Minimum-Necessary Admin Data

## 1. What Needs To Be Decided

This intake decides whether Pickup Lane's moderation-state, enforcement-notice,
and sensitive administrative-data work can execute as one engineering result or
must be divided before detailed planning begins. The decision matters because
the parent combines several sequential state machines with a separate privacy
boundary whose secure completion requires an audit capability not needed by all
moderation work.

The parent engineering work is `WS03-05 - Moderation states, safe notices, and
minimum-necessary admin data`. It covers versioned moderation findings,
content-bound evidence, conflict-safe review cases, action-scoped enforcement,
safe user notices, and excerpt-first administrative access with controlled
unmasking, anti-caching, restricted export, and sensitive-read auditing.

## 2. What We Know

This section contains the technical facts and accepted dependencies that change
how the parent should execute. The facts distinguish work that can proceed from
current repository contracts from work that requires a later responsibility-
specific capability.

| Topic | Current fact or constraint | Why it affects execution |
|---|---|---|
| Parent responsibility families | The parent owns seven controls: `ADM-009` and `ADM-010` govern moderation taxonomy and finding evidence; `ADM-012` governs review-case state; `ADM-013` and `ADM-014` govern enforcement and safe notices; `ADM-007` and `ADM-015` govern task-scoped sensitive administrative access and minimum-necessary data. | These controls form a sequence, but they do not share one invariant family, implementation boundary, or prerequisite state. |
| Accepted authorization foundation | `WS03-04` is complete. Its accepted admin/high-risk work proves current route authorization and state binding while explicitly leaving moderation taxonomy, safe notices, minimum-necessary admin data, controlled unmasking, and read auditing to this parent and WS09 as applicable. | WS03-05 can preserve accepted authorization behavior without reopening the authorization parent, while still implementing its distinct moderation and privacy controls. |
| Accepted database contracts | The applicable `WS04-02` transaction, invariant, lock-order, and PostgreSQL compatibility contracts are accepted. | Finding identity, case transitions, enforcement, and idempotency can be planned against settled transaction rules rather than waiting for another database parent to complete. |
| Current finding system | Current source has a deterministic scanner, finding types and priorities, scanner version, content hashes, evidence fingerprints, offsets, current/stale state, and review-case linkage. It does not yet provide the complete governed taxonomy/configuration record, canonicalization identity, language/context limits, execution-time record, or complete cross-representation lifecycle required by `ADM-009` and `ADM-010`. | The finding and evidence lifecycle is a coherent first result that can be corrected without simultaneously changing reviewer assignment, enforcement, notices, or sensitive-read presentation. |
| Current review-case system | Current review cases provide open/closed state, notes, outcomes, events, idempotent note/close operations, row locking, and one-open-case behavior for selected moderation targets. Assignment, reopen, general merge behavior, and complete concurrent-review semantics are not present. | Review-case lifecycle is a separate state-machine result that consumes stable finding identity and can be reviewed independently before enforcement is expanded. |
| Current enforcement and notices | Current moderation and account-support actions already use several state checks, idempotency keys, action records, reversals, targeted notices, and in-app notifications, but behavior is spread across action families. Authorization remains broadly admin-based in important paths, notice coverage is asymmetric, and delayed/suppressed notice state and review-next-step handling are incomplete. | Enforcement and its user notice must be reconciled together so an action cannot land with an unsafe, contradictory, or silently missing notice outcome. This work should follow the accepted review-state contract. |
| Approved notice direction | OPP-03 is approved: notices follow enforcement by default, contain only a safe general explanation and next step, protect reporters and internal detection/security details, and require a structured reason when delayed or suppressed. A basic manual review is available when appropriate. | The governing owner decision exists, so safe-notice source work is not blocked on a new parent-level decision. Detailed implementation must remain within that approved direction. |
| Current sensitive-data exposure | Administrative chat responses return full message bodies by default, review-case detail returns finding evidence and operational context, and the current admin UI renders that content directly. Current source has no controlled-unmask flow, systematic sensitive-read audit, or systematic private-response `no-store` contract for these surfaces. | Minimum-necessary administrative access is a backend, API, UI, privacy, and audit result, not a small extension of the moderation state machines. |
| Audit capability boundary | WS03-05 owns the domain rules for which moderation data is visible, excerpted, unmasked, exported, or denied and which sensitive-access events must be emitted. `WS09-02` owns the reusable append-only administrative audit capability, restricted audit access, and final append-only evidence. That reusable capability is not yet accepted. | Enabling controlled unmasking without the required durable audit behavior would be unsafe. The audit dependency applies to the sensitive-access result only; it must not block finding, review, enforcement, or safe-notice work, and it does not require WS09-02 parent completion. |
| Durable notice boundary | `WS05-01A` provides the accepted provider-independent job and transactional-handoff foundation. WS03-05 owns moderation/notice policy and the source contract that produces a safe notice outcome; `WS05-03` owns later durable notice delivery, retry, repair, and reconciliation responsibilities that consume that contract. | The accepted job foundation may be consumed where the selected notice design needs it, but WS05-03 parent completion is not a prerequisite for defining and implementing the WS03-owned moderation/notice contract. |
| Current trusted evidence | Accepted trusted evidence covers the preceding authorization and durable-job contracts, but no `ws03_05*.json` requirement declaration or trusted WS03-05 scope exists. | Each executable child needs its own requirement and evidence boundary; current tests cannot be treated as proof that this parent is already complete. |
| Infrastructure timing | The parent work is repository-owned schema, domain, API, UI, and privacy behavior that can be implemented and tested with synthetic data and PostgreSQL. It does not require selection of final hosting, database hosting, monitoring, or provider topology. | No mandatory final-infrastructure follow-up is needed under this parent. Later staging, operational, and centralized audit evidence remains with its established owners. |

## 3. Execution Decision

This section states the chosen execution shape and the technical reason for it.
WS03-05 should be split into four executable passes with an ordered dependency graph.

Outcome: split the parent into executable child passes.

| Order | Work | Depends on |
|---|---|---|
| `1` | `WS03-05A - Versioned moderation taxonomy and finding-evidence lifecycle` | Accepted `WS03-04` authorization boundaries and applicable `WS04-02` transaction/invariant contracts |
| `2` | `WS03-05B - Conflict-safe moderation review-case lifecycle` | Accepted `WS03-05A` finding/evidence contract and applicable `WS04-02` transaction/invariant contracts |
| `3` | `WS03-05C - Action-scoped moderation enforcement and safe-notice contract` | Accepted `WS03-05B`, approved OPP-03 notice direction, and the accepted `WS05-01A` job/handoff capability only where the selected notice design consumes it |
| `4` | `WS03-05D - Minimum-necessary admin data and audited sensitive access` | Accepted `WS03-05B` review-case contract and the applicable accepted reusable append-only audit capability produced under `WS09-02`; neither WS09-02 parent completion nor unrelated WS09-02 domain coverage is required |

A makes findings and their evidence stable enough to review. B makes reviewer
state and concurrent decisions stable enough for both downstream enforcement and
sensitive administrative access. C then applies action-scoped enforcement and
produces the safe-notice contract consumed by later delivery work. D is a separate
privacy consumer of the accepted finding/review contracts and permits controlled
sensitive access only when the required reusable audit capability is available.
D does not consume C's enforcement or notice contract, so C is not a prerequisite
for D.

The cohesion assessment confirms that one parent-sized executable pass would be
unsafe and difficult to review:

| Engineering question | Verdict | Effect on execution shape |
|---|---|---|
| One primary outcome | No - finding integrity, reviewer workflow, enforcement/notices, and sensitive access are independently meaningful outcomes. | Split. |
| One requirement family | No - the parent combines evidence identity, case-state transitions, enforcement side effects, notice safety, and privacy/data-access invariants. | Split. |
| One prerequisite state | No - A through C can proceed from accepted contracts, while D additionally requires the reusable append-only audit capability. | Split required. |
| One safe merge or forward-fix unit | No - combining scanner/finding schema, case transitions, many enforcement families, notice behavior, response minimization, unmasking, cache policy, and admin UI changes would create unrelated rollback risks. | Split required. |
| One evidence model | No - the children require distinct finding-history, concurrency/state-machine, enforcement/notice, and sensitive-response/audit proof. | Split. |
| One semantic review model | No - reviewers must answer four different questions: whether evidence remains attributable, cases resolve safely, enforcement/notices remain truthful, and sensitive reads expose only what is authorized. | Split. |
| Safe and useful intermediate state | Yes - each child leaves a coherent accepted contract for its consumer while the parent and later obligations remain explicitly open. | Ordered children are appropriate. |

Each proposed child also satisfies the executable-pass cohesion test on its own.
The checks below confirm that the split does not merely make the parent smaller;
each child leaves a coherent result that can be accepted independently.

#### WS03-05A cohesion

| Engineering question | Verdict and reasoning | Split implication |
|---|---|---|
| One primary outcome | Yes - establish stable moderation taxonomy and finding/evidence identity. | Keep A whole. |
| One coherent requirement/invariant family | Yes - `ADM-009` and `ADM-010` both govern attributable, versioned moderation findings and evidence lifecycle. | No further split. |
| One prerequisite state | Yes - accepted WS03-04 authorization and applicable WS04-02 transaction/invariant contracts are sufficient. | No blocked sub-scope. |
| One safe merge or forward-fix unit | Yes - taxonomy/finding identity and evidence-history changes form one source/schema compatibility boundary. | No rollback-driven split. |
| One evidence model | Yes - proof centers on stable finding identity, versioning, stale detection, rescans, and historical attribution. | One evidence boundary. |
| One semantic review model | Yes - review asks whether moderation findings remain correctly attributable to the content and scanner/configuration that produced them. | One review boundary. |
| Safe and useful intermediate state | Yes - B can consume A's accepted finding/evidence contract without requiring review-case or enforcement changes in A. | A is independently acceptable. |

#### WS03-05B cohesion

| Engineering question | Verdict and reasoning | Split implication |
|---|---|---|
| One primary outcome | Yes - establish a conflict-safe moderation review-case lifecycle. | Keep B whole. |
| One coherent requirement/invariant family | Yes - `ADM-012` governs review-case state, transitions, concurrency, assignment, merge/reopen, and resolution behavior. | No further split. |
| One prerequisite state | Yes - B consumes accepted A finding identity plus applicable WS04-02 transaction/invariant contracts. | No blocked sub-scope. |
| One safe merge or forward-fix unit | Yes - case-state and concurrency behavior must move together to avoid incompatible reviewer transitions. | Do not split state from concurrency. |
| One evidence model | Yes - proof centers on case transitions, stale decisions, one-case/merge behavior, and concurrent review outcomes. | One evidence boundary. |
| One semantic review model | Yes - review asks whether reviewer actions produce one valid, attributable case outcome under conflict and concurrency. | One review boundary. |
| Safe and useful intermediate state | Yes - accepted review-case behavior can be consumed independently by C and D. | B is independently acceptable. |

#### WS03-05C cohesion

| Engineering question | Verdict and reasoning | Split implication |
|---|---|---|
| One primary outcome | Yes - make moderation enforcement action-scoped and pair each action with a safe notice outcome. | Keep C whole. |
| One coherent requirement/invariant family | Yes - `ADM-013` enforcement correctness and `ADM-014` safe-notice behavior are coupled because an enforcement action must not produce an unsafe, contradictory, or silently missing notice outcome. | Keep enforcement and notice semantics together. |
| One prerequisite state | Yes - C consumes accepted B, OPP-03, and WS05-01A only where its selected notice handoff uses that capability. | No separate blocked sub-scope is required at intake. |
| One safe merge or forward-fix unit | Yes - enforcement state, reversal/restoration behavior, and notice outcome must remain compatible during rollout. | Do not split enforcement from its notice contract. |
| One evidence model | Yes - proof centers on action preconditions, idempotency/conflicts, reversal, notice timing/content, and delayed/suppressed outcomes. | One evidence boundary. |
| One semantic review model | Yes - review asks whether each moderation action is authorized, state-correct, reversible where required, and paired with a truthful safe notice outcome. | One review boundary. |
| Safe and useful intermediate state | Yes - C produces a complete source-owned enforcement/notice contract that WS05-03 can later deliver durably. | C is independently acceptable. |

#### WS03-05D cohesion

| Engineering question | Verdict and reasoning | Split implication |
|---|---|---|
| One primary outcome | Yes - enforce minimum-necessary administrative access with governed audited sensitive access. | Keep D whole. |
| One coherent requirement/invariant family | Yes - `ADM-007` and `ADM-015` jointly govern task-scoped exposure, excerpt-first defaults, controlled unmasking/export, anti-cache behavior, and sensitive-read auditing. | No further split. |
| One prerequisite state | Yes - D consumes the accepted B review/finding-facing contract and additionally requires the reusable append-only audit capability from WS09-02 before audited sensitive access is enabled. | D remains one blocked-later child rather than splitting privacy from audit-dependent access. |
| One safe merge or forward-fix unit | Yes - minimum-necessary defaults and controlled unmasking/audit behavior must move together to avoid either unusable review or unaudited sensitive exposure. | Do not split response minimization from governed access. |
| One evidence model | Yes - proof centers on minimized responses, task-scoped authorization, unmask/export denial or allowance, no-store behavior, and durable sensitive-read audit emission. | One evidence boundary. |
| One semantic review model | Yes - review asks whether administrative users see only what the task requires and whether every permitted sensitive read is governed and auditable. | One review boundary. |
| Safe and useful intermediate state | Yes - when its audit prerequisite is accepted, D can be completed without requiring C's enforcement/notice contract. | D is independently acceptable after its prerequisite is satisfied. |

The dependency graph is acyclic: `WS03-05A -> WS03-05B`, then B feeds C and D
as separate consumers. D additionally waits for the applicable reusable WS09-02
audit capability. There is no `WS03-05C -> WS03-05D` dependency because D does
not consume C's enforcement or notice contract. The reusable WS09-02 audit
foundation can be implemented without WS03-05 parent completion; its domain-
specific audit catalog may consume accepted WS03-05 contracts. Likewise,
WS05-03 consumes the accepted safe-notice contract from WS03-05C and is not a
prerequisite for A, B, C, or D.

Minimum-necessary response shaping and controlled unmasking remain together in
D because separating them would create an unsafe intermediate state: excerpting
without a governed access path can prevent legitimate review, while unmasking
without minimum-necessary defaults and durable read auditing preserves the
exposure this control family is meant to remove.

No mandatory deferred follow-up is created by this intake. The WS09 audit
capability needed by D is an ordinary responsibility-specific technical
prerequisite, and the WS05 notice-delivery obligations remain with their existing
parent owner.

## 4. Where The Parent Work Goes

This section accounts for the complete parent scope. Each row assigns one major
responsibility to its primary executable owner and identifies only the boundary
needed to prevent gaps or accidental overlap.

| Parent work | Goes to | Remaining boundary |
|---|---|---|
| Versioned moderation taxonomy; scanner or model identity, configuration, language/context limits, and execution-time attribution | `WS03-05A` | Operational ownership records travel with A; review-case workflow and enforcement policy do not. |
| Finding identity bound to target field and content/canonicalization version, minimal evidence and offsets, deduplication, rescan, stale state, and historical preservation | `WS03-05A` | B consumes accepted finding identity but does not redefine it. |
| Explicit review-case states, links, assignment, merge/reopen/automatic-resolution policy, outcomes, notes, and append-only domain event history | `WS03-05B` | Reusable cross-domain administrative audit persistence and permissions remain WS09-02-owned. |
| Idempotent and conflict-safe case creation, concurrent review, stale decision rejection, and reviewer transition behavior | `WS03-05B` | Enforcement side effects and user notices remain C-owned. |
| Action-scoped moderation permission, target/action/reason/current-state inputs, idempotency, preconditions, external-side-effect state, and reversal/restoration records | `WS03-05C` | C preserves accepted WS03-04 route authorization and does not take over the reusable WS09 audit system. |
| OPP-03 notice timing, safe content, delayed/suppressed state and reason, review next step, and the source-owned notice outcome/handoff contract | `WS03-05C` | Durable delivery, retry, repair, and reconciliation remain WS05-03-owned; C must not invent a delivery policy outside the accepted notice direction. |
| Task-scoped administrative read authorization and minimum-necessary moderation, private-message, review-evidence, audit-context, and export responses | `WS03-05D` | Existing operationally necessary financial/provider context is not automatically excessive; D must classify it from authority rather than remove it indiscriminately. |
| Excerpt-first defaults, controlled unmasking, anti-cache behavior, restricted or denied export, and sensitive-read audit emission | `WS03-05D` | The reusable append-only audit capability and its storage/access guarantees remain WS09-02-owned and must be accepted before D enables audited sensitive access. |
| Stale-evidence proof | `WS03-05A` | Later children retain compatibility with A's evidence identity. |
| Conflicting review and concurrent-case proof | `WS03-05B` | Enforcement conflicts are C-owned. |
| Conflicting enforcement, reversal, delayed/suppressed notice, and safe-content proof | `WS03-05C` | Delivery retry/reconciliation evidence remains WS05-03-owned. |
| Unmask, sensitive-read, excessive-response, cache, and denied-export proof | `WS03-05D` | Final reusable audit append-only evidence remains WS09-02-owned. |
| Final staging, centralized audit, durable delivery, and broader operational verification | Existing WS05, WS08, WS09, and later closure owners | These later evidence obligations do not substitute for the current source and deterministic proof owned by A through D. |

The allocation has no gap or implementation overlap. A owns evidence identity,
B owns reviewer state, C owns enforcement and safe-notice semantics, and D owns
sensitive administrative access. Shared edges are limited to accepted contracts
and compatibility proof. The parent remains incomplete until all four children
are accepted and every later-owned evidence obligation is truthfully preserved.

## 5. What Happens Next

This section identifies the next executable engineering result and whether any
technical fact prevents it from beginning.

`WS03-05A - Versioned moderation taxonomy and finding-evidence lifecycle` is the
next executable work. Its authorization and database prerequisites are accepted,
the current scanner/finding implementation provides a concrete repository-owned
surface to reconcile, and no final provider or runtime fact is required.

There is no blocker to planning WS03-05A. WS03-05D is not currently executable
because the applicable reusable append-only audit capability has not yet been
accepted, but that later responsibility-specific prerequisite does not block A,
B, or C.

## 6. Internal Record

| Detail | Value |
|---|---|
| Parent pass | `WS03-05 - Moderation states, safe notices, and minimum-necessary admin data` |
| Intake outcome | Split into four ordered executable children |
| Accepted baseline | `2fecae7e4b97a13d01265af178f59fc419556ddc` |
| Corrected canonical blueprint used for Stage 0 | Working-tree artifact `docs/production-readiness/planning/program/pickup-lane-master-production-readiness-blueprint.md`, SHA-256 `2e135725fd3b3cd1b481f4133f19a26738d591844c2ad1155db21dfbaa834f85`; this pre-existing blueprint change was not authored during Stage 0 |
| Working branch | `pr/WS03-05` |
| Intake path | `docs/production-readiness/planning/passes/ws03/ws03-05-intake.md` |
| Authority sources | `docs/production-readiness/00-READ-ME-FIRST.md`; `docs/production-readiness/01-PROGRAM-CONTEXT.md`; `docs/production-readiness/audit-research/pickup-lane-master-production-readiness-checklist.md`; `docs/production-readiness/audit-research/audit-part-2.md`; `docs/production-readiness/planning/program/pickup-lane-production-readiness-remediation-plan-final.md`; `docs/production-readiness/planning/program/pickup-lane-master-production-readiness-blueprint.md`; `docs/production-readiness/decisions/pickup-lane-decision-packet-4-approved.md`; applicable governance, workflow, template, accepted prerequisite artifacts, engineering/testing standards, current source, and current trusted evidence |
| Execution-register state | `WS03-05` is not yet decomposed or implemented. `WS03-04` and the applicable `WS04-02` children are accepted. `WS05-01A` is accepted; `WS05-01B` remains deferred for unrelated final worker-hosting proof. `WS09-02` has no accepted decomposition or reusable append-only capability yet. |
| Approved decisions and prerequisites | OPP-03 notice direction and OPP-11 append-only audit direction are approved. Accepted WS03-04 authorization, WS04-02 transaction/invariant, EN-02 correlation/redaction, and WS05-01A provider-independent job/handoff contracts are available where applicable. |
| Child order | `WS03-05A -> WS03-05B`; after B, `WS03-05C` and `WS03-05D` are separate consumers. D additionally waits for the applicable accepted reusable append-only audit capability produced under `WS09-02`. |
| Child allocation | `WS03-05A`: ADM-009/ADM-010 taxonomy and finding evidence; `WS03-05B`: ADM-012 review-case lifecycle; `WS03-05C`: ADM-013/ADM-014 enforcement and safe notices; `WS03-05D`: ADM-007/ADM-015 minimum-necessary and audited sensitive access |
| Dependency-integrity result | No whole-parent cycle. The child graph is `A -> B`, `B -> C`, and `B -> D`, with the applicable reusable WS09-02 audit capability also required by D. There is no `C -> D` edge. WS09-02 reusable audit foundation is not blocked by WS03-05 parent completion; domain-specific audit work may consume accepted WS03-05 contracts. WS05-03 consumes C's notice contract and is not a blanket prerequisite for WS03-05. |
| Final-infrastructure classification | A through D are provider-independent repository work. No mandatory final-infrastructure follow-up is created. Final centralized audit, durable delivery/runtime, staging, and operational evidence remains with existing later owners. |
| Mandatory deferred follow-up created by this intake | None |
| Current blockers | None for WS03-05A. WS03-05D is blocked until the applicable reusable append-only audit capability under WS09-02 is accepted. |
| Proposed canonical plan path | `docs/production-readiness/planning/passes/ws03/ws03-05a-versioned-moderation-taxonomy-finding-evidence-lifecycle.md` |
| Proposed requirement declaration | `backend/tests/support/requirements/ws03_05a.json` |
| Proposed trusted test or verification location | `backend/tests/domains/moderation_taxonomy_finding_evidence/` |
| Exact next allowed action | Stop after Stage 0 and present this intake for review with its frozen SHA-256. When Gate A is separately authorized, first verify that digest and the recorded corrected-blueprint digest, confirm the understood pre-existing blueprint changes, and create only the canonical WS03-05A plan at the proposed path; do not change source, tests, or the execution register. |
